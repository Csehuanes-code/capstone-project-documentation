"""Casos de uso de Reservas. Orquestan dominio, repositorios y puertos; no conocen HTTP ni SQL.

CU-08 disponibilidad · CU-11/CU-12 reservar (flujo crítico, también en grupo) · CU-13 lista de
espera · CU-14 cancelar · CU-16 pago simulado · CU-17 disputas · CU-18 comprobante y correos.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging
import uuid

from reservas.aplicacion import textos
from reservas.aplicacion.dto import (
    FiltroReservas,
    ResultadoDisputa,
    ResultadoIniciarReserva,
    ResultadoListaEspera,
    SolicitudCrearFranja,
    SolicitudIniciarReserva,
)
from reservas.aplicacion.puertos import (
    CondicionesOfertaPort,
    NotificadorPort,
    PagoPort,
    ResultadoCobro,
    UnitOfWork,
)
from reservas.dominio.entidades import (
    Disputa,
    EntradaListaEspera,
    EstadoDisputa,
    EstadoListaEspera,
    EstadoPago,
    EstadoReserva,
    FranjaDisponibilidad,
    Pago,
    Reserva,
    TipoPago,
    redondear_pesos,
)
from reservas.dominio.excepciones import (
    AccesoDenegadoDominioError,
    ClaveIdempotenciaDuplicadaError,
    CupoInsuficienteError,
    DisputaInvalidaError,
    ListaEsperaInvalidaError,
    OfertaNoDisponibleError,
    RecursoNoEncontradoError,
    ReembolsoFallidoError,
    ReservaNoCancelableError,
)

FabricaUnidad = Callable[[], UnitOfWork]
Reloj = Callable[[], datetime]

log = logging.getLogger("reservas.casos_uso")

TIPO_RESERVA_CONFIRMADA = "reservas.reserva.confirmada"
TIPO_CANCELACION_PENDIENTE = "reservas.cancelacion.pendiente"
TIPO_DISPUTA_ABIERTA = "reservas.disputa.abierta"


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


# --- utilidades compartidas -------------------------------------------------------------


def _resultado(
    reserva: Reserva,
    *,
    cobro: Pago | None,
    mensaje_es: str,
    mensaje_en: str,
) -> ResultadoIniciarReserva:
    pol = reserva.politica_cancelacion_copiada
    return ResultadoIniciarReserva(
        reserva_id=reserva.id,
        codigo=reserva.codigo,
        estado=reserva.estado.value,
        oferta_id=reserva.oferta_id,
        nombre_oferta=reserva.nombre_oferta,
        zona_id=reserva.zona_id,
        prestador_id=reserva.prestador_id,
        prestador_nombre=reserva.prestador_nombre,
        prestador_contacto=reserva.prestador_contacto,
        punto_encuentro=reserva.punto_encuentro,
        fecha_servicio=reserva.fecha_servicio.isoformat(),
        hora_servicio=reserva.hora_servicio.strftime("%H:%M"),
        personas=reserva.personas,
        acompanantes=[a.nombre_completo for a in reserva.asistentes],
        precio_unitario=reserva.precio_unitario_copiado,
        total=reserva.total,
        moneda=reserva.moneda,
        politica_cancelacion={
            "horas_reembolso_total": pol.horas_reembolso_total,
            "horas_reembolso_parcial": pol.horas_reembolso_parcial,
            "porcentaje_reembolso_parcial": pol.porcentaje_reembolso_parcial,
            "descripcion_es": pol.descripcion_es,
            "descripcion_en": pol.descripcion_en,
        },
        pago_aprobado=cobro is not None and cobro.estado == EstadoPago.APROBADO,
        referencia_pago=cobro.referencia_pasarela if cobro else None,
        monto_reembolso=reserva.monto_reembolso,
        mensaje_es=mensaje_es,
        mensaje_en=mensaje_en,
    )


def _ofrecer_cupo_liberado(uow: UnitOfWork, franja_id: str, ahora: datetime) -> None:
    """CU-13 paso 3: el cupo liberado se ofrece al primero de la lista, estrictamente en orden.

    El cupo se BLOQUEA para él durante el plazo (nadie más puede tomarlo). Si el primero no
    cabe en lo liberado, se espera a que se libere más: no se salta a nadie.
    """
    for _ in range(100):  # tope de seguridad; en la práctica son pocas vueltas
        entrada = uow.lista_espera.obtener_primera_esperando(franja_id)
        if entrada is None:
            return
        if not uow.franjas.bloquear_cupo_atomico(franja_id, entrada.personas):
            return
        entrada.ofrecer(ahora)
        if not uow.lista_espera.actualizar_si_estado(entrada, EstadoListaEspera.ESPERANDO):
            # Otro proceso ya se la ofreció: se devuelve el cupo y se mira al siguiente.
            uow.franjas.devolver_cupo_atomico(franja_id, entrada.personas)
            continue
        franja = uow.franjas.obtener_por_id(franja_id)
        assert franja is not None
        uow.notificaciones.guardar(textos.oferta_lista_espera(entrada, franja))


def _liberar_cupo(uow: UnitOfWork, franja_id: str, personas: int, ahora: datetime) -> None:
    uow.franjas.devolver_cupo_atomico(franja_id, personas)
    _ofrecer_cupo_liberado(uow, franja_id, ahora)


def _cobrar_sin_excepcion(pago_port: PagoPort, **kwargs: object) -> ResultadoCobro:
    """Un fallo inesperado de la pasarela se trata como tiempo agotado: se compensa sin cobrar."""
    try:
        return pago_port.cobrar(**kwargs)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        log.warning("La pasarela falló al cobrar: %s", exc)
        return ResultadoCobro(EstadoPago.TIEMPO_AGOTADO, "", f"Fallo de la pasarela: {exc}")


def _reembolsar_sin_excepcion(pago_port: PagoPort, **kwargs: object) -> ResultadoCobro:
    try:
        return pago_port.reembolsar(**kwargs)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        log.warning("La pasarela falló al reembolsar: %s", exc)
        return ResultadoCobro(EstadoPago.TIEMPO_AGOTADO, "", f"Fallo de la pasarela: {exc}")


# --- CU-11 / CU-12 / CU-16: reservar y pagar ---------------------------------------------


class IniciarReservaUseCase:
    """Flujo crítico CU-11 (diagrama de secuencia, sección 8.1) + CU-16 pago simulado.

    CU-12 (grupo) es la misma operación con personas > 1: todos los cupos se bloquean con UNA
    instrucción atómica (todo o nada) y se emite un único comprobante.
    """

    def __init__(
        self,
        uow_factory: FabricaUnidad,
        catalogo_port: CondicionesOfertaPort,
        pago_port: PagoPort,
        notificador_port: NotificadorPort | None = None,
        reloj: Reloj = _ahora_utc,
    ):
        self.uow_factory = uow_factory
        self.catalogo_port = catalogo_port
        self.pago_port = pago_port
        self.notificador_port = notificador_port
        self.reloj = reloj

    def ejecutar(self, solicitud: SolicitudIniciarReserva) -> ResultadoIniciarReserva:
        ahora = self.reloj()

        # Paso 7 (idempotencia): la misma Idempotency-Key devuelve la misma respuesta.
        with self.uow_factory() as uow:
            existente = self._respuesta_idempotente(uow, solicitud)
            if existente is not None:
                return existente
            franja = uow.franjas.obtener_por_id(solicitud.franja_id)
            if franja is None:
                raise RecursoNoEncontradoError(f"Franja '{solicitud.franja_id}' no encontrada.")
            if franja.inicio <= ahora:
                raise OfertaNoDisponibleError("La franja ya comenzó o pasó; elija otra fecha.")
            if solicitud.entrada_lista_espera_id:
                self._validar_oferta_lista_espera(uow, solicitud, franja, ahora)

        # Paso 2: condiciones en Catálogo (timeout 1 s + circuit breaker en el adaptador).
        # Si Catálogo no responde se lanza ServicioCatalogoNoDisponibleError (503) SIN tocar cupo.
        condiciones = self.catalogo_port.obtener_condiciones(franja.oferta_id, franja.fecha)
        if not condiciones.activa:
            raise OfertaNoDisponibleError(
                f"La oferta '{franja.oferta_id}' no está activa para nuevas reservas."
            )

        # Paso 3: transacción 1 → bloqueo atómico del cupo + reserva pendiente_pago. COMMIT.
        try:
            with self.uow_factory() as uow:
                if solicitud.entrada_lista_espera_id:
                    # El cupo ya está bloqueado para él desde que se le ofreció.
                    entrada = uow.lista_espera.obtener_por_id(solicitud.entrada_lista_espera_id)
                    if entrada is None or not entrada.oferta_vigente(ahora):
                        raise ListaEsperaInvalidaError("La oferta de cupo ya no está vigente.")
                    entrada.convertir()
                    if not uow.lista_espera.actualizar_si_estado(entrada, EstadoListaEspera.OFRECIDA):
                        raise ListaEsperaInvalidaError("La oferta de cupo ya no está vigente.")
                elif not uow.franjas.bloquear_cupo_atomico(franja.id, solicitud.personas):
                    existente = self._respuesta_idempotente(uow, solicitud)
                    if existente is not None:
                        return existente
                    actual = uow.franjas.obtener_por_id(franja.id)
                    disponibles = actual.cupo_disponible if actual else 0
                    raise CupoInsuficienteError(
                        f"No hay {solicitud.personas} cupo(s) en la franja; quedan "
                        f"{disponibles} disponibles. "
                        "Puede reservar menos personas o unirse a la lista de espera.",
                        disponibles=disponibles,
                    )
                reserva = Reserva.crear_pendiente(
                    clave_idempotencia=solicitud.clave_idempotencia,
                    franja=franja,
                    condiciones=condiciones,
                    turista_id=solicitud.turista_id,
                    correo_turista=solicitud.correo_turista,
                    idioma=solicitud.idioma,
                    personas=solicitud.personas,
                    acompanantes=solicitud.acompanantes,
                )
                uow.reservas.guardar_nueva(reserva)
                uow.commit()
        except ClaveIdempotenciaDuplicadaError:
            # Otra petición con la misma clave ganó la carrera: la transacción se revirtió
            # (el cupo NO quedó bloqueado dos veces) y se responde con la reserva que ganó.
            with self.uow_factory() as uow:
                existente = self._respuesta_idempotente(uow, solicitud)
            if existente is None:
                raise
            return existente

        # Paso 4: cobrar por el PagoPort, fuera de cualquier transacción SQL.
        cobro = _cobrar_sin_excepcion(
            self.pago_port,
            reserva_id=reserva.id,
            monto=reserva.total,
            moneda=reserva.moneda,
            metodo=solicitud.metodo_pago,
            datos_pago=solicitud.datos_pago or {},
        )
        if cobro.estado == EstadoPago.APROBADO:
            return self._confirmar(reserva, cobro, solicitud.metodo_pago)
        return self._compensar(reserva)

    # Paso 5: aprobado → confirmada + pago + evento + correo, en UNA transacción.
    def _confirmar(self, reserva: Reserva, cobro: ResultadoCobro, metodo: str) -> ResultadoIniciarReserva:
        ahora = self.reloj()
        with self.uow_factory() as uow:
            reserva.confirmar()
            if not uow.reservas.actualizar_si_estado(reserva, EstadoReserva.PENDIENTE_PAGO):
                # El expirador la venció mientras se cobraba: se devuelve el dinero.
                uow.rollback()
                return self._reembolsar_reserva_vencida(reserva, cobro)
            pago = Pago(
                id=str(uuid.uuid4()),
                reserva_id=reserva.id,
                monto=reserva.total,
                moneda=reserva.moneda,
                metodo=metodo,
                estado=EstadoPago.APROBADO,
                referencia_pasarela=cobro.referencia_pasarela,
                tipo=TipoPago.COBRO,
                creado_en=ahora,
            )
            uow.pagos.guardar(pago)
            notificacion = textos.confirmacion(reserva)
            uow.notificaciones.guardar(notificacion)
            # Evento exacto de contratos/eventos/reservas.reserva.confirmada.schema.json.
            # Sin datos personales del turista (RD-04): ni id, ni correo, ni nombres.
            uow.registrar_evento_outbox(
                tipo=TIPO_RESERVA_CONFIRMADA,
                datos={
                    "reserva_id": reserva.codigo,
                    "oferta_id": reserva.oferta_id,
                    "zona_id": reserva.zona_id,
                    "personas": reserva.personas,
                    "fecha_servicio": reserva.fecha_servicio.isoformat(),
                    "total": float(reserva.total),
                    "moneda": reserva.moneda,
                },
            )
            uow.commit()

        self._enviar_ya(notificacion.id, notificacion)
        return _resultado(
            reserva,
            cobro=pago,
            mensaje_es="¡Reserva confirmada! Te enviamos el comprobante por correo.",
            mensaje_en="Booking confirmed! We sent the receipt to your email.",
        )

    # Paso 6: rechazado o tiempo agotado → expirada + cupo devuelto, sin cobro.
    def _compensar(self, reserva: Reserva) -> ResultadoIniciarReserva:
        ahora = self.reloj()
        with self.uow_factory() as uow:
            reserva.expirar()
            if uow.reservas.actualizar_si_estado(reserva, EstadoReserva.PENDIENTE_PAGO):
                _liberar_cupo(uow, reserva.franja_id, reserva.personas, ahora)
            uow.commit()
        return _resultado(
            reserva,
            cobro=None,
            mensaje_es="Pago no realizado, sin cobro. El cupo fue liberado.",
            mensaje_en="Payment not completed, no charge applied. Capacity has been released.",
        )

    def _reembolsar_reserva_vencida(self, reserva: Reserva, cobro: ResultadoCobro) -> ResultadoIniciarReserva:
        resultado = _reembolsar_sin_excepcion(
            self.pago_port,
            reserva_id=reserva.id,
            referencia_cobro=cobro.referencia_pasarela,
            monto=reserva.total,
            moneda=reserva.moneda,
        )
        if resultado.estado != EstadoPago.APROBADO:
            log.error("Reserva %s vencida con cobro %s sin reembolso automático",
                      reserva.codigo, cobro.referencia_pasarela)
        reserva.estado = EstadoReserva.EXPIRADA
        return _resultado(
            reserva,
            cobro=None,
            mensaje_es="El tiempo para pagar se agotó; el cobro fue reversado.",
            mensaje_en="The payment window expired; the charge was reversed.",
        )

    def _enviar_ya(self, notificacion_id: str, notificacion) -> None:  # type: ignore[no-untyped-def]
        """Envío inmediato best-effort; si falla, el proceso de fondo la reintenta."""
        if self.notificador_port is None:
            return
        try:
            self.notificador_port.enviar_correo(notificacion)
            with self.uow_factory() as uow:
                uow.notificaciones.marcar_enviada(notificacion_id)
                uow.commit()
        except Exception as exc:  # noqa: BLE001
            log.warning("Correo no enviado (se reintentará): %s", exc)

    @staticmethod
    def _respuesta_idempotente(
        uow: UnitOfWork, solicitud: SolicitudIniciarReserva
    ) -> ResultadoIniciarReserva | None:
        existente = uow.reservas.obtener_por_idempotencia(
            solicitud.turista_id, solicitud.clave_idempotencia
        )
        if existente is None:
            return None
        cobro = uow.pagos.obtener_cobro(existente.id)
        if existente.estado == EstadoReserva.CONFIRMADA:
            return _resultado(
                existente,
                cobro=cobro,
                mensaje_es="¡Reserva confirmada! Te enviamos el comprobante por correo.",
                mensaje_en="Booking confirmed! We sent the receipt to your email.",
            )
        return _resultado(
            existente,
            cobro=cobro,
            mensaje_es="Pago no realizado, sin cobro. El cupo fue liberado.",
            mensaje_en="Payment not completed, no charge applied. Capacity has been released.",
        )

    @staticmethod
    def _validar_oferta_lista_espera(
        uow: UnitOfWork,
        solicitud: SolicitudIniciarReserva,
        franja: FranjaDisponibilidad,
        ahora: datetime,
    ) -> None:
        entrada = uow.lista_espera.obtener_por_id(solicitud.entrada_lista_espera_id or "")
        if entrada is None or entrada.turista_id != solicitud.turista_id:
            raise ListaEsperaInvalidaError("No tiene una oferta de cupo con ese identificador.")
        if entrada.franja_id != franja.id or entrada.personas != solicitud.personas:
            raise ListaEsperaInvalidaError(
                f"La oferta de cupo es para la franja {entrada.franja_id} y {entrada.personas} persona(s)."
            )
        if not entrada.oferta_vigente(ahora):
            raise ListaEsperaInvalidaError("La oferta de cupo ya no está vigente.")


# --- CU-08: disponibilidad ----------------------------------------------------------------


class ConsultarDisponibilidadUseCase:
    """CU-08 / RF-RES-01: franjas con cupo para la fecha y número de personas indicados."""

    def __init__(self, uow_factory: FabricaUnidad, reloj: Reloj = _ahora_utc):
        self.uow_factory = uow_factory
        self.reloj = reloj

    def ejecutar(
        self, oferta_id: str, fecha: date | None = None, personas: int = 1
    ) -> list[FranjaDisponibilidad]:
        ahora = self.reloj()
        with self.uow_factory() as uow:
            franjas = uow.franjas.buscar_disponibles(
                oferta_id=oferta_id, desde=fecha, hasta=fecha, personas=personas
            )
        return [f for f in franjas if f.inicio > ahora]


class SugerirFechasCercanasUseCase:
    """RF-RES-02: si la fecha pedida está agotada, sugiere las franjas con cupo más cercanas."""

    def __init__(self, uow_factory: FabricaUnidad, reloj: Reloj = _ahora_utc):
        self.uow_factory = uow_factory
        self.reloj = reloj

    def ejecutar(
        self, oferta_id: str, fecha: date, personas: int = 1, dias: int = 7, limite: int = 10
    ) -> list[FranjaDisponibilidad]:
        ahora = self.reloj()
        with self.uow_factory() as uow:
            franjas = uow.franjas.buscar_disponibles(
                oferta_id=oferta_id,
                desde=fecha - timedelta(days=dias),
                hasta=fecha + timedelta(days=dias),
                personas=personas,
            )
        futuras = [f for f in franjas if f.inicio > ahora and f.fecha != fecha]
        futuras.sort(key=lambda f: (abs((f.fecha - fecha).days), f.fecha, f.hora_inicio))
        return futuras[:limite]


# --- CU-18 / W5 / W6 / W7: consultas ------------------------------------------------------


class ConsultarComprobanteUseCase:
    """CU-18 / W5: comprobante; solo el turista dueño, el prestador de la oferta o un admin."""

    def __init__(self, uow_factory: FabricaUnidad):
        self.uow_factory = uow_factory

    def ejecutar(self, reserva_id: str, actor_id: str, actor_rol: str) -> ResultadoIniciarReserva:
        with self.uow_factory() as uow:
            reserva = uow.reservas.obtener_por_id(reserva_id)
            if reserva is None:
                raise RecursoNoEncontradoError(f"Reserva '{reserva_id}' no encontrada.")
            es_dueno = actor_rol == "turista" and reserva.turista_id == actor_id
            es_prestador = actor_rol == "prestador" and reserva.prestador_id == actor_id
            es_admin = actor_rol == "administrador"
            if not (es_dueno or es_prestador or es_admin):
                raise AccesoDenegadoDominioError(
                    "No tiene permiso para consultar el comprobante de esta reserva."
                )
            cobro = uow.pagos.obtener_cobro(reserva.id)
        return _resultado(reserva, cobro=cobro, mensaje_es="Comprobante de reserva",
                          mensaje_en="Booking receipt")


def _filtrar(reservas: list[Reserva], filtro: FiltroReservas | None) -> list[Reserva]:
    if filtro is None:
        return reservas
    return [
        r
        for r in reservas
        if (filtro.estado is None or r.estado.value == filtro.estado)
        and (filtro.desde is None or r.fecha_servicio >= filtro.desde)
        and (filtro.hasta is None or r.fecha_servicio <= filtro.hasta)
        and (filtro.prestador_id is None or r.prestador_id == filtro.prestador_id)
    ]


class ListarReservasTuristaUseCase:
    """W6 / CU-15 / RF-RES-15: historial del turista, filtrable por estado, fechas y prestador."""

    def __init__(self, uow_factory: FabricaUnidad):
        self.uow_factory = uow_factory

    def ejecutar(self, turista_id: str, filtro: FiltroReservas | None = None) -> list[ResultadoIniciarReserva]:
        with self.uow_factory() as uow:
            reservas = _filtrar(uow.reservas.listar_por_turista(turista_id), filtro)
            cobros = {r.id: uow.pagos.obtener_cobro(r.id) for r in reservas}
        return [
            _resultado(r, cobro=cobros[r.id], mensaje_es="Reserva registrada",
                       mensaje_en="Registered booking")
            for r in reservas
        ]


class ListarReservasPrestadorUseCase:
    """W7 + RC-N03: reservas de las ofertas del prestador; 403 si pide las de otro."""

    def __init__(self, uow_factory: FabricaUnidad):
        self.uow_factory = uow_factory

    def ejecutar(
        self,
        prestador_autenticado_id: str,
        prestador_solicitado_id: str | None = None,
        filtro: FiltroReservas | None = None,
    ) -> list[ResultadoIniciarReserva]:
        objetivo = prestador_solicitado_id or prestador_autenticado_id
        if objetivo != prestador_autenticado_id:
            raise AccesoDenegadoDominioError(
                "RC-N03: Un prestador no puede consultar las reservas de otro prestador."
            )
        with self.uow_factory() as uow:
            reservas = _filtrar(uow.reservas.listar_por_prestador(prestador_autenticado_id), filtro)
            cobros = {r.id: uow.pagos.obtener_cobro(r.id) for r in reservas}
        return [
            _resultado(r, cobro=cobros[r.id], mensaje_es="Reserva de oferta del prestador",
                       mensaje_en="Provider offer booking")
            for r in reservas
        ]


# --- Franjas del prestador ----------------------------------------------------------------


class CrearFranjaPrestadorUseCase:
    """El prestador publica franjas de disponibilidad SOLO para sus propias ofertas.

    La propiedad se comprueba con la proyección local que alimentan los eventos
    catalogo.oferta.* (Reservas nunca lee la base de Catálogo).
    """

    def __init__(self, uow_factory: FabricaUnidad, reloj: Reloj = _ahora_utc):
        self.uow_factory = uow_factory
        self.reloj = reloj

    def ejecutar(self, solicitud: SolicitudCrearFranja) -> FranjaDisponibilidad:
        with self.uow_factory() as uow:
            proyeccion = uow.proyecciones.obtener(solicitud.oferta_id)
            if proyeccion is None:
                raise OfertaNoDisponibleError(
                    f"La oferta '{solicitud.oferta_id}' no está publicada en Catálogo (o aún no "
                    "llegó su evento)."
                )
            if proyeccion.prestador_id != solicitud.prestador_id:
                raise AccesoDenegadoDominioError(
                    "La oferta pertenece a otro prestador; no puede crear franjas sobre ella."
                )
            if not proyeccion.activa:
                raise OfertaNoDisponibleError("La oferta está retirada en Catálogo.")
            franja = FranjaDisponibilidad(
                id=str(uuid.uuid4()),
                oferta_id=solicitud.oferta_id,
                zona_id=proyeccion.zona_id,
                prestador_id=solicitud.prestador_id,
                fecha=solicitud.fecha,
                hora_inicio=solicitud.hora_inicio,
                cupo_total=solicitud.cupo_total,
                cupo_disponible=solicitud.cupo_total,
            )
            if franja.inicio <= self.reloj():
                raise OfertaNoDisponibleError("No se pueden crear franjas en el pasado.")
            guardada = uow.franjas.guardar(franja)
            uow.commit()
            return guardada


# --- CU-14: cancelar -----------------------------------------------------------------------


class CancelarReservaUseCase:
    """CU-14 / RF-RES-13 / RF-RES-14.

    1) Aplica la política copiada (100 %, parcial o 0 % según la anticipación).
    2) En UNA transacción: reserva cancelada + cupo liberado (y ofrecido a la lista de espera).
       El cambio de estado es condicional: dos cancelaciones simultáneas no reembolsan dos veces.
    3) Reembolso por el PagoPort (CU-16). Si falla: 'cancelacion_pendiente' + evento para el
       administrador (CU-27), y el turista recibe aviso.
    """

    def __init__(
        self,
        uow_factory: FabricaUnidad,
        pago_port: PagoPort,
        reloj: Reloj = _ahora_utc,
    ):
        self.uow_factory = uow_factory
        self.pago_port = pago_port
        self.reloj = reloj

    def ejecutar(self, reserva_id: str, turista_id: str) -> ResultadoIniciarReserva:
        ahora = self.reloj()
        with self.uow_factory() as uow:
            reserva = uow.reservas.obtener_por_id(reserva_id)
            if reserva is None:
                raise RecursoNoEncontradoError(f"Reserva '{reserva_id}' no encontrada.")
            if reserva.turista_id != turista_id:
                raise AccesoDenegadoDominioError("Solo el turista titular puede cancelar su reserva.")
            estado_anterior = reserva.estado
            porcentaje, monto = reserva.calcular_reembolso(ahora)
            reserva.cancelar(ahora, monto)
            if not uow.reservas.actualizar_si_estado(reserva, estado_anterior):
                raise ReservaNoCancelableError("La reserva cambió de estado; vuelva a consultarla.")
            _liberar_cupo(uow, reserva.franja_id, reserva.personas, ahora)
            cobro = uow.pagos.obtener_cobro(reserva.id)
            if monto <= 0:
                uow.notificaciones.guardar(textos.cancelacion(reserva, porcentaje, False))
            uow.commit()

        if monto <= 0:
            return _resultado(
                reserva,
                cobro=cobro,
                mensaje_es="Reserva cancelada y cupo liberado."
                + (" Fuera del plazo de reembolso: no aplica reembolso." if cobro else ""),
                mensaje_en="Booking cancelled and capacity released."
                + (" Outside the refund window: no refund applies." if cobro else ""),
            )

        assert cobro is not None
        resultado = _reembolsar_sin_excepcion(
            self.pago_port,
            reserva_id=reserva.id,
            referencia_cobro=cobro.referencia_pasarela,
            monto=monto,
            moneda=reserva.moneda,
        )
        with self.uow_factory() as uow:
            if resultado.estado == EstadoPago.APROBADO:
                uow.pagos.guardar(
                    Pago(
                        id=str(uuid.uuid4()),
                        reserva_id=reserva.id,
                        monto=monto,
                        moneda=reserva.moneda,
                        metodo=cobro.metodo,
                        estado=EstadoPago.APROBADO,
                        referencia_pasarela=resultado.referencia_pasarela,
                        tipo=TipoPago.REEMBOLSO,
                    )
                )
                uow.notificaciones.guardar(textos.cancelacion(reserva, porcentaje, False))
                uow.commit()
                return _resultado(
                    reserva,
                    cobro=cobro,
                    mensaje_es=f"Reserva cancelada. Reembolso del {porcentaje} % aprobado.",
                    mensaje_en=f"Booking cancelled. {porcentaje}% refund approved.",
                )
            reserva.marcar_cancelacion_pendiente()
            uow.reservas.actualizar_si_estado(reserva, EstadoReserva.CANCELADA)
            uow.registrar_evento_outbox(
                tipo=TIPO_CANCELACION_PENDIENTE,
                datos={
                    "reserva_id": reserva.codigo,
                    "monto_reembolso": float(monto),
                    "moneda": reserva.moneda,
                    "motivo": resultado.detalle[:200],
                },
            )
            uow.notificaciones.guardar(textos.cancelacion(reserva, porcentaje, True))
            uow.commit()
        return _resultado(
            reserva,
            cobro=cobro,
            mensaje_es="Reserva cancelada; el reembolso quedó pendiente y lo gestiona un administrador.",
            mensaje_en="Booking cancelled; the refund is pending and will be handled by an administrator.",
        )


# --- Tareas periódicas ---------------------------------------------------------------------


class ExpirarBloqueosVencidosUseCase:
    """CU-11 paso 8: vence reservas pendiente_pago con más de 10 min y devuelve su cupo."""

    def __init__(self, uow_factory: FabricaUnidad, reloj: Reloj = _ahora_utc):
        self.uow_factory = uow_factory
        self.reloj = reloj

    def ejecutar(self, ahora: datetime | None = None) -> int:
        corte = ahora or self.reloj()
        expiradas = 0
        with self.uow_factory() as uow:
            for reserva in uow.reservas.listar_pendientes_vencidas(corte):
                reserva.expirar()
                if uow.reservas.actualizar_si_estado(reserva, EstadoReserva.PENDIENTE_PAGO):
                    _liberar_cupo(uow, reserva.franja_id, reserva.personas, corte)
                    expiradas += 1
            uow.commit()
        return expiradas


class ExpirarOfertasListaEsperaUseCase:
    """CU-13 3a: quien no confirmó a tiempo pierde la oferta y el cupo pasa al siguiente."""

    def __init__(self, uow_factory: FabricaUnidad, reloj: Reloj = _ahora_utc):
        self.uow_factory = uow_factory
        self.reloj = reloj

    def ejecutar(self, ahora: datetime | None = None) -> int:
        corte = ahora or self.reloj()
        with self.uow_factory() as uow:
            vencidas = uow.lista_espera.listar_ofertas_vencidas(corte)
            expiradas = 0
            for entrada in vencidas:
                entrada.expirar()
                if uow.lista_espera.actualizar_si_estado(entrada, EstadoListaEspera.OFRECIDA):
                    _liberar_cupo(uow, entrada.franja_id, entrada.personas, corte)
                    expiradas += 1
            uow.commit()
        return expiradas


class EnviarNotificacionesPendientesUseCase:
    """CU-18: envía los correos que no salieron (SMTP caído) con un máximo de intentos."""

    def __init__(
        self,
        uow_factory: FabricaUnidad,
        notificador_port: NotificadorPort,
        limite: int = 20,
        max_intentos: int = 5,
    ):
        self.uow_factory = uow_factory
        self.notificador_port = notificador_port
        self.limite = limite
        self.max_intentos = max_intentos

    def ejecutar(self) -> int:
        with self.uow_factory() as uow:
            pendientes = uow.notificaciones.listar_pendientes(self.limite, self.max_intentos)
        enviadas = 0
        for notificacion in pendientes:
            try:
                self.notificador_port.enviar_correo(notificacion)
                exito = True
            except Exception as exc:  # noqa: BLE001
                log.warning("Correo %s no enviado: %s", notificacion.id, exc)
                exito = False
            with self.uow_factory() as uow:
                if exito:
                    uow.notificaciones.marcar_enviada(notificacion.id)
                    enviadas += 1
                else:
                    uow.notificaciones.registrar_intento_fallido(notificacion.id)
                uow.commit()
        return enviadas


# --- CU-13: lista de espera -----------------------------------------------------------------


def _resultado_lista(uow: UnitOfWork, entrada: EntradaListaEspera, es: str, en: str) -> ResultadoListaEspera:
    posicion = uow.lista_espera.posicion(entrada) if entrada.estado == EstadoListaEspera.ESPERANDO else None
    return ResultadoListaEspera(
        entrada_id=entrada.id,
        franja_id=entrada.franja_id,
        personas=entrada.personas,
        estado=entrada.estado.value,
        posicion=posicion,
        oferta_expira_en=entrada.oferta_expira_en,
        mensaje_es=es,
        mensaje_en=en,
    )


class UnirseListaEsperaUseCase:
    """CU-13 / RF-RES-11: registro por orden de llegada en una franja sin cupo suficiente."""

    def __init__(self, uow_factory: FabricaUnidad, reloj: Reloj = _ahora_utc):
        self.uow_factory = uow_factory
        self.reloj = reloj

    def ejecutar(
        self, *, franja_id: str, turista_id: str, correo_turista: str, idioma: str, personas: int
    ) -> ResultadoListaEspera:
        with self.uow_factory() as uow:
            franja = uow.franjas.obtener_por_id(franja_id)
            if franja is None:
                raise RecursoNoEncontradoError(f"Franja '{franja_id}' no encontrada.")
            if franja.inicio <= self.reloj():
                raise ListaEsperaInvalidaError("La franja ya comenzó o pasó.")
            if personas > franja.cupo_total:
                raise ListaEsperaInvalidaError(
                    f"La franja admite como máximo {franja.cupo_total} personas."
                )
            if franja.cupo_disponible >= personas:
                raise ListaEsperaInvalidaError("Aún hay cupo en esta franja: puede reservar directamente.")
            if uow.lista_espera.existe_activa(franja_id, turista_id):
                raise ListaEsperaInvalidaError("Ya está en la lista de espera de esta franja.")
            entrada = EntradaListaEspera(
                id=str(uuid.uuid4()),
                franja_id=franja_id,
                turista_id=turista_id,
                correo_turista=correo_turista,
                idioma=idioma if idioma in ("es", "en") else "es",
                personas=personas,
                creado_en=self.reloj(),
            )
            uow.lista_espera.guardar(entrada)
            resultado = _resultado_lista(
                uow, entrada,
                "Quedaste en la lista de espera. Te avisaremos por correo si se libera cupo.",
                "You are on the waitlist. We will email you if a spot opens up.",
            )
            uow.commit()
            return resultado


class RetirarseListaEsperaUseCase:
    """CU-13 3a: el turista declina; si tenía cupo ofrecido, pasa al siguiente de la lista."""

    def __init__(self, uow_factory: FabricaUnidad, reloj: Reloj = _ahora_utc):
        self.uow_factory = uow_factory
        self.reloj = reloj

    def ejecutar(self, entrada_id: str, turista_id: str) -> ResultadoListaEspera:
        ahora = self.reloj()
        with self.uow_factory() as uow:
            entrada = uow.lista_espera.obtener_por_id(entrada_id)
            if entrada is None:
                raise RecursoNoEncontradoError(f"Entrada '{entrada_id}' no encontrada.")
            if entrada.turista_id != turista_id:
                raise AccesoDenegadoDominioError("Esta entrada de lista de espera es de otro turista.")
            estado_anterior = entrada.estado
            entrada.retirar()
            if not uow.lista_espera.actualizar_si_estado(entrada, estado_anterior):
                raise ListaEsperaInvalidaError("La entrada cambió de estado; vuelva a consultarla.")
            if estado_anterior == EstadoListaEspera.OFRECIDA:
                _liberar_cupo(uow, entrada.franja_id, entrada.personas, ahora)
            resultado = _resultado_lista(uow, entrada, "Saliste de la lista de espera.",
                                         "You left the waitlist.")
            uow.commit()
            return resultado


class ListarMiListaEsperaUseCase:
    def __init__(self, uow_factory: FabricaUnidad):
        self.uow_factory = uow_factory

    def ejecutar(self, turista_id: str) -> list[ResultadoListaEspera]:
        with self.uow_factory() as uow:
            return [
                _resultado_lista(uow, e, "", "") for e in uow.lista_espera.listar_por_turista(turista_id)
            ]


# --- CU-17: disputas de pago ------------------------------------------------------------------


def _resultado_disputa(d: Disputa) -> ResultadoDisputa:
    return ResultadoDisputa(
        disputa_id=d.id,
        reserva_id=d.reserva_id,
        estado=d.estado.value,
        motivo=d.motivo,
        justificacion=d.justificacion,
        monto_reembolso=d.monto_reembolso,
        creado_en=d.creado_en,
        resuelta_en=d.resuelta_en,
    )


class AbrirDisputaUseCase:
    """CU-17: el turista reporta un cobro incorrecto; queda 'en_revision' para el administrador."""

    def __init__(self, uow_factory: FabricaUnidad):
        self.uow_factory = uow_factory

    def ejecutar(self, *, reserva_id: str, turista_id: str, motivo: str) -> ResultadoDisputa:
        with self.uow_factory() as uow:
            reserva = uow.reservas.obtener_por_id(reserva_id)
            if reserva is None:
                raise RecursoNoEncontradoError(f"Reserva '{reserva_id}' no encontrada.")
            if reserva.turista_id != turista_id:
                raise AccesoDenegadoDominioError("Solo el titular puede disputar el cobro de su reserva.")
            cobro = uow.pagos.obtener_cobro(reserva.id)
            if cobro is None:
                raise DisputaInvalidaError("Esta reserva no tiene un cobro que disputar.")
            if uow.disputas.existe_en_revision(reserva.id):
                raise DisputaInvalidaError("Ya hay una disputa en revisión para esta reserva.")
            disputa = Disputa.abrir(
                reserva_id=reserva.id, pago_id=cobro.id, turista_id=turista_id, motivo=motivo
            )
            uow.disputas.guardar(disputa)
            # Aviso al administrador (sin datos personales; el detalle se consulta en Reservas).
            uow.registrar_evento_outbox(
                tipo=TIPO_DISPUTA_ABIERTA,
                datos={
                    "disputa_id": disputa.id,
                    "reserva_id": reserva.codigo,
                    "monto": float(cobro.monto),
                    "moneda": cobro.moneda,
                },
            )
            uow.commit()
            return _resultado_disputa(disputa)


class ListarDisputasUseCase:
    def __init__(self, uow_factory: FabricaUnidad):
        self.uow_factory = uow_factory

    def ejecutar(self, estado: str | None = None) -> list[ResultadoDisputa]:
        with self.uow_factory() as uow:
            filtro = EstadoDisputa(estado) if estado else None
            return [_resultado_disputa(d) for d in uow.disputas.listar(filtro)]


class ResolverDisputaUseCase:
    """CU-17 pasos 3-4: el administrador aprueba (con reembolso) o rechaza, con justificación.

    Si la pasarela rechaza el reembolso, la disputa sigue en revisión (4a: gestión manual).
    """

    def __init__(self, uow_factory: FabricaUnidad, pago_port: PagoPort):
        self.uow_factory = uow_factory
        self.pago_port = pago_port

    def ejecutar(
        self,
        *,
        disputa_id: str,
        administrador_id: str,
        aprobada: bool,
        justificacion: str,
        monto_reembolso: Decimal | None = None,
    ) -> ResultadoDisputa:
        with self.uow_factory() as uow:
            disputa = uow.disputas.obtener_por_id(disputa_id)
            if disputa is None:
                raise RecursoNoEncontradoError(f"Disputa '{disputa_id}' no encontrada.")
            reserva = uow.reservas.obtener_por_id(disputa.reserva_id)
            cobro = uow.pagos.obtener_cobro(disputa.reserva_id)
            reembolsado = sum(
                (p.monto for p in uow.pagos.listar_por_reserva(disputa.reserva_id)
                 if p.tipo == TipoPago.REEMBOLSO and p.estado == EstadoPago.APROBADO),
                Decimal("0"),
            )
        assert reserva is not None and cobro is not None

        monto: Decimal | None = None
        if aprobada:
            maximo = cobro.monto - reembolsado
            monto = redondear_pesos(monto_reembolso if monto_reembolso is not None else maximo)
            if not (Decimal("0") < monto <= maximo):
                raise DisputaInvalidaError(
                    f"El reembolso debe ser mayor que 0 y no superar {maximo} {cobro.moneda} "
                    "(lo cobrado menos lo ya reembolsado)."
                )
        # Valida la justificación ANTES de mover dinero (lanza si no cumple).
        disputa.resolver(
            aprobada=aprobada,
            justificacion=justificacion,
            administrador_id=administrador_id,
            monto_reembolso=monto,
        )

        # Primero se "reclama" la disputa con un UPDATE condicional: si dos administradores la
        # resuelven a la vez, solo uno pasa y el reembolso no se hace dos veces.
        with self.uow_factory() as uow:
            if not uow.disputas.resolver_si_en_revision(disputa):
                raise DisputaInvalidaError("Otro administrador resolvió esta disputa al mismo tiempo.")
            uow.commit()

        referencia = None
        if aprobada and monto is not None:
            resultado = _reembolsar_sin_excepcion(
                self.pago_port,
                reserva_id=reserva.id,
                referencia_cobro=cobro.referencia_pasarela,
                monto=monto,
                moneda=cobro.moneda,
            )
            if resultado.estado != EstadoPago.APROBADO:
                with self.uow_factory() as uow:
                    uow.disputas.revertir_a_revision(disputa.id)
                    uow.commit()
                raise ReembolsoFallidoError(
                    "La pasarela rechazó el reembolso; la disputa sigue en revisión para "
                    "gestionarla manualmente con el proveedor."
                )
            referencia = resultado.referencia_pasarela

        with self.uow_factory() as uow:
            if referencia is not None and monto is not None:
                uow.pagos.guardar(
                    Pago(
                        id=str(uuid.uuid4()),
                        reserva_id=reserva.id,
                        monto=monto,
                        moneda=cobro.moneda,
                        metodo=cobro.metodo,
                        estado=EstadoPago.APROBADO,
                        referencia_pasarela=referencia,
                        tipo=TipoPago.REEMBOLSO,
                    )
                )
            uow.notificaciones.guardar(textos.disputa_resuelta(disputa, reserva))
            uow.commit()
        return _resultado_disputa(disputa)
