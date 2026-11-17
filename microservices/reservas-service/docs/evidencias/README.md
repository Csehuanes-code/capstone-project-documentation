# Evidencias de validación de Reservas

Ejecución dentro de Docker, con el código del monorepo montado en `/repo`. Resultados de
integración comprobados el 17 de noviembre de 2026 (UTC).

| Requisito/escenario | Evidencia ejecutada | Resultado |
|---|---|---|
| EC-DISP-01 / RF-RES-07: concurrencia de reserva | `tests/test_postgres.py::test_postgres_ultimo_cupo_acepta_exactamente_una_reserva`, 12 solicitudes concurrentes contra el último cupo de PostgreSQL 16. | **Aprobado para la sobreventa:** 1 reserva, 1 cobro, cupo restante 0. La prueba hermana de idempotencia paralela también terminó aprobada. |
| EC-DISP-01: disponibilidad y detección de réplica | `GET /health/ready` durante el flujo de Compose respondió `{"estado":"listo","servicio":"reservas","dependencias":{"postgresql":"ok","rabbitmq":"ok"}}`. | **Parcial, no certifica el escenario completo.** No se ejecutó una prueba de duración mensual para medir ≥99% ni una caída de réplica detrás de balanceador para demostrar detección <30 s. El Compose local levanta una sola API. |
| RC-N03 / RNF-SEG-04: aislamiento entre prestadores | `tests/test_api.py::test_prestador_no_consulta_reservas_ajenas_ni_crea_franja_ajena`. Un prestador pidió las reservas de otro y trató de publicar horario en una oferta ajena. | **Aprobado:** ambas respuestas fueron HTTP 403. |
| Reembolsos, lista de espera y disputas | `tests/test_api.py` y `tests/test_contratos.py` recorren reembolso total/parcial/cero, fallo de reembolso, turno estricto, vencimiento, retiro y disputa. | **Aprobado** en SQLite con reloj controlado; los eventos persistidos validan los esquemas JSON compartidos. |
| PostgreSQL concurrente | `pytest -q tests/test_migraciones.py tests/test_postgres.py` con `RESERVAS_TEST_DATABASE_URL` configurada. | **4 pruebas aprobadas:** migración/modelos y dos escenarios de concurrencia (incluida la misma clave idempotente en paralelo). |
| RabbitMQ real | `pytest -q tests/test_rabbitmq.py` con `RESERVAS_TEST_RABBITMQ_URL` configurada. | **Aprobado:** publicó un evento del outbox, recibió eventos `catalogo.oferta.*` una sola vez y envió el JSON inválido a la cola `.errores`. |
| Flujo punta a punta con Compose | Se levantaron API, PostgreSQL, RabbitMQ y Mailpit; se consultó disponibilidad, se reservó con JWT ES256 firmado y se revisaron las integraciones reales. | **Aprobado:** HTTP 201, comprobante `SMT-O6L34S`, Mailpit informó `total: 1` y RabbitMQ recibió `reservas.reserva.confirmada`. El despliegue temporal se apagó al acabar la prueba. |

Comandos de integración:

```powershell
docker exec -e RESERVAS_TEST_DATABASE_URL=postgresql+psycopg://reservas:reservas@res-pg:5432/reservas_test `
  -e RESERVAS_TEST_RABBITMQ_URL=amqp://guest:guest@res-mq:5672/%2F res-dev pytest -q -rs
docker exec res-dev sh -c 'cd /repo/comun && pytest -q'
```

La disponibilidad mensual y el comportamiento de alta disponibilidad con varias réplicas
siguen siendo una prueba de despliegue/carga pendiente; no se infieren de la prueba de
concurrencia de cupos ni del healthcheck de una sola instancia.
