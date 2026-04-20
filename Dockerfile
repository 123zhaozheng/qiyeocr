FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/

ENV PYTHONPATH=/app/src

CMD [".venv/bin/uvicorn", "qiweiocr.app:app", "--host", "0.0.0.0", "--port", "8000"]
