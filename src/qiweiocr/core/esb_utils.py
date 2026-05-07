from __future__ import annotations

import threading
import time
from copy import deepcopy
from datetime import date
from enum import Enum
from typing import Any


APP_NAME = "AIMP"


class Counter:
    __slots__ = ("_lock", "_value", "_last_ms")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value = 0
        self._last_ms = 0

    def get_next(self) -> tuple[int, int]:
        current_ms = int(time.time() * 1000)
        with self._lock:
            if current_ms != self._last_ms:
                self._value = 0
                self._last_ms = current_ms
            self._value += 1
            seq_val = self._value % 1_000_000
            return current_ms, seq_val


counter = Counter()


class EsbRespStatus(Enum):
    SUCCESS = ("S", "成功")
    FAIL = ("F", "失败")
    UNKNOWN = ("U", "未知")
    UN_AUTH = ("A", "需要授权")

    def __init__(self, code: str, msg: str) -> None:
        self._code = code
        self._msg = msg

    @property
    def code(self) -> str:
        return self._code

    @property
    def msg(self) -> str:
        return self._msg


class RspInfoDto:
    def __init__(self) -> None:
        self.rsp_info: dict[str, Any] = {
            "IttrDt": "",
            "IttrStmInd": "",
            "IttrChlInd": "",
            "GloSeqNum": "",
            "I18nInd": "",
            "ReqStmInd": "",
            "SvcNo": "",
            "ScnNo": "",
            "SvcVerNo": "",
            "ScnVerNo": "",
            "ReqStmDt": "",
            "ReqStmTm": "",
            "ReqSeqNum": "",
            "LegOrgId": "",
            "MAC": None,
            "BckInd": None,
            "BckId": None,
            "SvcStmInd": "",
            "SvcStmTxnDt": "",
            "SvcStmRespSeqNum": "",
            "TechFlw": None,
            "RespSt": "",
            "RespInfo": "",
            "RespInfoDsc": "",
        }

    @staticmethod
    def generate_response_seq() -> str:
        now = time.localtime()
        date_part = time.strftime("%Y%m%d", now)
        timestamp_ms, seq_val = counter.get_next()
        timestamp_part = str(timestamp_ms % 10**10).zfill(10)[-10:]
        seq_part = str(seq_val).zfill(6)[-6:]
        unique_code = timestamp_part + seq_part
        return f"R{APP_NAME}{date_part}000{unique_code}"

    def build_rsp_info_dto(
        self,
        request: dict[str, Any],
        resp_st: EsbRespStatus,
        resp_info_code: str,
        desc: str,
    ) -> RspInfoDto:
        req_info = request.get("ReqInfo", {})
        self.rsp_info["IttrDt"] = req_info.get("IttrDt", "")
        self.rsp_info["IttrStmInd"] = req_info.get("IttrStmInd", "")
        self.rsp_info["IttrChlInd"] = req_info.get("IttrChlInd", "")
        self.rsp_info["GloSeqNum"] = req_info.get("GloSeqNum", "")
        self.rsp_info["I18nInd"] = req_info.get("I18nInd", "")
        self.rsp_info["ReqStmInd"] = req_info.get("ReqStmInd", "")
        self.rsp_info["ReqStmDt"] = req_info.get("ReqStmDt", "")
        self.rsp_info["ReqStmTm"] = req_info.get("ReqStmTm", "")
        self.rsp_info["SvcNo"] = req_info.get("SvcNo", "")
        self.rsp_info["ScnNo"] = req_info.get("ScnNo", "")
        self.rsp_info["SvcVerNo"] = req_info.get("SvcVerNo", "")
        self.rsp_info["ScnVerNo"] = req_info.get("ScnVerNo", "")
        self.rsp_info["ReqSeqNum"] = req_info.get("ReqSeqNum", "")
        self.rsp_info["LegOrgId"] = req_info.get("LegOrgId", "")
        self.rsp_info["SvcStmInd"] = APP_NAME
        self.rsp_info["SvcStmTxnDt"] = date.today().isoformat()
        self.rsp_info["SvcStmRespSeqNum"] = self.generate_response_seq()
        self.rsp_info["RespSt"] = resp_st.code
        self.rsp_info["RespInfo"] = APP_NAME + resp_info_code
        self.rsp_info["RespInfoDsc"] = desc
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.rsp_info


class EsbWrapper:
    @staticmethod
    def unwrap_request(esb_request: dict[str, Any]) -> dict[str, Any]:
        if "Request" not in esb_request:
            raise ValueError("Invalid ESB request: missing 'Request' field")

        request_data = esb_request["Request"]

        for key in ("Input", "input", "InPut", "INPUT"):
            if key in request_data:
                return request_data[key]

        if isinstance(request_data, dict) and request_data:
            return request_data

        raise ValueError("Invalid ESB request: missing 'Input' field in Request")

    @staticmethod
    def wrap_response(
        esb_request: dict[str, Any],
        business_data: dict[str, Any],
        resp_st: EsbRespStatus,
        resp_info_code: str,
        desc: str,
    ) -> dict[str, Any]:
        rsp_info_dto = RspInfoDto()
        rsp_info_dto.build_rsp_info_dto(esb_request, resp_st, resp_info_code, desc)
        return {
            "RspInfo": rsp_info_dto.to_dict(),
            "Response": {
                "OutPut": business_data,
            },
        }

    @staticmethod
    def wrap_error_response(
        esb_request: dict[str, Any],
        error_message: str,
        error_code: str,
    ) -> dict[str, Any]:
        rsp_info_dto = RspInfoDto()
        rsp_info_dto.build_rsp_info_dto(esb_request, EsbRespStatus.FAIL, error_code, error_message)
        return {
            "RspInfo": rsp_info_dto.to_dict(),
            "Response": {
                "OutPut": {},
            },
        }

    @staticmethod
    def clone_esb_request(esb_request: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(esb_request)
