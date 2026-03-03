FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api/src:/app/packages/analyzer-core/src

WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN /app/.venv/bin/python -m ensurepip --upgrade && \
    /app/.venv/bin/python -m spacy download ru_core_news_sm && \
    /app/.venv/bin/python -m spacy download en_core_web_sm

COPY apps ./apps
COPY packages ./packages

EXPOSE 8000
CMD ["/bin/sh", "-c", "uv run alembic -c apps/api/alembic.ini upgrade head && uv run uvicorn chat_analyzer_api.main:app --host 0.0.0.0 --port 8000"]
