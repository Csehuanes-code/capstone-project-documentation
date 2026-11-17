from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest

from reservas.dominio.entidades import (
    CondicionesOferta,
    EstadoReserva,
    FranjaDisponibilidad,
    PoliticaCancelacionCopia,
    Reserva,
)


def _reserva():
    franja = FranjaDisponibilidad(
        "franja", "oferta", "zona", "prestador",
        datetime(2026, 12, 15).date(), time(10), 3, 3,
    )
    condiciones = CondicionesOferta(
        "oferta", "Experiencia", "zona", True, Decimal("12500"),
        "COP", PoliticaCancelacionCopia(48, 24, 50),
    )
    reserva = Reserva.crear_pendiente(
        clave_idempotencia="clave",
        franja=franja,
        condiciones=condiciones,
        turista_id="turista",
        correo_turista="turista@example.com",
        idioma="es",
        personas=2,
        acompanantes=["Ana"],
    )
    return franja, condiciones, reserva


def test_entidad_crea_reserva_grupal_y_copia_precio_politica():
    _, condiciones, reserva = _reserva()

    otras_condiciones = CondicionesOferta(
        "oferta", "Experiencia", "zona", True, Decimal("999999"),
        "COP", PoliticaCancelacionCopia(1, 0, 0),
    )

    assert reserva.estado is EstadoReserva.PENDIENTE_PAGO
    assert reserva.total == Decimal("25000.00")
    assert reserva.precio_unitario_copiado == Decimal("12500")
    assert reserva.politica_cancelacion_copiada == PoliticaCancelacionCopia(48, 24, 50)
    assert otras_condiciones.tarifa_por_persona != reserva.precio_unitario_copiado
    assert [a.nombre_completo for a in reserva.asistentes] == ["Ana"]


@pytest.mark.parametrize(
    ("horas", "porcentaje", "monto"),
    [(72, 100, "25000.00"), (36, 50, "12500.00"), (12, 0, "0.00")],
)
def test_calcula_reembolso_segun_politica_copiada(horas, porcentaje, monto):
    _, _, reserva = _reserva()
    reserva.confirmar()
    ahora = reserva.inicio_servicio - timedelta(hours=horas)

    assert reserva.calcular_reembolso(ahora) == (porcentaje, Decimal(monto))
