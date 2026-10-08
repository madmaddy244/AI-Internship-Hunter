from __future__ import annotations

from backend.models import Internship


def create_demo_template(internship: Internship, kind: str) -> str:
    company = internship.company.removesuffix(" (sample)")
    role = internship.role

    templates = {
        "cover_letter": (
            f"Hello Hiring Team,\n\n"
            f"I’m interested in the {role} opportunity at {company}. "
            "I’m especially interested in [add a specific, truthful reason].\n\n"
            "My relevant experience includes [describe a real project or responsibility] "
            "using [name tools you actually used]. That work helped me [state a result you "
            "can support].\n\n"
            "I’d welcome the chance to discuss how my experience fits this internship.\n\n"
            "Best,\n[Your name]"
        ),
        "recruiter_message": (
            f"Hi [Recruiter name], I’m interested in the {role} opportunity at {company}. "
            "My experience with [relevant skill] includes [one true example]. "
            "Would you be open to sharing more about the team’s work and the application process?"
        ),
        "application_email": (
            f"Subject: Application for {role} at {company}\n\n"
            "Hello Hiring Team,\n\n"
            f"I’m writing to express my interest in the {role} opportunity at {company}. "
            "My background includes [brief, accurate example relevant to the role].\n\n"
            "I’ve attached [documents you are actually including]. Thank you for your time.\n\n"
            "Best,\n[Your name]"
        ),
        "preparation_suggestions": (
            f"Example preparation checklist for the fictional {role} listing:\n\n"
            "1. Choose a real project that demonstrates one of the listed skills.\n"
            "2. Prepare a short explanation of what you did and what you learned.\n"
            "3. Review the skills shown on the sample listing and note any honest gaps.\n"
            "4. Prepare one question about the team, mentor, or internship expectations.\n\n"
            "This is a generic sample checklist, not an AI-generated assessment."
        ),
    }
    content = templates.get(kind)
    if content is None:
        raise ValueError("Unsupported demo material type.")
    return (
        "SAMPLE TEMPLATE — NOT AI-GENERATED\n"
        "Replace bracketed text with accurate details before use.\n\n"
        f"{content}"
    )
