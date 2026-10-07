from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models import Application, ApplicationUpdate, CandidateProfile, Internship
from backend.services.activity_service import record_activity
from backend.services.nebius_client import complete, model_name

MATERIAL_PROMPTS = {
    "cover_letter": (
        "Write a concise one-page cover letter tailored to this internship. Use only the "
        "candidate profile and job evidence. Do not invent achievements, metrics, experience, "
        "or company facts. Leave a bracketed placeholder only when a required personal detail "
        "is missing."
    ),
    "recruiter_message": (
        "Write a brief, professional recruiter message for this internship. Mention one or two "
        "evidenced profile strengths relevant to the role. Do not invent achievements or claim "
        "the candidate already applied."
    ),
    "application_email": (
        "Write a concise application email for this internship. Use evidenced profile details "
        "only. Do not claim files are attached or an application has been submitted."
    ),
    "preparation_suggestions": (
        "Give a short preparation checklist for applying to this internship. Separate resume "
        "evidence from role requirements and identify gaps without claiming the candidate has them."
    ),
}


def application_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "internship_id": row["internship_id"],
        "company": row["company"],
        "role": row["role"],
        "application_url": row["application_url"],
        "date_applied": row["date_applied"],
        "status": row["status"],
        "notes": row["notes"],
        "generated_material": json.loads(row["generated_material"] or "{}"),
        "job_description": row["job_description"],
        "created_at": row["created_at"],
    }


def list_applications(
    connection: sqlite3.Connection, session_id: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM applications WHERE session_id = ? ORDER BY created_at DESC",
        (session_id,),
    ).fetchall()
    return [application_from_row(row) for row in rows]


def get_application(
    connection: sqlite3.Connection, session_id: str, application_id: str
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM applications WHERE session_id = ? AND id = ?",
        (session_id, application_id),
    ).fetchone()
    return application_from_row(row) if row else None


def save_application(
    connection: sqlite3.Connection, session_id: str, internship_id: str, notes: str = ""
) -> dict[str, Any] | None:
    existing = connection.execute(
        "SELECT * FROM applications WHERE session_id = ? AND internship_id = ?",
        (session_id, internship_id),
    ).fetchone()
    if existing:
        return application_from_row(existing)
    job_row = connection.execute(
        "SELECT data_json FROM internships WHERE session_id = ? AND id = ?",
        (session_id, internship_id),
    ).fetchone()
    if not job_row:
        return None
    job = Internship.model_validate_json(job_row["data_json"])
    application_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO applications (
          id, session_id, internship_id, company, role, application_url,
          date_applied, status, notes, generated_material, job_description, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, 'saved', ?, '{}', ?, ?)
        """,
        (
            application_id,
            session_id,
            internship_id,
            job.company,
            job.role,
            job.application_url,
            notes[:4000],
            job.description,
            created_at,
        ),
    )
    record_activity(connection, session_id, f"Saved {job.role} at {job.company}", "saved")
    return get_application(connection, session_id, application_id)


def update_application(
    connection: sqlite3.Connection,
    session_id: str,
    application_id: str,
    update: ApplicationUpdate,
) -> dict[str, Any] | None:
    current = get_application(connection, session_id, application_id)
    if current is None:
        return None
    changes: list[str] = []
    values: list[Any] = []
    fields = update.model_fields_set
    if "status" in fields and update.status is not None:
        changes.append("status = ?")
        values.append(update.status)
        if update.status != "saved" and not current["date_applied"]:
            changes.append("date_applied = ?")
            values.append(datetime.now(timezone.utc).isoformat())
        record_activity(
            connection,
            session_id,
            f"{current['company']} application moved to {update.status.title()}",
            "status",
        )
    if "notes" in fields and update.notes is not None:
        changes.append("notes = ?")
        values.append(update.notes[:4000])
    if "generated_material" in fields and update.generated_material is not None:
        changes.append("generated_material = ?")
        values.append(json.dumps(update.generated_material, ensure_ascii=False))
    if not changes:
        return current
    values.extend([session_id, application_id])
    connection.execute(
        f"UPDATE applications SET {', '.join(changes)} WHERE session_id = ? AND id = ?",
        values,
    )
    return get_application(connection, session_id, application_id)


def save_generated_material(
    connection: sqlite3.Connection,
    session_id: str,
    application_id: str,
    kind: str,
    content: str,
) -> dict[str, Any] | None:
    current = get_application(connection, session_id, application_id)
    if current is None:
        return None
    updated_material = {**current["generated_material"], kind: content}
    connection.execute(
        "UPDATE applications SET generated_material = ? WHERE session_id = ? AND id = ?",
        (json.dumps(updated_material, ensure_ascii=False), session_id, application_id),
    )
    return get_application(connection, session_id, application_id)


def generate_material(
    application: dict[str, Any],
    profile: CandidateProfile,
    kind: str,
) -> str:
    prompt = MATERIAL_PROMPTS[kind]
    response = complete(
        messages=[
            {
                "role": "system",
                "content": (
                    "You create application drafts for a student. Be specific but never fabricate. "
                    "Do not imply that you submitted an application."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": prompt,
                        "candidate_profile": profile.model_dump(mode="json"),
                        "internship": {
                            "company": application["company"],
                            "role": application["role"],
                            "description": application["job_description"][:7000],
                            "application_url": application["application_url"],
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        max_tokens=1200,
        temperature=0.4,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("Nemotron returned an empty application draft.")
    return content[:8000]


def material_result(kind: str, content: str) -> dict[str, Any]:
    return {"kind": kind, "content": content, "ai_used": True, "model": model_name()}


def typed_application(value: dict[str, Any]) -> Application:
    return Application.model_validate(value)
