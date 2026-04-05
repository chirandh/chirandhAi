import logging

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.schemas import HealthResponse, ReadyResponse
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.storage import _client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse)
async def ready():
    settings = get_settings()
    redis_ok = False
    db_ok = False
    storage_ok = False
    try:
        r = Redis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        logger.exception("ready check: redis failed")

    try:
        async with get_session_factory()() as session:  # type: AsyncSession
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("ready check: database failed")

    try:
        c = _client()
        c.head_bucket(Bucket=settings.s3_bucket)
        storage_ok = True
    except Exception:
        logger.exception("ready check: storage failed")

    openai_ok = bool(settings.openai_api_key)
    overall = redis_ok and db_ok and storage_ok
    return ReadyResponse(
        status="ready" if overall else "degraded",
        redis=redis_ok,
        database=db_ok,
        storage=storage_ok,
        openai_configured=openai_ok,
    )


@router.get("/metrics")
async def metrics():
    from fastapi.responses import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
