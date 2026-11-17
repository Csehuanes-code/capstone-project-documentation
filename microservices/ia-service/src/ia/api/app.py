"""Controladores REST del servicio IA. Rutas bajo /api/v1/ia (el Gateway enruta por prefijo)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from ia.aplicacion.casos_uso import (
    LIMITE_MAXIMO,
    ConsultarCriterios,
    ConsultarRecomendacion,
    ConsultarSalud,
    GenerarRecomendaciones,
    ListarPopulares,
)
from ia.aplicacion.dto import criterios_dto, popular_dto, recomendacion_dto
from ia.aplicacion.errores import RecomendacionNoEncontrada, VersionCriteriosNoEncontrada

from . import esquemas

Idioma = Literal["es", "en"]


@dataclass(frozen=True)
class CasosDeUso:
    generar: GenerarRecomendaciones
    consultar: ConsultarRecomendacion
    criterios: ConsultarCriterios
    populares: ListarPopulares
    salud: ConsultarSalud


def _casos(request: Request) -> CasosDeUso:
    return request.app.state.casos


def turista_actual() -> str | None:
    """Identidad del turista.

    TODO(sprint 6): reemplazar por la validación de JWT de la plantilla común (ADR-06) y
    devolver el `sub` del token. Mientras tanto el endpoint es anónimo.
    """
    return None


router = APIRouter(prefix="/api/v1/ia", tags=["Recomendaciones"])


@router.get(
    "/recomendaciones",
    response_model=esquemas.RecomendacionRespuesta,
    summary="Recomendación personalizada explicable (CU-21, pantalla W3 y 'Para ti' de W1)",
)
def generar_recomendaciones(
    intereses: str | None = Query(
        None,
        description="Intereses separados por coma",
        examples=["naturaleza,cultura"],
    ),
    limite: int = Query(5, ge=1, le=LIMITE_MAXIMO),
    idioma: Idioma = "es",
    turista_id: str | None = Depends(turista_actual),
    casos: CasosDeUso = Depends(_casos),
):
    lista = intereses.split(",") if intereses else []
    rec = casos.generar.ejecutar(lista, limite=limite, turista_id=turista_id)
    return recomendacion_dto(rec, idioma)


@router.get(
    "/recomendaciones/{recomendacion_id}",
    response_model=esquemas.RecomendacionRespuesta,
    responses={404: {"model": esquemas.Error}},
    summary="'¿Por qué veo esto?': la recomendación emitida, con su desglose original",
)
def consultar_recomendacion(
    recomendacion_id: UUID,
    idioma: Idioma = "es",
    casos: CasosDeUso = Depends(_casos),
):
    try:
        rec = casos.consultar.ejecutar(recomendacion_id)
    except RecomendacionNoEncontrada:
        raise HTTPException(404, "Recomendación no encontrada") from None
    return recomendacion_dto(rec, idioma)


@router.get(
    "/criterios",
    response_model=esquemas.CriteriosRespuesta,
    responses={404: {"model": esquemas.Error}},
    summary="'Cómo funcionan las recomendaciones': pesos vigentes o de una versión",
)
def consultar_criterios(
    version: int | None = Query(None, ge=1),
    idioma: Idioma = "es",
    casos: CasosDeUso = Depends(_casos),
):
    try:
        return criterios_dto(casos.criterios.ejecutar(version), idioma)
    except VersionCriteriosNoEncontrada:
        raise HTTPException(404, "Versión de criterios no encontrada") from None


@router.get(
    "/populares",
    response_model=list[esquemas.Popular],
    summary="Ofertas más reservadas (respaldo sin personalización)",
)
def listar_populares(
    limite: int = Query(5, ge=1, le=LIMITE_MAXIMO),
    casos: CasosDeUso = Depends(_casos),
):
    return [popular_dto(p) for p in casos.populares.ejecutar(limite)]


def crear_app(
    casos: CasosDeUso,
    al_iniciar: Sequence[Callable[[], None]] = (),
    al_detener: Sequence[Callable[[], None]] = (),
) -> FastAPI:
    """al_iniciar / al_detener: tareas de fondo que main.py conecta (ej. el consumidor de eventos).
    Corren una vez por proceso de uvicorn, al arrancar y al apagarse."""

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI):
        for tarea in al_iniciar:
            tarea()
        try:
            yield
        finally:
            for tarea in al_detener:
                tarea()

    app = FastAPI(
        lifespan=ciclo_de_vida,
        title="Servicio IA — Recomendación",
        version="0.1.0",
        description=(
            "Recomendación personalizada explicable para la Plataforma de Turismo de Santa Marta. "
            "Puntaje multicriterio con pesos versionados (ADR-07)."
        ),
    )
    app.state.casos = casos
    app.include_router(router)

    @app.get("/health", tags=["Operación"], summary="Liveness: el proceso está vivo")
    def health() -> dict[str, str]:
        return {"estado": "ok", "servicio": "ia"}

    @app.get(
        "/health/ready",
        tags=["Operación"],
        summary="Readiness: las dependencias responden (503 si no). Para el balanceador.",
    )
    def ready(casos: CasosDeUso = Depends(_casos)):
        estado = casos.salud.ejecutar()
        return JSONResponse(
            status_code=200 if estado.listo else 503,
            content={
                "estado": "listo" if estado.listo else "no_listo",
                "servicio": "ia",
                "dependencias": estado.dependencias,
            },
        )

    return app
