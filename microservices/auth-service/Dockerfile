FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY src/ ./src/
COPY migrations/ ./migrations/

RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 appuser

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn auth_service.api.main:app --host 0.0.0.0 --port 8000"]
