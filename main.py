"""Uvicorn compatibility entry point: python -m uvicorn main:app."""

from backend.main import app

__all__ = ["app"]
