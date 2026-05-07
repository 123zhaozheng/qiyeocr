from __future__ import annotations

import json
import logging
from typing import Any
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from fastapi.routing import APIRoute

from qiweiocr.core.esb_utils import EsbRespStatus
from qiweiocr.core.esb_utils import EsbWrapper

logger = logging.getLogger(__name__)


class EsbRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            esb_request: dict[str, Any] | None = None
            new_body_bytes: bytes | None = None

            if request.method in ("POST", "PUT", "PATCH"):
                try:
                    raw = await request.body()
                    if raw:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict) and "ReqInfo" in parsed and "Request" in parsed:
                            esb_request = parsed
                            business_data = EsbWrapper.unwrap_request(parsed)
                            new_body_bytes = json.dumps(business_data).encode("utf-8")
                            logger.info("[ESB] Unwrapped request on %s", request.url.path)
                except json.JSONDecodeError:
                    logger.debug("[ESB] Non-JSON body, bypassing ESB unwrap")
                except Exception as exc:
                    logger.error("[ESB] Failed to unwrap ESB request: %s", exc, exc_info=True)
                    if esb_request:
                        esb_error = EsbWrapper.wrap_error_response(
                            esb_request=esb_request,
                            error_message=str(exc),
                            error_code="4001",
                        )
                        return JSONResponse(content=esb_error, status_code=200)
                    return JSONResponse(
                        status_code=400,
                        content={"error": True, "message": f"Invalid ESB request: {exc}"},
                    )

            if esb_request and new_body_bytes is not None:
                async def receive() -> dict[str, Any]:
                    return {"type": "http.request", "body": new_body_bytes, "more_body": False}

                request._receive = receive  # type: ignore[attr-defined]
                setattr(request, "_body", new_body_bytes)
                request.state.esb_request = esb_request

            response = await original_route_handler(request)

            if not getattr(request.state, "esb_request", None):
                return response

            try:
                body_bytes = b""
                if hasattr(response, "body_iterator"):
                    async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                        body_bytes += chunk
                else:
                    raw = getattr(response, "body", b"")
                    if raw is None:
                        body_bytes = b""
                    elif isinstance(raw, (bytes, bytearray, memoryview)):
                        body_bytes = bytes(raw)
                    else:
                        body_bytes = bytes(raw)

                try:
                    business_resp = json.loads(body_bytes) if body_bytes else {}
                except json.JSONDecodeError:
                    logger.warning("[ESB] Response is not JSON, returning as-is")
                    return Response(
                        content=body_bytes,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                        background=getattr(response, "background", None),
                    )

                if 200 <= response.status_code < 300:
                    esb_resp = EsbWrapper.wrap_response(
                        esb_request=request.state.esb_request,
                        business_data=business_resp,
                        resp_st=EsbRespStatus.SUCCESS,
                        resp_info_code="000000",
                        desc="成功",
                    )
                else:
                    msg = business_resp.get("message") or business_resp.get("detail") or "Unknown error"
                    esb_resp = EsbWrapper.wrap_error_response(
                        esb_request=request.state.esb_request,
                        error_message=msg,
                        error_code=str(response.status_code),
                    )

                passthrough_headers = {
                    key: value
                    for key, value in dict(response.headers).items()
                    if key.lower() != "content-length"
                }
                return JSONResponse(
                    content=esb_resp,
                    status_code=200,
                    headers=passthrough_headers,
                    background=getattr(response, "background", None),
                )
            except Exception as exc:
                logger.error("[ESB] Failed to wrap ESB response: %s", exc, exc_info=True)
                try:
                    esb_resp = EsbWrapper.wrap_error_response(
                        esb_request=request.state.esb_request,
                        error_message=str(exc),
                        error_code="9999",
                    )
                    return JSONResponse(
                        content=esb_resp,
                        status_code=200,
                        background=getattr(response, "background", None),
                    )
                except Exception:
                    return JSONResponse(
                        status_code=500,
                        content={"error": True, "message": "Internal server error"},
                    )

        return custom_route_handler


def get_esb_ctx(request: Request) -> dict[str, Any] | None:
    return getattr(request.state, "esb_request", None)
