"""Router for reviews and moderation (CU-19, CU-20, CU-29)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from catalog_service.api.dependencies import (
    CurrentUser,
    get_current_user,
    get_repos,
    require_admin,
    require_prestador,
)
from catalog_service.api.schemas import (
    CalificacionCreateRequest,
    CalificacionResponse,
    ModeracionRequest,
    RespuestaCalificacionRequest,
    RespuestaCalificacionResponse,
)
from catalog_service.application.use_cases import (
    CrearCalificacionUseCase,
    ModerarContenidoUseCase,
    ResponderCalificacionUseCase,
)

router = APIRouter(prefix="/api/v1/catalogo", tags=["Calificaciones"])


@router.post(
    "/ofertas/{oferta_id}/calificaciones",
    response_model=CalificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calificar y comentar una experiencia completada (CU-19)",
    description=(
        "Permite al turista calificar un servicio completado. Verifica sincrónicamente con "
        "Reservas que la reserva esté en estado 'completada' (RF-CAT-15, ADR-04 §4.2), "
        "rechaza calificaciones duplicadas para la misma reserva y actualiza el promedio."
    ),
)
async def crear_calificacion(
    oferta_id: UUID,
    req: CalificacionCreateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> CalificacionResponse:
    use_case = CrearCalificacionUseCase(
        calificacion_repo=repos["calificacion_repo"],
        oferta_repo=repos["oferta_repo"],
        zona_repo=repos["zona_repo"],
        reservas_client=repos["reservas_client"],
        event_publisher=repos["event_publisher"],
    )
    calif = await use_case.execute(
        oferta_id=oferta_id,
        turista_id=current_user.user_id,
        reserva_id=req.reserva_id,
        puntaje=req.puntaje,
        comentario=req.comentario,
    )
    return CalificacionResponse(
        id=calif.id,
        oferta_id=calif.oferta_id,
        turista_id=calif.turista_id,
        reserva_id=calif.reserva_id,
        puntaje=calif.puntaje,
        comentario=calif.comentario,
        estado_moderacion=calif.estado_moderacion.value,
        creada_en=calif.creada_en,
    )


@router.post(
    "/calificaciones/{calificacion_id}/respuesta",
    response_model=RespuestaCalificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Responder a una calificación recibida (CU-20)",
    description="Permite al prestador dueño de la oferta responder públicamente a una reseña (RF-CAT-17).",
)
async def responder_calificacion(
    calificacion_id: UUID,
    req: RespuestaCalificacionRequest,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> RespuestaCalificacionResponse:
    use_case = ResponderCalificacionUseCase(
        calificacion_repo=repos["calificacion_repo"],
        oferta_repo=repos["oferta_repo"],
    )
    resp = await use_case.execute(
        calificacion_id=calificacion_id,
        prestador_id=current_user.user_id,
        texto=req.texto,
    )
    return RespuestaCalificacionResponse(
        calificacion_id=resp.calificacion_id,
        prestador_id=resp.prestador_id,
        texto=resp.texto,
        estado_moderacion=resp.estado_moderacion.value,
        creada_en=resp.creada_en,
    )


@router.put(
    "/calificaciones/{calificacion_id}/moderacion",
    response_model=CalificacionResponse,
    summary="Moderar contenido de una calificación (CU-29)",
    description="Permite al administrador cambiar el estado de moderación (RF-CAT-18).",
)
async def moderar_calificacion(
    calificacion_id: UUID,
    req: ModeracionRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> CalificacionResponse:
    use_case = ModerarContenidoUseCase(calificacion_repo=repos["calificacion_repo"])
    calif = await use_case.execute(
        calificacion_id=calificacion_id,
        nuevo_estado=req.nuevo_estado,
        justificacion=req.justificacion,
    )
    return CalificacionResponse(
        id=calif.id,
        oferta_id=calif.oferta_id,
        turista_id=calif.turista_id,
        reserva_id=calif.reserva_id,
        puntaje=calif.puntaje,
        comentario=calif.comentario,
        estado_moderacion=calif.estado_moderacion.value,
        creada_en=calif.creada_en,
    )
