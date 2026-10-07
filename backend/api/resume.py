from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile

from backend.api.dependencies import session_key
from backend.database import connect, profile_state, save_profile
from backend.models import ResumeResult
from backend.services.activity_service import record_activity
from backend.services.nebius_client import NebiusError
from backend.services.resume_service import profile_from_resume
from backend.tools.resume_tool import ResumeParseError, extract_pdf_text

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/resume", response_model=ResumeResult, tags=["profile"])
async def upload_resume(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    session_id: str = Depends(session_key),
) -> ResumeResult:
    filename = (file.filename or "").casefold()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF resume.")
    try:
        file_bytes = await file.read(10 * 1024 * 1024 + 1)
        resume_text = extract_pdf_text(file_bytes)
        profile, method, ai_configured = profile_from_resume(resume_text)
    except ResumeParseError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except NebiusError as error:
        raise HTTPException(
            status_code=error.status_code, detail=error.public_message
        ) from None
    except Exception as error:
        logger.error("Resume processing failed (%s)", type(error).__name__)
        raise HTTPException(
            status_code=502,
            detail="The resume was read, but profile extraction failed. Try again or edit the profile manually.",
        ) from None

    with connect() as connection:
        save_profile(
            connection,
            session_id,
            profile,
            resume_text=resume_text,
            resume_loaded=True,
            extraction_method=method,
        )
        record_activity(
            connection,
            session_id,
            "Resume text extracted and candidate profile prepared",
            "resume",
        )
        state = profile_state(connection, session_id)

    message = (
        "Nemotron structured this profile from resume evidence. Review every field before using it."
        if method == "nemotron"
        else "PDF text was extracted. This profile uses deterministic text parsing, not Nemotron; review and edit every field."
    )
    return ResumeResult(
        **state,
        extracted_characters=len(resume_text),
        ai_configured=ai_configured,
        message=message,
    )
