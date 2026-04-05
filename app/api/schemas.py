from typing import Any, Literal

from pydantic import BaseModel, Field

ResumeState = Literal["created", "proposed", "compiling", "ready", "failed"]

JobStatus = Literal["queued", "running", "succeeded", "failed"]


class SessionCreate(BaseModel):
    resume_text: str = Field(..., max_length=50_000)
    job_description: str = Field(..., max_length=50_000)


class SessionCreateResponse(BaseModel):
    session_id: str
    state: ResumeState


class ProposeEditsResponse(BaseModel):
    session_id: str
    state: ResumeState
    proposal: dict[str, Any]
    propose_round: int


class DraftResponse(BaseModel):
    session_id: str
    state: ResumeState
    latex_source: str | None
    refined_resume_text: str | None
    ats_score: int | None


class ConfirmCompileResponse(BaseModel):
    session_id: str
    state: ResumeState
    compile_job_id: str


class JobStatusResponse(BaseModel):
    compile_job_id: str
    session_id: str
    status: JobStatus
    error_message: str | None = None


class ArtifactUrlResponse(BaseModel):
    compile_job_id: str
    download_url: str
    expires_in_seconds: int


class SummaryResponse(BaseModel):
    session_id: str
    state: ResumeState
    ats_score: int | None
    edits_count: int
    headline: str


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str
    redis: bool
    database: bool
    storage: bool
    openai_configured: bool
