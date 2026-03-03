FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api/src:/app/packages/analyzer-core/src

WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY apps ./apps
COPY packages ./packages

EXPOSE 8000
CMD [".venv/bin/uvicorn", "chat_analyzer_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
