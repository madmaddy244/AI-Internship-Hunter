from __future__ import annotations

import re
from typing import Any

from backend.models import CandidateProfile, Internship


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", value.casefold()).strip()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        normalized = _key(cleaned)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(cleaned)
    return result


def _phrase_in_text(phrase: str, text: str) -> bool:
    normalized_phrase = _key(phrase)
    normalized_text = _key(text)
    if not normalized_phrase:
        return False
    return bool(
        re.search(
            rf"(?<![a-z0-9+#.]){re.escape(normalized_phrase)}(?![a-z0-9+#.])",
            normalized_text,
        )
    )


def calculate_match(
    profile: CandidateProfile, job: dict[str, Any] | Internship
) -> dict[str, Any]:
    job_data = job.model_dump(mode="json") if isinstance(job, Internship) else job
    profile_data = profile.model_dump(mode="json")
    candidate_skills = _unique(
        profile_data.get("skills", [])
        + profile_data.get("programming_languages", [])
        + profile_data.get("frameworks", [])
        + profile_data.get("ai_ml_skills", [])
        + profile_data.get("cloud_skills", [])
    )
    job_skills = _unique(job_data.get("skills", []))
    job_text = " ".join(
        [
            job_data.get("role", ""),
            job_data.get("description", ""),
            *job_data.get("requirements", []),
        ]
    ).casefold()

    matched = [
        skill
        for skill in candidate_skills
        if _key(skill)
        and any(
            _key(skill) == _key(job_skill)
            or _phrase_in_text(skill, job_skill)
            for job_skill in job_skills
        )
    ]
    matched_keys = {_key(skill) for skill in matched}
    missing = [
        skill
        for skill in job_skills
        if not any(
            _key(skill) == candidate_key
            or _key(skill) in candidate_key
            or candidate_key in _key(skill)
            for candidate_key in matched_keys
        )
    ]

    skill_score = round(100 * len(matched) / len(job_skills)) if job_skills else 50
    preferred_roles = profile_data.get("preferred_roles", [])
    role_score = (
        100
        if any(
            _phrase_in_text(role, job_data.get("role", ""))
            or _phrase_in_text(job_data.get("role", ""), role)
            for role in preferred_roles
        )
        else 35
        if preferred_roles
        else 50
    )
    education_text = " ".join(profile_data.get("education", [])).casefold()
    education_score = (
        100
        if education_text
        and any(
            _phrase_in_text(term, education_text)
            and _phrase_in_text(term, job_text)
            for term in ("computer science", "engineering", "data science", "statistics")
        )
        else 60
        if education_text
        else 50
    )
    locations = profile_data.get("locations", [])
    location_text = job_data.get("location", "").casefold()
    location_score = (
        100
        if job_data.get("remote") or any(location.casefold() in location_text for location in locations if location)
        else 35
        if locations
        else 50
    )
    experience_text = " ".join(profile_data.get("experience", [])).casefold()
    experience_score = (
        100
        if experience_text and any(_key(skill) in _key(experience_text) for skill in matched)
        else 40
        if experience_text
        else 50
    )
    score = round(
        skill_score * 0.55
        + role_score * 0.20
        + education_score * 0.10
        + location_score * 0.10
        + experience_score * 0.05
    )
    summary = (
        f"Deterministic fit: {len(matched)} of {len(job_skills)} listed skills matched "
        f"({skill_score}%); role {role_score}%, education {education_score}%, "
        f"location {location_score}%, experience {experience_score}%. "
        "Nemotron explanation unavailable until configured."
    )
    return {
        "match_score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "match_summary": summary,
    }


def add_match(profile: CandidateProfile, job: dict[str, Any]) -> dict[str, Any]:
    return {**job, **calculate_match(profile, job)}
