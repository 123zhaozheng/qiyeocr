from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ExtractType(StrEnum):
    TEXT = "text"
    IMAGE = "image"


class ExtractRecipientRequest(BaseModel):
    type: ExtractType
    content: str = Field(min_length=1)


class ExtractRecipientResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    Acctno: str = ""
    Accnm: str = ""
    BankNo: str = ""
    AcctnoBankName: str = ""
    BufferDesc: bool = False


class ErrorResponse(BaseModel):
    message: str
