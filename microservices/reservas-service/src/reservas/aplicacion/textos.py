"""Textos de los correos al turista en español e inglés (RC-S02).

Cada función arma una Notificacion que se guarda en la tabla `notificacion` en la misma
transacción del cambio; un proceso de fondo la envía y la reintenta si el correo falla (CU-18).
"""

from __future__ import annotations

from decimal import Decimal

from reservas.dominio.entidades import (
    Disputa,
    EntradaListaEspera,
    FranjaDisponibilidad,
    Notificacion,
    Reserva,
)


def _dinero(valor: Decimal, moneda: str) -> str:
    return f"{valor:,.0f} {moneda}".replace(",", ".")


def _fecha_hora(reserva: Reserva) -> str:
    return f"{reserva.fecha_servicio.isoformat()} {reserva.hora_servicio.strftime('%H:%M')}"


def confirmacion(reserva: Reserva) -> Notificacion:
    pol = reserva.politica_cancelacion_copiada
    if reserva.idioma == "en":
        asunto = f"Booking confirmed {reserva.codigo} — {reserva.nombre_oferta}"
        lineas = [
            f"Your booking {reserva.codigo} for '{reserva.nombre_oferta}' is confirmed.",
            f"Date: {_fecha_hora(reserva)}",
            f"Guests: {reserva.personas}",
            f"Total paid: {_dinero(reserva.total, reserva.moneda)}",
            f"Cancellation policy: {pol.descripcion_en}",
        ]
        if reserva.punto_encuentro:
            lineas.insert(3, f"Meeting point: {reserva.punto_encuentro}")
        if reserva.prestador_nombre:
            lineas.insert(3, f"Provider: {reserva.prestador_nombre} {reserva.prestador_contacto}".strip())
    else:
        asunto = f"Reserva confirmada {reserva.codigo} — {reserva.nombre_oferta}"
        lineas = [
            f"Tu reserva {reserva.codigo} para '{reserva.nombre_oferta}' está confirmada.",
            f"Fecha: {_fecha_hora(reserva)}",
            f"Personas: {reserva.personas}",
            f"Total pagado: {_dinero(reserva.total, reserva.moneda)}",
            f"Política de cancelación: {pol.descripcion_es}",
        ]
        if reserva.punto_encuentro:
            lineas.insert(3, f"Punto de encuentro: {reserva.punto_encuentro}")
        if reserva.prestador_nombre:
            lineas.insert(3, f"Prestador: {reserva.prestador_nombre} {reserva.prestador_contacto}".strip())
    return _para(reserva, asunto, lineas)


def cancelacion(reserva: Reserva, porcentaje: int, reembolso_pendiente: bool) -> Notificacion:
    monto = reserva.monto_reembolso or Decimal("0")
    if reserva.idioma == "en":
        asunto = f"Booking cancelled {reserva.codigo}"
        lineas = [f"Your booking {reserva.codigo} for '{reserva.nombre_oferta}' was cancelled."]
        if monto > 0 and reembolso_pendiente:
            lineas.append(
                f"Your refund of {_dinero(monto, reserva.moneda)} is being processed manually; "
                "we will contact you."
            )
        elif monto > 0:
            lineas.append(f"Refund ({porcentaje}%): {_dinero(monto, reserva.moneda)}.")
        elif porcentaje == 0 and reserva.confirmada_en is not None:
            lineas.append("Cancelled outside the refund window: no refund applies.")
    else:
        asunto = f"Reserva cancelada {reserva.codigo}"
        lineas = [f"Tu reserva {reserva.codigo} para '{reserva.nombre_oferta}' fue cancelada."]
        if monto > 0 and reembolso_pendiente:
            lineas.append(
                f"El reembolso de {_dinero(monto, reserva.moneda)} se está gestionando "
                "manualmente; te contactaremos."
            )
        elif monto > 0:
            lineas.append(f"Reembolso ({porcentaje} %): {_dinero(monto, reserva.moneda)}.")
        elif porcentaje == 0 and reserva.confirmada_en is not None:
            lineas.append("Cancelación fuera del plazo de reembolso: no aplica reembolso.")
    return _para(reserva, asunto, lineas)


def oferta_lista_espera(entrada: EntradaListaEspera, franja: FranjaDisponibilidad) -> Notificacion:
    vence = entrada.oferta_expira_en.strftime("%Y-%m-%d %H:%M UTC") if entrada.oferta_expira_en else ""
    fecha = f"{franja.fecha.isoformat()} {franja.hora_inicio.strftime('%H:%M')}"
    if entrada.idioma == "en":
        asunto = "A spot opened up for you"
        cuerpo = (
            f"A spot for {entrada.personas} person(s) opened up on {fecha}. It is held for you "
            f"until {vence}. Confirm your booking before then (waitlist entry {entrada.id})."
        )
    else:
        asunto = "Se liberó un cupo para ti"
        cuerpo = (
            f"Se liberó cupo para {entrada.personas} persona(s) el {fecha}. Lo guardamos para ti "
            f"hasta {vence}. Confirma tu reserva antes de esa hora (lista de espera {entrada.id})."
        )
    return Notificacion.nueva(
        destinatario_id=entrada.turista_id,
        correo_destino=entrada.correo_turista,
        idioma=entrada.idioma,
        asunto=asunto,
        cuerpo_texto=cuerpo,
    )


def disputa_resuelta(disputa: Disputa, reserva: Reserva) -> Notificacion:
    aprobada = disputa.monto_reembolso is not None
    if reserva.idioma == "en":
        asunto = f"Your payment dispute for {reserva.codigo} was resolved"
        lineas = [
            "Result: " + ("approved" if aprobada else "rejected") + ".",
            f"Reason: {disputa.justificacion}",
        ]
        if aprobada:
            lineas.append(f"Refund: {_dinero(disputa.monto_reembolso or Decimal(0), reserva.moneda)}.")
    else:
        asunto = f"Tu disputa de pago de {reserva.codigo} fue resuelta"
        lineas = [
            "Resultado: " + ("aprobada" if aprobada else "rechazada") + ".",
            f"Justificación: {disputa.justificacion}",
        ]
        if aprobada:
            lineas.append(f"Reembolso: {_dinero(disputa.monto_reembolso or Decimal(0), reserva.moneda)}.")
    return _para(reserva, asunto, lineas)


def _para(reserva: Reserva, asunto: str, lineas: list[str]) -> Notificacion:
    return Notificacion.nueva(
        reserva_id=reserva.id,
        destinatario_id=reserva.turista_id,
        correo_destino=reserva.correo_turista,
        idioma=reserva.idioma,
        asunto=asunto,
        cuerpo_texto="\n".join(lineas),
    )


def confirmacion_registro(
    *, destinatario_id: str, correo: str, token: str, idioma: str, url_frontend: str
) -> Notificacion:
    """Correo de confirmación de cuenta que pide Auth (evento auth.notificacion.solicitada).

    Las notificaciones viven en Reservas (ADR-02): Auth solo deja la solicitud en su outbox.
    """
    enlace = f"{url_frontend.rstrip('/')}/confirmar?token={token}"
    if idioma == "en":
        asunto = "Confirm your account — Turismo Santa Marta"
        cuerpo = (
            "Welcome! Confirm your email to activate your account:\n"
            f"{enlace}\n\nThe link expires in 24 hours."
        )
    else:
        asunto = "Confirma tu cuenta — Turismo Santa Marta"
        cuerpo = (
            "¡Bienvenido! Confirma tu correo para activar tu cuenta:\n"
            f"{enlace}\n\nEl enlace vence en 24 horas."
        )
    return Notificacion.nueva(
        destinatario_id=destinatario_id,
        correo_destino=correo,
        idioma=idioma if idioma in ("es", "en") else "es",
        asunto=asunto,
        cuerpo_texto=cuerpo,
    )
