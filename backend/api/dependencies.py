from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timezone

from fastapi import Request, Response

COOKIE_NAME = "internship_session"
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,48}$")


def session_key(request: Request, response: Response) -> str:
    token = request.cookies.get(COOKIE_NAME, "")
    if not SESSION_PATTERN.fullmatch(token):
        token = secrets.token_urlsafe(32)
        forwarded_protocol = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
        request_protocol = forwarded_protocol or request.url.scheme
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            secure=request_protocol == "https",
            samesite="lax",
            path="/",
        )
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
