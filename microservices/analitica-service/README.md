# Servicio de Analítica y Sostenibilidad

Microservicio inicial para los casos CU-30 y CU-31 (RF-ANA-01 a RF-ANA-05). Usa Python 3.12, FastAPI, PostgreSQL 16, Alembic y RabbitMQ; mantiene dominio y casos de uso independientes de los adaptadores.

## Funcionalidad implementada

- Consume `reservas.reserva.confirmada` en el exchange topic `turismo`; valida el sobre común y el esquema v1 del evento antes de persistir.
- Guarda hechos sin datos personales, aplica idempotencia por `evento_id` y `reserva_id`, y confirma el mensaje RabbitMQ solo después del commit.
- Calcula por zona y período reservas confirmadas, visitantes reservados, ingresos COP, participación/concentración y ocupación estimada frente al umbral.
- Permite al administrador consultar métricas, exportarlas como CSV UTF-8 y configurar umbrales por zona.
- Compara el nuevo umbral con el promedio diario de visitantes reservados de los 30 días anteriores. Si sería menor que ese promedio, primero responde con una advertencia y no guarda; para confirmar, repetir con `confirmar_advertencia: true`.
- Cuando una nueva reserva o un umbral recalculado sitúa la ocupación diaria estimada en 90% o más, persiste una alerta activa y crea en la misma transacción un evento de outbox `analitica.zona.ocupacion_actualizada` para IA. Al bajar de 90%, cierra la alerta.
- El JWT administrativo se valida con ES256, `sub`, `rol`, `iss`, `aud`, `iat`, `exp` y `jti`, usando el JWKS de Auth o un PEM público. La API falla cerrada si no hay clave configurada.

> La ocupación se estima con personas en reservas confirmadas cuya fecha de servicio cae en la ventana del umbral; no representa conteo físico de visitantes. Para ocupación observada hacen falta datos de sensores/check-in, que no están en los contratos actuales. El evento compartido solo publica la zona con su ocupación y marca de medición.

## API

Todas las rutas de datos requieren `Authorization: Bearer <JWT>` con rol `administrador`.

| Método y ruta | Uso |
|---|---|
| `GET /health` | Liveness |
| `GET /health/ready` | Verifica conexión PostgreSQL |
| `GET /api/v1/analitica/indicadores?desde=YYYY-MM-DD&hasta=YYYY-MM-DD&zona_id=minca` | Indicadores agregados |
| `GET /api/v1/analitica/indicadores.csv?...` | Exportación CSV accesible |
| `GET /api/v1/analitica/umbrales` | Umbrales vigentes |
| `PUT /api/v1/analitica/umbrales` | Crear/actualizar umbral |
| `GET /api/v1/analitica/alertas` | Alertas de capacidad activas |

Ejemplo de actualización:

```json
{
  "zona_id": "tayrona",
  "visitantes_maximos": 1200,
  "periodo_dias": 1,
  "confirmar_advertencia": false
}
```

IDs válidos de zona: `minca`, `tayrona`, `centro`, `los-naranjos`, `taganga`, `rodadero`, conforme a `../../contratos/vocabulario.json`.

## Ejecutar localmente

```powershell
Copy-Item .env.example .env
docker compose up --build
```

- API: `http://localhost:8004/docs`
- PostgreSQL: `localhost:55434`
- RabbitMQ management: `http://localhost:15673`
- Queue: `analitica.eventos`; dead-letter queue: `analitica.eventos.errores`.

El compose crea infraestructura aislada para desarrollo. En el despliegue del monorepo, configura `ANALITICA_RABBITMQ_URL` hacia el broker común y alinea `JWT_ISSUER`, `JWT_AUDIENCE` y la URL JWKS con Auth. No compartas claves privadas; Analítica solo usa una clave pública.

## Migraciones y comandos de calidad

Desde esta carpeta:

```powershell
python -m pip install -e ".[dev]"
alembic upgrade head
ruff check src migrations
mypy src
```

Docker aplica Alembic antes de levantar Uvicorn. PostgreSQL es el único motor de producción soportado.

## Límites de integración pendientes

- El contrato compartido define la medición de ocupación y la reserva confirmada, pero no define un evento de alerta/notificación. Las alertas quedan consultables en esta API; el aviso push/correo debe conectarse cuando exista el contrato de Notificaciones.
- El requisito permite umbrales por zona o atractivo; el vocabulario y el evento actual solo identifican zonas. Esta primera entrega soporta umbral por zona. Agregar `atractivo_id` requiere actualizar el contrato de eventos y el vocabulario conjuntamente.
- El contrato no define importación de umbrales de autoridad en un formato. RF-ANA-04 queda pendiente de acordar formato y fuente.
- No hay evento de check-in/salida. “Ocupación” es una estimación basada en reservas confirmadas, explícitamente identificada como tal en el reporte.
- Alerta se crea al procesar una reserva o cambiar un umbral. El tiempo menor de cinco minutos depende de que Reservas publique su outbox y RabbitMQ esté disponible; se requieren pruebas de integración/carga y monitoreo en el despliegue común.
- Esta carpeta es una implementación inicial del equipo; los contratos compartidos conservan estado de propuesta hasta aprobación del grupo.
