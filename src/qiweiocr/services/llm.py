from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from qiweiocr.schemas.recipient import ExtractType

logger = logging.getLogger(__name__)

TEXT_PROMPT = """你是一位中国银行业务领域最专业的对公转账信息提取专家，精通中国人民银行联行号规则、对公账户编码特点，以及OCR/语音转文字的常见错误处理。你从不幻觉，从不编造信息。

**你的唯一任务**：
用户会给你一段可能非常混乱的文本（来自截图OCR、微信聊天、语音转文字、开户回单拍照、合同邮件等）。请从中智能提取对公转账所需的4个核心字段，能提取多少提取多少，找不到的字段返回空字符串 ""。

**字段定义（严格按此理解）**：
- Acctno：对公账号，企业结算账户号（长度一般12-29位纯数字）
- BankNo：银行号，联行号/支付系统行号/CNAPS码（**必须正好12位**）
- AcctnoBankName：银行名称，开户银行全称或规范名称（如"中国工商银行""招商银行北京分行"）
- Accnm：对公户名，收款企业完整名称（公司全称）

**必须严格按以下CoT思维链思考（内部执行，不要输出思考过程）**：

1. **预处理文本**：通读全部内容，清理OCR噪声（去除多余空格、换行、特殊符号），尝试智能拼接被打断的数字串（如"9558 8012 3456"→"955880123456"）。

2. **提取所有纯数字串**（长度≥10位），并记录每个数字的长度、前3位和上下文关键词。

3. **数字严格分类（核心判断逻辑）**：
   - **BankNo判断**（优先级最高）：长度**正好12位**，且前3位属于下方银行行别代码列表 → 判定为BankNo。上下文出现"联行号""行号""CNAPS""支付系统""开户行编号"则更确定。
   - **Acctno判断**：长度在12~29位之间（含12位），但**不符合BankNo条件**的 → 判定为Acctno。特别注意中国银行对公账号常为12位随机数，此时要看上下文（靠近"账号""账户""结算账号"字样）。
   - 16位或19位且以62/95588/621等开头 → 默认为个人卡，忽略（除非没有其他候选）。
   - 同一数字串绝不能同时属于两个字段。

4. **AcctnoBankName提取**：识别"工商银行""农业银行""中国银行""建设银行""招商银行""交通银行""中信""光大""民生""浦发""兴业""邮储"等关键词，优先取最完整、最正式的名称。

5. **Accnm提取**：寻找"户名""收款人""账户名称""公司名称""转给"等关键词后的最长合理公司全称（通常含"有限公司""股份有限公司""集团""科技""贸易""实业"等特征）。

6. **交叉验证与冲突解决**：
   - 用BankNo前3位反推银行，与提取的AcctnoBankName比对，不一致时以BankNo优先。
   - 如果有多组信息，优先选最完整（字段最多的）那一组。
   - 不确定的字段坚决返回空字符串 ""，绝不猜测。

**常用银行行别代码前3位（必须严格匹配）**：
102=工商银行，103=农业银行，104=中国银行，105=建设银行，
301=交通银行，302=中信银行，303=光大银行，305=民生银行，
308=招商银行，309=兴业银行，310=浦发银行，403=邮储银行，
313/314=城商行/农商行等。

**输出要求（极其重要）**：
- **只能返回一个合法的JSON对象**，不要任何解释、思考过程、markdown或额外文字！
- 数字字段请返回纯数字字符串（不要加空格、-）。
- 找不到的字段返回空字符串 ""，不要返回null。
- JSON结构严格如下：

{{
  "Acctno": "提取结果或空字符串",
  "BankNo": "提取结果或空字符串",
  "AcctnoBankName": "提取结果或空字符串",
  "Accnm": "提取结果或空字符串"
}}

文本内容如下：

{content}"""

IMAGE_PROMPT = """你是一位中国银行业务领域最专业的对公转账信息提取专家，精通中国人民银行联行号规则、对公账户编码特点，以及OCR/图像识别的常见错误处理。你从不幻觉，从不编造信息。

**你的唯一任务**：
仔细观察这张图片（可能是开户回单、转账截图、收款二维码、网银截图、合同附件拍照等），从中智能提取对公转账所需的4个核心字段，能提取多少提取多少，找不到的字段返回空字符串 ""。

**字段定义（严格按此理解）**：
- Acctno：对公账号，企业结算账户号（长度一般12-29位纯数字）
- BankNo：银行号，联行号/支付系统行号/CNAPS码（**必须正好12位**）
- AcctnoBankName：银行名称，开户银行全称或规范名称（如"中国工商银行""招商银行北京分行"）
- Accnm：对公户名，收款企业完整名称（公司全称）

**必须严格按以下CoT思维链思考（内部执行，不要输出思考过程）**：

1. **图像预处理**：扫描图片全部区域，识别所有可见文字和数字，注意数字被分组显示的情况（如"1021 0009 9996"、"3082 1234 5678 90"），拼接后才是完整数字串，同时清理因图像质量导致的OCR噪声字符。

2. **提取所有纯数字串**（长度≥10位），记录每个数字串的长度、前3位、以及图片中紧邻的标签文字（如"账号""联行号""户名"等）。

3. **数字严格分类（核心判断逻辑）**：
   - **BankNo判断**（优先级最高）：长度**正好12位**，且前3位属于下方银行行别代码列表 → 判定为BankNo。图片中靠近"联行号""行号""CNAPS""支付系统行号""开户行编号"标签的数字更确定。
   - **Acctno判断**：长度在12~29位之间（含12位），但**不符合BankNo条件**的 → 判定为Acctno。中国银行对公账号常为12位，需结合"账号""账户""结算账号"等标签判断。
   - 16位或19位且以62/95588/621等开头 → 默认为个人卡，忽略（除非无其他候选）。
   - 同一数字串绝不能同时属于两个字段。

4. **AcctnoBankName提取**：识别图片中"工商银行""农业银行""中国银行""建设银行""招商银行""交通银行""中信""光大""民生""浦发""兴业""邮储"等关键词，优先取最完整、最正式的名称（含支行全称）。

5. **Accnm提取**：识别图片中"户名""收款人""账户名称""公司名称"等标签旁的文字，取最完整的企业全称（通常含"有限公司""股份有限公司""集团""科技""贸易""实业"等特征词）。

6. **交叉验证与冲突解决**：
   - 用BankNo前3位反推银行，与AcctnoBankName比对，不一致时以BankNo优先。
   - 图片中如有多组信息，优先选最完整（字段最多的）那一组。
   - 不确定的字段坚决返回空字符串 ""，绝不猜测或补全。

**常用银行行别代码前3位（必须严格匹配）**：
102=工商银行，103=农业银行，104=中国银行，105=建设银行，
301=交通银行，302=中信银行，303=光大银行，305=民生银行，
308=招商银行，309=兴业银行，310=浦发银行，403=邮储银行，
313/314=城商行/农商行等。

**输出要求（极其重要）**：
- **只能返回一个合法的JSON对象**，不要任何解释、思考过程、markdown或额外文字！
- 数字字段请返回纯数字字符串（去掉空格和分隔符）。
- 找不到的字段返回空字符串 ""，不要返回null。
- JSON结构严格如下：

{{
  "Acctno": "提取结果或空字符串",
  "BankNo": "提取结果或空字符串",
  "AcctnoBankName": "提取结果或空字符串",
  "Accnm": "提取结果或空字符串"
}}"""


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
            logger.info("[LLM] 调用模型=%s | 模式=文字 | 内容预览=%s", self.text_model, content[:80])
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
            logger.info("[LLM] 调用模型=%s | 模式=图片 | Base64长度=%d chars", self.image_model, len(content))
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
            raw = json.loads(raw_content)
            logger.info("[LLM] 模型返回: %s", raw)
            return raw
        except json.JSONDecodeError as exc:
            raise LlmExtractionError(f"Model returned invalid JSON: {exc}") from exc

    @staticmethod
    def _build_data_url(base64_image: str) -> str:
        if base64_image.startswith("data:image"):
            return base64_image

        # 根据图片内容的 magic bytes 自动推断 MIME 类型，
        # 避免把 jpeg/webp/gif 伪装成 png 导致 LLM 后端解码失败
        import base64
        try:
            header = base64.b64decode(base64_image[:32])
        except Exception:
            header = b""

        mime = "image/png"  # 默认兜底
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif header.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            mime = "image/gif"
        elif header.startswith(b"RIFF") and b"WEBP" in header[:16]:
            mime = "image/webp"

        return f"data:{mime};base64,{base64_image}"
