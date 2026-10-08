from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.models import CandidateProfile
from backend.services.matching_service import add_match

SAMPLE_CANDIDATE_PROFILE = CandidateProfile(
    name="Sample candidate",
    education=["BSc Computer Science (sample)"],
    skills=["Python", "SQL", "Git"],
    programming_languages=["Python"],
    frameworks=["FastAPI", "scikit-learn"],
    ai_ml_skills=["Machine Learning", "Computer Vision"],
    cloud_skills=[],
    projects=["Sample image-classification project (fictional)"],
    experience=["Sample student research experience (fictional)"],
    certifications=[],
    locations=["Hyderabad", "Bengaluru", "Remote, India"],
    preferred_roles=[
        "Machine Learning Intern",
        "AI Engineering Intern",
        "Computer Vision Intern",
    ],
)

SAMPLE_LISTINGS: list[dict[str, Any]] = [
    {
        "id": "demo-northstar-ml",
        "company": "Northstar Research (sample)",
        "role": "Machine Learning Intern",
        "location": "Hyderabad, India",
        "remote": False,
        "description": (
            "Sample listing for a machine learning internship. Practice building Python data "
            "pipelines, evaluating scikit-learn models, and documenting experiments with a "
            "research mentor. This is fictional demonstration data, not an open position."
        ),
        "requirements": ["Python", "Machine Learning", "scikit-learn", "SQL"],
        "skills": ["Python", "Machine Learning", "scikit-learn", "SQL"],
        "salary": None,
        "deadline": None,
        "source": "Demo sample dataset · fictional listing",
        "application_url": None,
    },
    {
        "id": "demo-lumen-ai",
        "company": "Lumen AI Studio (sample)",
        "role": "Generative AI Engineering Intern",
        "location": "Remote, India",
        "remote": True,
        "description": (
            "Sample listing for a generative AI internship. Explore retrieval-augmented "
            "generation prototypes using Python, LLM APIs, and FastAPI. This is fictional "
            "demonstration data, not an open position."
        ),
        "requirements": ["Python", "LLMs", "RAG", "FastAPI", "Git"],
        "skills": ["Python", "LLMs", "RAG", "FastAPI", "Git"],
        "salary": None,
        "deadline": None,
        "source": "Demo sample dataset · fictional listing",
        "application_url": None,
    },
    {
        "id": "demo-cobalt-vision",
        "company": "Cobalt Vision Lab (sample)",
        "role": "Computer Vision Intern",
        "location": "Bengaluru, India",
        "remote": False,
        "description": (
            "Sample listing for a computer vision internship. Learn image data preparation, "
            "PyTorch model evaluation, and reproducible experiment workflows. This is fictional "
            "demonstration data, not an open position."
        ),
        "requirements": ["Python", "Computer Vision", "PyTorch", "Docker"],
        "skills": ["Python", "Computer Vision", "PyTorch", "Docker"],
        "salary": None,
        "deadline": None,
        "source": "Demo sample dataset · fictional listing",
        "application_url": None,
    },
]


def demo_internships(
    query: str, location: str, remote_only: bool, profile: CandidateProfile, limit: int
) -> list[dict[str, Any]]:
    searchable = f"{query} {location}".casefold()
    words = [
        word.strip(".,!?")
        for word in searchable.split()
        if len(word.strip(".,!?")) >= 3
        and word.casefold() not in {"internship", "internships", "intern", "jobs"}
    ]
    matches = []
    for sample in SAMPLE_LISTINGS:
        if remote_only and not sample["remote"]:
            continue
        if location and location.casefold() not in sample["location"].casefold():
            if not (sample["remote"] and "india" in location.casefold()):
                continue
        text = " ".join(
            [
                sample["company"],
                sample["role"],
                sample["location"],
                sample["description"],
                *sample["skills"],
            ]
        ).casefold()
        if words and not any(word in text for word in words):
            continue
        job = {
            **sample,
            "date_found": datetime.now(timezone.utc),
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "match_summary": "",
        }
        matches.append(add_match(profile, job))
    return matches[:limit]
