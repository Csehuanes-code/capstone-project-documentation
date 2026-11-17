"""FastAPI dependency injection providers."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from catalog_service.infrastructure.config import settings
from catalog_service.infrastructure.database import get_db_session
from catalog_service.infrastructure.dependencies_helper import (
    get_singleton_in_memory_container,
)
from catalog_service.infrastructure.event_publisher import (
    SqlAlchemyOutboxEventPublisher,
)
from catalog_service.infrastructure.repositories import (
    SqlAlchemyCalificacionRepository,
    SqlAlchemyFavoritoRepository,
    SqlAlchemyImagenOfertaRepository,
    SqlAlchemyItinerarioRepository,
    SqlAlchemyLoteRepository,
    SqlAlchemyOfertaRepository,
    SqlAlchemyPerfilPrestadorRepository,
    SqlAlchemyPoliticaCancelacionRepository,
    SqlAlchemyTarifaRepository,
    SqlAlchemyTipoServicioRepository,
    SqlAlchemyZonaRepository,
)
from catalog_service.infrastructure.reservas_client import (
    HttpReservasClient,
    MockReservasClient,
)
from catalog_service.infrastructure.security import TokenInvalido, obtener_verificador

# ---------------------------------------------------------------------------
# Auth / User Extraction (ADR-06 §1.1)
# ---------------------------------------------------------------------------


class CurrentUser:
    def __init__(self, user_id: UUID, role: str) -> None:
        self.user_id = user_id
        self.role = role


async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    """Usuario del JWT emitido por Auth (ES256, validado con su clave pública; ADR-06).

    Solo se acepta `Authorization: Bearer <token>`. No hay cabeceras de simulación ni tokens
    de prueba: en las pruebas se firman tokens reales con una clave de prueba
    (tests/auth_util.py). Sin token, o con un token inválido, devuelve None y las rutas
    protegidas responden 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    verificador = obtener_verificador()
    if verificador is None:
        return None
    try:
        identidad = verificador.verificar(authorization.removeprefix("Bearer ").strip())
    except TokenInvalido:
        return None
    return CurrentUser(user_id=identidad.user_id, role=identidad.rol)


async def get_current_user(
    user: Annotated[CurrentUser | None, Depends(get_current_user_optional)],
) -> CurrentUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Proporcione una cabecera Authorization válida.",
        )
    return user


async def require_prestador(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if user.role not in ("prestador", "administrador"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción solo puede ser realizada por un prestador de servicios turísticos.",
        )
    return user


async def require_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if user.role != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere rol de administrador.",
        )
    return user


# ---------------------------------------------------------------------------
# Repositories & Use Cases injection
# ---------------------------------------------------------------------------


async def get_repos(
    session: Annotated[AsyncSession | None, Depends(get_db_session)] = None,
) -> dict[str, Any]:
    if settings.USE_IN_MEMORY_REPO or session is None:
        return get_singleton_in_memory_container()

    return {
        "zona_repo": SqlAlchemyZonaRepository(session),
        "tipo_repo": SqlAlchemyTipoServicioRepository(session),
        "oferta_repo": SqlAlchemyOfertaRepository(session),
        "prestador_repo": SqlAlchemyPerfilPrestadorRepository(session),
        "tarifa_repo": SqlAlchemyTarifaRepository(session),
        "politica_repo": SqlAlchemyPoliticaCancelacionRepository(session),
        "imagen_repo": SqlAlchemyImagenOfertaRepository(session),
        "calificacion_repo": SqlAlchemyCalificacionRepository(session),
        "favorito_repo": SqlAlchemyFavoritoRepository(session),
        "itinerario_repo": SqlAlchemyItinerarioRepository(session),
        "lote_repo": SqlAlchemyLoteRepository(session),
        "event_publisher": SqlAlchemyOutboxEventPublisher(session),
        "reservas_client": HttpReservasClient()
        if settings.ENVIRONMENT == "production"
        else MockReservasClient(),
    }
