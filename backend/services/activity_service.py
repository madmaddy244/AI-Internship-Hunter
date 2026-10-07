from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


def record_activity(
    connection: sqlite3.Connection, session_id: str, message: str, kind: str
) -> None:
    connection.execute(
        "INSERT INTO activities (id, session_id, message, created_at, kind) VALUES (?, ?, ?, ?, ?)",
        (
            uuid.uuid4().hex,
            session_id,
            message[:240],
            datetime.now(timezone.utc).isoformat(),
            kind[:40],
        ),
    )
