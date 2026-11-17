# Servicio IA — Recomendación

Microservicio de recomendación personalizada y explicable de la Plataforma de Turismo de Santa Marta (Grupo 4).
Responsable: Julián Tobias. Implementa **CU-21** según **ADR-07**.

## Cómo correrlo

**Opción A: sin Docker** (repositorios en memoria con los tours de prueba)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q                                   # pruebas (incluye import-linter)
.\.venv\Scripts\python.exe -m uvicorn ia.main:app --app-dir src --reload   # servidor
```

**Opción B: con Docker** (servicio + PostgreSQL 16, como en producción)

```powershell
docker compose up --build
```

En ambos casos: http://127.0.0.1:8000/docs

### Variables de entorno

| Variable | Efecto |
|---|---|
| `IA_DATABASE_URL` | Si existe, usa SQLAlchemy. Ej.: `postgresql+psycopg://usuario:clave@host:5432/ia_db`. Si no, memoria. |
| `IA_MIGRAR_AL_INICIAR=1` | (Docker) aplica `alembic upgrade head` antes de arrancar |
| `IA_SEMBRAR_DATOS_PRUEBA=1` | Carga los tours de prueba si no hay ofertas (solo desarrollo) |
| `IA_CREAR_ESQUEMA=1` | Crea tablas sin Alembic; atajo para SQLite local |
| `IA_RABBITMQ_URL` | Si existe (ej. `amqp://guest:guest@rabbitmq:5672/%2F`), escucha eventos en la cola `ia.eventos`. Si no, funciona sin recibir eventos |
| `IA_RABBITMQ_COLA` | Nombre de la cola (por defecto `ia.eventos`; cambiarlo solo en pruebas) |

### Migraciones (Alembic)

```powershell
$env:IA_DATABASE_URL = "postgresql+psycopg://usuario:clave@host:5432/ia_db"
.\.venv\Scripts\alembic.exe upgrade head          # aplicar
.\.venv\Scripts\alembic.exe upgrade head --sql    # solo ver el SQL, sin conectarse
```

La migración `0001` crea las tablas de `ia_db`, inserta los **pesos v1** (configuración real) y, en PostgreSQL,
el trigger que impide modificar o borrar una versión de pesos.

## Endpoints

| Método y ruta | Para qué | Pantalla |
|---|---|---|
| `GET /api/v1/ia/recomendaciones?intereses=naturaleza,cultura&limite=5&idioma=es` | Genera y guarda una recomendación con desglose | W1 "Recomendado para ti", W3 |
| `GET /api/v1/ia/recomendaciones/{id}` | La recomendación ya emitida, con el desglose con que se calculó | W3 "¿Por qué veo esto?" |
| `GET /api/v1/ia/criterios[?version=N]` | Pesos vigentes o de una versión | "Cómo funcionan las recomendaciones" |
| `GET /api/v1/ia/populares?limite=5` | Las más reservadas, sin personalizar | Respaldo |
| `GET /health` | Liveness: el proceso está vivo | — |
| `GET /health/ready` | Readiness: 503 si la base de datos no responde. También informa si RabbitMQ está conectado, sin quitar el servicio de rotación | Balanceador / Docker |

Contratos para el equipo (API, eventos y vocabulario compartido): [contratos/](../../contratos/README.md) (en la raíz del repo, fuente única para los 5 servicios).

## Eventos (RabbitMQ, ADR-04)

IA mantiene copias locales (proyecciones) de lo que publican los demás servicios, para recomendar
sin llamarlos en cada petición. Escucha en la cola `ia.eventos` del exchange topic `turismo`:

| Routing key | Publica | Efecto en `ia_db` |
|---|---|---|
| `catalogo.oferta.*` (publicada, actualizada, retirada) | Catálogo | Crea o reemplaza `proyeccion_oferta` (`retirada` → inactiva) |
| `reservas.reserva.confirmada` | Reservas | +1 a la popularidad de la oferta |
| `analitica.zona.ocupacion_actualizada` | Analítica | Actualiza la ocupación de la zona (ignora mediciones más viejas) |

- `api/consumidor_eventos.py` valida el sobre y los datos contra [contratos/eventos/](../../contratos/eventos) y llama al manejador de `aplicacion/eventos.py`.
- `infraestructura/rabbitmq.py` es el cliente (pika, en un hilo de fondo que se reconecta solo).
- El mensaje se confirma solo después de guardar. Un evento repetido no cambia nada (`evento_procesado`).
- Mensaje que no cumple el contrato → `ia.eventos.errores` (se ve en el panel, http://localhost:15672).
- Fallo temporal (ej. la base no responde) → se reintenta.
- Si RabbitMQ se cae, las recomendaciones siguen funcionando con lo que ya está en `ia_db`.

## Algoritmo (ADR-07)

`puntaje = 0,45·afinidad + 0,25·calidad + 0,20·descongestión + 0,10·sostenibilidad` (pesos versión 1)

| Criterio | Cálculo |
|---|---|
| Afinidad | Solapamiento \|intereses ∩ categorías\| / min(\|intereses\|, \|categorías\|). Sin intereses → 0,5 |
| Calidad | Calificación bayesiana (10·4,3 + n·x̄)/(10 + n), dividida entre 5 |
| Descongestión | 1 − ocupación de la zona. Sin dato → 0,5 |
| Sostenibilidad | Índice 0..1 de la oferta |

Reglas después del puntaje:
- **Descongestión:** si una oferta está en una zona con ocupación ≥ 80 %, se reemplaza por la mejor oferta de una zona no saturada que comparta categoría. Si no hay alternativa, se mantiene y la explicación lo advierte.
- **Diversidad:** máximo 2 ofertas por zona.
- **Equidad:** el prestador no interviene en ningún criterio (prueba `test_el_prestador_no_influye_en_el_puntaje`).
- **Pesos versionados e inmutables:** cada recomendación guarda su versión y su desglose.

La prueba `test_reproduce_el_ejemplo_del_boceto_w3` reproduce el 0,92 del Tour cascadas de Minca.

## Estructura (Clean Architecture)

```
src/ia/
  dominio/          modelos, puntaje, ranking, repositorios abstractos (ABC)   (no depende de nada)
  aplicacion/       casos de uso, puertos (ABC), eventos, explicaciones ES/EN, DTO   (→ dominio)
  api/              FastAPI + entrada de eventos (consumidor_eventos.py)       (→ aplicacion)
  infraestructura/
    rabbitmq.py     consumidor de RabbitMQ (pika) y su comprobación de salud
    memoria.py      repositorios en memoria
    semilla.py      datos de prueba (tours de los bocetos W1 y W3)
    sql/            SQLAlchemy para ia_db: tablas, repositorios, conexión, salud (→ aplicacion, dominio)
  main.py           raíz de composición: elige memoria o base de datos y conecta las capas
migraciones/        Alembic
.github/workflows/  CI
```

Regla de dependencia (EC-MANT-01), verificada en cada `pytest` y en el CI:
- [.importlinter](.importlinter): contrato de capas + prohibición de FastAPI, Pydantic y SQLAlchemy en dominio y aplicación.
- `tests/test_arquitectura.py`: misma regla revisando los `import` con `ast`.

## Pruebas

| Archivo | Qué verifica |
|---|---|
| `test_puntaje.py`, `test_ranking.py` | Fórmula, ejemplo W3, calificación bayesiana, equidad, descongestión, diversidad |
| `test_aplicacion.py` | Casos de uso, explicación en el 100 % (ES/EN), pesos versionados, eventos idempotentes |
| `test_repositorios.py` | Mismas pruebas contra memoria, SQLite y PostgreSQL (este último solo con `IA_TEST_DATABASE_URL`) |
| `test_migraciones.py` | La migración produce exactamente el esquema de los modelos, inserta pesos v1 y se revierte |
| `test_api.py` | Endpoints sobre memoria y SQLite; 503 cuando la base cae |
| `test_arquitectura.py`, `test_import_linter.py` | Regla de dependencia entre capas |
| `test_consumidor_eventos.py` | Cada evento llega a su manejador (con los ejemplos de los contratos), repetidos se ignoran, mensajes que no cumplen el contrato se rechazan, RabbitMQ no crítico en `/health/ready` |
| `test_rabbitmq.py` | Contra **RabbitMQ real** (solo con `IA_TEST_RABBITMQ_URL`): popularidad, reenvío del outbox, cola de errores, reintento tras fallo temporal, app completa |

Para correr `test_rabbitmq.py` en local:

```powershell
docker run -d --rm --name ia-rabbitmq-prueba -p 5673:5672 rabbitmq:3-management
$env:IA_TEST_RABBITMQ_URL = "amqp://guest:guest@localhost:5673/%2F"
.\.venv\Scripts\python.exe -m pytest tests/test_rabbitmq.py
```

**CI** ([.github/workflows/ci.yml](.github/workflows/ci.yml)): en cada push corre todo lo anterior con Python 3.12 contra
**PostgreSQL 16 y RabbitMQ reales**, construye la imagen Docker y comprueba que responde.

## Pendiente

Depende del equipo:
- [ ] **JWT**: reemplazar `turista_actual()` en `api/app.py` por la validación de la plantilla común (ADR-06).
- [x] **RabbitMQ**: consumidor de `ia.eventos` con cola de errores (ver "Eventos").
- [ ] **RabbitMQ compartido**: en el compose general, quitar el `rabbitmq` de este compose y apuntar `IA_RABBITMQ_URL` al del grupo.
- [ ] **Validar el sobre con la plantilla común** (`comun.eventos.SobreEvento`) cuando esté en el monorepo: solo cambia `_validar_sobre` en `api/consumidor_eventos.py`.
- [ ] **Catálogo** debe publicar `catalogo.oferta.*`: sin esos eventos IA solo tiene los datos de prueba.
- [ ] **X-Correlation-Id, logs estructurados, outbox**: plantilla común (Santiago).
- [ ] **Gateway**: ruta `/api/v1/ia/*` y healthcheck `/health/ready` (Carlos).
- [ ] Decidir de dónde salen los intereses del turista y quién calcula `indice_sostenibilidad`.

Propio (sprint 6):
- [x] **Unidad de trabajo**: `evento_procesado` y el cambio de la proyección se guardan en la misma transacción (`UnidadDeTrabajoSql`).
- [ ] Prueba de carga.
