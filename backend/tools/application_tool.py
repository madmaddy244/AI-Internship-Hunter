from __future__ import annotations

import sqlite3
from typing import Any

from backend.models import ApplicationUpdate
from backend.services.application_service import (
    get_application,
    save_application,
    update_application,
)


def save_application_tool(
    connection: sqlite3.Connection, session_id: str, internship_id: str
) -> dict[str, Any] | None:
    return save_application(connection, session_id, internship_id)


def get_application_status_tool(
    connection: sqlite3.Connection, session_id: str, application_id: str
) -> dict[str, Any] | None:
    return get_application(connection, session_id, application_id)


def update_application_status_tool(
    connection: sqlite3.Connection,
    session_id: str,
    application_id: str,
    status: str,
) -> dict[str, Any] | None:
    update = ApplicationUpdate(status=status)  # type: ignore[arg-type]
    return update_application(connection, session_id, application_id, update)
