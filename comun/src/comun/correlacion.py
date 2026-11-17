from contextvars import ContextVar
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

HEADER_CORRELATION_ID = "X-Correlation-Id"

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def obtener_correlation_id() -> str | None:
    """Devuelve el correlation_id activo en el contexto actual."""
    return _correlation_id_ctx.get()


def establecer_correlation_id(cid: str | None) -> None:
    """Fija manualmente el correlation_id en el contexto (útil en workers/consumidores)."""
    _correlation_id_ctx.set(cid)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Lee X-Correlation-Id de la petición o genera un UUIDv4, lo propaga al contexto y a la respuesta."""

    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get(HEADER_CORRELATION_ID) or str(uuid.uuid4())
        token = _correlation_id_ctx.set(cid)
        request.state.correlation_id = cid
        try:
            response = await call_next(request)
            response.headers[HEADER_CORRELATION_ID] = cid
            return response
        finally:
            _correlation_id_ctx.reset(token)
