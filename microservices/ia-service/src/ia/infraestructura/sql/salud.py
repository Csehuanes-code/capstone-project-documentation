from __future__ import annotations

from sqlalchemy import Engine, text

from ia.aplicacion.puertos import ComprobacionSalud


class SaludBaseDatos(ComprobacionSalud):
    nombre = "base_de_datos"

    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def disponible(self) -> bool:
        with self._motor.connect() as conexion:
            conexion.execute(text("SELECT 1"))
        return True
