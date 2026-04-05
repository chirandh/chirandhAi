from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _rate_key(request: Request) -> str:
    key = request.headers.get("X-API-Key") or "anonymous"
    return f"{key}:{get_remote_address(request)}"


def build_limiter() -> Limiter:
    settings = get_settings()
    if settings.environment == "test":
        return Limiter(key_func=_rate_key)
    return Limiter(
        key_func=_rate_key,
        storage_uri=settings.redis_url,
    )


limiter = build_limiter()


def reset_limiter() -> Limiter:
    global limiter
    limiter = build_limiter()
    return limiter
