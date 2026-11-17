# Servicio IA — Recomendación (Python 3.12 según ADR-09)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Dependencias primero: se reutiliza la capa si solo cambia el código.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY migraciones ./migraciones
COPY src ./src

# Sin privilegios de root.
RUN useradd --create-home --uid 10001 ia
USER ia

EXPOSE 8000

# El balanceador y Docker usan /health/ready: si la base no responde, el contenedor no está listo.
HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).status == 200 else 1)"

# IA_WORKERS: procesos de Python que atienden en paralelo (uno por vCPU; las VMs de ADR-08 tienen 2).
ENV IA_WORKERS=2

# IA_MIGRAR_AL_INICIAR=1 aplica las migraciones antes de arrancar (útil en local).
# En producción, con dos réplicas, conviene migrar una sola vez desde el despliegue.
CMD ["sh", "-c", "if [ \"$IA_MIGRAR_AL_INICIAR\" = \"1\" ]; then alembic upgrade head; fi && exec uvicorn ia.main:app --host 0.0.0.0 --port 8000 --proxy-headers --workers ${IA_WORKERS}"]
