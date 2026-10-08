from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from backend.api.dependencies import session_key
from backend.config import ai_enabled, search_enabled
from backend.database import connect, read_profile
from backend.models import Internship, SearchInput, SearchResult
from backend.services.activity_service import record_activity
from backend.services.agent import explain_matches, select_search_tool
from backend.services.matching_service import add_match
from backend.services.nebius_client import NebiusError
from backend.tools.demo_data import SAMPLE_CANDIDATE_PROFILE, demo_internships
from backend.tools.job_parser import normalize_and_match
from backend.tools.search_tool import SearchError, search_internships

logger = logging.getLogger(__name__)
router = APIRouter()


def _store_jobs(connection: Any, session_id: str, jobs: list[dict[str, Any]]) -> None:
    for job in jobs:
        connection.execute(
            """
            INSERT INTO internships (id, session_id, data_json) VALUES (?, ?, ?)
            ON CONFLICT(session_id, id) DO UPDATE SET data_json = excluded.data_json
            """,
            (job["id"], session_id, json.dumps(job, ensure_ascii=False, default=str)),
        )


def _summary_message(data_mode: str, count: int, ai_used: bool, ai_note: str = "") -> str:
    if data_mode == "demo":
        label = "Demo Mode returned clearly labeled sample listings"
    else:
        label = "Tavily returned live web search results"
    if not count:
        return f"{label}, but no internship listings could be normalized from those results."
    if ai_used:
        return (
            f"{label}. Nemotron was used for search planning and/or match explanations; "
            "the deterministic fit factors remain visible."
        )
    if ai_note:
        return f"{label}. Deterministic match factors are shown; Nemotron was not used: {ai_note}"
    return f"{label}. Deterministic match factors are shown; Nemotron is not configured."


@router.get("/internships", response_model=list[Internship], tags=["internships"])
def list_internships(
    request: Request,
    response: Response,
    q: str | None = Query(default=None, max_length=240),
    limit: int = Query(default=50, ge=1, le=100),
    session_id: str = Depends(session_key),
) -> list[Internship]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT data_json FROM internships WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    jobs = [Internship.model_validate_json(row["data_json"]) for row in rows]
    if q:
        needle = q.casefold().strip()
        jobs = [
            job
            for job in jobs
            if needle
            in " ".join(
                [job.company, job.role, job.location, job.description, *job.skills]
            ).casefold()
        ]
    jobs.sort(key=lambda job: (job.match_score, job.date_found), reverse=True)
    return jobs[:limit]


@router.post("/internships/search", response_model=SearchResult, tags=["internships", "agent"])
def search(
    body: SearchInput,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> SearchResult:
    with connect() as connection:
        stored_profile = read_profile(connection, session_id)

    ai_used = False
    ai_note = ""
    data_mode = "demo" if body.demo_mode else "live"
    use_sample_profile = body.demo_mode and body.demo_sample_profile
    profile = SAMPLE_CANDIDATE_PROFILE if use_sample_profile else stored_profile
    if body.demo_mode:
        jobs = demo_internships(
            body.query, body.location, body.remote_only, profile, body.max_results
        )
        if ai_enabled() and jobs:
            try:
                explanations = explain_matches(profile, jobs)
                for job in jobs:
                    job["match_summary"] = explanations.get(
                        job["id"], job["match_summary"]
                    )
                ai_used = bool(explanations)
            except NebiusError as error:
                ai_note = error.public_message
                logger.warning("Nemotron demo analysis was unavailable (HTTP %s)", error.status_code)
        with connect() as connection:
            _store_jobs(connection, session_id, jobs)
            record_activity(
                connection,
                session_id,
                f"Demo Mode matched {len(jobs)} sample internship listing(s)",
                "search",
            )
    else:
        if not search_enabled():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Live search is not configured. Add TAVILY_API_KEY, or turn on clearly labeled Demo Mode."
                ),
            )
        query = f"{body.query} internship"
        location = body.location
        remote_only = body.remote_only
        if ai_enabled():
            try:
                criteria = select_search_tool(
                    body.query, body.location, body.remote_only, profile
                )
                query = criteria["query"]
                location = criteria["location"]
                remote_only = criteria["remote_only"]
                ai_used = True
                with connect() as connection:
                    record_activity(
                        connection,
                        session_id,
                        "Nemotron selected internship search criteria",
                        "agent",
                    )
            except NebiusError as error:
                ai_note = error.public_message
                logger.warning("Nemotron search tool selection was unavailable (HTTP %s)", error.status_code)
        query_parts = [query]
        if location:
            query_parts.append(location)
        if remote_only:
            query_parts.append("remote")
        try:
            results = search_internships(" ".join(query_parts), body.max_results)
        except SearchError as error:
            raise HTTPException(status_code=error.status_code, detail=error.public_message) from None
        jobs = normalize_and_match(results, profile, body.max_results)
        if remote_only:
            jobs = [job for job in jobs if job["remote"]]
        if ai_enabled() and jobs and not ai_note:
            try:
                explanations = explain_matches(profile, jobs)
                for job in jobs:
                    job["match_summary"] = explanations.get(
                        job["id"], job["match_summary"]
                    )
                ai_used = ai_used or bool(explanations)
            except NebiusError as error:
                ai_note = error.public_message
                logger.warning("Nemotron match analysis was unavailable (HTTP %s)", error.status_code)
        with connect() as connection:
            _store_jobs(connection, session_id, jobs)
            record_activity(
                connection,
                session_id,
                f"Live internship search completed: {len(jobs)} listing(s) normalized",
                "search",
            )

    return SearchResult(
        jobs=[Internship.model_validate(job) for job in jobs],
        count=len(jobs),
        data_mode=data_mode,  # type: ignore[arg-type]
        demo_sample_profile=use_sample_profile,
        ai_used=ai_used,
        message=_summary_message(data_mode, len(jobs), ai_used, ai_note),
    )


@router.get("/internships/{internship_id}", response_model=Internship, tags=["internships"])
def get_internship(
    internship_id: str,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> Internship:
    with connect() as connection:
        row = connection.execute(
            "SELECT data_json FROM internships WHERE session_id = ? AND id = ?",
            (session_id, internship_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Internship not found in this session.")
    return Internship.model_validate_json(row["data_json"])
