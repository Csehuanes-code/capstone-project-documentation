"""Entidades y reglas de negocio de Reservas (sin frameworks: ni FastAPI, ni Pydantic, ni SQLAlchemy)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
import secrets
import string
import uuid

from reservas.dominio.excepciones import (
    DisputaInvalidaError,
    ReservaNoCancelableError,
    TransicionEstadoInvalidaError,
)

# Santa Marta usa la hora de Colombia (UTC-5, sin horario de verano). La fecha y hora de una
# franja son locales; para calcular plazos de cancelación se convierten con esta zona.
ZONA_HORARIA_COLOMBIA = timezone(timedelta(hours=-5), name="America/Bogota")

MINUTOS_BLOQUEO_PAGO = 10  # temporizador de W4: el cupo se libera si el pago no se confirma
MINUTOS_OFERTA_LISTA_ESPERA = 30  # plazo para que el primero de la lista confirme (CU-13)


class EstadoReserva(str, Enum):
    PENDIENTE_PAGO = "pendiente_pago"
    CONFIRMADA = "confirmada"
    EXPIRADA = "expirada"
    CANCELADA = "cancelada"
    # CU-14 3a / RF-RES-14: la reserva se canceló y el cupo se liberó, pero el reembolso falló;
    # queda pendiente para que el administrador lo gestione.
    CANCELACION_PENDIENTE = "cancelacion_pendiente"


class EstadoPago(str, Enum):
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    TIEMPO_AGOTADO = "tiempo_agotado"


class TipoPago(str, Enum):
    COBRO = "cobro"
    REEMBOLSO = "reembolso"


class EstadoListaEspera(str, Enum):
    ESPERANDO = "esperando"
    OFRECIDA = "ofrecida"  # se le reservó el cupo liberado y tiene un plazo para confirmar
    CONVERTIDA = "convertida"  # confirmó y ya tiene reserva
    EXPIRADA = "expirada"  # no confirmó a tiempo: el cupo pasa al siguiente
    RETIRADA = "retirada"  # el turista salió de la lista


class EstadoDisputa(str, Enum):
    EN_REVISION = "en_revision"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


def generar_codigo_reserva() -> str:
    """Genera códigos legibles tipo SMT-7K3Q9P como en el wireframe W5."""
    alfabeto = string.ascii_uppercase + string.digits
    sufijo = "".join(secrets.choice(alfabeto) for _ in range(6))
    return f"SMT-{sufijo}"


def redondear_pesos(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PoliticaCancelacionCopia:
    """Copia inmutable de la política del prestador al momento de reservar (sección 3.1).

    Mismo modelo que Catálogo (OfertaCondicionesResponse.politica_cancelacion):
      - cancelando con >= horas_reembolso_total de anticipación: reembolso del 100 %
      - con >= horas_reembolso_parcial: reembolso de porcentaje_reembolso_parcial %
      - con menos: sin reembolso (penalidad total)
    """

    horas_reembolso_total: int
    horas_reembolso_parcial: int
    porcentaje_reembolso_parcial: int

    def __post_init__(self) -> None:
        if not (0 <= self.horas_reembolso_parcial <= self.horas_reembolso_total):
            raise ValueError("Debe cumplirse 0 <= horas_reembolso_parcial <= horas_reembolso_total.")
        if not (0 <= self.porcentaje_reembolso_parcial <= 100):
            raise ValueError("porcentaje_reembolso_parcial debe estar entre 0 y 100.")

    def porcentaje_reembolso(self, horas_de_anticipacion: float) -> int:
        if horas_de_anticipacion >= self.horas_reembolso_total:
            return 100
        if self.horas_reembolso_parcial > 0 and horas_de_anticipacion >= self.horas_reembolso_parcial:
            return self.porcentaje_reembolso_parcial
        return 0

    @property
    def descripcion_es(self) -> str:
        texto = f"Reembolso total cancelando con al menos {self.horas_reembolso_total} h de anticipación"
        if self.horas_reembolso_parcial > 0 and self.porcentaje_reembolso_parcial > 0:
            texto += (
                f"; {self.porcentaje_reembolso_parcial} % con al menos "
                f"{self.horas_reembolso_parcial} h"
            )
        return texto + "; después, sin reembolso."

    @property
    def descripcion_en(self) -> str:
        texto = f"Full refund when cancelling at least {self.horas_reembolso_total} h in advance"
        if self.horas_reembolso_parcial > 0 and self.porcentaje_reembolso_parcial > 0:
            texto += (
                f"; {self.porcentaje_reembolso_parcial}% with at least "
                f"{self.horas_reembolso_parcial} h"
            )
        return texto + "; after that, no refund."


@dataclass(frozen=True)
class CondicionesOferta:
    """Condiciones que entrega Catálogo antes de bloquear el cupo (CU-11 paso 2)."""

    oferta_id: str
    nombre_oferta: str
    zona_id: str
    activa: bool
    tarifa_por_persona: Decimal
    moneda: str
    politica_cancelacion: PoliticaCancelacionCopia
    # Opcionales: Catálogo aún no los envía; el comprobante los muestra si llegan.
    prestador_nombre: str = ""
    prestador_contacto: str = ""
    punto_encuentro: str = ""


@dataclass
class FranjaDisponibilidad:
    id: str
    oferta_id: str
    zona_id: str
    prestador_id: str
    fecha: date
    hora_inicio: time
    cupo_total: int
    cupo_disponible: int

    def __post_init__(self) -> None:
        if self.cupo_total <= 0:
            raise ValueError("El cupo_total debe ser mayor que cero.")
        if not (0 <= self.cupo_disponible <= self.cupo_total):
            raise ValueError("El cupo_disponible debe cumplir 0 <= cupo_disponible <= cupo_total.")

    @property
    def inicio(self) -> datetime:
        return datetime.combine(self.fecha, self.hora_inicio, tzinfo=ZONA_HORARIA_COLOMBIA)


@dataclass
class Asistente:
    id: str
    reserva_id: str
    nombre_completo: str
    documento: str | None = None


@dataclass
class Pago:
    id: str
    reserva_id: str
    monto: Decimal
    moneda: str
    metodo: str
    estado: EstadoPago
    referencia_pasarela: str
    tipo: TipoPago = TipoPago.COBRO
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Disputa:
    """CU-17: reclamo por un cobro incorrecto, distinto de una cancelación (CU-14)."""

    id: str
    reserva_id: str
    pago_id: str
    turista_id: str
    motivo: str
    estado: EstadoDisputa = EstadoDisputa.EN_REVISION
    justificacion: str | None = None
    monto_reembolso: Decimal | None = None
    resuelta_por: str | None = None
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resuelta_en: datetime | None = None

    @classmethod
    def abrir(cls, *, reserva_id: str, pago_id: str, turista_id: str, motivo: str) -> Disputa:
        motivo = motivo.strip()
        if len(motivo) < 10:
            raise DisputaInvalidaError("Describa el motivo de la disputa (mínimo 10 caracteres).")
        return cls(
            id=str(uuid.uuid4()),
            reserva_id=reserva_id,
            pago_id=pago_id,
            turista_id=turista_id,
            motivo=motivo,
        )

    def resolver(
        self,
        *,
        aprobada: bool,
        justificacion: str,
        administrador_id: str,
        monto_reembolso: Decimal | None = None,
    ) -> None:
        """Regla de negocio CU-17: toda disputa se resuelve con una justificación registrada."""
        if self.estado != EstadoDisputa.EN_REVISION:
            raise DisputaInvalidaError(f"La disputa ya fue resuelta ({self.estado.value}).")
        justificacion = justificacion.strip()
        if len(justificacion) < 10:
            raise DisputaInvalidaError("La resolución requiere una justificación (mínimo 10 caracteres).")
        self.estado = EstadoDisputa.APROBADA if aprobada else EstadoDisputa.RECHAZADA
        self.justificacion = justificacion
        self.monto_reembolso = monto_reembolso if aprobada else None
        self.resuelta_por = administrador_id
        self.resuelta_en = datetime.now(timezone.utc)


@dataclass
class EntradaListaEspera:
    """CU-13: turista esperando que se libere cupo en una franja agotada (orden de llegada)."""

    id: str
    franja_id: str
    turista_id: str
    correo_turista: str
    idioma: str
    personas: int
    estado: EstadoListaEspera = EstadoListaEspera.ESPERANDO
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    oferta_expira_en: datetime | None = None

    def ofrecer(self, ahora: datetime, minutos: int = MINUTOS_OFERTA_LISTA_ESPERA) -> None:
        if self.estado != EstadoListaEspera.ESPERANDO:
            raise TransicionEstadoInvalidaError("Solo se ofrece cupo a quien está esperando.")
        self.estado = EstadoListaEspera.OFRECIDA
        self.oferta_expira_en = ahora + timedelta(minutes=minutos)

    def oferta_vigente(self, ahora: datetime) -> bool:
        return (
            self.estado == EstadoListaEspera.OFRECIDA
            and self.oferta_expira_en is not None
            and ahora < self.oferta_expira_en
        )

    def convertir(self) -> None:
        if self.estado != EstadoListaEspera.OFRECIDA:
            raise TransicionEstadoInvalidaError("Solo se convierte en reserva una oferta vigente.")
        self.estado = EstadoListaEspera.CONVERTIDA

    def expirar(self) -> None:
        if self.estado != EstadoListaEspera.OFRECIDA:
            raise TransicionEstadoInvalidaError("Solo expira una oferta de cupo.")
        self.estado = EstadoListaEspera.EXPIRADA

    def retirar(self) -> None:
        if self.estado not in (EstadoListaEspera.ESPERANDO, EstadoListaEspera.OFRECIDA):
            raise TransicionEstadoInvalidaError("Esta entrada ya no está activa en la lista.")
        self.estado = EstadoListaEspera.RETIRADA


@dataclass
class Notificacion:
    id: str
    reserva_id: str | None
    destinatario_id: str
    correo_destino: str
    idioma: str
    asunto: str
    cuerpo_texto: str
    enviada: bool = False
    intentos: int = 0
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def nueva(
        cls,
        *,
        destinatario_id: str,
        correo_destino: str,
        idioma: str,
        asunto: str,
        cuerpo_texto: str,
        reserva_id: str | None = None,
    ) -> Notificacion:
        return cls(
            id=str(uuid.uuid4()),
            reserva_id=reserva_id,
            destinatario_id=destinatario_id,
            correo_destino=correo_destino,
            idioma=idioma,
            asunto=asunto,
            cuerpo_texto=cuerpo_texto,
        )


@dataclass
class ProyeccionOfertaLocal:
    """Proyección local alimentada por eventos catalogo.oferta.* (zona_id, prestador_id, activa)."""
    oferta_id: str
    nombre: str
    zona_id: str
    prestador_id: str
    activa: bool


@dataclass
class Reserva:
    id: str
    codigo: str
    clave_idempotencia: str
    franja_id: str
    oferta_id: str
    nombre_oferta: str
    zona_id: str
    prestador_id: str
    prestador_nombre: str
    prestador_contacto: str
    punto_encuentro: str
    turista_id: str
    correo_turista: str
    idioma: str
    fecha_servicio: date
    hora_servicio: time
    personas: int
    precio_unitario_copiado: Decimal
    total: Decimal
    moneda: str
    politica_cancelacion_copiada: PoliticaCancelacionCopia
    estado: EstadoReserva = EstadoReserva.PENDIENTE_PAGO
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bloqueo_expira_en: datetime | None = None
    confirmada_en: datetime | None = None
    cancelada_en: datetime | None = None
    monto_reembolso: Decimal | None = None
    asistentes: list[Asistente] = field(default_factory=list)

    @classmethod
    def crear_pendiente(
        cls,
        *,
        clave_idempotencia: str,
        franja: FranjaDisponibilidad,
        condiciones: CondicionesOferta,
        turista_id: str,
        correo_turista: str,
        idioma: str,
        personas: int,
        minutos_bloqueo: int = MINUTOS_BLOQUEO_PAGO,
        acompanantes: list[str] | None = None,
    ) -> Reserva:
        """Precio y política se COPIAN en la reserva: si el prestador los cambia después, la
        reserva conserva lo que el turista aceptó (sección 3.1)."""
        if personas <= 0:
            raise ValueError("La cantidad de personas debe ser al menos 1.")
        ahora = datetime.now(timezone.utc)
        reserva_id = str(uuid.uuid4())
        total = redondear_pesos(condiciones.tarifa_por_persona * Decimal(personas))
        asistentes = [
            Asistente(id=str(uuid.uuid4()), reserva_id=reserva_id, nombre_completo=nombre.strip())
            for nombre in (acompanantes or [])
            if nombre.strip()
        ]
        if len(asistentes) > personas:
            raise ValueError("Hay más acompañantes que personas en la reserva.")
        return cls(
            id=reserva_id,
            codigo=generar_codigo_reserva(),
            clave_idempotencia=clave_idempotencia,
            franja_id=franja.id,
            oferta_id=franja.oferta_id,
            nombre_oferta=condiciones.nombre_oferta,
            zona_id=condiciones.zona_id or franja.zona_id,
            # El prestador sale de la franja (la creó él); Catálogo no lo envía en condiciones.
            prestador_id=franja.prestador_id,
            prestador_nombre=condiciones.prestador_nombre,
            prestador_contacto=condiciones.prestador_contacto,
            punto_encuentro=condiciones.punto_encuentro,
            turista_id=turista_id,
            correo_turista=correo_turista,
            idioma=idioma if idioma in ("es", "en") else "es",
            fecha_servicio=franja.fecha,
            hora_servicio=franja.hora_inicio,
            personas=personas,
            precio_unitario_copiado=redondear_pesos(condiciones.tarifa_por_persona),
            total=total,
            moneda=condiciones.moneda,
            politica_cancelacion_copiada=condiciones.politica_cancelacion,
            estado=EstadoReserva.PENDIENTE_PAGO,
            creado_en=ahora,
            bloqueo_expira_en=ahora + timedelta(minutes=minutos_bloqueo),
            asistentes=asistentes,
        )

    @property
    def inicio_servicio(self) -> datetime:
        return datetime.combine(self.fecha_servicio, self.hora_servicio, tzinfo=ZONA_HORARIA_COLOMBIA)

    def confirmar(self) -> None:
        if self.estado != EstadoReserva.PENDIENTE_PAGO:
            raise TransicionEstadoInvalidaError(
                f"Solo se puede confirmar una reserva en pendiente_pago (actual: {self.estado.value})."
            )
        self.estado = EstadoReserva.CONFIRMADA
        self.confirmada_en = datetime.now(timezone.utc)

    def expirar(self) -> None:
        if self.estado != EstadoReserva.PENDIENTE_PAGO:
            raise TransicionEstadoInvalidaError(
                f"Solo se puede expirar una reserva en pendiente_pago (actual: {self.estado.value})."
            )
        self.estado = EstadoReserva.EXPIRADA

    def calcular_reembolso(self, ahora: datetime) -> tuple[int, Decimal]:
        """CU-14 paso 2: aplica la política copiada. Devuelve (porcentaje, monto) a reembolsar.

        Una reserva grupal se cancela como unidad (regla de CU-12): el reembolso es sobre el total.
        """
        if self.estado == EstadoReserva.PENDIENTE_PAGO:
            return 0, Decimal("0.00")  # aún no se cobró nada
        if self.estado != EstadoReserva.CONFIRMADA:
            raise ReservaNoCancelableError(
                f"No se puede cancelar una reserva en estado {self.estado.value}."
            )
        if ahora >= self.inicio_servicio:
            raise ReservaNoCancelableError("El servicio ya comenzó o pasó; no se puede cancelar.")
        horas = (self.inicio_servicio - ahora).total_seconds() / 3600
        porcentaje = self.politica_cancelacion_copiada.porcentaje_reembolso(horas)
        return porcentaje, redondear_pesos(self.total * Decimal(porcentaje) / Decimal(100))

    def cancelar(self, ahora: datetime, monto_reembolso: Decimal) -> None:
        if self.estado not in (EstadoReserva.PENDIENTE_PAGO, EstadoReserva.CONFIRMADA):
            raise ReservaNoCancelableError(
                f"No se puede cancelar una reserva en estado {self.estado.value}."
            )
        self.estado = EstadoReserva.CANCELADA
        self.cancelada_en = ahora
        self.monto_reembolso = monto_reembolso

    def marcar_cancelacion_pendiente(self) -> None:
        """RF-RES-14: el reembolso falló; la reserva sigue cancelada pero queda pendiente."""
        if self.estado != EstadoReserva.CANCELADA:
            raise TransicionEstadoInvalidaError("Solo una reserva cancelada puede quedar pendiente.")
        self.estado = EstadoReserva.CANCELACION_PENDIENTE
