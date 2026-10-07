from types import SimpleNamespace

from backend.models import CandidateProfile
from backend.services import agent


def test_search_agent_executes_a_function_tool_and_sanitizes_arguments(monkeypatch):
    captured = {}
    tool_call = SimpleNamespace(
        function=SimpleNamespace(
            name="search_internships",
            arguments='{"query":"Python AI internships","location":"Hyderabad","remote_only":false,"ignored":"x"}',
        )
    )
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(tool_calls=[tool_call])
            )
        ]
    )

    def fake_complete(**kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr(agent, "complete", fake_complete)
    criteria = agent.select_search_tool(
        "AI internship",
        "Hyderabad",
        False,
        CandidateProfile(skills=["Python"]),
    )

    assert captured["tools"][0]["function"]["name"] == "search_internships"
    assert captured["tool_choice"]["function"]["name"] == "search_internships"
    assert criteria == {
        "query": "Python AI internships",
        "location": "Hyderabad",
        "remote_only": False,
    }
