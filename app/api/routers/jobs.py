import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.api.schemas import JobStatusResponse
from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.db.models import CompileJob, ResumeSession
from app.db.session import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _load_job_for_owner(
    compile_job_id: str,
    db: AsyncSession,
    api_key: str,
) -> CompileJob:
    from app.api.deps import fingerprint_api_key as fp_fn

    fp = fp_fn(api_key)
    job = await db.get(CompileJob, compile_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    sess = await db.get(ResumeSession, job.session_id)
    if sess is None or not hmac.compare_digest(sess.owner_fingerprint, fp):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{compile_job_id}/status", response_model=JobStatusResponse)
@limiter.limit(get_settings().rate_limit_default)
async def job_status(
    request: Request,
    compile_job_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    job = await _load_job_for_owner(compile_job_id, db, api_key)
    return JobStatusResponse(
        compile_job_id=job.id,
        session_id=job.session_id,
        status=job.status,  # type: ignore[arg-type]
        error_message=job.error_message,
    )
