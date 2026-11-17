from typing import Callable
from fastapi import APIRouter, Response, status


def crear_router_salud(
    nombre_servicio: str,
    verificar_db: Callable[[], bool],
    verificar_broker: Callable[[], bool] | None = None,
) -> APIRouter:
    """Crea los endpoints estándar /health (liveness) y /health/ready (readiness)."""
    router = APIRouter(tags=["Salud"])

    @router.get("/health")
    def health() -> dict:
        return {"estado": "ok", "servicio": nombre_servicio}

    @router.get("/health/ready")
    def health_ready(response: Response) -> dict:
        db_ok = False
        broker_ok = True
        try:
            db_ok = bool(verificar_db())
        except Exception:
            db_ok = False

        if verificar_broker is not None:
            try:
                broker_ok = bool(verificar_broker())
            except Exception:
                broker_ok = False

        listo = db_ok and broker_ok
        if not listo:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "estado": "listo" if listo else "no_disponible",
            "servicio": nombre_servicio,
            "dependencias": {
                "postgresql": "ok" if db_ok else "error",
                "rabbitmq": "ok" if broker_ok else "error",
            },
        }

    return router
