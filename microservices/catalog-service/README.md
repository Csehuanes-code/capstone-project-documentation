# 🌴 Microservicio de Catálogos (Plataforma de Turismo Santa Marta — Grupo 4)

Microservicio responsable de la gestión de oferta turística, atractivos, actividades guiadas, eventos, tarifas estacionales, políticas de cancelación, calificaciones, favoritos, itinerarios y sincronización en lote para la **Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta**.

Desarrollado bajo **Clean Architecture** (4 capas), **Python 3.12**, **FastAPI**, **PostgreSQL 16**, **SQLAlchemy 2.0 async**, **Alembic**, **Docker Compose** y pruebas con **pytest**.

---

## 🏛️ Arquitectura Limpia (Clean Architecture)

El proyecto organiza el código en cuatro capas estrictamente desacopladas:

```
catalog-service/
├── catalog_service/
│   ├── domain/               # Capa 1: Dominio puro (Entidades, Reglas, Value Objects, Excepciones)
│   │   ├── entities.py       # Zona, TipoServicio, PerfilPrestador, Oferta, Tarifa, etc.
│   │   ├── rules.py          # Reglas de negocio puras (vocabulario, solapamiento, calificaciones)
│   │   ├── value_objects.py  # Enums canónicos y Dinero (Decimal)
│   │   └── exceptions.py     # Excepciones de negocio (sin dependencias web)
│   ├── application/          # Capa 2: Aplicación (Casos de uso y Puertos)
│   │   ├── ports.py          # Interfaces abstractas de repositorios y clientes externos
│   │   └── use_cases.py      # CU-07, CU-09, CU-10, CU-19, CU-20, CU-22, CU-23, CU-24, CU-29
│   ├── api/                  # Capa 3: API REST (FastAPI)
│   │   ├── main.py           # App FastAPI, CORS, OpenAPI, /health
│   │   ├── schemas.py        # Esquemas Pydantic v2 (contratos HTTP)
│   │   ├── dependencies.py   # Inyección de dependencias y verificación de roles JWT
│   │   ├── error_handlers.py # Traducción de excepciones de dominio a HTTP (400, 403, 404, 409)
│   │   └── routers/          # Rutas: ofertas, calificaciones, favoritos, itinerarios, lotes, zonas
│   └── infrastructure/       # Capa 4: Infraestructura y Adaptadores
│       ├── config.py         # Configuración basada en variables de entorno (Pydantic Settings)
│       ├── database.py       # Engine y sesión asíncrona de SQLAlchemy 2.0
│       ├── models.py         # Modelos ORM para PostgreSQL 16 con soporte JSONB
│       ├── repositories.py   # Implementación SQLAlchemy de los puertos
│       ├── memory_repositories.py # Implementación en memoria para pruebas y desarrollo aislado
│       ├── event_publisher.py# Publicador de eventos en tabla 'outbox' (Transactional Outbox)
│       ├── reservas_client.py# Cliente HTTP síncrono hacia Reservas (timeout 1s)
│       └── seed.py           # Poblado inicial de zonas y tipos desde vocabulario.json
├── alembic.ini               # Configuración de migraciones
├── Dockerfile                # Imagen Docker multi-stage (Python 3.12-slim)
├── docker-compose.yml        # Orquestación con PostgreSQL 16
├── pyproject.toml            # Dependencias y configuración de herramientas
├── .importlinter             # Reglas de límites de capas arquitectónicas
├── .env.example              # Plantilla de variables de entorno (sin secretos)
├── tests/                    # Suite de pruebas unitarias, de API, de contrato y de arquitectura
└── README.md                 # Esta documentación
```

---

## 📋 Requisitos y Casos de Uso Cubiertos

| Requisito / CU | Operación | Endpoint / Adaptador | Persistencia | Regla de Dominio |
|---|---|---|---|---|
| **CU-07 / RF-CAT-01** | Consultar Catálogo | `GET /api/v1/catalogo/ofertas` | Tabla `oferta` | Solo ofertas `publicada`, filtros canónicos |
| **RF-CAT-03 / RF-IA-04** | Respaldo IA Popularidad | `GET /api/v1/catalogo/ofertas?orden=popularidad` | Índices `calificacion_promedio` | Orden explícito por calificación y número de reseñas |
| **ADR-04 §4.2** | Consulta de Condiciones | `GET /api/v1/catalogo/ofertas/{id}/condiciones` | Tablas `tarifa`, `politica_cancelacion` | Retorna tarifa vigente y política con timeout 1s |
| **CU-22 / RF-CAT-08** | Crear Oferta | `POST /api/v1/catalogo/ofertas` | Tabla `oferta` + `outbox` | Solo prestadores `verificado=true` pueden publicar |
| **CU-22 / RF-CAT-09** | Editar / Retirar Oferta | `PUT` / `DELETE /api/v1/catalogo/ofertas/{id}` | Tabla `oferta` + `outbox` | Aislamiento por prestador (403 si es ajena) |
| **CU-24 / RF-CAT-13** | Configurar Tarifas | `POST /api/v1/catalogo/ofertas/{id}/tarifas` | Tabla `tarifa` | Restricción de no solapamiento en misma temporada |
| **CU-19 / RF-CAT-15** | Calificar Experiencia | `POST /api/v1/catalogo/ofertas/{id}/calificaciones` | Tabla `calificacion` | Verifica reserva completada en Reservas + calif. única |
| **CU-20 / RF-CAT-17** | Responder Reseña | `POST /api/v1/catalogo/calificaciones/{id}/respuesta` | Tabla `respuesta_calificacion` | Solo el prestador dueño de la oferta puede responder |
| **CU-09 / RF-CAT-05** | Favoritos | `POST`/`DELETE`/`GET /api/v1/catalogo/favoritos` | Tabla `favorito` | Asociación turista-oferta |
| **CU-10 / RF-CAT-06** | Itinerarios | `POST`/`GET /api/v1/catalogo/itinerarios` | Tablas `itinerario`, `item_itinerario` | Alerta de solapamiento de horario sin bloquear (RF-CAT-07) |
| **CU-23 / RF-CAT-11** | Sincronización en Lote | `POST /api/v1/catalogo/lotes` | Tabla `lote_sincronizacion` | Responde `202 Accepted` + consistencia todo o nada |
| **CU-29 / RF-CAT-18** | Moderar Contenido | `PUT /api/v1/catalogo/calificaciones/{id}/moderacion` | Tabla `calificacion` | Solo administradores (403 para otros roles) |

---

## 🚀 Guía de Instalación y Ejecución en Windows

### 1. Requisitos Previos
- **Python 3.12** instalado en Windows.
- **Git** y **PowerShell** (o terminal de comandos).
- **Docker Desktop** (opcional, para base de datos PostgreSQL real).

### 2. Clonar y Configurar Entorno Virtual

Abre PowerShell en la carpeta de trabajo:

```powershell
# Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Actualizar pip e instalar dependencias con herramientas de desarrollo
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 3. Variables de Entorno

Copia el archivo de plantilla `.env.example` a `.env`:

```powershell
Copy-Item .env.example .env
```

Si deseas ejecutar el servicio en **modo aislado (In-Memory)** sin necesidad de levantar PostgreSQL:
Configura en `.env`:
```ini
USE_IN_MEMORY_REPO=true
```

### 4. Ejecución con Docker Compose (PostgreSQL 16)

Para ejecutar con la base de datos real:

```powershell
# Iniciar base de datos y microservicio
docker compose up -d

# Ver registros de ejecución
docker compose logs -f catalog-service
```

### 5. Ejecución Local Directa con Uvicorn

```powershell
# Aplicar migraciones con Alembic (si usas Postgres local)
alembic upgrade head

# Iniciar el servidor de desarrollo
uvicorn catalog_service.api.main:app --reload --port 8002
```

La documentación interactiva Swagger estará disponible en:
👉 **http://localhost:8002/docs**

---

## 🧪 Ejecución de Pruebas y Verificación

### 1. Ejecutar Suite Completa con Cobertura (pytest)

```powershell
pytest --cov=catalog_service --cov-report=term-missing
```

### 2. Verificar Límites de Arquitectura (import-linter)

```powershell
lint-imports --config .importlinter
```

### 3. Verificación de Tipos Estáticos (mypy)

```powershell
mypy catalog_service
```

---

## 🔒 Contratos y Seguridad

- **Vocabulario Canónico (`vocabulario.json`):** Solo se admiten los intereses `naturaleza`, `cultura`, `gastronomia`, `historia`, `playa`, `aventura` y las zonas `minca`, `tayrona`, `centro`, `los-naranjos`, `taganga`, `rodadero`.
- **Contrato de Oferta (`catalogo.oferta.schema.json`):** Todos los eventos publicados cumplen estrictamente con los 9 campos requeridos, tipos y rangos.
- **Transactional Outbox (`sobre-evento.schema.json`):** Los eventos se persisten en la tabla `outbox` en la misma transacción atómica de negocio y usan el sobre común.
- **Relevo a RabbitMQ (`infrastructure/outbox_relay.py`):** con `RABBITMQ_URL` configurado, un proceso de fondo publica los eventos pendientes del outbox en el exchange topic `turismo` (routing key = tipo, p. ej. `catalogo.oferta.publicada`) con confirmación del broker, y marca `publicado_en`. Si RabbitMQ no responde, los eventos esperan y se reintentan. Entrega al menos una vez: los consumidores (IA, Reservas) descartan repetidos por `evento_id`.
- **Eventos que consume (`api/eventos.py` + `infrastructure/event_consumer.py`):** cola `catalogo.eventos` del exchange `turismo`. Hoy: `auth.prestador.verificacion_resuelta` (contrato en `contratos/eventos/`), que Auth emite al resolver la verificación de un prestador (CU-28); Catálogo marca `verificado = (estado == "aprobada")` y solo entonces el prestador puede publicar ofertas (RF-USR-19). Cada evento se aplica una sola vez (`evento_procesado` en la misma transacción); los que no cumplen el contrato van a `catalogo.eventos.errores`; los fallos temporales se reintentan.
- **Salud:** `/health` (proceso vivo) y `/health/ready` (503 si PostgreSQL no responde; también informa si el consumidor de RabbitMQ está conectado, sin sacar al servicio de rotación). Docker y Compose usan `/health/ready`.
- **Migraciones:** `001_initial` + `002_alinear_indices`. El CI corre `alembic check`: la migración debe producir exactamente los modelos.
- **JWT de Auth (ADR-06, `infrastructure/security.py`):** solo se acepta `Authorization: Bearer <token>` firmado por Auth con **ES256**; se validan firma, emisor (`JWT_ISSUER`), audiencia (`JWT_AUDIENCE`), expiración y rol. La clave pública se configura con `JWT_PUBLIC_KEY_FILE` (PEM) o `JWT_JWKS_URL` (endpoint `/jwks` de Auth). Sin clave configurada, las rutas protegidas responden 401. No existen cabeceras de simulación (`X-User-Id`) ni tokens de prueba: las pruebas firman tokens reales con una clave de prueba (`tests/auth_util.py`, `tests/api/test_seguridad_jwt.py`).
- **Sin Credenciales en Repositorio:** El archivo `.env` está ignorado en `.gitignore`. No se almacenan claves privadas ni tokens.
