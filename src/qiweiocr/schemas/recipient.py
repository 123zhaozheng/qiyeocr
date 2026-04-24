from __future__ import annotations

from enum import StrEnum

from pydantic import AliasChoices
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ExtractType(StrEnum):
    TEXT = "text"
    IMAGE = "image"


class ExtractRecipientRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    DataFormat: ExtractType = Field(
        validation_alias=AliasChoices("DataFormat", "type"),
        serialization_alias="DataFormat",
    )
    EssayContent: str = Field(
        min_length=1,
        validation_alias=AliasChoices("EssayContent", "content"),
        serialization_alias="EssayContent",
        description="文本模式传原始文本；图片模式传 FTP 文件路径。",
    )


class ExtractRecipientResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    Acctno: str = ""
    Accnm: str = ""
    BankNo: str = ""
    AcctnoBankName: str = ""
    BufferDesc: bool = False


class ErrorResponse(BaseModel):
    message: str
