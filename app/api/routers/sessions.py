import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import fingerprint_api_key, load_owned_session, verify_api_key
from app.api.schemas import (
    ConfirmCompileResponse,
    DraftResponse,
    ProposeEditsResponse,
    SessionCreate,
    SessionCreateResponse,
    SummaryResponse,
)
from app.core.config import get_settings as get_app_settings
from app.core.ratelimit import limiter
from app.db.models import CompileJob, CompileJobStatus, ResumeSession, SessionState
from app.db.session import get_db
from app.services.edit_validation import EditValidationError, apply_edits_to_resume
from app.services.job_queue import enqueue_compile_job
from app.services.latex_render import render_resume_latex
from app.services.llm_service import propose_edits as llm_propose_edits, score_resume_jd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse)
@limiter.limit(get_app_settings().rate_limit_default)
async def create_session(
    request: Request,
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    fp = fingerprint_api_key(api_key)
    row = ResumeSession(
        owner_fingerprint=fp,
        state=SessionState.created.value,
        resume_text=body.resume_text,
        jd_text=body.job_description,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SessionCreateResponse(session_id=row.id, state=row.state)  # type: ignore[arg-type]


@router.post("/{session_id}/propose-edits", response_model=ProposeEditsResponse)
@limiter.limit(get_app_settings().rate_limit_default)
async def propose_edits(
    request: Request,
    session: ResumeSession = Depends(load_owned_session),
    db: AsyncSession = Depends(get_db),
):
    settings = get_app_settings()
    if session.state not in (
        SessionState.created.value,
        SessionState.proposed.value,
        SessionState.failed.value,
    ):
        raise HTTPException(status_code=409, detail="Cannot propose edits in current state")
    if session.propose_rounds >= settings.max_propose_rounds_per_session:
        raise HTTPException(status_code=429, detail="Maximum proposal rounds reached for this session")

    try:
        proposal = llm_propose_edits(session.resume_text, session.jd_text)
        refined = apply_edits_to_resume(session.resume_text, proposal["edits"])
        latex = render_resume_latex(refined)
    except EditValidationError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": e.message}) from e
    except Exception:
        logger.exception("propose_edits failed for session %s", session.id)
        raise HTTPException(status_code=502, detail="Proposal service unavailable") from None

    session.proposal_json = json.dumps(proposal)
    session.refined_resume_text = refined
    session.latex_source = latex
    session.ats_score = proposal.get("ats_score")
    session.state = SessionState.proposed.value
    session.propose_rounds = session.propose_rounds + 1
    await db.commit()
    await db.refresh(session)
    return ProposeEditsResponse(
        session_id=session.id,
        state=session.state,  # type: ignore[arg-type]
        proposal=proposal,
        propose_round=session.propose_rounds,
    )


@router.get("/{session_id}/draft", response_model=DraftResponse)
@limiter.limit(get_app_settings().rate_limit_default)
async def get_draft(request: Request, session: ResumeSession = Depends(load_owned_session)):
    if not session.proposal_json:
        raise HTTPException(status_code=400, detail="No proposal yet; call propose-edits first")
    return DraftResponse(
        session_id=session.id,
        state=session.state,  # type: ignore[arg-type]
        latex_source=session.latex_source,
        refined_resume_text=session.refined_resume_text,
        ats_score=session.ats_score,
    )


@router.get("/{session_id}/ats-score")
@limiter.limit(get_app_settings().rate_limit_default)
async def get_ats_score(request: Request, session: ResumeSession = Depends(load_owned_session)):
    """Cheap model pass: keyword coverage-style ATS score (JSON)."""
    try:
        return score_resume_jd(session.resume_text, session.jd_text)
    except Exception:
        logger.exception("ats-score failed for session %s", session.id)
        raise HTTPException(status_code=502, detail="Scoring service unavailable") from None


@router.get("/{session_id}/summary", response_model=SummaryResponse)
@limiter.limit(get_app_settings().rate_limit_default)
async def get_summary(request: Request, session: ResumeSession = Depends(load_owned_session)):
    if not session.proposal_json:
        raise HTTPException(status_code=400, detail="No proposal yet")
    proposal = json.loads(session.proposal_json)
    edits = proposal.get("edits") or []
    headline = f"{len(edits)} proposed edits; ATS score {session.ats_score or proposal.get('ats_score')}"
    return SummaryResponse(
        session_id=session.id,
        state=session.state,  # type: ignore[arg-type]
        ats_score=session.ats_score,
        edits_count=len(edits),
        headline=headline,
    )


@router.post("/{session_id}/confirm-compile", response_model=ConfirmCompileResponse)
@limiter.limit(get_app_settings().rate_limit_default)
async def confirm_compile(
    request: Request,
    session: ResumeSession = Depends(load_owned_session),
    db: AsyncSession = Depends(get_db),
):
    if session.state != SessionState.proposed.value:
        raise HTTPException(
            status_code=409,
            detail="Session must be in proposed state with user-approved content before compile",
        )
    if not session.latex_source:
        raise HTTPException(status_code=400, detail="No LaTeX draft available")

    job = CompileJob(session_id=session.id, status=CompileJobStatus.queued.value)
    db.add(job)
    session.state = SessionState.compiling.value
    await db.commit()
    await db.refresh(job)

    try:
        await enqueue_compile_job(job.id, session.id)
    except Exception:
        logger.exception("enqueue failed for job %s", job.id)
        job.status = CompileJobStatus.failed.value
        job.error_message = "Queue unavailable"
        session.state = SessionState.failed.value
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable") from None

    await db.refresh(session)
    return ConfirmCompileResponse(
        session_id=session.id,
        state=session.state,  # type: ignore[arg-type]
        compile_job_id=job.id,
    )
