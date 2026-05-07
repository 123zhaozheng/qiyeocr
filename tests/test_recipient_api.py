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
            "Request": {
                "Input": {
                    "DataFormat": "text",
                    "EssayContent": "张三丰 6212263602001234567 工商银行",
                }
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["RspInfo"]["RespSt"] == "S"
    assert data["RspInfo"]["RespInfo"] == "AIMP000000"
    assert data["RspInfo"]["RespInfoDsc"] == "成功"
    assert data["RspInfo"]["SvcStmInd"] == "AIMP"
    assert data["RspInfo"]["SvcStmRespSeqNum"].startswith("RAIMP")
    assert data["Response"]["OutPut"] == {
        "Acctno": "6212263602001234567",
        "Accnm": "张三丰",
        "BankNo": "102100099996",
        "AcctnoBankName": "中国工商银行北京市海淀区支行",
        "BufferDesc": False,
    }


def test_esb_error_wrapped_with_http_200() -> None:
    client = build_client(StubExtractor(raise_error=True))

    response = client.post(
        "/api/v1/extract-recipient",
        json={
            "ReqInfo": {"TranCode": "TEST001"},
            "Request": {
                "Input": {
                    "DataFormat": "text",
                    "EssayContent": "bad",
                }
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["RspInfo"]["RespSt"] == "F"
    assert data["RspInfo"]["RespInfo"] == "AIMP400"
    assert data["RspInfo"]["RespInfoDsc"] == "提取失败，请手动填写"
    assert data["RspInfo"]["SvcStmInd"] == "AIMP"
    assert data["Response"]["OutPut"] == {}
