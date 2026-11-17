"""Plantilla común (Grupo 4 — Turismo Santa Marta).

Provee:
- Validación JWT ES256 y control de roles (ADR-06)
- Middleware X-Correlation-Id
- Logs estructurados en JSON
- Patrón Outbox transaccional + trabajador de reenvío a RabbitMQ (ADR-04)
- Consumidor idempotente de eventos con tabla evento_procesado
- Sobre estándar de eventos (sobre-evento.schema.json)
- Endpoints estándar de Healthcheck (/health y /health/ready)
"""

__version__ = "0.1.0"
