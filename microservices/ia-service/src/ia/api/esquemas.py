"""Esquemas de respuesta: definen el contrato OpenAPI que se comparte con el equipo."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Nivel = Literal["tranquila", "moderada", "muy_concurrida", "desconocida"]


class Aporte(BaseModel):
    criterio: Literal["afinidad", "calidad", "descongestion", "sostenibilidad"]
    etiqueta: str = Field(examples=["Afinidad con tus intereses"])
    peso: float = Field(examples=[0.45])
    valor: float = Field(ge=0, le=1, examples=[1.0])
    aporte: float = Field(examples=[0.45], description="peso × valor")


class Zona(BaseModel):
    id: str
    nombre: str | None
    ocupacion: float | None = Field(description="visitantes / capacidad de carga")
    nivel: Nivel


class AlternativaDe(BaseModel):
    oferta_id: str
    nombre: str
    zona: str | None


class Item(BaseModel):
    posicion: int
    oferta_id: str
    nombre: str
    zona: Zona
    calificacion_promedio: float
    numero_resenas: int
    puntaje: float = Field(description="Suma de los aportes del desglose")
    motivo: Literal["personalizada", "alternativa_descongestion"]
    explicacion: str = Field(examples=["Coincide con tus intereses: naturaleza."])
    desglose: list[Aporte]
    alternativa_de: AlternativaDe | None = Field(
        description="Oferta de zona saturada a la que esta reemplaza (solo si motivo es alternativa)"
    )


class RecomendacionRespuesta(BaseModel):
    id: UUID
    version_pesos: int
    intereses: list[str]
    generada_en: datetime
    idioma: Literal["es", "en"]
    items: list[Item]


class Peso(BaseModel):
    criterio: str
    etiqueta: str
    peso: float


class CriteriosRespuesta(BaseModel):
    version: int
    creada_en: datetime
    pesos: list[Peso]
    umbral_tranquila: float
    umbral_saturacion: float
    prior_media: float
    prior_peso: int
    max_por_zona: int


class Popular(BaseModel):
    oferta_id: str
    nombre: str
    zona: Zona
    calificacion_promedio: float
    numero_resenas: int
    reservas_confirmadas: int


class Error(BaseModel):
    detail: str
