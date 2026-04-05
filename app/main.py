import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routers import artifacts, health, jobs, sessions
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.core.ratelimit import limiter
from app.db.session import init_db
from app.services.job_queue import close_arq_pool

logger = logging.getLogger(__name__)


def _path_group(path: str) -> str:
    for prefix in (
        "/sessions",
        "/jobs",
        "/artifacts",
        "/health",
        "/ready",
        "/metrics",
        "/openapi.json",
        "/docs",
        "/redoc",
    ):
        if path == prefix or path.startswith(prefix + "/"):
            return prefix + "/*" if not path.endswith(prefix) and prefix != path else prefix
    if path == "/" or path == "":
        return "/"
    parts = path.strip("/").split("/")
    return f"/{parts[0]}/*" if parts[0] else path


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    Path("data").mkdir(parents=True, exist_ok=True)
    await init_db()
    try:
        from app.services.storage import ensure_bucket_exists

        ensure_bucket_exists()
    except Exception:
        logger.exception("Could not verify object storage bucket (continuing)")
    yield
    await close_arq_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        description=(
            "ATS-oriented resume refinement API for Custom GPT Actions. "
            "Flow: create session → propose-edits → review draft → confirm-compile → poll job status → "
            "fetch signed download URL for PDF. PDFs are built only after confirm-compile."
        ),
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        group = _path_group(request.url.path)
        REQUEST_LATENCY.labels(method=request.method, path=group).observe(elapsed)
        REQUEST_COUNT.labels(method=request.method, path=group, status=response.status_code).inc()
        return response

    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(jobs.router)
    app.include_router(artifacts.router)

    return app


app = create_app()
