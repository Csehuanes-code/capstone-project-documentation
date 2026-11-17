import json
import logging
import time
from datetime import datetime, timezone
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from comun.correlacion import obtener_correlation_id


class JsonFormatter(logging.Formatter):
    """Formateador de logs estructurados en JSON."""

    def __init__(self, nombre_servicio: str):
        super().__init__()
        self.nombre_servicio = nombre_servicio

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nivel": record.levelname,
            "servicio": self.nombre_servicio,
            "logger": record.name,
            "mensaje": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None) or obtener_correlation_id(),
        }
        if hasattr(record, "ruta"):
            payload["ruta"] = record.ruta
        if hasattr(record, "metodo"):
            payload["metodo"] = record.metodo
        if hasattr(record, "estado_http"):
            payload["estado_http"] = record.estado_http
        if hasattr(record, "duracion_ms"):
            payload["duracion_ms"] = record.duracion_ms
        if record.exc_info:
            payload["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configurar_logging_json(nombre_servicio: str, nivel: int = logging.INFO) -> logging.Logger:
    """Configura el logger raíz con salida JSON estándar."""
    root = logging.getLogger()
    root.setLevel(nivel)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(nombre_servicio))
    root.handlers = [handler]
    return logging.getLogger(nombre_servicio)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Registra cada petición HTTP en JSON con ruta, estado y duración en ms."""

    def __init__(self, app, nombre_servicio: str):
        super().__init__(app)
        self.logger = logging.getLogger(f"{nombre_servicio}.http")

    async def dispatch(self, request: Request, call_next):
        inicio = time.perf_counter()
        response = await call_next(request)
        duracion_ms = round((time.perf_counter() - inicio) * 1000, 2)
        self.logger.info(
            f"{request.method} {request.url.path} -> {response.status_code}",
            extra={
                "correlation_id": obtener_correlation_id(),
                "metodo": request.method,
                "ruta": request.url.path,
                "estado_http": response.status_code,
                "duracion_ms": duracion_ms,
            },
        )
        return response
