from __future__ import annotations

from fastapi.testclient import TestClient

from qiweiocr.app import create_app
from qiweiocr.dependencies import get_recipient_extractor
from qiweiocr.schemas.recipient import ExtractRecipientResponse
from qiweiocr.schemas.recipient import ExtractType
from qiweiocr.services.llm import LlmExtractionError


class StubExtractor:
    def __init__(self, response: ExtractRecipientResponse | None = None, raise_error: bool = False) -> None:
        self.response = response or ExtractRecipientResponse(
            Acctno="6212263602001234567",
            Accnm="张三丰",
            BankNo="102100099996",
            AcctnoBankName="中国工商银行北京市海淀区支行",
            BufferDesc=False,
        )
        self.raise_error = raise_error

    async def extract(self, extract_type: ExtractType, content: str) -> ExtractRecipientResponse:
        _ = (extract_type, content)
        if self.raise_error:
            raise LlmExtractionError("bad output")
        return self.response


def build_client(stub: StubExtractor) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_recipient_extractor] = lambda: stub
    return TestClient(app)


def test_direct_request_returns_business_json() -> None:
    client = build_client(StubExtractor())

    response = client.post(
        "/api/v1/extract-recipient",
        json={"type": "text", "content": "张三丰 6212263602001234567 工商银行"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "Acctno": "6212263602001234567",
        "Accnm": "张三丰",
        "BankNo": "102100099996",
        "AcctnoBankName": "中国工商银行北京市海淀区支行",
        "BufferDesc": False,
    }


def test_esb_request_returns_esb_payload() -> None:
    client = build_client(StubExtractor())

    response = client.post(
        "/api/v1/extract-recipient",
        json={
            "ReqInfo": {"TranCode": "TEST001"},
            "Request": {"type": "text", "content": "张三丰 6212263602001234567 工商银行"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "RspInfo": {"RspCode": "0000", "RspDesc": "成功"},
        "Response": {
            "Acctno": "6212263602001234567",
            "Accnm": "张三丰",
            "BankNo": "102100099996",
            "AcctnoBankName": "中国工商银行北京市海淀区支行",
            "BufferDesc": False,
        },
    }


def test_esb_error_wrapped_with_http_200() -> None:
    client = build_client(StubExtractor(raise_error=True))

    response = client.post(
        "/api/v1/extract-recipient",
        json={
            "ReqInfo": {"TranCode": "TEST001"},
            "Request": {"type": "text", "content": "bad"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "RspInfo": {"RspCode": "400", "RspDesc": "提取失败，请手动填写"},
        "Response": {},
    }
