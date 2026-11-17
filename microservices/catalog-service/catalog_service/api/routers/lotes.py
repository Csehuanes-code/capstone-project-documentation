"""Router for batch inventory synchronization (CU-23, RF-CAT-11, RF-CAT-12, EC-INTEROP-01)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from catalog_service.api.dependencies import (
    CurrentUser,
    get_repos,
    require_prestador,
)
from catalog_service.api.schemas import LoteResponse, SincronizacionLoteRequest
from catalog_service.application.use_cases import SincronizarLoteUseCase

router = APIRouter(prefix="/api/v1/catalogo/lotes", tags=["Sincronización por Lote"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sincronizar inventario en lote (CU-23)",
    description=(
        "Permite a hoteles y operadores establecidos sincronizar inventario de forma asíncrona "
        "(ADR-04 §4.4, EC-INTEROP-01). Responde 202 Accepted con lote_id. "
        "Aplica regla de consistencia: o todas las filas válidas o ninguna (RF-CAT-12)."
    ),
)
async def sincronizar_lote(
    req: SincronizacionLoteRequest,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> JSONResponse:
    use_case = SincronizarLoteUseCase(
        lote_repo=repos["lote_repo"],
        oferta_repo=repos["oferta_repo"],
        zona_repo=repos["zona_repo"],
        tipo_repo=repos["tipo_repo"],
    )
    # Process batch
    lote = await use_case.execute(
        prestador_id=current_user.user_id,
        fuente_id=req.fuente_id,
        registros=[r.model_dump() for r in req.registros],
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "lote_id": str(lote.id),
            "estado": lote.estado.value,
            "total_registros": lote.total_registros,
            "aceptados": lote.aceptados,
            "rechazados": lote.rechazados,
            "mensaje": "Lote recibido y procesado con política todo-o-nada.",
        },
    )


@router.get(
    "/{lote_id}",
    response_model=LoteResponse,
    summary="Consultar estado de sincronización de un lote (CU-23, RF-CAT-12)",
)
async def consultar_lote(
    lote_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> LoteResponse:
    lote = await repos["lote_repo"].get_by_id(lote_id)
    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lote {lote_id} no encontrado.",
        )
    return LoteResponse(
        id=lote.id,
        prestador_id=lote.prestador_id,
        fuente_id=lote.fuente_id,
        estado=lote.estado.value,
        total_registros=lote.total_registros,
        aceptados=lote.aceptados,
        rechazados=lote.rechazados,
        recibido_en=lote.recibido_en,
        finalizado_en=lote.finalizado_en,
    )
