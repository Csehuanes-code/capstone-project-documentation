# Plantilla común (`comun`) — Grupo 4 (Turismo Santa Marta)

Paquete Python compartido por los cinco microservicios (`auth`, `catalogo`, `reservas`, `ia`, `analitica`).
No contiene lógica de negocio y solo debe importarse desde las capas `api/` e `infraestructura/` (nunca desde `dominio/` ni `aplicacion/`).

## Instalación en desarrollo

```bash
pip install -e ../comun
```

## Componentes incluidos

1. **Seguridad JWT ES256 (`comun.seguridad`)**:
   - `ValidadorJWT` lee `JWT_CLAVE_PUBLICA` y verifica firma ES256, `exp`, `iss` y `aud`.
   - `crear_dependencia_identidad` retorna `Identidad(sub, rol)` o lanza `401`.
   - `requiere_rol(dep, "turista")` verifica el rol o lanza `403`.
   - `generar_par_claves_es256()` y `emitir_token_prueba(...)` facilitan las pruebas unitarias e integración.
2. **Trazabilidad (`comun.correlacion`)**:
   - `CorrelationIdMiddleware` lee o genera `X-Correlation-Id` (UUIDv4), lo expone en `obtener_correlation_id()` y lo devuelve en la respuesta.
3. **Observabilidad (`comun.logging_json`)**:
   - `configurar_logging_json("reservas")` y `RequestLoggingMiddleware` emiten logs en JSON con `nivel`, `servicio`, `correlation_id`, `ruta` y `duracion_ms`.
4. **Eventos y Outbox (`comun.eventos`)**:
   - `SobreEvento` valida el formato definido en `contratos/eventos/sobre-evento.schema.json`.
   - `registrar_en_outbox(sesion, tipo, datos)` inserta en la tabla `outbox` en la misma transacción SQL.
   - `ProcesadorOutbox` publica en el exchange topic `turismo` de RabbitMQ usando `tipo` como routing key y reintenta si el broker está caído.
   - `ConsumidorIdempotente` garantiza procesamiento único mediante `evento_procesado`.
5. **Healthcheck (`comun.salud`)**:
   - `crear_router_salud` expone `GET /health` y `GET /health/ready` (devuelve `503` si PostgreSQL o RabbitMQ fallan).
