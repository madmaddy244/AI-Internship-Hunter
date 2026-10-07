from backend.models import CandidateProfile
from backend.services.matching_service import calculate_match
from backend.services.resume_service import deterministic_profile_from_text
from backend.tools.job_parser import normalize_search_result


def test_match_factors_use_candidate_evidence_and_show_missing_skills():
    profile = CandidateProfile(
        skills=["Python", "C++"],
        ai_ml_skills=["Machine Learning"],
        preferred_roles=["Machine Learning Intern"],
        locations=["Hyderabad"],
        education=["BSc Computer Science"],
        experience=["Built a Python data pipeline"],
    )
    job = {
        "role": "Machine Learning Intern",
        "description": "Use Python and PyTorch to evaluate models in Hyderabad.",
        "requirements": ["Python", "PyTorch"],
        "skills": ["Python", "PyTorch"],
        "location": "Hyderabad, India",
        "remote": False,
    }

    result = calculate_match(profile, job)

    assert result["matched_skills"] == ["Python"]
    assert result["missing_skills"] == ["PyTorch"]
    assert 0 <= result["match_score"] <= 100
    assert "Deterministic fit" in result["match_summary"]
    assert "experience" in result["match_summary"]


def test_resume_profile_does_not_add_skills_absent_from_resume():
    profile = deterministic_profile_from_text(
        """Mira Chen
mira@example.com

Education
BSc Computer Science

Skills
Python

Projects
Built a small Python data-cleaning tool.
"""
    )

    assert profile.name == "Mira Chen"
    assert profile.email == "mira@example.com"
    assert profile.programming_languages == ["Python"]
    assert "PyTorch" not in profile.skills
    assert profile.education == ["BSc Computer Science"]
    assert profile.projects == ["Built a small Python data-cleaning tool."]


def test_job_parser_only_marks_careers_or_job_board_links_as_application_urls():
    result = normalize_search_result(
        {
            "title": "AI Research Intern at Sample Lab",
            "url": "https://sample-lab.example/blog/intern-program",
            "content": (
                "Internship program for AI Research. Requirements include Python, machine "
                "learning, and experience with research prototypes."
            ),
        }
    )

    assert result is not None
    assert result["company"] == "Sample Lab"
    assert result["application_url"] is None
    assert result["source"].endswith("sample-lab.example")
