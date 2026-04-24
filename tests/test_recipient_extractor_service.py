from __future__ import annotations

import pytest

from qiweiocr.schemas.recipient import ExtractType
from qiweiocr.services.recipient_extractor import RecipientExtractorService


class StubCacheService:
    def __init__(self) -> None:
        self.storage: dict[str, dict] = {}

    async def get_json(self, key: str) -> dict | None:
        return self.storage.get(key)

    async def set_json(self, key: str, value: dict) -> None:
        self.storage[key] = value


class StubFtpFileService:
    def __init__(self) -> None:
        self.paths: list[str] = []

    async def download_base64(self, remote_path: str) -> str:
        self.paths.append(remote_path)
        return "ftp-base64-content"


class StubLlmService:
    def __init__(self) -> None:
        self.calls: list[tuple[ExtractType, str]] = []

    async def extract(self, extract_type: ExtractType, content: str) -> dict[str, str]:
        self.calls.append((extract_type, content))
        return {
            "Acctno": "6222000000000000000",
            "Accnm": "测试公司",
            "BankNo": "102100099996",
            "AcctnoBankName": "中国工商银行北京分行",
        }


@pytest.mark.asyncio
async def test_image_request_downloads_file_from_ftp_before_calling_llm() -> None:
    cache_service = StubCacheService()
    ftp_file_service = StubFtpFileService()
    llm_service = StubLlmService()
    service = RecipientExtractorService(
        cache_service=cache_service,
        llm_service=llm_service,
        ftp_file_service=ftp_file_service,
    )

    response = await service.extract(ExtractType.IMAGE, "/incoming/a.png")

    assert ftp_file_service.paths == ["/incoming/a.png"]
    assert llm_service.calls == [(ExtractType.IMAGE, "ftp-base64-content")]
    assert response.BufferDesc is False


@pytest.mark.asyncio
async def test_cached_image_request_skips_ftp_and_llm() -> None:
    cache_service = StubCacheService()
    ftp_file_service = StubFtpFileService()
    llm_service = StubLlmService()
    service = RecipientExtractorService(
        cache_service=cache_service,
        llm_service=llm_service,
        ftp_file_service=ftp_file_service,
    )

    await service.extract(ExtractType.IMAGE, "/incoming/a.png")
    cached = await service.extract(ExtractType.IMAGE, "/incoming/a.png")

    assert ftp_file_service.paths == ["/incoming/a.png"]
    assert llm_service.calls == [(ExtractType.IMAGE, "ftp-base64-content")]
    assert cached.BufferDesc is True
