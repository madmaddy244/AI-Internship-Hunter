from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api.dependencies import session_key
from backend.database import connect, profile_state, read_profile, save_profile
from backend.models import ProfileInput, ProfileState
from backend.services.activity_service import record_activity

router = APIRouter()


@router.get("/profile", response_model=ProfileState, tags=["profile"])
def get_profile(
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> ProfileState:
    with connect() as connection:
        return ProfileState.model_validate(profile_state(connection, session_id))


@router.put("/profile", response_model=ProfileState, tags=["profile"])
def update_profile(
    body: ProfileInput,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> ProfileState:
    with connect() as connection:
        save_profile(connection, session_id, body)
        record_activity(connection, session_id, "Candidate profile updated", "profile")
        return ProfileState.model_validate(profile_state(connection, session_id))
