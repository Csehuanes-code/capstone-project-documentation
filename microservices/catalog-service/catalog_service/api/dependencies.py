"""FastAPI dependency injection providers."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID, uuid4

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

# ---------------------------------------------------------------------------
# Auth / User Extraction (ADR-06 §1.1)
# ---------------------------------------------------------------------------


class CurrentUser:
    def __init__(self, user_id: UUID, role: str) -> None:
        self.user_id = user_id
        self.role = role


async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> CurrentUser | None:
    """Extract authenticated user from JWT token or fallback simulation headers (ADR-06)."""
    # 1. Direct simulation headers (for local testing/gateway forwarded headers)
    if x_user_id:
        try:
            uid = UUID(x_user_id)
            role = x_user_role or "turista"
            return CurrentUser(user_id=uid, role=role)
        except ValueError:
            pass

    # 2. Bearer token (JWT inspection)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        # For simplicity and testability in dev, allow dummy token or parse
        if token.startswith("test-"):
            # Format: test-<role>-<uuid>
            parts = token.split("-", 2)
            role = parts[1] if len(parts) > 1 else "turista"
            try:
                uid = UUID(parts[2]) if len(parts) > 2 else uuid4()
            except ValueError:
                uid = uuid4()
            return CurrentUser(user_id=uid, role=role)

        # In production with PyJWT
        try:
            import jwt

            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
                options={
                    "verify_signature": False if settings.ENVIRONMENT == "development" else True
                },
            )
            sub = payload.get("sub")
            role = payload.get("rol", "turista")
            if sub:
                return CurrentUser(user_id=UUID(sub), role=role)
        except Exception:
            return None

    return None


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
