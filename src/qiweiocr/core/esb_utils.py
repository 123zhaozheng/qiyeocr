from __future__ import annotations

from copy import deepcopy
from enum import StrEnum
from typing import Any


class EsbRespStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class EsbWrapper:
    @staticmethod
    def unwrap_request(esb_request: dict[str, Any]) -> dict[str, Any]:
        request = esb_request.get("Request")
        if not isinstance(request, dict):
            raise ValueError("ESB Request must be an object")
        return request

    @staticmethod
    def wrap_response(
        esb_request: dict[str, Any],
        business_data: dict[str, Any],
        resp_st: EsbRespStatus,
        resp_info_code: str,
        desc: str,
    ) -> dict[str, Any]:
        _ = resp_st
        return {
            "RspInfo": {
                "RspCode": resp_info_code,
                "RspDesc": desc,
            },
            "Response": business_data,
        }

    @staticmethod
    def wrap_error_response(
        esb_request: dict[str, Any],
        error_message: str,
        error_code: str,
    ) -> dict[str, Any]:
        _ = esb_request
        return {
            "RspInfo": {
                "RspCode": error_code,
                "RspDesc": error_message,
            },
            "Response": {},
        }

    @staticmethod
    def clone_esb_request(esb_request: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(esb_request)
