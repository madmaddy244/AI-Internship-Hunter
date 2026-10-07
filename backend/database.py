from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

from backend.models import CandidateProfile

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.getenv(
    "INTERNSHIP_HUNTER_DATABASE_URL", "sqlite:///./internship_agent.db"
)


def database_path() -> Path:
    if not DATABASE_URL.startswith("sqlite:///"):
        raise RuntimeError("This initial release supports SQLite DATABASE_URL values only.")
    raw_path = DATABASE_URL.removeprefix("sqlite:///")
    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                session_id TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL,
                resume_text TEXT NOT NULL DEFAULT '',
                resume_loaded INTEGER NOT NULL DEFAULT 0,
                extraction_method TEXT NOT NULL DEFAULT 'manual'
            );
            CREATE TABLE IF NOT EXISTS internships (
                id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                data_json TEXT NOT NULL,
                PRIMARY KEY (session_id, id)
            );
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                internship_id TEXT NOT NULL,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                application_url TEXT,
                date_applied TEXT,
                status TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                generated_material TEXT NOT NULL DEFAULT '{}',
                job_description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                PRIMARY KEY (session_id, id),
                UNIQUE (session_id, internship_id)
            );
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT NOT NULL PRIMARY KEY,
                session_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_internships_session
                ON internships(session_id);
            CREATE INDEX IF NOT EXISTS idx_applications_session
                ON applications(session_id, status);
            CREATE INDEX IF NOT EXISTS idx_activities_session
                ON activities(session_id, created_at);
            """
        )


def profile_row(connection: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT profile_json, resume_text, resume_loaded, extraction_method "
        "FROM profiles WHERE session_id = ?",
        (session_id,),
    ).fetchone()


def read_profile(connection: sqlite3.Connection, session_id: str) -> CandidateProfile:
    row = profile_row(connection, session_id)
    if row is None:
        return CandidateProfile()
    return CandidateProfile.model_validate_json(row["profile_json"])


def save_profile(
    connection: sqlite3.Connection,
    session_id: str,
    profile: CandidateProfile,
    *,
    resume_text: str | None = None,
    resume_loaded: bool | None = None,
    extraction_method: str | None = None,
) -> None:
    existing = profile_row(connection, session_id)
    saved_resume_text = (
        resume_text
        if resume_text is not None
        else (existing["resume_text"] if existing else "")
    )
    saved_resume_loaded = (
        int(resume_loaded)
        if resume_loaded is not None
        else (existing["resume_loaded"] if existing else 0)
    )
    saved_extraction_method = (
        extraction_method
        if extraction_method is not None
        else (existing["extraction_method"] if existing else "manual")
    )
    connection.execute(
        """
        INSERT INTO profiles (session_id, profile_json, resume_text, resume_loaded, extraction_method)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
          profile_json = excluded.profile_json,
          resume_text = excluded.resume_text,
          resume_loaded = excluded.resume_loaded,
          extraction_method = excluded.extraction_method
        """,
        (
            session_id,
            profile.model_dump_json(),
            saved_resume_text,
            saved_resume_loaded,
            saved_extraction_method,
        ),
    )


def profile_state(connection: sqlite3.Connection, session_id: str) -> dict[str, Any]:
    row = profile_row(connection, session_id)
    if row is None:
        return {
            "profile": CandidateProfile().model_dump(mode="json"),
            "resume_loaded": False,
            "extraction_method": "manual",
        }
    return {
        "profile": json.loads(row["profile_json"]),
        "resume_loaded": bool(row["resume_loaded"]),
        "extraction_method": row["extraction_method"],
    }
