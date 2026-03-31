from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from qiweiocr.api.routes.recipient import router as recipient_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Recipient Extract API",
        version="1.0.0",
        description="Bank recipient extraction service with ESB support.",
    )
    app.include_router(recipient_router)
    return app


app = create_app()


def main() -> None:
    uvicorn.run("qiweiocr.app:app", host="0.0.0.0", port=8000, reload=False)
