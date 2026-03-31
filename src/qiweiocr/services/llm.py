from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from qiweiocr.schemas.recipient import ExtractType

TEXT_PROMPT = """你是一位专业的银行转账信息提取助手。
请从以下用户提供的文本中，准确提取以下字段，只返回严格的 JSON，不要添加任何解释、备注或多余文字。
字段名必须严格使用以下英文名称：
- Acctno：收款人账号（通常18-19位数字）
- Accnm：收款人姓名/户名
- BankNo：银行联行号 / 银行号（通常12位数字）
- AcctnoBankName：开户行全称或规范简称

找不到的字段返回空字符串 ""。
文本内容如下：

{content}"""

IMAGE_PROMPT = """你是一位专业的银行转账信息提取助手。
请仔细观察这张图片（可能是收款二维码、转账截图、纸质回单、手机短信截图等），准确提取以下字段，只返回严格的 JSON，不要添加任何解释、备注或多余文字。
字段名必须严格使用以下英文名称：
{
  "Acctno": "收款人账号",
  "Accnm": "收款人姓名/户名",
  "BankNo": "银行联行号 / 银行号",
  "AcctnoBankName": "开户行名称"
}

找不到或无法识别的字段返回空字符串 ""。"""


class LlmExtractionError(RuntimeError):
    pass


class LlmService:
    def __init__(
        self,
        api_key: str,
        base_url: str | None,
        text_model: str,
        image_model: str,
        timeout_seconds: float,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
        self.text_model = text_model
        self.image_model = image_model

    async def extract(self, extract_type: ExtractType, content: str) -> dict[str, Any]:
        if extract_type == ExtractType.TEXT:
            response = await self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {
                        "role": "user",
                        "content": TEXT_PROMPT.format(content=content),
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        else:
            response = await self.client.chat.completions.create(
                model=self.image_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": IMAGE_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": self._build_data_url(content),
                                },
                            },
                        ],
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )

        raw_content = response.choices[0].message.content
        if not raw_content:
            raise LlmExtractionError("Model returned empty content")
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise LlmExtractionError(f"Model returned invalid JSON: {exc}") from exc

    @staticmethod
    def _build_data_url(base64_image: str) -> str:
        if base64_image.startswith("data:image"):
            return base64_image
        return f"data:image/png;base64,{base64_image}"
