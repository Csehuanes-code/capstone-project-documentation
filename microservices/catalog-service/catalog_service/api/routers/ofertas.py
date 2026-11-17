"""Router for tourism offers (CU-07, CU-22, CU-24, and sync conditions)."""

from __future__ import annotations

import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from catalog_service.api.dependencies import (
    CurrentUser,
    get_repos,
    require_prestador,
)
from catalog_service.api.schemas import (
    OfertaCondicionesResponse,
    OfertaCreateRequest,
    OfertaDetalleResponse,
    OfertaItemResponse,
    OfertaUpdateRequest,
    PaginatedResponse,
    PoliticaCancelacionRequest,
    PoliticaCancelacionResponse,
    TarifaCreateRequest,
    TarifaResponse,
)
from catalog_service.application.use_cases import (
    ConfigurarTarifasUseCase,
    ConsultarCatalogoUseCase,
    ConsultarOfertaDetalleUseCase,
    GestionarOfertaUseCase,
    ObtenerCondicionesOfertaUseCase,
)

router = APIRouter(prefix="/api/v1/catalogo/ofertas", tags=["Ofertas"])


@router.get(
    "",
    response_model=PaginatedResponse[OfertaItemResponse],
    summary="Consultar Catálogo de Atractivos y Actividades (CU-07)",
    description=(
        "Permite al turista explorar y filtrar el catálogo sin autenticación. "
        "Soporta filtros canónicos de zona y categoría, ordenamiento por popularidad o calificación, "
        "y paginación (RF-CAT-01 a RF-CAT-04)."
    ),
)
async def listar_ofertas(
    repos: Annotated[dict[str, Any], Depends(get_repos)],
    tipo_codigo: str | None = Query(None, description="Código del tipo de servicio"),
    zona_codigo: str | None = Query(None, description="Código de zona canónica (vocabulario.json)"),
    categoria: str | None = Query(
        None, description="Categoría de interés canónica (vocabulario.json)"
    ),
    orden: Literal["relevancia", "popularidad", "calificacion"] = Query(
        "relevancia", description="Criterio de orden explícito (RF-CAT-03)"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    idioma: Literal["es", "en"] = Query("es", description="Idioma para visualización"),
) -> PaginatedResponse[OfertaItemResponse]:
    use_case = ConsultarCatalogoUseCase(
        oferta_repo=repos["oferta_repo"],
        zona_repo=repos["zona_repo"],
    )
    items, total = await use_case.execute(
        tipo_codigo=tipo_codigo,
        zona_codigo=zona_codigo,
        categoria=categoria,
        orden=orden,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(
        items=[
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
            for o in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{oferta_id}",
    response_model=OfertaDetalleResponse,
    summary="Detalle completo de una oferta turística",
)
async def consultar_detalle_oferta(
    oferta_id: UUID,
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> OfertaDetalleResponse:
    use_case = ConsultarOfertaDetalleUseCase(
        oferta_repo=repos["oferta_repo"],
        imagen_repo=repos["imagen_repo"],
        tarifa_repo=repos["tarifa_repo"],
        politica_repo=repos["politica_repo"],
        zona_repo=repos["zona_repo"],
        tipo_repo=repos["tipo_repo"],
        prestador_repo=repos["prestador_repo"],
    )
    res = await use_case.execute(oferta_id)
    of = res["oferta"]
    return OfertaDetalleResponse(
        oferta=OfertaItemResponse(
            id=of.id,
            tipo_servicio_id=of.tipo_servicio_id,
            zona_id=of.zona_id,
            prestador_id=of.prestador_id,
            nombre_es=of.nombre_es,
            nombre_en=of.nombre_en,
            descripcion_es=of.descripcion_es,
            descripcion_en=of.descripcion_en,
            atributos=of.atributos,
            estado=of.estado.value,
            calificacion_promedio=float(of.calificacion_promedio),
            total_calificaciones=of.total_calificaciones,
            creado_en=of.creado_en,
            actualizado_en=of.actualizado_en,
        ),
        zona=res["zona"],
        tipo_servicio=res["tipo_servicio"],
        imagenes=res["imagenes"],
        tarifas=[
            TarifaResponse(
                id=t.id,
                oferta_id=t.oferta_id,
                temporada=t.temporada.value,
                vigente_desde=t.vigente_desde,
                vigente_hasta=t.vigente_hasta,
                precio_por_persona=float(t.precio_por_persona),
                moneda=t.moneda,
            )
            for t in res["tarifas"]
        ],
        politica_cancelacion=res["politica_cancelacion"],
    )


@router.get(
    "/{oferta_id}/condiciones",
    response_model=OfertaCondicionesResponse,
    summary="Consulta de condiciones para el flujo de reserva (ADR-04 §4.2)",
    description=(
        "Llamada síncrona invocada por Reservas antes de iniciar o confirmar un cupo. "
        "Devuelve la tarifa vigente, estado de la oferta y política de cancelación con timeout de 1s."
    ),
)
async def obtener_condiciones(
    oferta_id: UUID,
    repos: Annotated[dict[str, Any], Depends(get_repos)],
    fecha: datetime.date | None = Query(None, description="Fecha del servicio para evaluar tarifa"),
) -> OfertaCondicionesResponse:
    use_case = ObtenerCondicionesOfertaUseCase(
        oferta_repo=repos["oferta_repo"],
        tarifa_repo=repos["tarifa_repo"],
        politica_repo=repos["politica_repo"],
        zona_repo=repos["zona_repo"],
    )
    data = await use_case.execute(oferta_id, fecha)
    return OfertaCondicionesResponse(**data)


@router.post(
    "",
    response_model=OfertaItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva oferta turística (CU-22)",
    description=(
        "Permite al prestador crear una nueva oferta turística. "
        "Si el estado solicitado es 'publicada', se valida que el prestador esté verificado (RF-USR-19)."
    ),
)
async def crear_oferta(
    req: OfertaCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> OfertaItemResponse:
    use_case = GestionarOfertaUseCase(
        oferta_repo=repos["oferta_repo"],
        zona_repo=repos["zona_repo"],
        tipo_repo=repos["tipo_repo"],
        prestador_repo=repos["prestador_repo"],
        event_publisher=repos["event_publisher"],
    )
    oferta = await use_case.crear_oferta(
        prestador_id=current_user.user_id,
        tipo_servicio_id=req.tipo_servicio_id,
        zona_id=req.zona_id,
        nombre_es=req.nombre_es,
        nombre_en=req.nombre_en,
        descripcion_es=req.descripcion_es,
        descripcion_en=req.descripcion_en,
        atributos=req.atributos,
        estado=req.estado,
        indice_sostenibilidad=req.indice_sostenibilidad,
    )
    return OfertaItemResponse(
        id=oferta.id,
        tipo_servicio_id=oferta.tipo_servicio_id,
        zona_id=oferta.zona_id,
        prestador_id=oferta.prestador_id,
        nombre_es=oferta.nombre_es,
        nombre_en=oferta.nombre_en,
        descripcion_es=oferta.descripcion_es,
        descripcion_en=oferta.descripcion_en,
        atributos=oferta.atributos,
        estado=oferta.estado.value,
        calificacion_promedio=float(oferta.calificacion_promedio),
        total_calificaciones=oferta.total_calificaciones,
        creado_en=oferta.creado_en,
        actualizado_en=oferta.actualizado_en,
    )


@router.put(
    "/{oferta_id}",
    response_model=OfertaItemResponse,
    summary="Actualizar oferta turística (CU-22)",
)
async def actualizar_oferta(
    oferta_id: UUID,
    req: OfertaUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> OfertaItemResponse:
    use_case = GestionarOfertaUseCase(
        oferta_repo=repos["oferta_repo"],
        zona_repo=repos["zona_repo"],
        tipo_repo=repos["tipo_repo"],
        prestador_repo=repos["prestador_repo"],
        event_publisher=repos["event_publisher"],
    )
    oferta = await use_case.actualizar_oferta(
        oferta_id=oferta_id,
        prestador_id=current_user.user_id,
        nombre_es=req.nombre_es,
        nombre_en=req.nombre_en,
        descripcion_es=req.descripcion_es,
        descripcion_en=req.descripcion_en,
        atributos=req.atributos,
        estado=req.estado,
        indice_sostenibilidad=req.indice_sostenibilidad,
    )
    return OfertaItemResponse(
        id=oferta.id,
        tipo_servicio_id=oferta.tipo_servicio_id,
        zona_id=oferta.zona_id,
        prestador_id=oferta.prestador_id,
        nombre_es=oferta.nombre_es,
        nombre_en=oferta.nombre_en,
        descripcion_es=oferta.descripcion_es,
        descripcion_en=oferta.descripcion_en,
        atributos=oferta.atributos,
        estado=oferta.estado.value,
        calificacion_promedio=float(oferta.calificacion_promedio),
        total_calificaciones=oferta.total_calificaciones,
        creado_en=oferta.creado_en,
        actualizado_en=oferta.actualizado_en,
    )


@router.delete(
    "/{oferta_id}",
    response_model=OfertaItemResponse,
    summary="Dar de baja / retirar oferta turística (CU-22)",
)
async def retirar_oferta(
    oferta_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> OfertaItemResponse:
    use_case = GestionarOfertaUseCase(
        oferta_repo=repos["oferta_repo"],
        zona_repo=repos["zona_repo"],
        tipo_repo=repos["tipo_repo"],
        prestador_repo=repos["prestador_repo"],
        event_publisher=repos["event_publisher"],
    )
    oferta = await use_case.retirar_oferta(oferta_id, current_user.user_id)
    return OfertaItemResponse(
        id=oferta.id,
        tipo_servicio_id=oferta.tipo_servicio_id,
        zona_id=oferta.zona_id,
        prestador_id=oferta.prestador_id,
        nombre_es=oferta.nombre_es,
        nombre_en=oferta.nombre_en,
        descripcion_es=oferta.descripcion_es,
        descripcion_en=oferta.descripcion_en,
        atributos=oferta.atributos,
        estado=oferta.estado.value,
        calificacion_promedio=float(oferta.calificacion_promedio),
        total_calificaciones=oferta.total_calificaciones,
        creado_en=oferta.creado_en,
        actualizado_en=oferta.actualizado_en,
    )


@router.post(
    "/{oferta_id}/tarifas",
    response_model=TarifaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar tarifa por temporada (CU-24)",
)
async def agregar_tarifa(
    oferta_id: UUID,
    req: TarifaCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> TarifaResponse:
    use_case = ConfigurarTarifasUseCase(
        tarifa_repo=repos["tarifa_repo"],
        politica_repo=repos["politica_repo"],
        oferta_repo=repos["oferta_repo"],
        event_publisher=repos["event_publisher"],
    )
    tarifa = await use_case.agregar_tarifa(
        oferta_id=oferta_id,
        prestador_id=current_user.user_id,
        temporada=req.temporada,
        vigente_desde=req.vigente_desde,
        vigente_hasta=req.vigente_hasta,
        precio_por_persona=req.precio_por_persona,
        moneda=req.moneda,
    )
    return TarifaResponse(
        id=tarifa.id,
        oferta_id=tarifa.oferta_id,
        temporada=tarifa.temporada.value,
        vigente_desde=tarifa.vigente_desde,
        vigente_hasta=tarifa.vigente_hasta,
        precio_por_persona=float(tarifa.precio_por_persona),
        moneda=tarifa.moneda,
    )


@router.put(
    "/{oferta_id}/politica-cancelacion",
    response_model=PoliticaCancelacionResponse,
    summary="Configurar política de cancelación de la oferta (CU-24)",
)
async def configurar_politica_cancelacion(
    oferta_id: UUID,
    req: PoliticaCancelacionRequest,
    current_user: Annotated[CurrentUser, Depends(require_prestador)],
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> PoliticaCancelacionResponse:
    use_case = ConfigurarTarifasUseCase(
        tarifa_repo=repos["tarifa_repo"],
        politica_repo=repos["politica_repo"],
        oferta_repo=repos["oferta_repo"],
        event_publisher=repos["event_publisher"],
    )
    pol = await use_case.configurar_politica_cancelacion(
        oferta_id=oferta_id,
        prestador_id=current_user.user_id,
        horas_reembolso_total=req.horas_reembolso_total,
        horas_reembolso_parcial=req.horas_reembolso_parcial,
        porcentaje_reembolso_parcial=req.porcentaje_reembolso_parcial,
    )
    return PoliticaCancelacionResponse(
        oferta_id=pol.oferta_id,
        horas_reembolso_total=pol.horas_reembolso_total,
        horas_reembolso_parcial=pol.horas_reembolso_parcial,
        porcentaje_reembolso_parcial=pol.porcentaje_reembolso_parcial,
    )
