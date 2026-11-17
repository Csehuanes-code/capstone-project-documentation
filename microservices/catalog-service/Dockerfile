# Multi-stage build for Catálogo microservice (ADR-08, ADR-09)
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# hatchling necesita el README (readme del pyproject) y el paquete para instalar.
COPY pyproject.toml README.md ./
COPY catalog_service ./catalog_service
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd -r catalog && useradd -r -g catalog -u 1000 catalog

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY catalog_service ./catalog_service
COPY alembic.ini .

USER catalog

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')" || exit 1

CMD ["uvicorn", "catalog_service.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
