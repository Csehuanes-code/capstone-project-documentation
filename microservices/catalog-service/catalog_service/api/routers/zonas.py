"""Router for Zones and Service Types reference data."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from catalog_service.api.dependencies import get_repos
from catalog_service.api.schemas import TipoServicioResponse, ZonaResponse

router = APIRouter(prefix="/api/v1/catalogo", tags=["Referencia"])


@router.get(
    "/zonas",
    response_model=list[ZonaResponse],
    summary="Listar zonas canónicas de Santa Marta",
    description="Devuelve las zonas canónicas definidas en vocabulario.json.",
)
async def listar_zonas(
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> list[ZonaResponse]:
    zonas = await repos["zona_repo"].list_all()
    return [
        ZonaResponse(
            id=z.id,
            codigo=z.codigo,
            nombre_es=z.nombre_es,
            nombre_en=z.nombre_en,
            ecosistema_sensible=z.ecosistema_sensible,
            latitud=z.latitud,
            longitud=z.longitud,
        )
        for z in zonas
    ]


@router.get(
    "/tipos-servicio",
    response_model=list[TipoServicioResponse],
    summary="Listar tipos de servicio turístico",
    description="Devuelve los tipos de servicio configurados y su JSON Schema de atributos.",
)
async def listar_tipos_servicio(
    repos: Annotated[dict[str, Any], Depends(get_repos)],
) -> list[TipoServicioResponse]:
    tipos = await repos["tipo_repo"].list_all()
    return [
        TipoServicioResponse(
            id=t.id,
            codigo=t.codigo,
            nombre_es=t.nombre_es,
            nombre_en=t.nombre_en,
            reservable=t.reservable,
            esquema_atributos=t.esquema_atributos,
        )
        for t in tipos
    ]
