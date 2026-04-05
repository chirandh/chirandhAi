import logging
from datetime import UTC, datetime, timedelta
from typing import BinaryIO

import boto3
from botocore.client import Config

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _s3_client(*, endpoint_url: str | None) -> object:
    settings = get_settings()
    addressing = "path" if endpoint_url else "virtual"
    kwargs = {
        "region_name": settings.s3_region,
        "config": Config(signature_version="s3v4", s3={"addressing_style": addressing}),
    }
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def _client():
    return _s3_client(endpoint_url=get_settings().s3_endpoint_url)


def ensure_bucket_exists() -> None:
    settings = get_settings()
    if settings.environment == "test":
        return
    c = _client()
    try:
        c.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        try:
            c.create_bucket(Bucket=settings.s3_bucket)
        except Exception:
            logger.exception("Could not ensure bucket %s", settings.s3_bucket)


def put_pdf_bytes(key: str, data: bytes, content_type: str = "application/pdf") -> None:
    settings = get_settings()
    c = _client()
    c.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def put_pdf_stream(key: str, stream: BinaryIO, content_type: str = "application/pdf") -> None:
    settings = get_settings()
    c = _client()
    c.upload_fileobj(stream, settings.s3_bucket, key, ExtraArgs={"ContentType": content_type})


def presigned_get_url(key: str) -> str:
    """Presigned URL host must be reachable by the user's browser (not Docker-only hostnames)."""
    settings = get_settings()
    public_endpoint = settings.s3_presign_endpoint_url or settings.s3_endpoint_url
    c = _s3_client(endpoint_url=public_endpoint)
    return c.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=settings.artifact_url_ttl_seconds,
    )


def retention_cutoff() -> datetime:
    settings = get_settings()
    return datetime.now(UTC) - timedelta(days=settings.artifact_retention_days)
