"""Configuración de proceso leída del entorno."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Configuracion:
    database_url: str = os.getenv(
        "ANALITICA_DATABASE_URL", "postgresql+psycopg://analitica:analitica_local@localhost:55434/analitica_db"
    )
    rabbitmq_url: str = os.getenv("ANALITICA_RABBITMQ_URL", "")
    exchange: str = os.getenv("ANALITICA_RABBITMQ_EXCHANGE", "turismo")
    queue: str = os.getenv("ANALITICA_RABBITMQ_QUEUE", "analitica.eventos")
    issuer: str = os.getenv("JWT_ISSUER", "http://localhost:8001")  # mismo valor por defecto que Auth
    audience: str = os.getenv("JWT_AUDIENCE", "santa-marta-platform")
    jwks_url: str = os.getenv("JWT_JWKS_URL", "")
    public_key_file: str = os.getenv("JWT_PUBLIC_KEY_FILE", "")
    alert_ratio: float = float(os.getenv("ANALITICA_ALERT_RATIO", "0.90"))
    outbox_interval: float = float(os.getenv("ANALITICA_OUTBOX_INTERVAL_SECONDS", "1"))
    # Cada cuánto se recalcula y publica la ocupación de todas las zonas con umbral, para que
    # IA no se quede con la del día anterior aunque no lleguen reservas.
    recalculo_segundos: float = float(os.getenv("ANALITICA_RECALCULO_SEGUNDOS", "300"))


config = Configuracion()
