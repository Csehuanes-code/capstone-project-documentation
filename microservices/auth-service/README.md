# Borrador independiente: Auth

Punto de partida local para el servicio **Usuarios y Seguridad** de la Plataforma de Turismo de Santa Marta. Este borrador todavía no pertenece al repositorio del grupo; se integrará cuando Tobias comparta el código y el equipo confirme los contratos entre servicios.

## Alcance asignado

El diseño del proyecto asigna a David los casos **CU-01, CU-02, CU-26 y CU-28**. **CU-06** queda como alcance adicional por confirmar. Los requisitos siguientes se extrajeron de `requirements-document/use-cases.md`, `requirements-specification.md`, `constraints-analysis.md` y `measurable-quiality-attributes.md`.

| Caso | Comportamiento requerido | Requisitos relacionados |
|---|---|---|
| CU-01 — Registro | Crear una cuenta con correo único y rol permitido. Guardar versión de la política de datos y fecha/hora del consentimiento; sin aceptación no se crea la cuenta. Solicitar confirmación al servicio de notificaciones. | RF-USR-01 a RF-USR-03 |
| CU-02 — Autenticación | Validar credenciales, emitir token de acceso de corta duración y refresh token, y autorizar mediante RBAC. Bloquear temporalmente tras 5 intentos fallidos en 60 segundos; auditar accesos exitosos y fallidos. | RF-USR-04 a RF-USR-07; EC-SEG-01 |
| CU-26 — Solicitud de verificación | Permitir que un prestador envíe datos del negocio, documentos y número de RNT; guardar borrador y dejar la solicitud pendiente. No permitir publicar oferta antes de la verificación. | RF-USR-18 y RF-USR-19 |
| CU-28 — Decisión de verificación | Permitir a un administrador aprobar, rechazar o pedir información adicional con justificación registrada; contrastar el RNT y notificar la decisión. La aprobación habilita la publicación de ofertas. | RF-USR-19 a RF-USR-21 |
| CU-06 — Derechos de datos (adicional) | Registrar solicitudes de acceso, rectificación, eliminación o portabilidad; permitir exportar JSON/CSV y conservar marca de tiempo y resolución. La eliminación puede requerir revisión por obligaciones legales. | RF-USR-15 a RF-USR-17; EC-SEG-02 |

## Reglas de seguridad y privacidad

- Almacenar contraseñas con **Argon2id**; no guardar contraseñas en texto plano.
- Usar JWT de corta duración y refresh tokens. Los permisos se resuelven por roles; el token no debe conceder capacidades ajenas al rol.
- Usar respuestas genéricas ante credenciales inválidas, limitar intentos y registrar los eventos de autenticación.
- El diseño exige TLS 1.3 en el tráfico. WAF y rate limiting perimetral dependen del gateway/despliegue y deben coordinarse con el equipo.
- Minimizar datos personales y registrar el consentimiento. Si se incluye CU-06, la especificación fija un máximo de 10 días hábiles para consultas y 15 días hábiles para reclamos.
- Proteger documentos de prestadores en reposo y auditar cada decisión de verificación.

## Pendiente de acordar con el equipo

1. Nombre canónico de roles y estados: los documentos alternan `Prestador` y `operador`.
2. Contrato de JWT: emisor, audiencia, claims, expiración, refresh/revocación y cómo validarán el token los otros servicios.
3. Contratos de integración para solicitar notificaciones y compartir el estado de verificación.
4. Campos y formato permitidos para documentos y datos del negocio; responsable del almacenamiento de archivos.
5. Si CU-06 forma parte de la entrega de David o queda para otra etapa.
6. Los archivos de requisitos incluyen propuestas arquitectónicas alternativas y señalan decisiones en evaluación. Para implementar se debe seguir la arquitectura final aprobada por el grupo (incluido ADR-09) y no tratar cada propuesta como una decisión vigente.

## Estado del borrador

Está implementada una primera base independiente de infraestructura:

- Dominio: roles, correo normalizado, usuario, consentimiento, activación de cuenta, seguimiento de intentos fallidos y transiciones de verificación.
- Aplicación asíncrona: registro y confirmación de correo (CU-01), autenticación y rotación/revocación de refresh tokens (CU-02), envío de verificación (CU-26) y resolución administrativa (CU-28), definidos mediante puertos para encajar con `asyncpg`.
- Seguridad: adaptador Argon2id con los parámetros del ADR-06; emisión y verificación JWT ES256 sin datos personales en sus claims; JWKS público; refresh tokens opacos persistidos como hash, con rotación de un solo uso y revocación.
- Persistencia: tablas y adaptadores SQLAlchemy async para usuarios, consentimientos, verificaciones, confirmaciones de correo, refresh tokens, auditoría, intentos de login y outbox. Los cambios de registro y decisión de verificación escriben su evento outbox en la misma transacción; los primeros intentos de login se crean mediante upsert atómico para evitar carreras entre solicitudes simultáneas.
- API: rutas para registro, confirmación de correo, inicio de sesión, refresh, revocación, JWKS, salud y solicitudes/decisiones de verificación. `/health` comprueba que el proceso responda; `/ready` hace `SELECT 1` en PostgreSQL y devuelve 503 si no hay conexión o base configurada. Docker usa `/ready` como healthcheck de la API. La confirmación activa la cuenta una sola vez; el token expira en 24 horas y la base guarda su hash. Refresh rota el token en la misma fila; el anterior deja de servir, y el endpoint de revocación no revela si el token existía. Las rutas de verificación validan firma, emisor, audiencia y expiración del bearer JWT, y aplican roles de prestador y administrador. Si `AUTH_DATABASE_URL` y la configuración JWT están presentes, el arranque conecta FastAPI a los adaptadores SQL; sin ellas, `/health` sigue disponible y `/ready` devuelve 503.
- Migraciones: configuración Alembic y migraciones para el esquema, los tokens de confirmación y la reclamación/reintentos del outbox.
- Outbox: el caso de uso `DispatchOutbox` reclama lotes de 50 eventos por defecto mediante leases de 60 segundos; PostgreSQL usa `SKIP LOCKED` para permitir varios workers. Cada reclamo recibe un token de lease: un worker atrasado no puede publicar ni liberar el evento después de que otro lo haya reclamado. Si el publicador devuelve un error tipado, el evento se libera y se reintenta con espera exponencial (1, 2, 4… hasta 3600 segundos). Solo se persiste un código breve, nunca el texto de excepción. Al confirmar la publicación se marca el evento y se eliminan correo y token de confirmación del payload.
- Arquitectura: `lint-imports` comprueba las capas y prohíbe que las rutas HTTP importen directamente adaptadores de infraestructura. Solo `api.main`, el punto de ensamblaje, tiene una excepción explícita para crear los adaptadores.
- Pruebas: 68 pasan localmente; se omiten dos pruebas que requieren PostgreSQL. Contra PostgreSQL 16 pasan las 70, incluida la secuencia registro-confirmación-login-rotación-revocación, 12 intentos de login simultáneos y los casos de readiness, lease, bloqueo obsoleto, lote y reintentos. Ruff, Import-Linter, mypy y `alembic check` también pasan.

El registro deja una solicitud de notificación en el outbox con el correo y token de confirmación para que el servicio de notificaciones pueda construir el enlace. El payload conserva esos datos solo hasta que el publicador confirme la entrega; después, `SqlOutboxRepository.mark_published` los elimina. La aplicación y el adaptador de persistencia del despacho están listos, pero todavía no hay un worker periódico ni publicador RabbitMQ. Para conectarlos faltan el sobre y nombre de evento comunes, la política de confirmación del broker, las credenciales/URL de RabbitMQ y el lugar de ejecución del worker. No se inventó ese contrato mientras el equipo no lo confirme.

La duración del bloqueo temporal no está definida en los documentos; por eso el seguidor de intentos exige configurarla. El emisor, audiencia, `kid`, rotación de claves y formato final de eventos también deben alinearse con los contratos del equipo antes de integrar. El inicio de sesión solo crea sesión para cuentas activas; el equipo debe confirmar cuándo una cuenta recién registrada pasa de `pendiente` a `activo`.

El diseño que describió Tobias fija Python 3.12 y FastAPI; se conservará esa base mientras el equipo confirma la estructura y los contratos del repositorio compartido.

## Estructura

El borrador tiene cuatro capas: `domain`, `application`, `api` e `infrastructure`. Los puertos viven en `application`, las rutas HTTP en `api` y los adaptadores SQL/criptográficos en `infrastructure`; `api.main` es el punto de composición.

## Ejecución local

Requiere Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
uvicorn auth_service.api.main:app --reload --port 8001
```

Para instalar también las herramientas de desarrollo: `python -m pip install -e ".[dev]"`.

### Base PostgreSQL local

1. Copia `.env.example` a `.env` y cambia `POSTGRES_PASSWORD` por una clave local.
2. Genera `secrets/auth-es256.pem` con el comando de la sección siguiente.
3. Inicia PostgreSQL y la API: `docker compose up --build -d`.
4. Comprueba el estado con `docker compose ps`; `/health` revisa la API y `/ready` confirma que también puede consultar PostgreSQL.

Compose aplica las migraciones antes de iniciar FastAPI. Los archivos `.env` y `secrets/` están excluidos de Git. Para apagar los contenedores conserva los datos de la base con `docker compose down`; `docker compose down -v` también elimina el volumen y los datos locales.

## Configuración del servicio

El arranque con persistencia requiere estas variables de entorno (configúralas fuera del repositorio; nunca guardes secretos en Git). Para la clave de firma puedes indicar un archivo local ignorado por Git o pasar el contenido PEM directamente:

```text
AUTH_DATABASE_URL=postgresql+asyncpg://usuario:clave@localhost:5432/auth_db
AUTH_JWT_PRIVATE_KEY_FILE=secrets/auth-es256.pem
AUTH_JWT_KID=<identificador de clave>
AUTH_JWT_ISSUER=<emisor acordado por el equipo>
AUTH_JWT_AUDIENCE=<audiencia acordada por el equipo>
AUTH_LOGIN_LOCKOUT_SECONDS=<duración acordada del bloqueo>
```

Para generar una clave local ES256 en PowerShell, crea primero `secrets` y ejecuta:

```powershell
New-Item -ItemType Directory -Force secrets
python -c "from pathlib import Path; from cryptography.hazmat.primitives import serialization; from cryptography.hazmat.primitives.asymmetric import ec; key=ec.generate_private_key(ec.SECP256R1()); Path('secrets/auth-es256.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))"
```

Con las variables configuradas, crea/actualiza el esquema con `alembic upgrade head` y arranca con `uvicorn auth_service.api.main:app --reload`. La duración del bloqueo, el emisor y la audiencia son valores provisionales por contrato: acuerda los definitivos con el equipo antes de desplegar.

Para probar los adaptadores contra PostgreSQL, define `AUTH_TEST_DATABASE_URL` apuntando a una base temporal vacía y ejecuta `python -m pytest tests/unit/infrastructure/test_database_adapters.py -p no:cacheprovider`. Estas pruebas eliminan y recrean sus tablas; nunca uses para ellas una base con información que debas conservar.

La prueba integral crea una cuenta, lee el token del outbox, confirma el correo e inicia sesión. Ejecútala solo contra una base PostgreSQL separada para pruebas, después de aplicar `alembic upgrade head`, definiendo `AUTH_INTEGRATION_DATABASE_URL` y ejecutando `python -m pytest tests/integration -p no:cacheprovider`.

## Verificación local en Windows

Con el entorno virtual activado, ejecuta:

```powershell
python -m pytest -p no:cacheprovider
ruff check src tests
lint-imports
mypy --strict src
```

Si no activaste `.venv`, puedes usar `\.venv\Scripts\python.exe -m pytest -p no:cacheprovider`, `\.venv\Scripts\ruff.exe check src tests` y `\.venv\Scripts\mypy.exe --strict src`.

Abre `http://127.0.0.1:8001/health`, `http://127.0.0.1:8001/ready` o `http://127.0.0.1:8001/docs` (con Docker Compose; con `uvicorn` local agrega `--port 8001`). Puertos del grupo: IA 8000, Auth 8001, Catálogo 8002, Reservas 8003, Analítica 8004.

No usar datos reales ni guardar claves, contraseñas o secretos en este borrador.
