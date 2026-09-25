## Atributos de Calidad Formulados como Escenarios Medibles

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Modelo de calidad: ISO 25010:2023](https://img.shields.io/badge/Modelo-ISO%2FIEC_25010%3A2023-orange?style=flat-square)

> **Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta.

> [!NOTE]
> **Propósito de la sección:** en cumplimiento de `Diseño-de-Ingenieria.md` ("atributos de calidad formulados como escenarios medibles"), esta sección formaliza los atributos de calidad priorizados en `Descripcion-General.md` y `Fundamentacion-de-Decisiones.md` (escalabilidad, disponibilidad, interoperabilidad, seguridad, mantenibilidad, rendimiento, capacidad de evolución) mediante la **plantilla de escenario de atributo de calidad de seis partes** (estímulo, fuente del estímulo, artefacto, ambiente, respuesta, medida de la respuesta), clasificados según las nueve características del producto de software de **ISO/IEC 25010:2023**.

---

### 1. Marco normativo: ISO/IEC 25010:2023

ISO/IEC 25010:2023 define un modelo de calidad de producto compuesto por nueve características: **adecuación funcional, eficiencia de desempeño, compatibilidad, capacidad de interacción, confiabilidad, seguridad, mantenibilidad, flexibilidad y seguridad operacional (*safety*)**. Frente a la edición 2011, esta versión reemplaza *usabilidad* y *portabilidad* por *capacidad de interacción* y *flexibilidad* respectivamente, añade *seguridad operacional* como característica propia (con subcaracterísticas de restricción operacional, identificación de riesgos, falla segura, advertencia de peligro e integración segura), e incorpora *inclusividad* como subcaracterística de capacidad de interacción — relevante directamente para el requisito de accesibilidad del proyecto (SH-14, WCAG AA).

**Mapeo entre la terminología del curso y ISO 25010:2023:**

| Término usado en `Descripcion-General.md` | Característica ISO/IEC 25010:2023 |
|---|---|
| Escalabilidad | Flexibilidad → subcaracterística de escalabilidad |
| Disponibilidad | Confiabilidad → subcaracterística de disponibilidad |
| Interoperabilidad | Compatibilidad |
| Seguridad | Seguridad |
| Mantenibilidad | Mantenibilidad |
| Rendimiento | Eficiencia de desempeño |
| Capacidad de evolución | Flexibilidad → subcaracterística de adaptabilidad |
| Accesibilidad (WCAG AA, `Restricciones.md`) | Capacidad de interacción → subcaracterística de inclusividad |
| Explicabilidad de la IA (`Restricciones.md`) | Adecuación funcional (correctitud funcional) + Capacidad de interacción (transparencia de la respuesta al usuario) |

---

### 2. Plantilla de escenario (seis partes)

Cada escenario se especifica con los siguientes campos: **Fuente del estímulo** (quién o qué genera el estímulo), **Estímulo** (la condición que llega al sistema), **Artefacto** (la parte del sistema afectada), **Ambiente** (el estado del sistema cuando ocurre el estímulo), **Respuesta** (lo que el sistema debe hacer) y **Medida de la respuesta** (el criterio cuantificable de éxito).

---

### 3. Escenarios por Atributo de Calidad

#### 3.1 Confiabilidad — Disponibilidad

| ID | EC-DISP-01 |
|---|---|
| **Característica ISO 25010** | Confiabilidad (disponibilidad) |
| **Fuente del estímulo** | Turistas concurrentes durante temporada alta |
| **Estímulo** | Pico de tráfico de consultas y reservas (ej. puente festivo, alta demanda de Semana Santa) |
| **Artefacto** | Módulo de Disponibilidad y Reservas |
| **Ambiente** | Operación normal, carga estacional alta |
| **Respuesta** | El sistema mantiene el servicio de consulta y reserva operativo mediante réplicas activas del módulo detrás de un balanceador |
| **Medida de la respuesta** | Disponibilidad mensual ≥ 99% (máximo ~7,3 horas de indisponibilidad acumulada al mes); tiempo de detección de una réplica caída < 30 segundos (latido/heartbeat) |
| **Trazabilidad** | `Restricciones.md` (disponibilidad ≥99%); CU-08, CU-11, CU-32 |

| ID | EC-DISP-02 |
|---|---|
| **Característica ISO 25010** | Confiabilidad (tolerancia a fallos) |
| **Fuente del estímulo** | Fallo transitorio de la pasarela de pagos externa (Wompi/ePayco) |
| **Estímulo** | Timeout o error 5xx durante el procesamiento de un pago (CU-16) |
| **Artefacto** | Módulo Financiero/Pagos, saga orquestada de reserva |
| **Ambiente** | Operación normal |
| **Respuesta** | El sistema reintenta con *circuit breaker*, libera el cupo bloqueado y notifica al turista sin cobrar |
| **Medida de la respuesta** | Máximo 3 reintentos con backoff exponencial en menos de 15 segundos; 100% de los cupos bloqueados por pagos fallidos se liberan en menos de 60 segundos |
| **Trazabilidad** | `architectures-technical-details.md` (patrón *adapter* y resiliencia); CU-11, CU-16 |

#### 3.2 Eficiencia de Desempeño

| ID | EC-DESM-01 |
|---|---|
| **Característica ISO 25010** | Eficiencia de desempeño (comportamiento temporal) |
| **Fuente del estímulo** | Turista |
| **Estímulo** | Consulta de catálogo con filtros (CU-07) bajo carga concurrente de hasta 500 usuarios simultáneos |
| **Artefacto** | Módulo Catálogo (PostgreSQL + JSONB + índices GIN) |
| **Ambiente** | Temporada alta, carga pico simulada |
| **Respuesta** | El sistema retorna resultados filtrados sin degradación perceptible |
| **Medida de la respuesta** | Percentil 95 (p95) del tiempo de respuesta < 800 ms; percentil 99 (p99) < 1.500 ms |
| **Trazabilidad** | `Restricciones.md` (alta concurrencia); CU-07 |

| ID | EC-DESM-02 |
|---|---|
| **Característica ISO 25010** | Eficiencia de desempeño (utilización de recursos) |
| **Fuente del estímulo** | Turista solicitando recomendación personalizada |
| **Estímulo** | Invocación al microservicio de IA (CU-21) |
| **Artefacto** | Microservicio de IA (recomendación) |
| **Ambiente** | Operación normal, sin caché previa |
| **Respuesta** | El sistema calcula y retorna una recomendación explicada, usando caché de resultados frecuentes cuando aplique |
| **Medida de la respuesta** | Tiempo de respuesta p95 < 2 segundos en frío; < 300 ms cuando el resultado está en caché; si el modelo no responde en 3 segundos, se activa el *fallback* por popularidad (CU-21) |
| **Trazabilidad** | Laboratorio 1 (táctica de caché en IA); CU-21 |

#### 3.3 Flexibilidad — Escalabilidad y Evolutividad

| ID | EC-ESC-01 |
|---|---|
| **Característica ISO 25010** | Flexibilidad (escalabilidad) |
| **Fuente del estímulo** | Aumento sostenido de la demanda (crecimiento del número de turistas registrados o de operadores) |
| **Estímulo** | El tráfico transaccional se duplica respecto a la línea base de la temporada baja |
| **Artefacto** | Núcleo (monolito modular) y microservicios extraídos (IA, Notificaciones) |
| **Ambiente** | Crecimiento progresivo, no un pico puntual |
| **Respuesta** | El sistema escala horizontalmente añadiendo réplicas del núcleo y del microservicio de IA, sin interrupción del servicio |
| **Medida de la respuesta** | Escalado horizontal completado en menos de 5 minutos desde que se supera el umbral de CPU/latencia definido (ej. 70% CPU sostenido por 3 minutos); cero pérdida de solicitudes durante el escalado |
| **Trazabilidad** | `Descripcion-General.md` (arquitectura preparada para crecimiento progresivo) |

| ID | EC-EVOL-01 |
|---|---|
| **Característica ISO 25010** | Flexibilidad (adaptabilidad) |
| **Fuente del estímulo** | Equipo de desarrollo / entidad gestora del destino |
| **Estímulo** | Necesidad de incorporar un nuevo tipo de prestador turístico o una nueva fuente externa de datos (ej. un nuevo operador de guías) |
| **Artefacto** | Módulo Catálogo (esquema JSONB) y capa de integración |
| **Ambiente** | Sistema en producción, sin ventana de mantenimiento extendida |
| **Respuesta** | El nuevo tipo de atractivo/servicio se modela como un nuevo esquema JSONB sin alterar la estructura relacional del núcleo ni requerir migración destructiva |
| **Medida de la respuesta** | Incorporación de un nuevo tipo de atractivo en menos de 1 día-persona de desarrollo, sin tiempo de inactividad (*downtime* = 0) |
| **Trazabilidad** | `Descripcion-General.md` ("facilitar la evolución... sin modificaciones significativas en el núcleo"); `architectures-technical-details.md` (A.2.1) |

#### 3.4 Compatibilidad — Interoperabilidad

| ID | EC-INTEROP-01 |
|---|---|
| **Característica ISO 25010** | Compatibilidad (interoperabilidad) |
| **Fuente del estímulo** | Hotel/Operador Establecido (SH-03) |
| **Estímulo** | Envío de un lote de sincronización de inventario vía API (CU-23) |
| **Artefacto** | API de integración del módulo Catálogo |
| **Ambiente** | Operación normal |
| **Respuesta** | El sistema valida, procesa los registros correctos y reporta los rechazados sin dejar el catálogo en estado inconsistente |
| **Medida de la respuesta** | Procesamiento de un lote de 1.000 registros en menos de 60 segundos; 0% de inconsistencia parcial ante fallos (todo o nada por lote, o reporte exacto de rechazados) |
| **Trazabilidad** | `stakeholders.md` (SH-03); CU-23 |

#### 3.5 Seguridad

| ID | EC-SEG-01 |
|---|---|
| **Característica ISO 25010** | Seguridad (confidencialidad, autenticidad) |
| **Fuente del estímulo** | Atacante externo |
| **Estímulo** | Intento de fuerza bruta contra el endpoint de autenticación (CU-02) |
| **Artefacto** | Módulo Usuarios y Seguridad (API Gateway + WAF) |
| **Ambiente** | Operación normal |
| **Respuesta** | El sistema aplica *rate limiting* y bloqueo temporal de la cuenta/IP origen, registrando el evento en auditoría |
| **Medida de la respuesta** | Bloqueo activado tras 5 intentos fallidos en 60 segundos; contraseñas almacenadas exclusivamente con Argon2id; 100% de los intentos bloqueados quedan registrados en el log de auditoría |
| **Trazabilidad** | `Restricciones.md` (gestión segura de autenticación); CU-02, CU-33 |

| ID | EC-SEG-02 |
|---|---|
| **Característica ISO 25010** | Seguridad (confidencialidad de datos personales) |
| **Fuente del estímulo** | Titular de datos personales (turista) |
| **Estímulo** | Solicitud de acceso, rectificación o eliminación de datos personales (CU-06, Ley 1581 de 2012) |
| **Artefacto** | Módulo Usuarios y Seguridad + módulo de auditoría |
| **Ambiente** | Operación normal |
| **Respuesta** | El sistema resuelve la consulta o encola la solicitud para atención administrativa dentro de los plazos legales |
| **Medida de la respuesta** | Consultas de datos personales atendidas en máximo 10 días hábiles (con posibilidad de prórroga de hasta 5 días hábiles adicionales, informando motivo); reclamos resueltos en máximo 15 días hábiles, conforme a los artículos 14 y 15 de la Ley 1581 de 2012 |
| **Trazabilidad** | `Restricciones.md` (Ley 1581 de 2012); CU-06 |

#### 3.6 Capacidad de Interacción — Inclusividad y Accesibilidad

| ID | EC-ACC-01 |
|---|---|
| **Característica ISO 25010** | Capacidad de interacción (inclusividad) |
| **Fuente del estímulo** | Usuario con discapacidad visual o baja alfabetización digital (SH-14) |
| **Estímulo** | Navegación por las pantallas de búsqueda y reserva usando lector de pantalla o navegación por teclado |
| **Artefacto** | Interfaz web/móvil (frontend) |
| **Ambiente** | Uso normal, cualquier dispositivo |
| **Respuesta** | El sistema permite completar el flujo de consulta y reserva usando exclusivamente teclado/lector de pantalla, con etiquetas y contraste adecuados |
| **Medida de la respuesta** | Cumplimiento verificable del nivel **AA** de WCAG 2.1 en las pantallas de búsqueda, disponibilidad y reserva, conforme al Anexo Técnico 1 de la Resolución 1519 de 2020 de MinTIC (32 criterios de accesibilidad evaluables); 0 bloqueadores de navegación por teclado detectados en auditoría |
| **Trazabilidad** | `Restricciones.md` (accesibilidad); `stakeholders-standard-spec.md` (W3C WCAG); CU-01, CU-05, CU-07 |

| ID | EC-MULTI-01 |
|---|---|
| **Característica ISO 25010** | Capacidad de interacción (adecuación al usuario) |
| **Fuente del estímulo** | Turista internacional |
| **Estímulo** | Selección del idioma inglés en la configuración de la cuenta (CU-05) |
| **Artefacto** | Interfaz de usuario + microservicio de Notificaciones |
| **Ambiente** | Uso normal |
| **Respuesta** | Toda la interfaz, incluidas las notificaciones automáticas, se presenta en el idioma seleccionado |
| **Medida de la respuesta** | 100% de las cadenas de interfaz y de las plantillas de notificación disponibles en español e inglés; cambio de idioma aplicado sin recargar la sesión en menos de 1 segundo |
| **Trazabilidad** | `Restricciones.md` (disponibilidad en español e inglés); CU-05, CU-18 |

#### 3.7 Mantenibilidad

| ID | EC-MANT-01 |
|---|---|
| **Característica ISO 25010** | Mantenibilidad (modularidad, capacidad de prueba) |
| **Fuente del estímulo** | Desarrollador del equipo |
| **Estímulo** | Necesidad de corregir un defecto en el módulo de Disponibilidad y Reservas sin afectar Catálogo ni Usuarios |
| **Artefacto** | Núcleo del monolito modular |
| **Ambiente** | Entorno de desarrollo/CI |
| **Respuesta** | El cambio se realiza y despliega afectando exclusivamente el módulo de Reservas, verificado por la suite de pruebas del módulo |
| **Medida de la respuesta** | Tiempo de ciclo (commit → despliegue en entorno de pruebas) menor a 15 minutos; cobertura de pruebas unitarias del módulo modificado ≥ 70%; 0 regresiones detectadas en los demás módulos |
| **Trazabilidad** | `Diseño-de-Ingenieria.md` (separación clara de componentes); `architectures-technical-details.md` (A.3) |

#### 3.8 Adecuación Funcional — Explicabilidad de la IA

| ID | EC-IA-01 |
|---|---|
| **Característica ISO 25010** | Adecuación funcional (correctitud) + Capacidad de interacción (transparencia) |
| **Fuente del estímulo** | Turista que recibe una recomendación personalizada |
| **Estímulo** | El sistema genera una recomendación de atractivo o actividad (CU-21) |
| **Artefacto** | Microservicio de IA + log de auditoría de decisiones |
| **Ambiente** | Operación normal |
| **Respuesta** | El sistema entrega la recomendación junto con los criterios explicativos en lenguaje simple, y registra ambos en el log de auditoría |
| **Medida de la respuesta** | 100% de las recomendaciones entregadas incluyen al menos un criterio explicativo verificable (ej. "preferencias de naturaleza + baja congestión actual"); 100% quedan trazadas en el log de auditoría con marca de tiempo |
| **Trazabilidad** | `Restricciones.md` (explicabilidad, no sesgo comercial); CU-21, CU-33 |

| ID | EC-IA-02 |
|---|---|
| **Característica ISO 25010** | Adecuación funcional (equidad algorítmica) |
| **Fuente del estímulo** | Pequeño/mediano prestador turístico (SH-02) |
| **Estímulo** | Consulta de resultados de búsqueda/recomendación donde compite con operadores establecidos |
| **Artefacto** | Motor de ordenamiento del Catálogo y motor de recomendación de IA |
| **Ambiente** | Operación normal |
| **Respuesta** | El sistema ordena/recomienda con base en criterios explícitos y auditables (relevancia, disponibilidad, calificación), no en el tamaño o antigüedad del operador |
| **Medida de la respuesta** | Auditoría trimestral verifica que ningún operador reciba una ponderación de posicionamiento distinta a la definida en el modelo documentado; 0 criterios ocultos no auditables en el algoritmo |
| **Trazabilidad** | `Restricciones.md` (Restricciones Éticas); CU-07, CU-21 |

#### 3.9 Ambiental — Turismo Sostenible (extensión funcional ligada a Flexibilidad/Adecuación Funcional)

| ID | EC-SOST-01 |
|---|---|
| **Característica ISO 25010** | Adecuación funcional (idoneidad) aplicada al requisito ambiental |
| **Fuente del estímulo** | Administrador de la plataforma / Autoridad Ambiental |
| **Estímulo** | El indicador de ocupación de una zona sensible (ej. sector del Parque Tayrona) se aproxima al umbral de capacidad de carga configurado (CU-31) |
| **Artefacto** | Módulo Analítica/Reportes + motor de recomendación de IA |
| **Ambiente** | Temporada alta |
| **Respuesta** | El sistema emite una alerta al administrador y ajusta las recomendaciones de IA hacia atractivos alternativos de menor congestión |
| **Medida de la respuesta** | Alerta generada en menos de 5 minutos desde que el indicador supera el 90% del umbral configurado; al menos una alternativa de menor congestión incluida en el 100% de las recomendaciones generadas mientras la alerta esté activa |
| **Trazabilidad** | `Restricciones.md` (Restricciones Ambientales); CU-21, CU-30, CU-31 |

---

### 4. Síntesis de Cobertura

| Característica ISO/IEC 25010:2023 | Escenarios que la cubren | Restricción/objetivo de origen |
|---|---|---|
| Confiabilidad (disponibilidad, tolerancia a fallos) | EC-DISP-01, EC-DISP-02 | Disponibilidad ≥99% (`Restricciones.md`) |
| Eficiencia de desempeño | EC-DESM-01, EC-DESM-02 | Alta concurrencia estacional |
| Flexibilidad (escalabilidad, adaptabilidad) | EC-ESC-01, EC-EVOL-01 | Crecimiento progresivo, evolución sin romper el núcleo |
| Compatibilidad | EC-INTEROP-01 | Integración de múltiples fuentes/operadores |
| Seguridad | EC-SEG-01, EC-SEG-02 | Autenticación segura, Ley 1581 de 2012 |
| Capacidad de interacción (inclusividad, adecuación al usuario) | EC-ACC-01, EC-MULTI-01 | Accesibilidad WCAG AA, multilenguaje |
| Mantenibilidad | EC-MANT-01 | Separación de componentes, evolutividad |
| Adecuación funcional (explicabilidad, equidad) | EC-IA-01, EC-IA-02 | Explicabilidad de IA, no sesgo comercial |
| Sostenibilidad (extensión funcional) | EC-SOST-01 | Restricciones ambientales, capacidad de carga |

Esta tabla deja lista la base para el **método de evaluación arquitectónica** que `Diseño-de-Ingenieria.md` exige aplicar sobre el prototipo ("cada equipo deberá seleccionar, justificar y aplicar un método de evaluación arquitectónica adecuado a los principales riesgos y atributos de calidad identificados"): cada escenario aquí definido es, por construcción, un caso de prueba verificable que alimentará directamente la Matriz de Trazabilidad de Requisitos (RTM) y la tabla de validación de restricciones del Documento Final.
