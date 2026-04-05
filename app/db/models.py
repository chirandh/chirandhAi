import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SessionState(enum.StrEnum):
    created = "created"
    proposed = "proposed"
    compiling = "compiling"
    ready = "ready"
    failed = "failed"


class CompileJobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ResumeSession(Base):
    __tablename__ = "resume_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=SessionState.created.value, index=True)
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    refined_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposal_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    latex_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    ats_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    propose_rounds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    jobs: Mapped[list["CompileJob"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class CompileJob(Base):
    __tablename__ = "compile_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=CompileJobStatus.queued.value, index=True)
    artifact_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["ResumeSession"] = relationship(back_populates="jobs")
