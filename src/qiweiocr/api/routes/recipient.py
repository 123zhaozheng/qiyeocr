from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import JSONResponse

from qiweiocr.core.esb_route import EsbRoute
from qiweiocr.core.esb_route import get_esb_ctx
from qiweiocr.dependencies import get_recipient_extractor
from qiweiocr.schemas.recipient import ErrorResponse
from qiweiocr.schemas.recipient import ExtractRecipientRequest
from qiweiocr.schemas.recipient import ExtractRecipientResponse
from qiweiocr.services.llm import LlmExtractionError
from qiweiocr.services.recipient_extractor import RecipientExtractorService

router = APIRouter(route_class=EsbRoute)


@router.post(
    "/api/v1/extract-recipient",
    response_model=ExtractRecipientResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def extract_recipient(
    payload: ExtractRecipientRequest,
    extractor: RecipientExtractorService = Depends(get_recipient_extractor),
    esb_ctx: dict[str, Any] | None = Depends(get_esb_ctx),
) -> ExtractRecipientResponse | JSONResponse:
    _ = esb_ctx
    try:
        return await extractor.extract(payload.type, payload.content)
    except LlmExtractionError:
        return JSONResponse(
            status_code=400,
            content={"message": "提取失败，请手动填写"},
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"message": "提取失败，请手动填写"},
        )
