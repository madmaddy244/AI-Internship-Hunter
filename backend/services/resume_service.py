from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.config import ai_enabled
from backend.models import CandidateProfile
from backend.services.nebius_client import NebiusError, complete

logger = logging.getLogger(__name__)

PROFILE_FIELDS = {
    "name",
    "email",
    "education",
    "skills",
    "programming_languages",
    "frameworks",
    "ai_ml_skills",
    "cloud_skills",
    "projects",
    "experience",
    "certifications",
    "locations",
    "preferred_roles",
}

SKILL_GROUPS = {
    "programming_languages": [
        "Python",
        "JavaScript",
        "TypeScript",
        "Java",
        "C++",
        "C#",
        "Go",
        "Rust",
        "SQL",
        "R",
    ],
    "frameworks": [
        "React",
        "Node.js",
        "FastAPI",
        "Django",
        "Flask",
        "TensorFlow",
        "PyTorch",
        "scikit-learn",
        "Pandas",
        "NumPy",
        "Docker",
        "Kubernetes",
    ],
    "ai_ml_skills": [
        "Machine Learning",
        "Deep Learning",
        "Natural Language Processing",
        "Computer Vision",
        "LLMs",
        "Generative AI",
        "RAG",
        "Prompt Engineering",
        "MLOps",
        "Data Science",
    ],
    "cloud_skills": ["AWS", "Google Cloud", "Azure", "GCP"],
}

SECTION_NAMES = {
    "education": ("education", "academic background"),
    "projects": ("projects", "personal projects"),
    "experience": ("experience", "work experience", "internships", "employment"),
    "certifications": ("certifications", "certificates", "licenses"),
}


def _items(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result = []
    seen = set()
    for item in value:
        if isinstance(item, str) and item.strip():
            clean = item.strip()[:500]
            if clean.casefold() not in seen:
                seen.add(clean.casefold())
                result.append(clean)
    return result[:30]


def normalize_model_profile(value: dict[str, Any]) -> CandidateProfile:
    data = {field: value.get(field) for field in PROFILE_FIELDS if field in value}
    for field in PROFILE_FIELDS - {"name", "email"}:
        data[field] = _items(data.get(field))
    data["name"] = data.get("name") if isinstance(data.get("name"), str) else ""
    email = data.get("email")
    data["email"] = email.strip() if isinstance(email, str) else None
    return CandidateProfile.model_validate(data)


def deterministic_profile_from_text(text: str) -> CandidateProfile:
    lines = [line.strip(" \t•*-") for line in text.splitlines() if line.strip()]
    email_match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I)
    labeled_name = re.search(r"(?im)^\s*name\s*[:\-]\s*(.+?)\s*$", text)
    first_line = next(
        (
            line
            for line in lines
            if len(line) <= 80
            and "@" not in line
            and not re.match(
                r"(?i)^(resume|curriculum vitae|education|skills|experience|projects|certifications?)$",
                line,
            )
        ),
        "",
    )
    result: dict[str, Any] = {
        "name": (labeled_name.group(1) if labeled_name else first_line)[:120],
        "email": email_match.group(0) if email_match else None,
        "education": [],
        "skills": [],
        "programming_languages": [],
        "frameworks": [],
        "ai_ml_skills": [],
        "cloud_skills": [],
        "projects": [],
        "experience": [],
        "certifications": [],
        "locations": [],
        "preferred_roles": [],
    }
    lower_text = text.casefold()
    for field, vocabulary in SKILL_GROUPS.items():
        result[field] = [
            skill
            for skill in vocabulary
            if re.search(rf"(?<![a-z0-9]){re.escape(skill.casefold())}(?![a-z0-9])", lower_text)
        ]
    result["skills"] = list(
        dict.fromkeys(
            result["programming_languages"]
            + result["frameworks"]
            + result["ai_ml_skills"]
            + result["cloud_skills"]
        )
    )

    active_section: str | None = None
    section_pattern = re.compile(
        r"^(education|academic background|projects|personal projects|experience|work experience|"
        r"internships|employment|certifications?|certificates|licenses|skills?|technical skills|"
        r"core competencies|summary|professional summary|objective|contact)\s*:?\s*$",
        re.I,
    )
    for line in lines:
        match = section_pattern.match(line)
        if match:
            heading = match.group(1).casefold()
            active_section = next(
                (key for key, names in SECTION_NAMES.items() if heading in names),
                None,
            )
            continue
        if active_section and len(line) >= 3:
            result[active_section].append(line[:500])

    labeled_location = re.search(r"(?im)^\s*(?:location|based in)\s*[:\-]\s*(.+?)\s*$", text)
    if labeled_location:
        result["locations"] = [labeled_location.group(1)[:120]]

    return normalize_model_profile(result)


def profile_from_resume(text: str) -> tuple[CandidateProfile, str, bool]:
    if not ai_enabled():
        return deterministic_profile_from_text(text), "basic_pdf_text", False
    try:
        response = complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract a candidate profile from the supplied resume. Use only facts "
                        "explicitly present in its text; do not infer skills, dates, seniority, "
                        "locations, or achievements. Use empty strings, null email, or empty arrays "
                        "when information is absent. Return one JSON object with exactly these keys: "
                        "name, email, education, skills, programming_languages, frameworks, "
                        "ai_ml_skills, cloud_skills, projects, experience, certifications, "
                        "locations, preferred_roles."
                    ),
                },
                {"role": "user", "content": text[:30_000]},
            ],
            max_tokens=1600,
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise ValueError("Nemotron returned a response without a JSON profile.")
        profile = normalize_model_profile(json.loads(match.group(0)))
        return profile, "nemotron", True
    except NebiusError:
        raise
    except Exception as error:
        logger.warning("Nemotron resume extraction could not be parsed (%s)", type(error).__name__)
        return deterministic_profile_from_text(text), "basic_pdf_text", False
