from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api.dependencies import session_key
from backend.database import connect, read_profile
from backend.models import AssistantInput, AssistantReply
from backend.services.activity_service import record_activity
from backend.services.agent import answer_assistant
from backend.services.application_service import list_applications
from backend.services.nebius_client import NebiusError, model_name

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/assistant/chat", response_model=AssistantReply, tags=["agent"])
def ask(
    body: AssistantInput,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> AssistantReply:
    with connect() as connection:
        profile = read_profile(connection, session_id)
        jobs = [
            json.loads(row["data_json"])
            for row in connection.execute(
                "SELECT data_json FROM internships WHERE session_id = ? "
                "ORDER BY rowid DESC LIMIT 8",
                (session_id,),
            ).fetchall()
        ]
        applications = list_applications(connection, session_id)
    try:
        reply = answer_assistant(body.message, profile, jobs, applications)
    except NebiusError as error:
        raise HTTPException(
            status_code=error.status_code, detail=error.public_message
        ) from None
    except Exception as error:
        logger.warning("Assistant response failed (%s)", type(error).__name__)
        raise HTTPException(
            status_code=502, detail="Nemotron could not answer this question. Try again."
        ) from None
    if not reply:
        raise HTTPException(status_code=502, detail="Nemotron returned an empty answer.")
    with connect() as connection:
        record_activity(
            connection,
            session_id,
            "AI assistant answered a profile and internship question",
            "assistant",
        )
    return AssistantReply(reply=reply, ai_used=True, model=model_name())
