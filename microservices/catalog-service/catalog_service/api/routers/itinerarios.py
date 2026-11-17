"""Router for itineraries management (CU-10, RF-CAT-06, RF-CAT-07)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from catalog_service.api.dependencies import CurrentUser, get_current_user, get_repos
from catalog_service.api.schemas import (
    ItinerarioCreateRequest,
    ItinerarioItemRequest,
    ItinerarioItemResponse,
    ItinerarioResponse,
)
from catalog_service.application.use_cases import GestionarItinerariosUseCase

router = APIRouter(prefix="/api/v1/catalogo/itinerarios", tags=["Itinerarios"])


@router.post(
    "",
    response_model=ItinerarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear itinerario personalizado (CU-10)",
)
async def crear_itinerario(
    req: ItinerarioCreateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> ItinerarioResponse:
    use_case = GestionarItinerariosUseCase(
        itinerario_repo=repos["itinerario_repo"],
        oferta_repo=repos["oferta_repo"],
    )
    it = await use_case.crear_itinerario(
        turista_id=current_user.user_id,
        nombre=req.nombre,
        fecha_inicio=req.fecha_inicio,
        fecha_fin=req.fecha_fin,
    )
    return ItinerarioResponse(
        id=it.id,
        turista_id=it.turista_id,
        nombre=it.nombre,
        fecha_inicio=it.fecha_inicio,
        fecha_fin=it.fecha_fin,
        items=[],
    )


@router.post(
    "/{itinerario_id}/items",
    status_code=status.HTTP_201_CREATED,
    summary="Agregar actividad al itinerario (CU-10, RF-CAT-07)",
    description="Advierte solapamientos de horario sin bloquear el guardado (RF-CAT-07).",
)
async def agregar_item_itinerario(
    itinerario_id: UUID,
    req: ItinerarioItemRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> JSONResponse:
    use_case = GestionarItinerariosUseCase(
        itinerario_repo=repos["itinerario_repo"],
        oferta_repo=repos["oferta_repo"],
    )
    item, advertencias = await use_case.agregar_item(
        itinerario_id=itinerario_id,
        oferta_id=req.oferta_id,
        dia=req.dia,
        orden=req.orden,
        hora_inicio=req.hora_inicio,
        hora_fin=req.hora_fin,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "item": {
                "id": str(item.id),
                "itinerario_id": str(item.itinerario_id),
                "oferta_id": str(item.oferta_id),
                "dia": item.dia.isoformat(),
                "orden": item.orden,
                "hora_inicio": item.hora_inicio.isoformat() if item.hora_inicio else None,
                "hora_fin": item.hora_fin.isoformat() if item.hora_fin else None,
            },
            "advertencias": advertencias,
        },
    )


@router.get(
    "",
    response_model=list[ItinerarioResponse],
    summary="Listar itinerarios del turista (CU-10)",
)
async def listar_itinerarios(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> list[ItinerarioResponse]:
    use_case = GestionarItinerariosUseCase(
        itinerario_repo=repos["itinerario_repo"],
        oferta_repo=repos["oferta_repo"],
    )
    its = await use_case.listar_itinerarios(current_user.user_id)
    out: list[ItinerarioResponse] = []
    for it in its:
        items = await repos["itinerario_repo"].list_items(it.id)
        out.append(
            ItinerarioResponse(
                id=it.id,
                turista_id=it.turista_id,
                nombre=it.nombre,
                fecha_inicio=it.fecha_inicio,
                fecha_fin=it.fecha_fin,
                items=[
                    ItinerarioItemResponse(
                        id=i.id,
                        itinerario_id=i.itinerario_id,
                        oferta_id=i.oferta_id,
                        dia=i.dia,
                        orden=i.orden,
                        hora_inicio=i.hora_inicio,
                        hora_fin=i.hora_fin,
                    )
                    for i in items
                ],
            )
        )
    return out
