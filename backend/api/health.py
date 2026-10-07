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
        message = "Nebius Token Factory and Tavily are configured."
    elif configured_ai:
        message = "Nemotron is configured. Live search needs TAVILY_API_KEY; sample listings are available in Demo Mode."
    elif configured_search:
        message = "Tavily is configured. Nemotron AI features need NEBIUS_API_KEY."
    else:
        message = (
            "Nemotron and live search are not configured. Add NEBIUS_API_KEY and TAVILY_API_KEY, "
            "or use clearly labeled Demo Mode."
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
