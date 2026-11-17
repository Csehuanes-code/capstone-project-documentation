"""Router for favorites management (CU-09, RF-CAT-05)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from catalog_service.api.dependencies import CurrentUser, get_current_user, get_repos
from catalog_service.api.schemas import OfertaItemResponse
from catalog_service.application.use_cases import GestionarFavoritosUseCase

router = APIRouter(prefix="/api/v1/catalogo/favoritos", tags=["Favoritos"])


@router.post(
    "/{oferta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Marcar atractivo como favorito (CU-09)",
)
async def agregar_favorito(
    oferta_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> None:
    use_case = GestionarFavoritosUseCase(
        favorito_repo=repos["favorito_repo"],
        oferta_repo=repos["oferta_repo"],
    )
    await use_case.agregar_favorito(current_user.user_id, oferta_id)


@router.delete(
    "/{oferta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desmarcar atractivo de favoritos (CU-09)",
)
async def eliminar_favorito(
    oferta_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> None:
    use_case = GestionarFavoritosUseCase(
        favorito_repo=repos["favorito_repo"],
        oferta_repo=repos["oferta_repo"],
    )
    await use_case.eliminar_favorito(current_user.user_id, oferta_id)


@router.get(
    "",
    response_model=list[OfertaItemResponse],
    summary="Listar atractivos favoritos del turista autenticado (CU-09)",
)
async def listar_favoritos(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> list[OfertaItemResponse]:
    use_case = GestionarFavoritosUseCase(
        favorito_repo=repos["favorito_repo"],
        oferta_repo=repos["oferta_repo"],
    )
    ofertas = await use_case.listar_favoritos(current_user.user_id)
    return [
        OfertaItemResponse(
            id=o.id,
            tipo_servicio_id=o.tipo_servicio_id,
            zona_id=o.zona_id,
            prestador_id=o.prestador_id,
            nombre_es=o.nombre_es,
            nombre_en=o.nombre_en,
            descripcion_es=o.descripcion_es,
            descripcion_en=o.descripcion_en,
            atributos=o.atributos,
            estado=o.estado.value,
            calificacion_promedio=float(o.calificacion_promedio),
            total_calificaciones=o.total_calificaciones,
            creado_en=o.creado_en,
            actualizado_en=o.actualizado_en,
        )
        for o in ofertas
    ]
