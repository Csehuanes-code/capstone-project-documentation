# Microservicio Reservas

Servicio de disponibilidad, reservas individuales y grupales, pago de prueba, cancelaciones,
reembolsos, lista de espera y disputas para la Plataforma Digital de Turismo de Santa Marta.
La lógica está organizada en capas: `dominio` contiene las reglas, `aplicacion` orquesta los
casos de uso, `api` expone HTTP, `infraestructura` conecta SQL/HTTP/SMTP/RabbitMQ y `main.py`
ensambla los adaptadores.

## Ejecutar con Docker Compose

Desde la raíz del monorepo:

```powershell
docker compose -f microservices/reservas-service/docker-compose.yml up --build
```

La API escucha en `http://localhost:8003`, Swagger en `/docs`, Mailpit en
`http://localhost:8025` y RabbitMQ Management en `http://localhost:15672` (usuario/clave
locales `guest`/`guest`). Compose aplica `alembic upgrade head` antes de iniciar la API y carga
franjas de demostración futuras. Para apagarlo:

```powershell
docker compose -f microservices/reservas-service/docker-compose.yml down
```

Los puertos publicados por defecto son 8003 (API), 5434 (PostgreSQL), 5672/15672 (RabbitMQ) y
1025/8025 (Mailpit). Si ya están ocupados, se pueden sustituir con
`RESERVAS_API_HOST_PORT`, `RESERVAS_POSTGRES_HOST_PORT`, `RESERVAS_RABBITMQ_HOST_PORT`,
`RESERVAS_RABBITMQ_UI_HOST_PORT`, `RESERVAS_SMTP_HOST_PORT` y
`RESERVAS_MAILPIT_UI_HOST_PORT`. Los puertos internos entre contenedores no cambian.

## Probar

Las dependencias se instalan dentro de Docker para evitar compilar SQLAlchemy en Windows:

```powershell
docker exec res-dev sh -c 'pip install -e /repo/comun -e ".[dev]"'
docker exec res-dev pytest -q -rs
docker exec res-dev lint-imports --config .importlinter
docker exec res-dev sh -c 'cd /repo/comun && pytest -q'
```

Con PostgreSQL y RabbitMQ de prueba levantados y conectados a `res-net`, se habilitan también
las pruebas de integración:

```powershell
docker exec -e RESERVAS_TEST_DATABASE_URL=postgresql+psycopg://reservas:reservas@res-pg:5432/reservas_test `
  -e RESERVAS_TEST_RABBITMQ_URL=amqp://guest:guest@res-mq:5672/%2F res-dev pytest -q -rs
```

Los contratos se guardan una sola vez en [`contratos/`](../../contratos/). Para volver a generar
el OpenAPI después de cambiar una ruta:

```powershell
docker exec res-dev python /repo/microservices/reservas-service/scripts/exportar_openapi.py
```

## Configuración

| Variable | Uso |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL; Compose usa PostgreSQL `postgres:5432`. SQLite se usa en pruebas. |
| `RABBITMQ_URL` | URL AMQP. Vacía desactiva publicación/consumo; Compose conecta a `rabbitmq`. |
| `CATALOGO_URL` | URL base de Catálogo. Vacía habilita las ofertas locales de demostración. |
| `JWT_CLAVE_PUBLICA` | PEM público de Auth para validar JWT ES256. |
| `JWT_CLAVE_PUBLICA_FILE` | Alternativa: ruta a un archivo PEM público. |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Emisor y audiencia esperados por `comun.seguridad`. |
| `SMTP_HOST` / `SMTP_PORT` | Servidor de correo; Compose usa Mailpit en `mailpit:1025`. |
| `RESERVAS_WORKERS` | `0` desactiva tareas periódicas y el consumidor RabbitMQ. |
| `RESERVAS_SEMBRAR_DEMO` | `1` carga ofertas y horarios de demostración al arrancar. |
| `RESERVAS_CREAR_TABLAS` | `1` crea tablas automáticamente; solo para SQLite/pruebas. En PostgreSQL se usa Alembic. |

El token de acceso es ES256. Reservar/cancelar/consultar historial/unirse a la lista y abrir
disputas requieren el rol `turista`; administrar franjas/reservas requiere `prestador`; revisar y
resolver disputas requiere `administrador`. La consulta del comprobante permite al turista
titular, al prestador de esa oferta o a un administrador.

## Endpoints principales

Todos los endpoints funcionales usan el prefijo `/api/v1`.

| Método y ruta | Acceso | Para qué sirve |
|---|---|---|
| `GET /ofertas/{oferta_id}/disponibilidad` | Público | Franjas con cupo por fecha y personas. |
| `GET /ofertas/{oferta_id}/disponibilidad/cercanas` | Público | Fechas cercanas a una fecha agotada. |
| `POST /reservas` | Turista | Reserva/pago; exige `Idempotency-Key`; devuelve comprobante. |
| `GET /reservas/{reserva_id}` | Dueño, prestador dueño o admin | Consultar comprobante. |
| `GET /reservas/mias` | Turista | Historial filtrable por estado, fechas y prestador. |
| `POST /reservas/{reserva_id}/cancelar` | Turista titular | Cancelar y solicitar el reembolso aplicable. |
| `POST /franjas/{franja_id}/lista-espera` | Turista | Unirse solo si no hay cupo suficiente. |
| `GET /lista-espera/mias` / `DELETE /lista-espera/{entrada_id}` | Turista | Consultar o retirarse de la fila/oferta. |
| `POST /reservas/{reserva_id}/disputas` | Turista titular | Abrir disputa de cobro. |
| `GET /admin/disputas` / `POST /admin/disputas/{id}/resolver` | Admin | Revisar disputas y registrar decisión. |
| `GET /prestador/reservas` / `POST /prestador/franjas` | Prestador | Ver reservas propias y publicar franjas de ofertas propias. |

## Tarjetas de prueba (pasarela simulada)

Enviar en `datos_pago.numero_tarjeta`:

| Terminación | Resultado |
|---|---|
| `0002` | Cobro rechazado; se libera el cupo. |
| `9999` | Tiempo agotado; se libera el cupo. |
| `0019` | Cobro aprobado, pero el reembolso falla (sirve para comprobar gestión manual). |
| Otra | Cobro aprobado y reembolso simulado. |

No enviar ni guardar números reales de tarjeta. Esta pasarela es solo para el piloto; una
integración certificada debe implementar los puertos de pago sin cambiar las reglas de negocio.
