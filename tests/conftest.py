from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("NEBIUS_ENABLED", "true")
    monkeypatch.setenv("TAVILY_ENABLED", "true")
    with TestClient(app) as test_client:
        yield test_client
