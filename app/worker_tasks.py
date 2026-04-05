"""ARQ worker: LaTeX → PDF and artifact upload."""

import logging

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.metrics import COMPILE_OUTCOMES
from app.db.models import CompileJob, CompileJobStatus, ResumeSession, SessionState
from app.services.compile_runner import CompileError, compile_latex_to_pdf_bytes
from app.services.storage import put_pdf_bytes

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    setup_logging()
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    ctx["engine"] = engine
    # Match API session factory: avoid expiring ORM rows after commit so compile can read
    # latex_source without async lazy-load (MissingGreenlet) after status update + commit.
    ctx["session_factory"] = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def shutdown(ctx: dict) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()


async def run_compile_job(ctx: dict, job_id: str, session_id: str) -> None:
    factory = ctx["session_factory"]
    async with factory() as db:
        job = await db.get(CompileJob, job_id)
        if job is None:
            logger.error("compile job not found: %s", job_id)
            return
        sess = await db.get(ResumeSession, session_id)
        if sess is None:
            job.status = CompileJobStatus.failed.value
            job.error_message = "Session not found"
            await db.commit()
            COMPILE_OUTCOMES.labels(status="failed").inc()
            return

        job.status = CompileJobStatus.running.value
        await db.commit()

        try:
            if not sess.latex_source:
                raise CompileError("No LaTeX source for this session")
            pdf = compile_latex_to_pdf_bytes(sess.latex_source)
            key = f"artifacts/{session_id}/{job_id}.pdf"
            put_pdf_bytes(key, pdf)
            job.status = CompileJobStatus.succeeded.value
            job.artifact_key = key
            job.error_message = None
            sess.state = SessionState.ready.value
            COMPILE_OUTCOMES.labels(status="succeeded").inc()
        except CompileError as e:
            job.status = CompileJobStatus.failed.value
            job.error_message = e.public_message
            sess.state = SessionState.failed.value
            COMPILE_OUTCOMES.labels(status="failed").inc()
            logger.warning("compile failed (user-safe): %s", e.public_message)
        except Exception:
            logger.exception("compile job crashed: %s", job_id)
            job.status = CompileJobStatus.failed.value
            job.error_message = "PDF generation failed"
            sess.state = SessionState.failed.value
            COMPILE_OUTCOMES.labels(status="error").inc()
        await db.commit()


class WorkerSettings:
    functions = [run_compile_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
