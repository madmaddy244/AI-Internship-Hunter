def test_health_and_runtime_status_are_explicit_without_provider_secrets(client):
    health = client.get("/api/healthz")
    status = client.get("/api/status")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert status.status_code == 200
    assert status.json()["ai_configured"] is False
    assert status.json()["search_configured"] is False
    assert "NEBIUS_API_KEY" in status.json()["message"]
    assert "TAVILY_API_KEY" in status.json()["message"]
    assert "api_key" not in status.text


def test_demo_search_save_tracker_status_and_dashboard_flow(client):
    profile = client.put(
        "/api/profile",
        json={
            "name": "Mira Chen",
            "email": None,
            "education": ["BSc Computer Science"],
            "skills": ["Python"],
            "programming_languages": ["Python"],
            "frameworks": [],
            "ai_ml_skills": ["Machine Learning"],
            "cloud_skills": [],
            "projects": ["Python classification project"],
            "experience": [],
            "certifications": [],
            "locations": ["Hyderabad"],
            "preferred_roles": ["Machine Learning Intern"],
        },
    )
    assert profile.status_code == 200

    search = client.post(
        "/api/internships/search",
        json={
            "query": "machine learning",
            "location": "Hyderabad",
            "remote_only": False,
            "demo_mode": True,
            "max_results": 8,
        },
    )
    assert search.status_code == 200
    payload = search.json()
    assert payload["data_mode"] == "demo"
    assert payload["count"] == 1
    internship = payload["jobs"][0]
    assert "fictional" in internship["source"]
    assert internship["application_url"] is None
    assert internship["matched_skills"] == ["Python", "Machine Learning"]

    saved = client.post(
        "/api/applications",
        json={"internship_id": internship["id"], "notes": "Review this sample"},
    )
    assert saved.status_code == 201
    application = saved.json()
    assert application["status"] == "saved"
    assert application["date_applied"] is None

    updated = client.patch(
        f"/api/applications/{application['id']}",
        json={
            "status": "interview",
            "notes": "Personal note",
            "generated_material": {"recruiter_message": "Edited draft"},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "interview"
    assert updated.json()["date_applied"] is not None
    assert updated.json()["notes"] == "Personal note"
    assert updated.json()["generated_material"]["recruiter_message"] == "Edited draft"

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["internships_found"] == 1
    assert dashboard.json()["saved"] == 0
    assert dashboard.json()["interviews"] == 1
    assert dashboard.json()["applications"] == 1
    assert dashboard.json()["recent_activity"]


def test_provider_dependent_actions_fail_explicitly_when_unconfigured(client):
    live_search = client.post(
        "/api/internships/search",
        json={"query": "AI internship", "demo_mode": False},
    )
    assistant = client.post(
        "/api/assistant/chat",
        json={"message": "What skills appear in my profile?"},
    )

    assert live_search.status_code == 503
    assert "TAVILY_API_KEY" in live_search.json()["detail"]
    assert assistant.status_code == 503
    assert "NEBIUS_API_KEY" in assistant.json()["detail"]


def test_browser_sessions_are_isolated(client, monkeypatch):
    from backend.main import app
    from fastapi.testclient import TestClient

    first = client
    first.put(
        "/api/profile",
        json={
            "name": "Session One",
            "email": None,
            "education": [],
            "skills": [],
            "programming_languages": [],
            "frameworks": [],
            "ai_ml_skills": [],
            "cloud_skills": [],
            "projects": [],
            "experience": [],
            "certifications": [],
            "locations": [],
            "preferred_roles": [],
        },
    )
    with TestClient(app) as second:
        result = second.get("/api/profile").json()

    assert first.get("/api/profile").json()["profile"]["name"] == "Session One"
    assert result["profile"]["name"] == ""
