## Recipient Extract API

FastAPI service for bank recipient extraction with:

- direct JSON request support
- ESB route-level unwrap/wrap
- Redis cache
- OpenAI-compatible text and image model calls

### Run

```bash
uv sync
uv run uvicorn qiweiocr.app:app --host 0.0.0.0 --port 8000
```

### Test

```bash
uv run pytest
```
