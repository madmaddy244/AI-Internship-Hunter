from __future__ import annotations

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api.dependencies import session_key
from backend.database import connect, read_profile
from backend.models import (
    Application,
    ApplicationUpdate,
    GenerateMaterialInput,
    GeneratedMaterial,
    SaveApplicationInput,
)
from backend.services.activity_service import record_activity
from backend.services.application_service import (
    generate_material,
    get_application,
    list_applications,
    material_result,
    save_application,
    save_generated_material,
    update_application,
)
from backend.services.nebius_client import NebiusError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/applications", response_model=list[Application], tags=["applications"])
def applications(
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> list[Application]:
    with connect() as connection:
        return [Application.model_validate(item) for item in list_applications(connection, session_id)]


@router.post(
    "/applications",
    response_model=Application,
    status_code=201,
    tags=["applications"],
)
def save(
    body: SaveApplicationInput,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> Application:
    with connect() as connection:
        item = save_application(
            connection, session_id, body.internship_id, body.notes
        )
    if item is None:
        raise HTTPException(status_code=404, detail="Internship not found in this session.")
    return Application.model_validate(item)


@router.get(
    "/applications/{application_id}",
    response_model=Application,
    tags=["applications"],
)
def get(
    application_id: str,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> Application:
    with connect() as connection:
        item = get_application(connection, session_id, application_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return Application.model_validate(item)


@router.patch(
    "/applications/{application_id}",
    response_model=Application,
    tags=["applications"],
)
def update(
    application_id: str,
    body: ApplicationUpdate,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> Application:
    with connect() as connection:
        item = update_application(connection, session_id, application_id, body)
    if item is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return Application.model_validate(item)


@router.post(
    "/applications/{application_id}/generate",
    response_model=GeneratedMaterial,
    tags=["applications", "agent"],
)
def generate(
    application_id: str,
    body: GenerateMaterialInput,
    request: Request,
    response: Response,
    session_id: str = Depends(session_key),
) -> GeneratedMaterial:
    with connect() as connection:
        application = get_application(connection, session_id, application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Application not found.")
        profile = read_profile(connection, session_id)
    try:
        content = generate_material(application, profile, body.kind)
    except NebiusError as error:
        raise HTTPException(
            status_code=error.status_code, detail=error.public_message
        ) from None
    except Exception as error:
        logger.warning("Application draft generation failed (%s)", type(error).__name__)
        raise HTTPException(
            status_code=502, detail="Nemotron could not generate this draft. Try again."
        ) from None
    with connect() as connection:
        save_generated_material(
            connection, session_id, application_id, body.kind, content
        )
        record_activity(
            connection,
            session_id,
            f"Nemotron generated a {body.kind.replace('_', ' ')} draft",
            "generation",
        )
    return GeneratedMaterial(**material_result(body.kind, content))
