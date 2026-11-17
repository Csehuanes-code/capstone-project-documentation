"""Repositorios SQLAlchemy de reservas_db (PostgreSQL en producción; SQLite en pruebas rápidas).

Todas las transiciones de estado que pueden competir entre procesos usan UPDATE condicionales
(`... WHERE id = :id AND estado = :esperado`): solo uno gana y el otro se entera por rowcount.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from comun.eventos import registrar_en_outbox
from reservas.aplicacion.puertos import UnitOfWork
from reservas.dominio.entidades import (
    Asistente,
    Disputa,
    EntradaListaEspera,
    EstadoDisputa,
    EstadoListaEspera,
    EstadoPago,
    EstadoReserva,
    FranjaDisponibilidad,
    Notificacion,
    Pago,
    PoliticaCancelacionCopia,
    ProyeccionOfertaLocal,
    Reserva,
    TipoPago,
)
from reservas.dominio.excepciones import ClaveIdempotenciaDuplicadaError
from reservas.dominio.repositorios import (
    DisputaRepository,
    FranjaRepository,
    ListaEsperaRepository,
    NotificacionRepository,
    PagoRepository,
    ProyeccionOfertaRepository,
    ReservaRepository,
)
from reservas.infraestructura.sql.tablas import (
    AsistenteORM,
    DisputaORM,
    EntradaListaEsperaORM,
    FranjaDisponibilidadORM,
    NotificacionORM,
    PagoORM,
    ProyeccionOfertaORM,
    ReservaORM,
)


def _utc(valor: datetime | None) -> datetime | None:
    """SQLite devuelve fechas sin zona horaria; el dominio siempre trabaja en UTC con zona."""
    if valor is None:
        return None
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)


def _dec(valor: Any) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


# --- franjas ------------------------------------------------------------------------------


def _franja_a_dominio(row: FranjaDisponibilidadORM) -> FranjaDisponibilidad:
    return FranjaDisponibilidad(
        id=row.id,
        oferta_id=row.oferta_id,
        zona_id=row.zona_id,
        prestador_id=row.prestador_id,
        fecha=row.fecha,
        hora_inicio=row.hora_inicio,
        cupo_total=row.cupo_total,
        cupo_disponible=row.cupo_disponible,
    )


class FranjaRepositoryPostgres(FranjaRepository):
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar(self, franja: FranjaDisponibilidad) -> FranjaDisponibilidad:
        self.sesion.add(
            FranjaDisponibilidadORM(
                id=franja.id,
                oferta_id=franja.oferta_id,
                zona_id=franja.zona_id,
                prestador_id=franja.prestador_id,
                fecha=franja.fecha,
                hora_inicio=franja.hora_inicio,
                cupo_total=franja.cupo_total,
                cupo_disponible=franja.cupo_disponible,
            )
        )
        self.sesion.flush()
        return franja

    def obtener_por_id(self, franja_id: str) -> FranjaDisponibilidad | None:
        # populate_existing: relee de la base aunque la sesión tenga una copia vieja
        # (los UPDATE atómicos de cupo no pasan por el objeto en memoria).
        row = self.sesion.get(FranjaDisponibilidadORM, franja_id, populate_existing=True)
        return _franja_a_dominio(row) if row else None

    def buscar_disponibles(
        self,
        oferta_id: str,
        desde: date | None = None,
        hasta: date | None = None,
        personas: int = 1,
    ) -> list[FranjaDisponibilidad]:
        stmt = select(FranjaDisponibilidadORM).where(
            FranjaDisponibilidadORM.oferta_id == oferta_id,
            FranjaDisponibilidadORM.cupo_disponible >= personas,
        )
        if desde is not None:
            stmt = stmt.where(FranjaDisponibilidadORM.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(FranjaDisponibilidadORM.fecha <= hasta)
        stmt = stmt.order_by(FranjaDisponibilidadORM.fecha, FranjaDisponibilidadORM.hora_inicio)
        return [_franja_a_dominio(f) for f in self.sesion.execute(stmt).scalars().all()]

    def bloquear_cupo_atomico(self, franja_id: str, personas: int) -> bool:
        """Instrucción atómica de la sección 3.2:
        UPDATE franja_disponibilidad SET cupo_disponible = cupo_disponible - :n
        WHERE id = :franja AND cupo_disponible >= :n
        PostgreSQL bloquea la fila durante el UPDATE: de dos peticiones simultáneas por el
        último cupo, la segunda re-evalúa el WHERE después de la primera y afecta 0 filas.
        """
        stmt = (
            update(FranjaDisponibilidadORM)
            .where(
                FranjaDisponibilidadORM.id == franja_id,
                FranjaDisponibilidadORM.cupo_disponible >= personas,
            )
            .values(cupo_disponible=FranjaDisponibilidadORM.cupo_disponible - personas)
            .execution_options(synchronize_session=False)
        )
        return (self.sesion.execute(stmt).rowcount or 0) == 1

    def devolver_cupo_atomico(self, franja_id: str, personas: int) -> None:
        stmt = (
            update(FranjaDisponibilidadORM)
            .where(
                FranjaDisponibilidadORM.id == franja_id,
                FranjaDisponibilidadORM.cupo_disponible + personas <= FranjaDisponibilidadORM.cupo_total,
            )
            .values(cupo_disponible=FranjaDisponibilidadORM.cupo_disponible + personas)
            .execution_options(synchronize_session=False)
        )
        self.sesion.execute(stmt)


# --- reservas -----------------------------------------------------------------------------


def _reserva_a_dominio(row: ReservaORM) -> Reserva:
    return Reserva(
        id=row.id,
        codigo=row.codigo,
        clave_idempotencia=row.clave_idempotencia,
        franja_id=row.franja_id,
        oferta_id=row.oferta_id,
        nombre_oferta=row.nombre_oferta,
        zona_id=row.zona_id,
        prestador_id=row.prestador_id,
        prestador_nombre=row.prestador_nombre,
        prestador_contacto=row.prestador_contacto,
        punto_encuentro=row.punto_encuentro,
        turista_id=row.turista_id,
        correo_turista=row.correo_turista,
        idioma=row.idioma,
        fecha_servicio=row.fecha_servicio,
        hora_servicio=row.hora_servicio,
        personas=row.personas,
        precio_unitario_copiado=Decimal(str(row.precio_unitario_copiado)),
        total=Decimal(str(row.total)),
        moneda=row.moneda,
        politica_cancelacion_copiada=PoliticaCancelacionCopia(
            horas_reembolso_total=row.pol_horas_reembolso_total,
            horas_reembolso_parcial=row.pol_horas_reembolso_parcial,
            porcentaje_reembolso_parcial=row.pol_porcentaje_reembolso_parcial,
        ),
        estado=EstadoReserva(row.estado),
        creado_en=_utc(row.creado_en),  # type: ignore[arg-type]
        bloqueo_expira_en=_utc(row.bloqueo_expira_en),
        confirmada_en=_utc(row.confirmada_en),
        cancelada_en=_utc(row.cancelada_en),
        monto_reembolso=_dec(row.monto_reembolso),
        asistentes=[
            Asistente(id=a.id, reserva_id=a.reserva_id, nombre_completo=a.nombre_completo,
                      documento=a.documento)
            for a in row.asistentes
        ],
    )


class ReservaRepositoryPostgres(ReservaRepository):
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def obtener_por_id(self, reserva_id: str) -> Reserva | None:
        row = self.sesion.get(ReservaORM, reserva_id, populate_existing=True)
        return _reserva_a_dominio(row) if row else None

    def obtener_por_idempotencia(self, turista_id: str, clave_idempotencia: str) -> Reserva | None:
        stmt = select(ReservaORM).where(
            ReservaORM.turista_id == turista_id,
            ReservaORM.clave_idempotencia == clave_idempotencia,
        )
        row = self.sesion.execute(stmt).scalar_one_or_none()
        return _reserva_a_dominio(row) if row else None

    def listar_por_turista(self, turista_id: str) -> list[Reserva]:
        stmt = select(ReservaORM).where(ReservaORM.turista_id == turista_id).order_by(
            ReservaORM.creado_en.desc()
        )
        return [_reserva_a_dominio(r) for r in self.sesion.execute(stmt).scalars().all()]

    def listar_por_prestador(self, prestador_id: str) -> list[Reserva]:
        stmt = select(ReservaORM).where(ReservaORM.prestador_id == prestador_id).order_by(
            ReservaORM.creado_en.desc()
        )
        return [_reserva_a_dominio(r) for r in self.sesion.execute(stmt).scalars().all()]

    def guardar_nueva(self, reserva: Reserva) -> Reserva:
        pol = reserva.politica_cancelacion_copiada
        self.sesion.add(
            ReservaORM(
                id=reserva.id,
                codigo=reserva.codigo,
                clave_idempotencia=reserva.clave_idempotencia,
                franja_id=reserva.franja_id,
                oferta_id=reserva.oferta_id,
                nombre_oferta=reserva.nombre_oferta,
                zona_id=reserva.zona_id,
                prestador_id=reserva.prestador_id,
                prestador_nombre=reserva.prestador_nombre,
                prestador_contacto=reserva.prestador_contacto,
                punto_encuentro=reserva.punto_encuentro,
                turista_id=reserva.turista_id,
                correo_turista=reserva.correo_turista,
                idioma=reserva.idioma,
                fecha_servicio=reserva.fecha_servicio,
                hora_servicio=reserva.hora_servicio,
                personas=reserva.personas,
                precio_unitario_copiado=reserva.precio_unitario_copiado,
                total=reserva.total,
                moneda=reserva.moneda,
                pol_horas_reembolso_total=pol.horas_reembolso_total,
                pol_horas_reembolso_parcial=pol.horas_reembolso_parcial,
                pol_porcentaje_reembolso_parcial=pol.porcentaje_reembolso_parcial,
                estado=reserva.estado.value,
                creado_en=reserva.creado_en,
                bloqueo_expira_en=reserva.bloqueo_expira_en,
                confirmada_en=reserva.confirmada_en,
                asistentes=[
                    AsistenteORM(id=a.id, reserva_id=reserva.id, nombre_completo=a.nombre_completo,
                                 documento=a.documento)
                    for a in reserva.asistentes
                ],
            )
        )
        try:
            self.sesion.flush()
        except IntegrityError:
            # Se revierte TODA la transacción (incluido el bloqueo de cupo) y se averigua si
            # fue la restricción única de idempotencia (otra petición con la misma clave).
            self.sesion.rollback()
            if self.obtener_por_idempotencia(reserva.turista_id, reserva.clave_idempotencia):
                raise ClaveIdempotenciaDuplicadaError(reserva.clave_idempotencia) from None
            raise
        return reserva

    def actualizar_si_estado(self, reserva: Reserva, estado_esperado: EstadoReserva) -> bool:
        stmt = (
            update(ReservaORM)
            .where(ReservaORM.id == reserva.id, ReservaORM.estado == estado_esperado.value)
            .values(
                estado=reserva.estado.value,
                confirmada_en=reserva.confirmada_en,
                cancelada_en=reserva.cancelada_en,
                monto_reembolso=reserva.monto_reembolso,
            )
            .execution_options(synchronize_session=False)
        )
        return (self.sesion.execute(stmt).rowcount or 0) == 1

    def listar_pendientes_vencidas(self, corte: datetime) -> list[Reserva]:
        stmt = select(ReservaORM).where(
            ReservaORM.estado == EstadoReserva.PENDIENTE_PAGO.value,
            ReservaORM.bloqueo_expira_en.is_not(None),
            ReservaORM.bloqueo_expira_en <= corte,
        )
        return [_reserva_a_dominio(r) for r in self.sesion.execute(stmt).scalars().all()]


# --- pagos --------------------------------------------------------------------------------


def _pago_a_dominio(row: PagoORM) -> Pago:
    return Pago(
        id=row.id,
        reserva_id=row.reserva_id,
        monto=Decimal(str(row.monto)),
        moneda=row.moneda,
        metodo=row.metodo,
        estado=EstadoPago(row.estado),
        referencia_pasarela=row.referencia_pasarela,
        tipo=TipoPago(row.tipo),
        creado_en=_utc(row.creado_en),  # type: ignore[arg-type]
    )


class PagoRepositoryPostgres(PagoRepository):
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar(self, pago: Pago) -> Pago:
        self.sesion.add(
            PagoORM(
                id=pago.id,
                reserva_id=pago.reserva_id,
                tipo=pago.tipo.value,
                monto=pago.monto,
                moneda=pago.moneda,
                metodo=pago.metodo,
                estado=pago.estado.value,
                referencia_pasarela=pago.referencia_pasarela,
                creado_en=pago.creado_en,
            )
        )
        self.sesion.flush()
        return pago

    def obtener_cobro(self, reserva_id: str) -> Pago | None:
        stmt = select(PagoORM).where(
            PagoORM.reserva_id == reserva_id,
            PagoORM.tipo == TipoPago.COBRO.value,
            PagoORM.estado == EstadoPago.APROBADO.value,
        ).limit(1)
        row = self.sesion.execute(stmt).scalar_one_or_none()
        return _pago_a_dominio(row) if row else None

    def listar_por_reserva(self, reserva_id: str) -> list[Pago]:
        stmt = select(PagoORM).where(PagoORM.reserva_id == reserva_id).order_by(PagoORM.creado_en)
        return [_pago_a_dominio(r) for r in self.sesion.execute(stmt).scalars().all()]


# --- notificaciones -----------------------------------------------------------------------


class NotificacionRepositoryPostgres(NotificacionRepository):
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar(self, notificacion: Notificacion) -> Notificacion:
        self.sesion.add(
            NotificacionORM(
                id=notificacion.id,
                reserva_id=notificacion.reserva_id,
                destinatario_id=notificacion.destinatario_id,
                correo_destino=notificacion.correo_destino,
                idioma=notificacion.idioma,
                asunto=notificacion.asunto,
                cuerpo_texto=notificacion.cuerpo_texto,
                enviada=notificacion.enviada,
                intentos=notificacion.intentos,
                creado_en=notificacion.creado_en,
            )
        )
        self.sesion.flush()
        return notificacion

    def marcar_enviada(self, notificacion_id: str) -> None:
        self.sesion.execute(
            update(NotificacionORM)
            .where(NotificacionORM.id == notificacion_id)
            .values(enviada=True, intentos=NotificacionORM.intentos + 1)
            .execution_options(synchronize_session=False)
        )

    def registrar_intento_fallido(self, notificacion_id: str) -> None:
        self.sesion.execute(
            update(NotificacionORM)
            .where(NotificacionORM.id == notificacion_id)
            .values(intentos=NotificacionORM.intentos + 1)
            .execution_options(synchronize_session=False)
        )

    def listar_pendientes(self, limite: int, max_intentos: int) -> list[Notificacion]:
        stmt = (
            select(NotificacionORM)
            .where(NotificacionORM.enviada.is_(False), NotificacionORM.intentos < max_intentos)
            .order_by(NotificacionORM.creado_en)
            .limit(limite)
        )
        return [
            Notificacion(
                id=r.id,
                reserva_id=r.reserva_id,
                destinatario_id=r.destinatario_id,
                correo_destino=r.correo_destino,
                idioma=r.idioma,
                asunto=r.asunto,
                cuerpo_texto=r.cuerpo_texto,
                enviada=r.enviada,
                intentos=r.intentos,
                creado_en=_utc(r.creado_en),  # type: ignore[arg-type]
            )
            for r in self.sesion.execute(stmt).scalars().all()
        ]


# --- lista de espera ----------------------------------------------------------------------


def _entrada_a_dominio(row: EntradaListaEsperaORM) -> EntradaListaEspera:
    return EntradaListaEspera(
        id=row.id,
        franja_id=row.franja_id,
        turista_id=row.turista_id,
        correo_turista=row.correo_turista,
        idioma=row.idioma,
        personas=row.personas,
        estado=EstadoListaEspera(row.estado),
        creado_en=_utc(row.creado_en),  # type: ignore[arg-type]
        oferta_expira_en=_utc(row.oferta_expira_en),
    )


class ListaEsperaRepositoryPostgres(ListaEsperaRepository):
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        self.sesion.add(
            EntradaListaEsperaORM(
                id=entrada.id,
                franja_id=entrada.franja_id,
                turista_id=entrada.turista_id,
                correo_turista=entrada.correo_turista,
                idioma=entrada.idioma,
                personas=entrada.personas,
                estado=entrada.estado.value,
                creado_en=entrada.creado_en,
                oferta_expira_en=entrada.oferta_expira_en,
            )
        )
        self.sesion.flush()
        return entrada

    def actualizar_si_estado(self, entrada: EntradaListaEspera, estado_esperado: EstadoListaEspera) -> bool:
        stmt = (
            update(EntradaListaEsperaORM)
            .where(
                EntradaListaEsperaORM.id == entrada.id,
                EntradaListaEsperaORM.estado == estado_esperado.value,
            )
            .values(estado=entrada.estado.value, oferta_expira_en=entrada.oferta_expira_en)
            .execution_options(synchronize_session=False)
        )
        return (self.sesion.execute(stmt).rowcount or 0) == 1

    def obtener_por_id(self, entrada_id: str) -> EntradaListaEspera | None:
        row = self.sesion.get(EntradaListaEsperaORM, entrada_id, populate_existing=True)
        return _entrada_a_dominio(row) if row else None

    def obtener_primera_esperando(self, franja_id: str) -> EntradaListaEspera | None:
        stmt = (
            select(EntradaListaEsperaORM)
            .where(
                EntradaListaEsperaORM.franja_id == franja_id,
                EntradaListaEsperaORM.estado == EstadoListaEspera.ESPERANDO.value,
            )
            .order_by(EntradaListaEsperaORM.creado_en, EntradaListaEsperaORM.id)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        row = self.sesion.execute(stmt).scalar_one_or_none()
        return _entrada_a_dominio(row) if row else None

    def posicion(self, entrada: EntradaListaEspera) -> int:
        stmt = select(func.count()).select_from(EntradaListaEsperaORM).where(
            EntradaListaEsperaORM.franja_id == entrada.franja_id,
            EntradaListaEsperaORM.estado == EstadoListaEspera.ESPERANDO.value,
            or_(
                EntradaListaEsperaORM.creado_en < entrada.creado_en,
                and_(
                    EntradaListaEsperaORM.creado_en == entrada.creado_en,
                    EntradaListaEsperaORM.id < entrada.id,
                ),
            ),
        )
        return int(self.sesion.execute(stmt).scalar_one()) + 1

    def existe_activa(self, franja_id: str, turista_id: str) -> bool:
        stmt = select(func.count()).select_from(EntradaListaEsperaORM).where(
            EntradaListaEsperaORM.franja_id == franja_id,
            EntradaListaEsperaORM.turista_id == turista_id,
            EntradaListaEsperaORM.estado.in_(
                [EstadoListaEspera.ESPERANDO.value, EstadoListaEspera.OFRECIDA.value]
            ),
        )
        return int(self.sesion.execute(stmt).scalar_one()) > 0

    def listar_ofertas_vencidas(self, ahora: datetime) -> list[EntradaListaEspera]:
        stmt = select(EntradaListaEsperaORM).where(
            EntradaListaEsperaORM.estado == EstadoListaEspera.OFRECIDA.value,
            EntradaListaEsperaORM.oferta_expira_en <= ahora,
        )
        return [_entrada_a_dominio(r) for r in self.sesion.execute(stmt).scalars().all()]

    def listar_por_turista(self, turista_id: str) -> list[EntradaListaEspera]:
        stmt = select(EntradaListaEsperaORM).where(
            EntradaListaEsperaORM.turista_id == turista_id
        ).order_by(EntradaListaEsperaORM.creado_en.desc())
        return [_entrada_a_dominio(r) for r in self.sesion.execute(stmt).scalars().all()]


# --- disputas -----------------------------------------------------------------------------


def _disputa_a_dominio(row: DisputaORM) -> Disputa:
    return Disputa(
        id=row.id,
        reserva_id=row.reserva_id,
        pago_id=row.pago_id,
        turista_id=row.turista_id,
        motivo=row.motivo,
        estado=EstadoDisputa(row.estado),
        justificacion=row.justificacion,
        monto_reembolso=_dec(row.monto_reembolso),
        resuelta_por=row.resuelta_por,
        creado_en=_utc(row.creado_en),  # type: ignore[arg-type]
        resuelta_en=_utc(row.resuelta_en),
    )


class DisputaRepositoryPostgres(DisputaRepository):
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar(self, disputa: Disputa) -> Disputa:
        self.sesion.add(
            DisputaORM(
                id=disputa.id,
                reserva_id=disputa.reserva_id,
                pago_id=disputa.pago_id,
                turista_id=disputa.turista_id,
                motivo=disputa.motivo,
                estado=disputa.estado.value,
                creado_en=disputa.creado_en,
            )
        )
        self.sesion.flush()
        return disputa

    def resolver_si_en_revision(self, disputa: Disputa) -> bool:
        stmt = (
            update(DisputaORM)
            .where(DisputaORM.id == disputa.id, DisputaORM.estado == EstadoDisputa.EN_REVISION.value)
            .values(
                estado=disputa.estado.value,
                justificacion=disputa.justificacion,
                monto_reembolso=disputa.monto_reembolso,
                resuelta_por=disputa.resuelta_por,
                resuelta_en=disputa.resuelta_en,
            )
            .execution_options(synchronize_session=False)
        )
        return (self.sesion.execute(stmt).rowcount or 0) == 1

    def revertir_a_revision(self, disputa_id: str) -> None:
        self.sesion.execute(
            update(DisputaORM)
            .where(DisputaORM.id == disputa_id)
            .values(estado=EstadoDisputa.EN_REVISION.value, justificacion=None,
                    monto_reembolso=None, resuelta_por=None, resuelta_en=None)
            .execution_options(synchronize_session=False)
        )

    def obtener_por_id(self, disputa_id: str) -> Disputa | None:
        row = self.sesion.get(DisputaORM, disputa_id, populate_existing=True)
        return _disputa_a_dominio(row) if row else None

    def listar(self, estado: EstadoDisputa | None = None) -> list[Disputa]:
        stmt = select(DisputaORM).order_by(DisputaORM.creado_en)
        if estado is not None:
            stmt = stmt.where(DisputaORM.estado == estado.value)
        return [_disputa_a_dominio(r) for r in self.sesion.execute(stmt).scalars().all()]

    def existe_en_revision(self, reserva_id: str) -> bool:
        stmt = select(func.count()).select_from(DisputaORM).where(
            DisputaORM.reserva_id == reserva_id,
            DisputaORM.estado == EstadoDisputa.EN_REVISION.value,
        )
        return int(self.sesion.execute(stmt).scalar_one()) > 0


# --- proyección de ofertas ----------------------------------------------------------------


class ProyeccionOfertaRepositoryPostgres(ProyeccionOfertaRepository):
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar_o_actualizar(self, proyeccion: ProyeccionOfertaLocal) -> None:
        row = self.sesion.get(ProyeccionOfertaORM, proyeccion.oferta_id)
        if row is None:
            self.sesion.add(
                ProyeccionOfertaORM(
                    oferta_id=proyeccion.oferta_id,
                    nombre=proyeccion.nombre,
                    zona_id=proyeccion.zona_id,
                    prestador_id=proyeccion.prestador_id,
                    activa=proyeccion.activa,
                )
            )
        else:
            row.nombre = proyeccion.nombre
            row.zona_id = proyeccion.zona_id
            row.prestador_id = proyeccion.prestador_id
            row.activa = proyeccion.activa
        self.sesion.flush()

    def obtener(self, oferta_id: str) -> ProyeccionOfertaLocal | None:
        row = self.sesion.get(ProyeccionOfertaORM, oferta_id, populate_existing=True)
        if row is None:
            return None
        return ProyeccionOfertaLocal(
            oferta_id=row.oferta_id, nombre=row.nombre, zona_id=row.zona_id,
            prestador_id=row.prestador_id, activa=row.activa,
        )


# --- unidad de trabajo --------------------------------------------------------------------


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Una sesión = una transacción. Sin commit() explícito, todo se revierte al salir."""

    def __init__(self, session_factory):  # type: ignore[no-untyped-def]
        self._session_factory = session_factory
        self.sesion: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.sesion = self._session_factory()
        self.franjas = FranjaRepositoryPostgres(self.sesion)
        self.reservas = ReservaRepositoryPostgres(self.sesion)
        self.pagos = PagoRepositoryPostgres(self.sesion)
        self.notificaciones = NotificacionRepositoryPostgres(self.sesion)
        self.lista_espera = ListaEsperaRepositoryPostgres(self.sesion)
        self.disputas = DisputaRepositoryPostgres(self.sesion)
        self.proyecciones = ProyeccionOfertaRepositoryPostgres(self.sesion)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        assert self.sesion is not None
        try:
            self.sesion.rollback()  # no hace nada si ya se confirmó
        finally:
            self.sesion.close()
            self.sesion = None

    def registrar_evento_outbox(self, tipo: str, datos: dict[str, Any], version: int = 1) -> str:
        assert self.sesion is not None
        return registrar_en_outbox(self.sesion, tipo=tipo, datos=datos, version=version).evento_id

    def commit(self) -> None:
        assert self.sesion is not None
        self.sesion.commit()

    def rollback(self) -> None:
        assert self.sesion is not None
        self.sesion.rollback()
