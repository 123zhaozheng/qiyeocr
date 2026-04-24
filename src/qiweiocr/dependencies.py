from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from qiweiocr.config import Settings
from qiweiocr.config import get_settings
from qiweiocr.services.cache import CacheService
from qiweiocr.services.ftp_file import FtpFileService
from qiweiocr.services.llm import LlmService
from qiweiocr.services.recipient_extractor import RecipientExtractorService


@lru_cache
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=False)


@lru_cache
def get_cache_service() -> CacheService:
    settings = get_settings()
    return CacheService(
        redis_client=get_redis_client(),
        ttl_seconds=settings.redis_ttl_seconds,
        key_prefix=settings.redis_key_prefix,
    )


@lru_cache
def get_llm_service() -> LlmService:
    settings = get_settings()
    return LlmService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        text_model=settings.openai_model_text,
        image_model=settings.openai_model_image,
        timeout_seconds=settings.openai_timeout_seconds,
    )


@lru_cache
def get_ftp_file_service() -> FtpFileService:
    settings = get_settings()
    return FtpFileService(
        host=settings.ftp_host,
        port=settings.ftp_port,
        username=settings.ftp_username,
        password=settings.ftp_password,
        base_dir=settings.ftp_base_dir,
        timeout_seconds=settings.ftp_timeout_seconds,
        passive=settings.ftp_passive,
        use_tls=settings.ftp_use_tls,
        encoding=settings.ftp_encoding,
    )


def get_recipient_extractor() -> RecipientExtractorService:
    return RecipientExtractorService(
        cache_service=get_cache_service(),
        llm_service=get_llm_service(),
        ftp_file_service=get_ftp_file_service(),
    )
