import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool = None


async def get_arq_pool():
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue_compile_job(job_id: str, session_id: str) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job("run_compile_job", job_id, session_id)


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
