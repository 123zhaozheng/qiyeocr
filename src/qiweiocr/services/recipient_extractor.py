from __future__ import annotations

import hashlib

from qiweiocr.schemas.recipient import ExtractRecipientResponse
from qiweiocr.schemas.recipient import ExtractType
from qiweiocr.services.cache import CacheService
from qiweiocr.services.llm import LlmService


class RecipientExtractorService:
    def __init__(self, cache_service: CacheService, llm_service: LlmService) -> None:
        self.cache_service = cache_service
        self.llm_service = llm_service

    async def extract(self, extract_type: ExtractType, content: str) -> ExtractRecipientResponse:
        cache_suffix = self._hash_key(extract_type=extract_type, content=content)
        cached = await self.cache_service.get_json(cache_suffix)
        if cached:
            cached["BufferDesc"] = True
            return ExtractRecipientResponse.model_validate(cached)

        extracted = await self.llm_service.extract(extract_type=extract_type, content=content)
        normalized = ExtractRecipientResponse.model_validate(extracted).model_dump()
        normalized["BufferDesc"] = False
        await self.cache_service.set_json(cache_suffix, normalized)
        return ExtractRecipientResponse.model_validate(normalized)

    @staticmethod
    def _hash_key(extract_type: ExtractType, content: str) -> str:
        payload = f"{extract_type.value}|{content}".encode("utf-8")
        return hashlib.md5(payload, usedforsecurity=False).hexdigest()
