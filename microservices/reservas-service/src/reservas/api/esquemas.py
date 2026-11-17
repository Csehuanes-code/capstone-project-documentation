"""Esquemas HTTP (Pydantic v2). Solo viven en la capa api/."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CrearReservaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    franja_id: str = Field(..., min_length=1, max_length=36, description="Franja de disponibilidad elegida")
    personas: int = Field(..., ge=1, le=20, description="Personas (más de 1 = reserva grupal, CU-12)")
    correo_turista: EmailStr = Field(..., description="Correo donde llega el comprobante")
    idioma: Literal["es", "en"] = Field(default="es", description="Idioma del comprobante y correos (RC-S02)")
    metodo_pago: Literal["tarjeta", "pse"] = Field(default="tarjeta")
    datos_pago: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Datos de la pasarela SIMULADA. numero_tarjeta terminada en 0002 = rechazado, "
            "9999 = tiempo agotado, 0019 = aprobado pero sin reembolsos; otra = aprobado."
        ),
    )
    acompanantes: list[str] = Field(
        default_factory=list, max_length=19,
        description="Nombres opcionales de acompañantes (RF-RES-10: se pueden omitir)",
    )
    entrada_lista_espera_id: str | None = Field(
        default=None, max_length=36,
        description="Si confirma un cupo ofrecido desde la lista de espera (CU-13)",
    )


class PoliticaCancelacionDTO(BaseModel):
    horas_reembolso_total: int
    horas_reembolso_parcial: int
    porcentaje_reembolso_parcial: int
    descripcion_es: str
    descripcion_en: str


class ComprobanteReservaResponse(BaseModel):
    reserva_id: str
    codigo: str
    estado: Literal["pendiente_pago", "confirmada", "expirada", "cancelada", "cancelacion_pendiente"]
    oferta_id: str
    nombre_oferta: str
    zona_id: str
    prestador_id: str
    prestador_nombre: str
    prestador_contacto: str
    punto_encuentro: str
    fecha_servicio: str
    hora_servicio: str
    personas: int
    acompanantes: list[str]
    precio_unitario: Decimal
    total: Decimal
    moneda: str
    politica_cancelacion: PoliticaCancelacionDTO
    pago_aprobado: bool
    referencia_pago: str | None = None
    monto_reembolso: Decimal | None = None
    mensaje_es: str
    mensaje_en: str


class FranjaDisponibilidadResponse(BaseModel):
    id: str
    oferta_id: str
    zona_id: str
    prestador_id: str
    fecha: date
    hora_inicio: str
    cupo_total: int
    cupo_disponible: int


class CrearFranjaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta_id: str = Field(..., min_length=2, max_length=80)
    fecha: date
    hora_inicio: time
    cupo_total: int = Field(..., ge=1, le=500)


class UnirseListaEsperaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    personas: int = Field(..., ge=1, le=20)
    correo_turista: EmailStr
    idioma: Literal["es", "en"] = "es"


class EntradaListaEsperaResponse(BaseModel):
    entrada_id: str
    franja_id: str
    personas: int
    estado: Literal["esperando", "ofrecida", "convertida", "expirada", "retirada"]
    posicion: int | None = Field(None, description="Lugar en la fila mientras está 'esperando'")
    oferta_expira_en: datetime | None = Field(None, description="Plazo para confirmar si está 'ofrecida'")
    mensaje_es: str
    mensaje_en: str


class AbrirDisputaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(..., min_length=10, max_length=2000)


class ResolverDisputaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["aprobada", "rechazada"]
    justificacion: str = Field(..., min_length=10, max_length=2000)
    monto_reembolso: Decimal | None = Field(
        None, gt=0, description="Si se aprueba; por defecto, lo cobrado menos lo ya reembolsado"
    )


class DisputaResponse(BaseModel):
    disputa_id: str
    reserva_id: str
    estado: Literal["en_revision", "aprobada", "rechazada"]
    motivo: str
    justificacion: str | None
    monto_reembolso: Decimal | None
    creado_en: datetime
    resuelta_en: datetime | None


class ErrorResponse(BaseModel):
    detail: str


class CupoInsuficienteResponse(BaseModel):
    detail: str
    disponibles: int | None = Field(None, description="Máximo que sí se puede reservar (CU-12 3a)")
    lista_espera_disponible: bool = Field(True, description="Puede unirse a la lista de espera (CU-13)")
