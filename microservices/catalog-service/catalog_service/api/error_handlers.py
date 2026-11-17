"""Error handlers translating domain and application exceptions into HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from catalog_service.domain.exceptions import (
    AtributosInvalidos,
    CalificacionDuplicada,
    CategoriaNoCanonica,
    DomainError,
    EntityNotFoundError,
    PrestadorNoVerificado,
    TarifaSolapada,
    ZonaNoCanonica,
)


def register_error_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI application."""

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": {
                        "entity_type": exc.entity_type,
                        "entity_id": str(exc.entity_id),
                    },
                }
            },
        )

    @app.exception_handler(PrestadorNoVerificado)
    async def prestador_no_verificado_handler(
        request: Request, exc: PrestadorNoVerificado
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": {"prestador_id": str(exc.prestador_id)},
                }
            },
        )

    @app.exception_handler(CalificacionDuplicada)
    async def calificacion_duplicada_handler(
        request: Request, exc: CalificacionDuplicada
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": {"reserva_id": str(exc.reserva_id)},
                }
            },
        )

    @app.exception_handler(CategoriaNoCanonica)
    async def categoria_no_canonica_handler(
        request: Request, exc: CategoriaNoCanonica
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": {"categorias_invalidas": exc.categorias},
                }
            },
        )

    @app.exception_handler(ZonaNoCanonica)
    async def zona_no_canonica_handler(request: Request, exc: ZonaNoCanonica) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": {"zona_invalida": exc.zona},
                }
            },
        )

    @app.exception_handler(AtributosInvalidos)
    async def atributos_invalidos_handler(
        request: Request, exc: AtributosInvalidos
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": {"errores": exc.errores},
                }
            },
        )

    @app.exception_handler(TarifaSolapada)
    async def tarifa_solapada_handler(request: Request, exc: TarifaSolapada) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": {
                        "temporada": exc.temporada,
                        "rango_existente": exc.rango_existente,
                        "rango_nuevo": exc.rango_nuevo,
                    },
                }
            },
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        status_code = (
            status.HTTP_403_FORBIDDEN if exc.code == "FORBIDDEN" else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                }
            },
        )
