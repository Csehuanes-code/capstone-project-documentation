## Especificación de Requerimientos de Software (SRS)

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Verificación: T/D/I/A](https://img.shields.io/badge/Verificaci%C3%B3n-T_%7C_D_%7C_I_%7C_A-orange?style=flat-square)

> **Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta.

> [!NOTE]
> **Propósito de la sección:** en cumplimiento de `Diseño-de-Ingenieria.md` ("Especificación de requerimientos — ISO/IEC/IEEE 29148:2018"), esta sección transforma los 14 stakeholders (`stakeholders.md`), los 34 casos de uso (`use-cases.md`), los 15 escenarios de calidad (`measurable-quiality-attributes.md`) y las restricciones (`constraints-analysis.md`) en un conjunto de requisitos **singulares, verificables y trazables**, siguiendo la estructura de la SRS del estándar. Aplica la lección del QA de `stakeholders.md`: **100% de cobertura** — cada uno de los 34 CU y cada uno de los 15 escenarios tiene al menos un requisito.

---

### 1. Introducción

#### 1.1 Propósito

Definir qué debe hacer y qué cualidades debe tener la plataforma, de forma suficientemente precisa para diseñar la arquitectura, construir el prototipo y verificarlo. Audiencia: equipo de desarrollo (SH-05), docente evaluador (SH-06) y, por derivación, la entidad de gestión del destino (SH-07).

#### 1.2 Alcance

**Dentro del alcance:** consulta de catálogo y disponibilidad, reservas (incluida grupal y lista de espera), integración con pasarela de pagos externa, gestión de oferta por prestadores, verificación de prestadores, recomendación personalizada con IA explicable, indicadores y capacidad de carga, notificaciones ES/EN, seguridad, auditoría y observabilidad básica.

**Fuera del alcance:** construcción de una pasarela de pagos propia (se integra una certificada), sistemas de gestión interna de hoteles, funcionalidades de IA distintas a la recomendación personalizada (ver Anexo A de `use-cases.md`), operación posterior al piloto.

#### 1.3 Definiciones y acrónimos

| Término | Definición |
|---|---|
| Prestador | Pequeño/mediano operador turístico u operador establecido (SH-02, SH-03) |
| Cupo | Unidad de capacidad reservable de un servicio en una fecha/horario |
| Capacidad de carga | Umbral de visitantes por zona/atractivo configurado por el administrador (CU-31) |
| RNT | Registro Nacional de Turismo (ver `constraints-analysis.md`, RC-N05) |
| RBAC | Control de acceso basado en roles |
| EC-xxx | Escenario de calidad medible (`measurable-quiality-attributes.md`) |
| RC-xxx | Requisito de restricción (`constraints-analysis.md`) |

#### 1.4 Referencias

ISO/IEC/IEEE 29148:2018; ISO/IEC 25010:2023; `context.md`, `stakeholders.md`, `use-cases.md`, `measurable-quiality-attributes.md`, `constraints-analysis.md`, `development-plan-and-budget.md`, `Restricciones.md`, `Descripcion-General.md`, `Objetivos.md`, `Diseño-de-Ingenieria.md`.

---

### 2. Convenciones de especificación

#### 2.1 Redacción

- Los requisitos se redactan con la forma **"El sistema deberá…"** (obligatorio). "Debería" indica deseable; se usa solo donde se indica.
- Un requisito = una condición verificable (característica *singular* del estándar). Las medidas numéricas provienen de los escenarios EC-xxx.
- Los requisitos **no prescriben tecnología** salvo cuando una restricción lo exige (ISO 29148: evitar implicar una implementación). Las decisiones tecnológicas viven en los ADR.

#### 2.2 Atributos de cada requisito

| Atributo | Valores |
|---|---|
| **ID** | `RF-<módulo>-nn` (funcional), `RNF-<atributo>-nn` (no funcional), `RI-nn` (interfaz), `RD-nn` (datos) |
| **P** (prioridad) | Heredada del CU de origen (5 = crítica … 2 = baja); 4 para requisitos derivados normativos |
| **CU / EC** | Caso de uso o escenario de calidad de origen |
| **SH** | Stakeholder que origina o se afecta (de `stakeholders.md`) |
| **V** (verificación) | **T** = prueba, **D** = demostración, **I** = inspección, **A** = análisis |

---

### 3. Descripción general

#### 3.1 Perspectiva del producto

Plataforma nueva que agrega oferta turística hoy fragmentada (estado *as-is* en `context.md`). Se relaciona con: pasarela de pagos certificada, proveedor de correo transaccional, fuentes externas de información (portales, redes sociales, solo lectura), proveedor cloud y servicio de IA. Los límites y actores corresponden al Diagrama de Contexto del Laboratorio 1.

#### 3.2 Funciones principales (módulos)

| Código | Módulo | CU cubiertos |
|---|---|---|
| USR | Usuarios y Seguridad | CU-01 a CU-06, CU-26 a CU-28, CU-33, CU-34 |
| CAT | Catálogo y Reputación | CU-07, CU-09, CU-10, CU-19, CU-20, CU-22 a CU-24, CU-29 |
| RES | Disponibilidad y Reservas | CU-08, CU-11 a CU-15 |
| PAG | Financiero / Pagos | CU-16, CU-17, CU-25 |
| NOT | Notificaciones | CU-18 |
| IA | Recomendación personalizada | CU-21 |
| ANA | Analítica y Sostenibilidad | CU-30, CU-31 |
| OPS | Observabilidad | CU-32 |

#### 3.3 Características de los usuarios

| Usuario | Característica relevante para los requisitos |
|---|---|
| Turista nacional/internacional (SH-01) | Heterogéneo en idioma y alfabetización digital; accede desde móvil o web; picos estacionales |
| Pequeño/mediano prestador (SH-02) | Recursos tecnológicos limitados; necesita interfaz simplificada y bajo esfuerzo de carga |
| Hotel/operador establecido (SH-03) | Gestiona inventario masivo; requiere integración por lote/API |
| Administrador (SH-04) | Rol técnico y de gobernanza; requiere trazabilidad y paneles |
| Usuarios con discapacidad / baja alfabetización (SH-14) | Transversal: exige WCAG AA y lenguaje claro en el 100% de la UI |

#### 3.4 Supuestos y dependencias

- El prototipo se evalúa como piloto de una entidad pública/mixta de turismo (género *Gobierno*, Laboratorio 1).
- Disponibilidad de cuentas de prueba (sandbox) de la pasarela de pagos y del proveedor de correo.
- Disponibilidad de datos de oferta de prueba (sintéticos o cargados por los prestadores) para validar escenarios.
- Cobertura móvil intermitente en zonas naturales (supuesto a validar; ver RC-D01).

---

### 4. Interfaces externas

| ID | Requisito | P | Origen | V |
|---|---|---|---|---|
| RI-01 | El sistema deberá ofrecer una interfaz web accesible desde navegadores vigentes y adaptable a viewports desde 360 px de ancho | 5 | RC-T01 | D |
| RI-02 | El sistema deberá ofrecer acceso desde dispositivos móviles (aplicación o web adaptable) con el mismo conjunto de funciones de reserva | 5 | RC-T01 | D |
| RI-03 | El sistema deberá exponer una API documentada para prestadores con capacidad técnica propia (gestión de oferta y sincronización por lote) | 3 | CU-22, CU-23; SH-03 | I |
| RI-04 | El sistema deberá integrarse con una pasarela de pagos certificada mediante una interfaz desacoplada que permita reemplazar el proveedor sin modificar la lógica de reservas | 5 | CU-16; SH-12 | I |
| RI-05 | El sistema deberá integrarse con un proveedor de correo transaccional con soporte de plantillas multilenguaje | 4 | CU-18 | D |
| RI-06 | El sistema deberá consumir fuentes externas de información turística en modo solo lectura mediante adaptadores, de modo que incorporar una fuente nueva no modifique el núcleo | 4 | `Descripcion-General.md`; EC-EVOL-01 | A |
| RI-07 | El sistema deberá exponer el servicio de recomendación mediante un contrato (entradas, salidas y explicación) independiente del resto de componentes | 4 | CU-21; SH-13 | I |

---

### 5. Requisitos funcionales

#### 5.1 Usuarios y Seguridad (USR)

| ID | Requisito | P | CU | SH | V |
|---|---|---|---|---|---|
| RF-USR-01 | El sistema deberá permitir crear una cuenta con rol Turista o Prestador usando un correo único | 5 | CU-01 | SH-01, 02, 03 | T |
| RF-USR-02 | El sistema deberá registrar el consentimiento del titular (versión de la política de datos y marca de tiempo) y no deberá crear la cuenta si no se acepta | 5 | CU-01 | SH-09 | T |
| RF-USR-03 | El sistema deberá solicitar el envío de una confirmación de registro al módulo de notificaciones | 4 | CU-01 | SH-01 | T |
| RF-USR-04 | El sistema deberá autenticar al usuario con credenciales y emitir un token de acceso de corta duración y un token de renovación | 5 | CU-02 | SH-04 | T |
| RF-USR-05 | El sistema deberá autorizar cada operación según el rol (turista, prestador, administrador) | 5 | CU-02 | SH-04 | T |
| RF-USR-06 | El sistema deberá bloquear temporalmente el acceso tras 5 intentos fallidos en 60 segundos | 5 | CU-02; EC-SEG-01 | SH-04 | T |
| RF-USR-07 | El sistema deberá registrar en auditoría todo acceso exitoso o fallido | 5 | CU-02, CU-33 | SH-04, 09 | I |
| RF-USR-08 | El sistema deberá permitir restablecer la contraseña mediante un token de un solo uso con expiración corta | 4 | CU-03 | SH-01 | T |
| RF-USR-09 | El sistema deberá responder con un mensaje neutro si el correo no existe, sin revelar la existencia de cuentas | 4 | CU-03 | SH-09 | T |
| RF-USR-10 | El sistema deberá invalidar las sesiones activas al restablecer la contraseña | 4 | CU-03 | SH-01 | T |
| RF-USR-11 | El sistema deberá permitir editar datos de contacto y preferencias de viaje | 4 | CU-04 | SH-01 | T |
| RF-USR-12 | El sistema deberá exigir una verificación adicional para cambiar el correo de acceso | 4 | CU-04 | SH-09 | T |
| RF-USR-13 | El sistema deberá permitir seleccionar idioma (español/inglés) y aplicarlo de inmediato, persistiéndolo en el perfil si hay sesión | 3 | CU-05 | SH-01, 14 | T |
| RF-USR-14 | El sistema deberá permitir activar alto contraste y ajustar el tamaño de fuente | 3 | CU-05 | SH-14 | D |
| RF-USR-15 | El sistema deberá permitir al titular solicitar acceso, rectificación, eliminación o portabilidad de sus datos personales | 4 | CU-06 | SH-09 | T |
| RF-USR-16 | El sistema deberá registrar cada solicitud de datos personales con marca de tiempo y resolución, y atender consultas en máximo 10 días hábiles y reclamos en máximo 15 días hábiles | 4 | CU-06; EC-SEG-02 | SH-09 | A |
| RF-USR-17 | El sistema deberá permitir exportar los datos personales del titular en formato portable (JSON o CSV) | 4 | CU-06 | SH-09 | T |
| RF-USR-18 | El sistema deberá permitir al prestador enviar su solicitud de verificación (datos del negocio, documentos y número de RNT) y guardarla como borrador | 4 | CU-26 | SH-02, 04 | T |
| RF-USR-19 | El sistema no deberá permitir publicar oferta a un prestador que no esté verificado | 4 | CU-26, CU-28 | SH-04 | T |
| RF-USR-20 | El sistema deberá permitir al administrador aprobar, rechazar o solicitar información adicional sobre un prestador, con justificación registrada y notificación al prestador | 4 | CU-28 | SH-04 | T |
| RF-USR-21 | El sistema deberá permitir al administrador contrastar el número de RNT declarado por el prestador con el Registro Nacional de Turismo antes de aprobar | 4 | CU-28; RC-N05 | SH-04, 02 | D |
| RF-USR-22 | El sistema deberá permitir al administrador buscar cuentas, cambiar roles y bloquear o reactivar cuentas, auditando cada cambio con responsable y marca de tiempo | 4 | CU-27 | SH-04 | T |
| RF-USR-23 | El sistema deberá exigir doble confirmación cuando el administrador modifique su propia cuenta | 4 | CU-27 | SH-04 | T |
| RF-USR-24 | El sistema deberá permitir consultar el log de auditoría por rango de fechas y tipo de evento (incluidas decisiones de IA) y exportar el resultado | 3 | CU-33 | SH-04, 09 | T |
| RF-USR-25 | El sistema no deberá permitir modificar ni eliminar manualmente registros de auditoría | 3 | CU-33 | SH-09 | T |
| RF-USR-26 | El sistema deberá permitir al administrador activar, rotar y revocar integraciones externas, validando la conexión antes de activarla | 2 | CU-34 | SH-04, 12 | T |
| RF-USR-27 | El sistema no deberá mostrar en texto plano las credenciales de integraciones una vez guardadas | 2 | CU-34 | SH-04 | I |

#### 5.2 Catálogo y Reputación (CAT)

| ID | Requisito | P | CU | SH | V |
|---|---|---|---|---|---|
| RF-CAT-01 | El sistema deberá permitir consultar y filtrar atractivos, actividades, eventos y prestadores sin necesidad de autenticación | 5 | CU-07 | SH-01 | T |
| RF-CAT-02 | El sistema deberá presentar el catálogo en español e inglés | 5 | CU-07 | SH-01 | T |
| RF-CAT-03 | El sistema deberá ordenar los resultados únicamente con criterios explícitos y documentados (relevancia, disponibilidad, calificación) | 5 | CU-07; EC-IA-02 | SH-02 | A |
| RF-CAT-04 | El sistema deberá sugerir la recomendación personalizada cuando una consulta no arroje resultados | 5 | CU-07 | SH-01 | T |
| RF-CAT-05 | El sistema deberá permitir marcar y desmarcar atractivos como favoritos y consultar la lista | 2 | CU-09 | SH-01 | T |
| RF-CAT-06 | El sistema deberá permitir crear itinerarios por día con atractivos o actividades del catálogo o de favoritos, y reordenarlos | 3 | CU-10 | SH-01 | T |
| RF-CAT-07 | El sistema deberá advertir solapamientos de horario en un itinerario sin impedir su guardado, y no deberá reservar automáticamente los servicios incluidos | 3 | CU-10 | SH-01 | T |
| RF-CAT-08 | El sistema deberá permitir al prestador crear, editar y dar de baja su oferta mediante un formulario simplificado con atributos que varían por tipo de servicio | 5 | CU-22 | SH-02 | T |
| RF-CAT-09 | El sistema deberá restringir a cada prestador a editar únicamente su propia oferta | 5 | CU-22 | SH-02 | T |
| RF-CAT-10 | El sistema deberá mostrar el número de RNT del prestador en cada ficha de oferta | 4 | CU-22; RC-N05 | SH-01, 02 | I |
| RF-CAT-11 | El sistema deberá permitir sincronizar inventario por lote (API o archivo), procesar los registros válidos y reportar los rechazados | 3 | CU-23; EC-INTEROP-01 | SH-03 | T |
| RF-CAT-12 | El sistema deberá permitir consultar el estado de una sincronización previa y no deberá dejar el catálogo parcialmente inconsistente ante un fallo | 3 | CU-23 | SH-03 | T |
| RF-CAT-13 | El sistema deberá permitir al prestador definir política de cancelación y precios por temporada dentro de los límites que fije la plataforma, rechazando valores fuera de límite con explicación | 3 | CU-24 | SH-02, 03 | T |
| RF-CAT-14 | El sistema deberá auditar los cambios de precio y de política de cancelación | 3 | CU-24 | SH-04 | I |
| RF-CAT-15 | El sistema deberá permitir calificar y comentar solo a quien tenga una reserva completada, rechazando duplicados | 3 | CU-19 | SH-01 | T |
| RF-CAT-16 | El sistema deberá actualizar el indicador agregado de reputación al registrarse una calificación | 3 | CU-19 | SH-07 | T |
| RF-CAT-17 | El sistema deberá permitir al prestador responder reseñas de su propia oferta, enviando a revisión manual las respuestas marcadas por reglas de moderación | 2 | CU-20 | SH-02, 03 | T |
| RF-CAT-18 | El sistema deberá permitir al administrador mantener, ocultar o eliminar contenido señalado, con justificación registrada y notificación al autor si se remueve | 3 | CU-29 | SH-04 | T |
| RF-CAT-19 | El sistema deberá incorporar información de fuentes externas autorizadas al catálogo, identificando el origen y la fecha de actualización de cada dato | 4 | `Descripcion-General.md`; EC-EVOL-01 | SH-02, 03 | D |

#### 5.3 Disponibilidad y Reservas (RES)

| ID | Requisito | P | CU | SH | V |
|---|---|---|---|---|---|
| RF-RES-01 | El sistema deberá mostrar cupos, horarios y precio de un servicio para la fecha y número de personas indicados | 5 | CU-08 | SH-01 | T |
| RF-RES-02 | El sistema deberá reflejar el estado real de cupos al momento de la consulta y sugerir fechas cercanas cuando el servicio esté agotado | 5 | CU-08 | SH-01 | T |
| RF-RES-03 | El sistema deberá bloquear temporalmente el cupo al iniciar la confirmación de una reserva | 5 | CU-11 | SH-01 | T |
| RF-RES-04 | El sistema deberá confirmar la reserva y descontar el cupo solo después de confirmarse el pago | 5 | CU-11 | SH-01, 12 | T |
| RF-RES-05 | El sistema deberá liberar el cupo bloqueado cuando el pago falle o no se confirme a tiempo, sin cobrar al turista | 5 | CU-11; EC-DISP-02 | SH-01 | T |
| RF-RES-06 | El sistema deberá emitir un comprobante al confirmar la reserva | 5 | CU-11 | SH-01 | D |
| RF-RES-07 | El sistema no deberá confirmar más reservas que el cupo disponible, incluso con solicitudes concurrentes sobre el mismo cupo | 5 | CU-11; EC-DISP-01 | SH-01, 03 | T |
| RF-RES-08 | El sistema deberá ofrecer unirse a la lista de espera cuando el cupo se agote entre la consulta y la confirmación | 5 | CU-11 | SH-01 | T |
| RF-RES-09 | El sistema deberá permitir reservar cupos para varios asistentes como una unidad atómica (todo o nada) con un único comprobante | 3 | CU-12 | SH-01 | T |
| RF-RES-10 | El sistema deberá permitir omitir los datos individuales de acompañantes cuando el prestador no los exija | 3 | CU-12 | SH-01 | D |
| RF-RES-11 | El sistema deberá registrar en lista de espera, por orden de llegada, a quien lo solicite para un cupo agotado | 3 | CU-13 | SH-01 | T |
| RF-RES-12 | El sistema deberá ofrecer el cupo liberado al primero de la lista con un plazo limitado y, si declina o expira, al siguiente | 3 | CU-13 | SH-01 | T |
| RF-RES-13 | El sistema deberá permitir cancelar una reserva aplicando la política del prestador, solicitando el reembolso si corresponde y liberando el cupo | 4 | CU-14 | SH-01 | T |
| RF-RES-14 | El sistema deberá marcar la cancelación como pendiente y avisar al administrador cuando falle el reembolso | 4 | CU-14 | SH-04 | T |
| RF-RES-15 | El sistema deberá listar el historial de reservas clasificado por estado, con filtro por fechas y prestador | 3 | CU-15 | SH-01 | T |

#### 5.4 Financiero / Pagos (PAG)

| ID | Requisito | P | CU | SH | V |
|---|---|---|---|---|---|
| RF-PAG-01 | El sistema deberá procesar cobros y reembolsos mediante la pasarela certificada con captura de datos de tarjeta tokenizada del lado de la pasarela | 5 | CU-16 | SH-12 | I |
| RF-PAG-02 | El sistema no deberá almacenar datos de tarjeta de pago | 5 | CU-16; RC-N06 | SH-12, 01 | I |
| RF-PAG-03 | El sistema deberá soportar pago con tarjeta y con transferencia bancaria (PSE) | 5 | CU-16 | SH-01 | D |
| RF-PAG-04 | El sistema deberá reintentar hasta 3 veces con espera creciente, en menos de 15 segundos, ante timeout o error de la pasarela, y marcar el pago como fallido si persiste | 5 | CU-16; EC-DISP-02 | SH-12 | T |
| RF-PAG-05 | El sistema deberá registrar de forma auditable cada transacción y calcular la comisión asociada | 5 | CU-16 | SH-02, 04 | T |
| RF-PAG-06 | El sistema deberá permitir al turista reportar un problema con un pago, registrando el caso con estado "en revisión" y asignándolo al administrador | 3 | CU-17 | SH-01, 04 | T |
| RF-PAG-07 | El sistema deberá permitir al administrador aprobar (con reembolso) o rechazar una disputa con justificación registrada, notificando al turista | 3 | CU-17 | SH-04 | T |
| RF-PAG-08 | El sistema deberá permitir al prestador consultar y exportar sus ventas, reservas y comisiones por período, sin acceso a datos de otros prestadores | 3 | CU-25 | SH-02, 03 | T |

#### 5.5 Notificaciones (NOT)

| ID | Requisito | P | CU | SH | V |
|---|---|---|---|---|---|
| RF-NOT-01 | El sistema deberá enviar notificaciones de forma asíncrona ante registro, recuperación de contraseña, reserva, lista de espera, cancelación y disputa, sin bloquear la transacción que las origina | 4 | CU-18 | SH-01 | T |
| RF-NOT-02 | El sistema deberá seleccionar la plantilla según el tipo de evento y el idioma configurado del destinatario | 4 | CU-18; EC-MULTI-01 | SH-01 | T |
| RF-NOT-03 | El sistema deberá reintentar automáticamente los envíos fallidos | 4 | CU-18 | SH-01 | T |
| RF-NOT-04 | El sistema no deberá revertir una transacción ya persistida por el fallo de una notificación | 4 | CU-18 | SH-01 | T |
| RF-NOT-05 | El sistema deberá registrar el estado de entrega de cada notificación | 4 | CU-18 | SH-04 | I |

#### 5.6 Recomendación con IA (IA)

| ID | Requisito | P | CU | SH | V |
|---|---|---|---|---|---|
| RF-IA-01 | El sistema deberá generar recomendaciones de atractivos y actividades según las preferencias del turista | 4 | CU-21 | SH-01, 13 | T |
| RF-IA-02 | El sistema deberá entregar con cada recomendación al menos un criterio explicativo en lenguaje simple | 4 | CU-21; EC-IA-01 | SH-01, 13 | T |
| RF-IA-03 | El sistema deberá registrar cada recomendación y su explicación en el log de auditoría con marca de tiempo | 4 | CU-21; EC-IA-01 | SH-04, 09 | I |
| RF-IA-04 | El sistema deberá recurrir a resultados por popularidad si el servicio de IA no responde en 3 segundos | 4 | CU-21; EC-DESM-02 | SH-01 | T |
| RF-IA-05 | El sistema deberá ponderar la capacidad de carga e incluir al menos una alternativa de menor congestión en toda recomendación mientras haya una alerta de umbral activa | 4 | CU-21; EC-SOST-01 | SH-08, 07 | T |
| RF-IA-06 | El sistema deberá basar las recomendaciones solo en criterios documentados y auditables, sin ponderaciones por tamaño o antigüedad del operador | 4 | CU-21; EC-IA-02 | SH-02 | A |
| RF-IA-07 | El sistema deberá poder ofrecer una recomendación proactiva ante congestión alta detectada | 4 | CU-21 | SH-08 | D |

#### 5.7 Analítica y Sostenibilidad (ANA) y Observabilidad (OPS)

| ID | Requisito | P | CU | SH | V |
|---|---|---|---|---|---|
| RF-ANA-01 | El sistema deberá calcular indicadores de ocupación, demanda y concentración turística por período y zona | 4 | CU-30 | SH-07, 04 | T |
| RF-ANA-02 | El sistema deberá exportar reportes en formatos accesibles y resaltar las zonas cercanas a su umbral | 4 | CU-30 | SH-07, 08 | D |
| RF-ANA-03 | El sistema deberá permitir al administrador definir umbrales de capacidad de carga por zona o atractivo, advirtiendo cuando sean inconsistentes con datos históricos | 3 | CU-31 | SH-04, 08 | T |
| RF-ANA-04 | El sistema deberá permitir importar umbrales de referencia proporcionados por la autoridad ambiental | 3 | CU-31 | SH-08 | D |
| RF-ANA-05 | El sistema deberá emitir una alerta al administrador en menos de 5 minutos cuando un indicador supere el 90% de su umbral | 3 | CU-31; EC-SOST-01 | SH-04, 08 | T |
| RF-OPS-01 | El sistema deberá mostrar al administrador disponibilidad, latencia, estado de colas y uso de recursos | 4 | CU-32 | SH-04, 10 | D |
| RF-OPS-02 | El sistema deberá notificar al administrador cuando la disponibilidad caiga bajo el umbral definido | 4 | CU-32 | SH-04 | T |
| RF-OPS-03 | El sistema deberá registrar los incidentes que afecten la disponibilidad para el informe de validación de restricciones | 4 | CU-32 | SH-04, 06 | I |

---

### 6. Requisitos no funcionales

Cada requisito deriva de un escenario de `measurable-quiality-attributes.md` (la medida es la del escenario) o de una restricción.

| ID | Requisito | Característica ISO 25010:2023 | Origen | V |
|---|---|---|---|---|
| RNF-DISP-01 | El sistema deberá mantener disponibilidad mensual ≥ 99% (≈7,3 h de indisponibilidad máxima al mes) en el servicio de consulta y reserva | Confiabilidad | EC-DISP-01; RC-T04 | A, T |
| RNF-DISP-02 | El sistema deberá detectar la caída de una réplica en menos de 30 segundos | Confiabilidad | EC-DISP-01 | T |
| RNF-DISP-03 | El sistema deberá liberar el 100% de los cupos bloqueados por pagos fallidos en menos de 60 segundos | Confiabilidad | EC-DISP-02 | T |
| RNF-DESM-01 | El sistema deberá responder consultas de catálogo con p95 < 800 ms y p99 < 1.500 ms con 500 usuarios simultáneos | Eficiencia de desempeño | EC-DESM-01; RC-T03 | T |
| RNF-DESM-02 | El servicio de IA deberá responder con p95 < 2 s sin caché y < 300 ms con resultado en caché | Eficiencia de desempeño | EC-DESM-02 | T |
| RNF-ESC-01 | El sistema deberá escalar horizontalmente en menos de 5 minutos al superar el umbral definido (p. ej., 70% de CPU sostenido 3 minutos), sin pérdida de solicitudes | Flexibilidad | EC-ESC-01; RC-T05 | T |
| RNF-EVOL-01 | El sistema deberá permitir incorporar un nuevo tipo de atractivo o prestador en menos de 1 día-persona y sin tiempo de inactividad | Flexibilidad | EC-EVOL-01 | D |
| RNF-INT-01 | El sistema deberá procesar un lote de 1.000 registros de inventario en menos de 60 segundos | Compatibilidad | EC-INTEROP-01 | T |
| RNF-INT-02 | El sistema deberá garantizar 0% de inconsistencia parcial ante fallos de un lote (todo o nada, o reporte exacto de rechazados) | Compatibilidad | EC-INTEROP-01 | T |
| RNF-SEG-01 | El sistema deberá almacenar contraseñas exclusivamente con un algoritmo de hash resistente (Argon2id) | Seguridad | EC-SEG-01; RC-N04 | I |
| RNF-SEG-02 | El sistema deberá cifrar todo el tráfico con TLS 1.3 | Seguridad | RC-N01, RC-N04 | I |
| RNF-SEG-03 | El sistema deberá cifrar en reposo los datos personales sensibles | Seguridad | RC-N01, RC-N02 | I |
| RNF-SEG-04 | El sistema deberá aislar la información comercial de cada prestador (tarifas, disponibilidad, ventas) de los demás prestadores | Seguridad | RC-N03 | T |
| RNF-SEG-05 | El sistema deberá registrar el 100% de los intentos bloqueados en el log de auditoría | Seguridad | EC-SEG-01 | I |
| RNF-USA-01 | Las pantallas de búsqueda, disponibilidad y reserva deberán cumplir WCAG 2.1 nivel AA, sin bloqueadores de navegación por teclado | Capacidad de interacción | EC-ACC-01; RC-S04 | I, T |
| RNF-USA-02 | El 100% de las cadenas de interfaz y plantillas de notificación deberá estar disponible en español e inglés, con cambio de idioma en menos de 1 segundo sin recargar la sesión | Capacidad de interacción | EC-MULTI-01; RC-S02 | T |
| RNF-USA-03 | El flujo de consulta a comprobante de reserva deberá completarse en un máximo de 5 pantallas, con lenguaje claro (*meta propuesta, a validar con usuarios en la fase de validación*) | Capacidad de interacción | RC-S01 | D |
| RNF-USA-04 | La interfaz del prestador deberá permitir publicar un servicio con los campos mínimos en un solo formulario (*meta propuesta, a validar*) | Capacidad de interacción | RC-S03 | D |
| RNF-MANT-01 | El ciclo commit → despliegue en pruebas deberá ser menor a 15 minutos, con cobertura de pruebas unitarias ≥ 70% en el módulo modificado y 0 regresiones en otros módulos | Mantenibilidad | EC-MANT-01 | T |
| RNF-IA-01 | El 100% de las recomendaciones deberá incluir un criterio explicativo verificable y quedar trazado en auditoría | Adecuación funcional | EC-IA-01; RC-ET01 | T |
| RNF-IA-02 | Una auditoría trimestral deberá verificar que ningún operador reciba ponderación distinta a la del modelo documentado, con 0 criterios ocultos | Adecuación funcional | EC-IA-02; RC-ET02 | A |
| RNF-SOST-01 | El sistema deberá generar la alerta de capacidad de carga en menos de 5 minutos desde que el indicador supere el 90% del umbral | Adecuación funcional | EC-SOST-01; RC-A04 | T |
| RNF-OBS-01 | El sistema deberá exponer métricas de salud y colas de mensajes que alimenten el panel de monitoreo | Mantenibilidad | CU-32 | D |
| RNF-LOC-01 | El sistema deberá registrar los eventos de acceso a datos personales para auditoría | Seguridad | RC-N02; RC-ET04 | I |

---

### 7. Requisitos de datos

| ID | Requisito | Origen |
|---|---|---|
| RD-01 | El modelo de dominio deberá incluir como entidades principales Usuario (Turista, Prestador, Administrador), Servicio Turístico, Reserva, Pago, Calificación, Itinerario, Zona/Umbral de capacidad y Recomendación (arquetipos del Laboratorio 1, ampliados) | Lab. 1 §4.2 |
| RD-02 | Los atributos variables por tipo de servicio deberán poder modelarse sin migraciones estructurales del núcleo | EC-EVOL-01 |
| RD-03 | Los datos de reservas y pagos deberán conservar integridad transaccional (sin estados intermedios incoherentes) | RF-RES-07 |
| RD-04 | Los datos personales deberán minimizarse: solo se recolectan los necesarios para la reserva, la personalización y la obligación legal | RC-N02, RC-ET03 |
| RD-05 | Cada dato de origen externo deberá conservar su fuente y fecha de actualización | RF-CAT-19 |
| RD-06 | Los registros de auditoría deberán ser inmutables | RF-USR-25 |

---

### 8. Restricciones de diseño

Las 38 restricciones del proyecto (técnicas, económicas y temporales, sociales, ambientales, normativas, éticas, de proceso y supuestos) se especifican, interpretan y analizan en `constraints-analysis.md`. Cada una es un **requisito de restricción** (RC-xxx) que condiciona las decisiones arquitectónicas y se valida al final en la tabla *Restricción → Decisión → Evidencia → Resultado* exigida en `Diseño-de-Ingenieria.md`.

---

### 9. Verificación

| Método | Aplica a | Evidencia esperada |
|---|---|---|
| **T** — Prueba | Comportamientos y medidas de EC-xxx | Pruebas automatizadas, de carga y de seguridad sobre el prototipo |
| **D** — Demostración | Flujos de usuario e interfaces | Demostración funcional y capturas |
| **I** — Inspección | Decisiones estructurales y de configuración | Revisión de código, configuración, ADR y diagramas |
| **A** — Análisis | Propiedades no medibles directamente en el piloto | Cálculos, auditorías, revisión de criterios documentados |

La asignación de casos de prueba concretos se completa en la Matriz de Trazabilidad de Requisitos (sección 10).

---

### 10. Trazabilidad

#### 10.1 Cobertura de casos de uso

| CU | Requisitos | CU | Requisitos |
|---|---|---|---|
| CU-01 | RF-USR-01, 02, 03 | CU-18 | RF-NOT-01 a 05 |
| CU-02 | RF-USR-04, 05, 06, 07 | CU-19 | RF-CAT-15, 16 |
| CU-03 | RF-USR-08, 09, 10 | CU-20 | RF-CAT-17 |
| CU-04 | RF-USR-11, 12 | CU-21 | RF-IA-01 a 07 |
| CU-05 | RF-USR-13, 14 | CU-22 | RF-CAT-08, 09, 10 |
| CU-06 | RF-USR-15, 16, 17 | CU-23 | RF-CAT-11, 12 |
| CU-07 | RF-CAT-01 a 04 | CU-24 | RF-CAT-13, 14 |
| CU-08 | RF-RES-01, 02 | CU-25 | RF-PAG-08 |
| CU-09 | RF-CAT-05 | CU-26 | RF-USR-18, 19 |
| CU-10 | RF-CAT-06, 07 | CU-27 | RF-USR-22, 23 |
| CU-11 | RF-RES-03 a 08 | CU-28 | RF-USR-19, 20, 21 |
| CU-12 | RF-RES-09, 10 | CU-29 | RF-CAT-18 |
| CU-13 | RF-RES-11, 12 | CU-30 | RF-ANA-01, 02 |
| CU-14 | RF-RES-13, 14 | CU-31 | RF-ANA-03, 04, 05 |
| CU-15 | RF-RES-15 | CU-32 | RF-OPS-01, 02, 03 |
| CU-16 | RF-PAG-01 a 05 | CU-33 | RF-USR-07, 24, 25 |
| CU-17 | RF-PAG-06, 07 | CU-34 | RF-USR-26, 27 |

**Resultado:** 34 de 34 casos de uso con al menos un requisito (100%).

#### 10.2 Cobertura de escenarios de calidad

| Escenario | Requisito(s) | Escenario | Requisito(s) |
|---|---|---|---|
| EC-DISP-01 | RNF-DISP-01, 02; RF-RES-07 | EC-SEG-01 | RF-USR-06; RNF-SEG-01, 05 |
| EC-DISP-02 | RNF-DISP-03; RF-PAG-04; RF-RES-05 | EC-SEG-02 | RF-USR-16 |
| EC-DESM-01 | RNF-DESM-01 | EC-ACC-01 | RNF-USA-01 |
| EC-DESM-02 | RNF-DESM-02; RF-IA-04 | EC-MULTI-01 | RNF-USA-02; RF-NOT-02 |
| EC-ESC-01 | RNF-ESC-01 | EC-MANT-01 | RNF-MANT-01 |
| EC-EVOL-01 | RNF-EVOL-01; RD-02; RF-CAT-19 | EC-IA-01 | RNF-IA-01; RF-IA-02, 03 |
| EC-INTEROP-01 | RNF-INT-01, 02; RF-CAT-11 | EC-IA-02 | RNF-IA-02; RF-CAT-03; RF-IA-06 |
| | | EC-SOST-01 | RNF-SOST-01; RF-ANA-05; RF-IA-05 |

**Resultado:** 15 de 15 escenarios cubiertos (100%).

#### 10.3 Matriz de Trazabilidad de Requisitos (RTM) — estructura base

Esta tabla se completa en la fase de diseño (ADR) e implementación (casos de prueba). Se muestra la fila por módulo; la versión por requisito individual se genera a partir de las tablas de las secciones 5 y 6, que ya contienen las columnas *CU/EC*, *SH* y *V*.

| Módulo | Stakeholders | Restricciones (RC) | ADR candidatos | Prueba / evidencia | Estado |
|---|---|---|---|---|---|
| USR | SH-01, 02, 03, 04, 09 | N01–N05, ET03, ET04 | ADR-06 Seguridad y cumplimiento | Pruebas de seguridad, auditoría | Por definir |
| CAT | SH-01, 02, 03, 07 | T02, S03, N03, ET02 | ADR-03 Persistencia; ADR-04 Comunicación | Pruebas de catálogo y lote | Por definir |
| RES | SH-01, 03, 12 | T03, T04 | ADR-02 Estilo; ADR-08 Despliegue | Pruebas de concurrencia y carga | Por definir |
| PAG | SH-01, 02, 12 | N06, T07 | ADR-04 Comunicación; ADR-06 | Pruebas con *sandbox* de pasarela | Por definir |
| NOT | SH-01, 04 | S02, T07 | ADR-04 Comunicación | Pruebas de entrega ES/EN | Por definir |
| IA | SH-01, 02, 08, 13 | ET01, ET02, A01, A04 | ADR-07 IA explicable | Auditoría de explicabilidad y equidad | Por definir |
| ANA | SH-04, 07, 08 | A02, A04 | ADR-03 Persistencia | Pruebas de indicadores y alertas | Por definir |
| OPS | SH-04, 10 | T04, E01 | ADR-08 Despliegue | Evidencia de monitoreo | Por definir |

---

### 11. Verificación de calidad de la especificación

Evaluación de la SRS frente a las características de calidad de ISO/IEC/IEEE 29148:2018 (`use-cases-standard.md`, §2.3):

| Característica | Cómo se cumple en esta SRS | Estado |
|---|---|---|
| No ambiguo | Forma "El sistema deberá…" y medidas numéricas tomadas de los EC | Cumple |
| Completo | 34/34 CU y 15/15 EC cubiertos; restricciones en documento propio | Cumple |
| Singular | Un requisito por condición verificable | Cumple |
| Factible | Contrastado con presupuesto y plazo en `constraints-analysis.md` (§5) | Cumple |
| Verificable | Cada requisito tiene método V; las medidas provienen de los EC | Cumple |
| Correcto | Derivado de CU y stakeholders ya revisados | Parcial: pendiente validación con el docente |
| Conforme | Plantilla y atributos declarados en la sección 2 | Cumple |
| No redundante | Lo compartido se referencia por CU (autenticación, notificación) | Cumple |
| Actualizado | Vinculado a RTM; se revisa ante cambios de restricciones | Cumple |

---

### 12. Observaciones y decisiones abiertas

> [!IMPORTANT]
> Estos puntos no bloquean la SRS (los requisitos son neutros respecto a la arquitectura), pero deben resolverse antes del Documento de Diseño Arquitectónico Final.

1. **Divergencia de estilo arquitectónico.** La documentación previa selecciona monolito modular con IA y Notificaciones extraídos; el Laboratorio 1 deriva microservicios completos por la asignación individual de componentes. Esta SRS es válida bajo ambas; el análisis de impacto está en `constraints-analysis.md` (§6).
2. **Pagos y notificaciones.** El docente indicó en la revisión del Laboratorio 1 que la pasarela de pagos no se incluye en el sistema de ese diagrama de contexto y que las notificaciones se asumen implícitas dentro de Reservas. Esta SRS mantiene RF-PAG y RF-NOT porque CU-11 (flujo crítico) depende de ellos; se especifican como **integración con servicio externo** y **función interna**, respectivamente. Debe confirmarse con el docente si el flujo crítico se evalúa con pago real, simulado (*sandbox*) o excluido.
3. **Requisitos derivados no cubiertos por un CU explícito.** RF-CAT-19 (ingesta de fuentes externas) y los requisitos de RNT (RF-USR-18, 21; RF-CAT-10) surgen de `Descripcion-General.md` y de la investigación normativa (RC-N05). Se recomienda actualizar CU-22, CU-26 y CU-28 y valorar un CU específico de integración de fuentes.
4. **Metas de usabilidad propuestas.** RNF-USA-03 y RNF-USA-04 son metas del equipo, no derivadas de un EC; deben validarse con usuarios o ajustarse en la fase de validación.
