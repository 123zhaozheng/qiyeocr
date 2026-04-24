## Recipient Extract API

FastAPI service for bank recipient extraction with:

- direct JSON request support
- ESB route-level unwrap/wrap
- Redis cache
- OpenAI-compatible text and image model calls
- image mode can fetch files from FTP by remote path

### Request

- `DataFormat=text` or `type=text`: `EssayContent`/`content` 传原始文本
- `DataFormat=image` or `type=image`: `EssayContent`/`content` 传 FTP 文件路径，服务端按配置主动下载后再调用多模态模型

ESB request body uses `Request.Input` as the business payload, for example:

```json
{
  "ReqInfo": {
    "TranCode": "TEST001"
  },
  "Request": {
    "Input": {
      "DataFormat": "text",
      "EssayContent": "张三丰 6212263602001234567 工商银行"
    }
  }
}
```

### FTP Config

Configure these env vars when image requests use FTP:

```bash
FTP_HOST=127.0.0.1
FTP_PORT=21
FTP_USERNAME=demo
FTP_PASSWORD=demo
FTP_BASE_DIR=/upload/qiweiocr
FTP_TIMEOUT_SECONDS=30
FTP_PASSIVE=true
FTP_USE_TLS=false
FTP_ENCODING=utf-8
```

### Run

```bash
uv sync
uv run uvicorn qiweiocr.app:app --host 0.0.0.0 --port 8000
```

### Test

```bash
uv run pytest
```
