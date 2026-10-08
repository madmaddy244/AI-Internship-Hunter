from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "saved", "applied", "assessment", "interview", "offer", "rejected", "withdrawn"
]
MaterialKind = Literal[
    "cover_letter",
    "recruiter_message",
    "application_email",
    "preparation_suggestions",
]


class AppModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthStatus(AppModel):
    status: str


class RuntimeStatus(AppModel):
    ai_configured: bool
    ai_provider: str
    model: str
    search_configured: bool
    search_provider: str
    message: str


class Activity(AppModel):
    id: str
    message: str
    created_at: datetime
    kind: str


class Dashboard(AppModel):
    internships_found: int
    saved: int
    applications: int
    interviews: int
    pending: int
    recent_activity: list[Activity]


class CandidateProfile(AppModel):
    name: str = ""
    email: str | None = None
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    ai_ml_skills: list[str] = Field(default_factory=list)
    cloud_skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)


class ProfileInput(CandidateProfile):
    pass


class ProfileState(AppModel):
    profile: CandidateProfile
    resume_loaded: bool
    extraction_method: str


class ResumeResult(ProfileState):
    extracted_characters: int
    ai_configured: bool
    message: str


class Internship(AppModel):
    id: str
    company: str
    role: str
    location: str
    remote: bool
    description: str
    requirements: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    salary: str | None = None
    deadline: str | None = None
    source: str
    application_url: str | None = None
    date_found: datetime
    match_score: int = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    match_summary: str = ""


class SearchInput(AppModel):
    query: str = Field(min_length=2, max_length=240)
    location: str = Field(default="", max_length=120)
    remote_only: bool = False
    demo_mode: bool = False
    demo_sample_profile: bool = False
    max_results: int = Field(default=12, ge=1, le=20)


class SearchResult(AppModel):
    jobs: list[Internship]
    count: int
    data_mode: Literal["live", "demo"]
    demo_sample_profile: bool = False
    ai_used: bool
    message: str


class Application(AppModel):
    id: str
    internship_id: str
    company: str
    role: str
    application_url: str | None = None
    date_applied: datetime | None = None
    status: ApplicationStatus
    notes: str = ""
    generated_material: dict[str, str] = Field(default_factory=dict)
    job_description: str = ""
    created_at: datetime


class SaveApplicationInput(AppModel):
    internship_id: str
    notes: str = ""


class ApplicationUpdate(AppModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    generated_material: dict[str, str] | None = None


class GenerateMaterialInput(AppModel):
    kind: MaterialKind
    demo_template: bool = False


class GeneratedMaterial(AppModel):
    kind: MaterialKind
    content: str
    ai_used: bool
    model: str


class AssistantInput(AppModel):
    message: str = Field(min_length=1, max_length=4000)


class AssistantReply(AppModel):
    reply: str
    ai_used: bool
    model: str
