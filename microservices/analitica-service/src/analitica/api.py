"""API administrativa de CU-30/CU-31 y probes de operación."""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from analitica.aplicacion import ConfigurarUmbral, ConsultarIndicadores
from analitica.dominio import ZONAS_VALIDAS, ReglaDominioError, UmbralZona
from analitica.persistencia import RepositorioSql, get_engine
from analitica.seguridad import Identidad, administrador
from analitica.worker import Consumidor, RecalculoPeriodico, RelevoOutbox


class UmbralEntrada(BaseModel):
    zona_id: str
    visitantes_maximos: int = Field(gt=0)
    periodo_dias: int = Field(default=1, ge=1, le=365)
    confirmar_advertencia: bool = False


class UmbralRespuesta(BaseModel):
    zona_id: str
    visitantes_maximos: int
    periodo_dias: int
    promedio_historico_30_dias: float
    advertir: bool
    mensaje: str | None
    guardado: bool


repository = RepositorioSql()
consumer = Consumidor(repository)
relay = RelevoOutbox(repository)
recalculo = RecalculoPeriodico(repository)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    consumer.start()
    relay.start()
    recalculo.start()
    yield
    consumer.stop()
    relay.stop()
    recalculo.stop()
    get_engine().dispose()


app = FastAPI(title="Servicio de Analítica y Sostenibilidad", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["Operación"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "analitica"}


@app.get("/health/ready", tags=["Operación"])
def ready() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Base de datos no disponible") from None
    return {"status": "ready", "service": "analitica"}


@app.get("/api/v1/analitica/indicadores", tags=["CU-30"])
def indicadores(
    _: Annotated[Identidad, Depends(administrador)],
    desde: date,
    hasta: date,
    zona_id: str | None = None,
) -> list[dict[str, object]]:
    try:
        if zona_id is not None and zona_id not in ZONAS_VALIDAS:
            raise ValueError("zona_id no pertenece al vocabulario compartido")
        return ConsultarIndicadores(repository).ejecutar(desde, hasta, zona_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/v1/analitica/indicadores.csv", tags=["CU-30"])
def exportar_csv(
    _: Annotated[Identidad, Depends(administrador)],
    desde: date,
    hasta: date,
    zona_id: str | None = None,
) -> Response:
    if zona_id is not None and zona_id not in ZONAS_VALIDAS:
        raise HTTPException(422, "zona_id no pertenece al vocabulario compartido")
    try:
        rows = ConsultarIndicadores(repository).ejecutar(desde, hasta, zona_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    output = io.StringIO(newline="")
    fields = ["zona_id", "desde", "hasta", "reservas_confirmadas", "visitantes_reservados", "ingresos_cop", "concentracion", "umbral_visitantes", "ocupacion_estimada", "cerca_del_umbral"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=indicadores-analitica.csv"})


@app.get("/api/v1/analitica/umbrales", tags=["CU-31"])
def listar_umbrales(_: Annotated[Identidad, Depends(administrador)]) -> list[dict[str, object]]:
    return [u.__dict__ for u in repository.obtener_umbrales()]


@app.put("/api/v1/analitica/umbrales", tags=["CU-31"], response_model=UmbralRespuesta)
def configurar_umbral(
    body: UmbralEntrada,
    _: Annotated[Identidad, Depends(administrador)],
) -> UmbralRespuesta:
    try:
        umbral = UmbralZona(body.zona_id, body.visitantes_maximos, body.periodo_dias)
        result = ConfigurarUmbral(repository).ejecutar(umbral, body.confirmar_advertencia)
    except ReglaDominioError as exc:
        raise HTTPException(422, str(exc)) from exc
    return UmbralRespuesta(
        zona_id=result.zona_id, visitantes_maximos=result.visitantes_maximos,
        periodo_dias=umbral.periodo_dias, promedio_historico_30_dias=result.promedio_historico,
        advertir=result.advertir, mensaje=result.mensaje, guardado=result.guardado,
    )


@app.get("/api/v1/analitica/alertas", tags=["CU-31"])
def alertas_activas(_: Annotated[Identidad, Depends(administrador)]) -> list[dict[str, object]]:
    return repository.alertas_activas()
