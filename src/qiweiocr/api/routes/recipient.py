from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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
    preview = payload.EssayContent[:80] + "..." if len(payload.EssayContent) > 80 else payload.EssayContent
    logger.info("[请求接收] DataFormat=%s | EssayContent=%s", payload.DataFormat, preview)
    try:
        result = await extractor.extract(payload.DataFormat, payload.EssayContent)
        logger.info("[请求完成] 返回结果: %s", result.model_dump())
        return result
    except LlmExtractionError:
        logger.warning("[请求失败] LLM 提取异常，返回 400")
        return JSONResponse(
            status_code=400,
            content={"message": "提取失败，请手动填写"},
        )
    except Exception:
        logger.exception("[请求失败] 未知异常，返回 500")
        return JSONResponse(
            status_code=500,
            content={"message": "提取失败，请手动填写"},
        )
