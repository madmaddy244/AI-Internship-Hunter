from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.config import ai_enabled
from backend.models import CandidateProfile
from backend.services.nebius_client import NebiusError, complete

logger = logging.getLogger(__name__)

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_internships",
        "description": (
            "Choose a concise web-search query for current internships. Use the user's "
            "skills and requested role/location, but do not claim that a role exists."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms for current internship listings"},
                "location": {"type": "string", "description": "Requested location, or empty string"},
                "remote_only": {"type": "boolean"},
            },
            "required": ["query", "location", "remote_only"],
            "additionalProperties": False,
        },
    },
}


def _extract_json(content: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise ValueError("Nemotron did not return structured search criteria.")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Nemotron returned invalid search criteria.")
    return value


def select_search_tool(
    query: str,
    location: str,
    remote_only: bool,
    profile: CandidateProfile,
) -> dict[str, Any]:
    response = complete(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an internship search agent. Use the search_internships tool "
                    "to search the web. Improve the query using only relevant candidate skills. "
                    "Respect the user's location and remote-only choice. Do not invent openings."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "request": query,
                        "location": location,
                        "remote_only": remote_only,
                        "candidate_profile": profile.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        tools=[SEARCH_TOOL],
        tool_choice={"type": "function", "function": {"name": "search_internships"}},
        max_tokens=350,
        temperature=0.1,
    )
    tool_calls = response.choices[0].message.tool_calls or []
    call = next(
        (
            tool_call
            for tool_call in tool_calls
            if tool_call.function.name == "search_internships"
        ),
        None,
    )
    if not call:
        raise NebiusError(502, "Nemotron did not select the internship search tool. Retry the search.")
    try:
        arguments = json.loads(call.function.arguments)
    except (TypeError, json.JSONDecodeError):
        raise NebiusError(502, "Nemotron returned invalid search criteria. Retry the search.") from None
    chosen_query = arguments.get("query")
    if not isinstance(chosen_query, str) or not chosen_query.strip():
        raise NebiusError(502, "Nemotron returned an empty search query. Retry the search.")
    return {
        "query": chosen_query.strip()[:240],
        "location": str(arguments.get("location") or location).strip()[:120],
        "remote_only": bool(arguments.get("remote_only", remote_only)),
    }


def explain_matches(
    profile: CandidateProfile, jobs: list[dict[str, Any]]
) -> dict[str, str]:
    if not ai_enabled() or not jobs:
        return {}
    evidence = [
        {
            "id": job["id"],
            "role": job["role"],
            "company": job["company"],
            "description": job["description"][:1200],
            "skills": job["skills"],
            "matched_skills": job["matched_skills"],
            "missing_skills": job["missing_skills"],
        }
        for job in jobs[:12]
    ]
    response = complete(
        messages=[
            {
                "role": "system",
                "content": (
                    "Explain candidate-to-internship fit using only the supplied profile and "
                    "job evidence. Never invent experience, skills, qualifications, or outcomes. "
                    "Return one JSON object with an explanations array; each entry has id and "
                    "a concise summary of strengths and, when relevant, gaps. Do not include "
                    "private reasoning."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"candidate_profile": profile.model_dump(mode="json"), "jobs": evidence},
                    ensure_ascii=False,
                ),
            },
        ],
        max_tokens=1200,
        temperature=0.1,
    )
    content = response.choices[0].message.content or ""
    try:
        data = _extract_json(content)
        entries = data.get("explanations", [])
        valid_ids = {job["id"] for job in jobs}
        result = {}
        if isinstance(entries, list):
            for entry in entries:
                if (
                    isinstance(entry, dict)
                    and entry.get("id") in valid_ids
                    and isinstance(entry.get("summary"), str)
                    and entry["summary"].strip()
                ):
                    result[entry["id"]] = entry["summary"].strip()[:700]
        return result
    except (ValueError, json.JSONDecodeError, TypeError) as error:
        logger.warning("Nemotron match explanation could not be parsed (%s)", type(error).__name__)
        raise NebiusError(502, "Nemotron returned an unreadable match explanation.") from None


def answer_assistant(
    message: str,
    profile: CandidateProfile,
    jobs: list[dict[str, Any]],
    applications: list[dict[str, Any]],
) -> str:
    response = complete(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a practical internship application assistant. Answer the user's "
                    "question using only the supplied candidate profile, saved opportunities, "
                    "and applications. Never invent resume facts or claim an application was "
                    "submitted. If information is missing, say so and ask a focused follow-up. "
                    "Keep the answer concise. Do not reveal private reasoning."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": message,
                        "candidate_profile": profile.model_dump(mode="json"),
                        "internships": jobs[:8],
                        "applications": applications[:8],
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ],
        max_tokens=800,
        temperature=0.3,
    )
    return (response.choices[0].message.content or "").strip()
