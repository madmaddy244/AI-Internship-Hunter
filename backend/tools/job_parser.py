from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from backend.models import CandidateProfile
from backend.services.matching_service import add_match

SKILL_TERMS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "C++",
    "SQL",
    "React",
    "FastAPI",
    "Node.js",
    "Machine Learning",
    "Deep Learning",
    "PyTorch",
    "TensorFlow",
    "scikit-learn",
    "LLMs",
    "Generative AI",
    "RAG",
    "NLP",
    "Computer Vision",
    "Data Science",
    "Pandas",
    "NumPy",
    "Docker",
    "Kubernetes",
    "AWS",
    "GCP",
    "Azure",
    "Git",
    "Linux",
]


def _contains(text: str, term: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(term.casefold())}(?![a-z0-9])"
    return bool(re.search(pattern, text.casefold()))


def _role_company(title: str) -> tuple[str, str]:
    patterns = [
        r"(?i)^(?P<role>.+?\bintern(?:ship)?\b.*?)\s+(?:at|@|[-–|])\s+(?P<company>.+)$",
        r"(?i)^(?P<company>.+?)\s+[-–|]\s+(?P<role>.+?\bintern(?:ship)?\b.*)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, title.strip())
        if match:
            return match.group("role").strip(" -–|"), match.group("company").strip(" -–|")
    return title.strip() or "Internship role", "Company not identified"


def _likely_direct_application_url(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.casefold()
    path = parsed.path.casefold()
    known_job_boards = (
        "jobs.lever.co",
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.ashbyhq.com",
        "careers.smartrecruiters.com",
    )
    if any(host == domain or host.endswith("." + domain) for domain in known_job_boards):
        return url
    if any(marker in host for marker in ("careers.", "jobs.")):
        return url
    if any(marker in path for marker in ("/careers/", "/career/", "/jobs/", "/job/")):
        return url
    return None


def normalize_search_result(result: dict[str, Any]) -> dict[str, Any] | None:
    title = str(result.get("title") or "").strip()[:240]
    url = str(result.get("url") or "").strip()
    content = str(result.get("raw_content") or result.get("content") or "").strip()
    if len(content) < 40:
        content = title
    combined = f"{title}\n{content}"
    if not re.search(r"(?i)\b(intern(ship)?|summer associate|student placement)\b", combined):
        return None
    role, company = _role_company(title)
    listed_skills = [skill for skill in SKILL_TERMS if _contains(combined, skill)]

    requirements: list[str] = []
    for line in content.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if (
            cleaned
            and len(cleaned) <= 220
            and len(cleaned.split()) <= 30
            and (
                re.search(r"(?i)\b(require|must have|experience with|proficien|familiarity)\b", cleaned)
                or any(_contains(cleaned, skill) for skill in listed_skills)
            )
        ):
            if cleaned.casefold() not in {item.casefold() for item in requirements}:
                requirements.append(cleaned)
        if len(requirements) >= 8:
            break
    if not requirements:
        requirements = listed_skills[:8]

    location_match = re.search(
        r"(?i)\b(remote|hyderabad|bengaluru|bangalore|mumbai|pune|delhi|india|"
        r"chennai|noida|gurugram|gurgaon)\b",
        combined,
    )
    location = location_match.group(0).title() if location_match else "Location not specified"
    remote = _contains(combined, "remote")
    deadline_match = re.search(
        r"(?i)(?:deadline|apply by|applications close|closing date)\s*[:\-]?\s*"
        r"([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        combined,
    )
    salary_match = re.search(
        r"(?i)(?:₹|INR|USD|\$)\s*[\d,]+(?:\s*[-–]\s*(?:₹|INR|USD|\$)?\s*[\d,]+)?"
        r"(?:\s*(?:per|/)\s*(?:month|hour|year|annum|week))?",
        combined,
    )
    host = urlparse(url).hostname if url else None
    identity = f"{url.casefold() or title.casefold()}|{company.casefold()}|{role.casefold()}"
    job_id = "job_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:18]
    return {
        "id": job_id,
        "company": company or "Company not identified",
        "role": role,
        "location": location,
        "remote": remote,
        "description": content[:5000],
        "requirements": requirements,
        "skills": listed_skills,
        "salary": salary_match.group(0).strip() if salary_match else None,
        "deadline": deadline_match.group(1).strip() if deadline_match else None,
        "source": f"Tavily search · {host}" if host else "Tavily search",
        "application_url": _likely_direct_application_url(url),
        "date_found": datetime.now(timezone.utc),
        "match_score": 0,
        "matched_skills": [],
        "missing_skills": [],
        "match_summary": "",
    }


def normalize_and_match(
    results: list[dict[str, Any]], profile: CandidateProfile, limit: int
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        job = normalize_search_result(result)
        if not job:
            continue
        dedupe_key = "|".join(
            (
                re.sub(r"\W+", "", job["company"].casefold()),
                re.sub(r"\W+", "", job["role"].casefold()),
                re.sub(r"\W+", "", job["location"].casefold()),
            )
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(add_match(profile, job))
        if len(normalized) >= limit:
            break
    return normalized
