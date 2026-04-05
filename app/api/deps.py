import hashlib
import hmac
import logging

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ResumeSession
from app.db.session import get_db

logger = logging.getLogger(__name__)


def fingerprint_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    settings = get_settings()
    keys = settings.api_key_set()
    if not any(hmac.compare_digest(x_api_key, k) for k in keys):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


async def load_owned_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> ResumeSession:
    fp = fingerprint_api_key(_api_key)
    result = await db.execute(select(ResumeSession).where(ResumeSession.id == session_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not hmac.compare_digest(row.owner_fingerprint, fp):
        logger.warning("IDOR attempt on session %s", session_id)
        raise HTTPException(status_code=404, detail="Session not found")
    return row
