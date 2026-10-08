from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from backend.api.dependencies import session_key
from backend.config import (
    DEFAULT_NEBIUS_MODEL,
    ai_enabled,
    ai_model,
    search_enabled,
)
from backend.database import connect
from backend.models import Activity, Dashboard, HealthStatus, RuntimeStatus

router = APIRouter()


@router.get("/healthz", response_model=HealthStatus, tags=["health"])
def health_check() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/status", response_model=RuntimeStatus, tags=["health"])
def runtime_status() -> RuntimeStatus:
    configured_ai = ai_enabled()
    configured_search = search_enabled()
    if configured_ai and configured_search:
        message = "App setup is complete. Nebius AI and Tavily live search are connected."
    elif configured_ai:
        message = (
            "The app is built and ready. Only live search needs setup: add TAVILY_API_KEY in Replit Secrets. "
            "AI writing is already connected."
        )
    elif configured_search:
        message = (
            "The app is built and ready. Only AI writing needs setup: add NEBIUS_API_KEY in Replit Secrets. "
            "Live search is already connected."
        )
    else:
        message = (
            "The app is built and ready. The only remaining setup is adding provider API keys in Replit Secrets: "
            "NEBIUS_API_KEY for AI writing and TAVILY_API_KEY for live internship search."
        )
    return RuntimeStatus(
        ai_configured=configured_ai,
        ai_provider="Nebius Token Factory · NVIDIA Nemotron",
        model=ai_model() if configured_ai else DEFAULT_NEBIUS_MODEL,
        search_configured=configured_search,
        search_provider="Tavily" if configured_search else "Not configured",
        message=message,
    )


@router.get("/dashboard", response_model=Dashboard, tags=["dashboard"])
def dashboard(
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> Dashboard:
    with connect() as connection:
        internships_found = connection.execute(
            "SELECT COUNT(*) FROM internships WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        counts = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM applications "
                "WHERE session_id = ? GROUP BY status",
                (session_id,),
            ).fetchall()
        }
        activity_rows = connection.execute(
            "SELECT id, message, created_at, kind FROM activities "
            "WHERE session_id = ? ORDER BY created_at DESC LIMIT 8",
            (session_id,),
        ).fetchall()
    activities = [Activity.model_validate(dict(row)) for row in activity_rows]
    return Dashboard(
        internships_found=internships_found,
        saved=counts.get("saved", 0),
        applications=sum(count for status, count in counts.items() if status != "saved"),
        interviews=counts.get("interview", 0),
        pending=counts.get("applied", 0) + counts.get("assessment", 0),
        recent_activity=activities,
    )
