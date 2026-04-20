from __future__ import annotations

import hashlib
import logging

from qiweiocr.schemas.recipient import ExtractRecipientResponse
from qiweiocr.schemas.recipient import ExtractType
from qiweiocr.services.cache import CacheService
from qiweiocr.services.llm import LlmService

logger = logging.getLogger(__name__)


class RecipientExtractorService:
    def __init__(self, cache_service: CacheService, llm_service: LlmService) -> None:
        self.cache_service = cache_service
        self.llm_service = llm_service

    async def extract(self, extract_type: ExtractType, content: str) -> ExtractRecipientResponse:
        cache_suffix = self._hash_key(extract_type=extract_type, content=content)
        logger.info("[缓存] 查询 key=%s", cache_suffix)

        cached = await self.cache_service.get_json(cache_suffix)
        if cached:
            logger.info("[缓存] 命中，直接返回缓存结果")
            cached["BufferDesc"] = True
            return ExtractRecipientResponse.model_validate(cached)

        logger.info("[缓存] 未命中，调用 LLM 提取 | type=%s", extract_type)
        extracted = await self.llm_service.extract(extract_type=extract_type, content=content)
        normalized = ExtractRecipientResponse.model_validate(extracted).model_dump()
        normalized["BufferDesc"] = False

        has_result = any(normalized.get(f) for f in ("Acctno", "Accnm", "BankNo", "AcctnoBankName"))
        if has_result:
            logger.info("[LLM] 提取完成，写入缓存")
            await self.cache_service.set_json(cache_suffix, normalized)
        else:
            logger.warning("[LLM] 提取结果全部为空，跳过缓存")

        return ExtractRecipientResponse.model_validate(normalized)

    @staticmethod
    def _hash_key(extract_type: ExtractType, content: str) -> str:
        payload = f"{extract_type.value}|{content}".encode("utf-8")
        return hashlib.md5(payload, usedforsecurity=False).hexdigest()
