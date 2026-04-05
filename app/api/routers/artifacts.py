from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.api.routers.jobs import _load_job_for_owner
from app.api.schemas import ArtifactUrlResponse
from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.db.models import CompileJobStatus
from app.db.session import get_db
from app.services.storage import presigned_get_url

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{compile_job_id}/download-url", response_model=ArtifactUrlResponse)
@limiter.limit(get_settings().rate_limit_default)
async def artifact_download_url(
    request: Request,
    compile_job_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    settings = get_settings()
    job = await _load_job_for_owner(compile_job_id, db, _api_key)
    if job.status != CompileJobStatus.succeeded.value or not job.artifact_key:
        raise HTTPException(status_code=409, detail="Artifact not ready")
    url = presigned_get_url(job.artifact_key)
    return ArtifactUrlResponse(
        compile_job_id=job.id,
        download_url=url,
        expires_in_seconds=settings.artifact_url_ttl_seconds,
    )
