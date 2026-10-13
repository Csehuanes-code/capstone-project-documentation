## Análisis de Restricciones Técnicas, Económicas, Sociales, Normativas, Éticas y Arquitectónicas

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Restricciones: 38](https://img.shields.io/badge/Restricciones-38-orange?style=flat-square)

> **Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta.

> [!NOTE]
> **Propósito de la sección:** En cumplimiento de las directrices del proyecto y resolviendo las observaciones de revisión, esta sección enumera el 100% de las restricciones explícitas, incluyendo una sección dedicada exclusivamente a las **Restricciones Arquitectónicas y de Diseño**. Se traducen a condiciones verificables, se analiza su impacto en las decisiones arquitectónicas (ADR) y se contrasta su factibilidad.

---

### 1. Metodología y Clasificación

Cada restricción recibe un ID `RC-<tipo><nn>`:

| Prefijo | Tipo | Fuente |
|---|---|---|
| **ARQ** | Arquitectónica y de Diseño | `Proyecto capstone.docx` |
| **T** | Técnica | `Proyecto capstone.docx` |
| **E** | Económica y temporal | `Proyecto capstone.docx` |
| **S** | Social | `Proyecto capstone.docx` |
| **A** | Ambiental | `Proyecto capstone.docx` |
| **N** | Normativa | `Proyecto capstone.docx` + normativa colombiana |
| **ET** | Ética | `Proyecto capstone.docx` |

---

### 2. Catálogo y análisis de restricciones

#### 2.1 Restricciones Arquitectónicas y de Diseño
*(Sección explícita para guiar las Decisiones de Arquitectura de Software - ADR)*

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-ARQ01 | Paradigma Orientado a Objetos | Modelo de dominio y código en clases; lenguaje OO | Mantenibilidad | Elección de lenguaje y organización por capas/dominio | Inconsistencia con los requisitos de la rúbrica |
| RC-ARQ02 | Justificación de base de datos (Persistencia única o políglota) | ADR con comparación por tipo de dato, costo, complejidad y evolución | RNF-EVOL-01; RD-02 | Decide motores de BD y separación de almacenamiento estructurado/no estructurado | Complejidad operativa sin beneficio, o rigidez de esquema |
| RC-ARQ03 | Mecanismos de comunicación e integración justificados | ADR sobre estilo síncrono/asíncrono según interoperabilidad y seguridad | RI-04, RI-05, RI-07 | Define uso de REST/gRPC vs. eventos (Colas/RabbitMQ) | Acoplamiento fuerte y fallos en cascada |
| RC-ARQ04 | Separación clara de componentes | Código organizado según la arquitectura definida (repositorio estructurado) | RNF-MANT-01 | Límites de módulo estrictos; microservicios o monolito modular | Un monolito fuertemente acoplado (código espagueti) |
| RC-ARQ05 | Decisiones basadas en Trade-offs | Cada ADR debe ponderar costo, escalabilidad, conectividad, seguridad y mantenimiento | Todos los EC | Obliga análisis explícito en los ADR | Decisiones empíricas sin fundamento técnico |

#### 2.2 Restricciones técnicas

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-T01 | Acceso desde dispositivos móviles y Web | Mismas funciones críticas en ambos canales; viewport desde 360 px | Capacidad de interacción; RI-01, RI-02 | Frontend adaptable o dos clientes sobre una API común | Exclusión de turistas móviles |
| RC-T02 | Integración con múltiples fuentes de información | Incorporar una fuente nueva sin tocar el núcleo | EC-INTEROP-01, EC-EVOL-01 | Capa de adaptadores; modelo canónico de datos | Ecosistema fragmentado |
| RC-T03 | Alta concurrencia en temporadas turísticas | p95 < 800 ms con 500 usuarios simultáneos | EC-DESM-01, EC-DISP-01 | Réplicas horizontales, caché de lecturas | Caída o sobreventa en temporada alta |
| RC-T04 | Disponibilidad mínima del 99% | ≈ 7,3 h de indisponibilidad máxima/mes | EC-DISP-01/02 | Redundancia activa, balanceo, detección < 30 s | Incumplimiento del atributo prioritario |
| RC-T05 | Arquitectura preparada para crecimiento progresivo | Escalado horizontal < 5 min | EC-ESC-01, EC-EVOL-01 | Posibilidad de extraer componentes sin reescribir | Rediseño al crecer la demanda |

#### 2.3 Restricciones económicas y temporales

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-E01 | Presupuesto máximo de USD 20.000 para infraestructura inicial | Costo acumulado de infraestructura del piloto ≤ USD 20.000 | Costo | Favorece contenedores gestionados frente a mallas complejas | Inviabilidad del piloto |
| RC-E02 | Privilegiar software libre y nube de bajo costo | Componentes de código abierto o nivel gratuito | Costo, sostenibilidad | Selección de BD, colas y frameworks sin licencias pagas | Dependencia económica |
| RC-E03 | Equipo de cinco estudiantes con roles fijos | Cinco roles; carga y evaluación individual por rol | Mantenibilidad | Estilo arquitectónico modular para repartir trabajo | Sobrecarga o desbalance |
| RC-E04 | Tiempo máximo de ejecución de tres meses (12 semanas) | 6 sprints planificados y flujo crítico cerrado a tiempo | Factibilidad | Limita la complejidad operativa excesiva | Prototipo incompleto |

#### 2.4 Restricciones sociales

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-S01 | Interfaces accesibles para baja alfabetización digital | Flujo de reserva ≤ 5 pantallas, lenguaje claro | RNF-USA-03 | Elección de framework UI y patrones simples | Abandono de usuarios |
| RC-S02 | Disponibilidad en español e inglés | 100% de cadenas y plantillas en ES/EN; cambio < 1 s | EC-MULTI-01 | Internacionalización desde el diseño (i18n) | Turista internacional sin servicio |
| RC-S03 | Inclusión de pequeños operadores con recursos limitados | Publicar oferta con formulario simple manual | RNF-USA-04; RF-CAT-08 | Bajo costo de adopción tecnológica | Concentración de oferta en operadores grandes |
| RC-S04 | Accesibilidad para personas con discapacidad | WCAG 2.1 AA en búsqueda y reserva | EC-ACC-01 | Componentes accesibles semánticamente | Incumplimiento legal y exclusión |

#### 2.5 Restricciones ambientales

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-A01 | Recomendar destinos alternativos para disminuir congestión | Algoritmo redirige flujo con alerta activa | EC-SOST-01; RF-IA-05 | La IA consume datos de ocupación y umbrales | Persiste la concentración turística |
| RC-A02 | Reducir el impacto sobre ecosistemas sensibles | Zonas con umbral propio y alerta | RF-ANA-03 | Modelo de datos con zonificación de sensibilidad | Presión sobre áreas protegidas |
| RC-A03 | Difundir buenas prácticas ambientales | Contenido ambiental en fichas | CU-07, CU-18 | Plantillas de notificación dinámicas | Cumplimiento solo declarativo |
| RC-A04 | Monitorear la capacidad de carga turística | Indicador vs. umbral; alerta rápida al 90% | EC-SOST-01; RNF-SOST-01 | Módulo de analítica desacoplado del transaccional | Sobrecarga sin detección |

#### 2.6 Restricciones normativas

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-N01 | Protección de datos personales | Minimización, cifrado en tránsito (TLS 1.3) y en reposo | RNF-SEG-02, 03 | Seguridad transversal; datos sensibles aislados | Sanción y pérdida de confianza |
| RC-N02 | Cumplimiento de la Ley 1581 de 2012 (Habeas Data) | Consentimiento registrado; derechos de acceso/supresión | EC-SEG-02; RF-USR-15 | Módulo de solicitudes y anonimización de datos | Incumplimiento legal crítico |
| RC-N03 | Protección de información comercial de operadores | Aislamiento de datos de ventas y disponibilidad por propietario | RNF-SEG-04 | RBAC (Control de acceso basado en roles) estricto | Fuga de información competitiva |
| RC-N04 | Gestión segura de autenticación y autorización | Hash resistente (Argon2id), tokens de corta duración | EC-SEG-01; RNF-SEG-01 | API Gateway / WAF | Acceso no autorizado |

#### 2.7 Restricciones éticas

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-ET01 | Recomendaciones de IA explicadas al usuario | 100% de recomendaciones con criterio explicativo | EC-IA-01; RF-IA-02 | Interfaz de IA devuelve justificación | Decisiones opacas |
| RC-ET02 | No favorecer sistemáticamente a un operador (Sin sesgo comercial) | Ponderaciones documentadas y auditables | EC-IA-02; RF-CAT-03 | Modelo algorítmico basado en reglas transparentes | Daño a pequeños operadores |
| RC-ET03 | Protección de la privacidad de turistas | Geolocalización y datos de uso solo con consentimiento | RD-04; RNF-SEG-03 | Minimización de datos recolectados | Vigilancia no consentida |
| RC-ET04 | Transparencia en el tratamiento de datos | Registro de accesos a datos personales | RNF-LOC-01; RF-USR-24 | Auditoría inmutable | Pérdida de legitimidad |

---

### 3. Tensiones entre restricciones

Las restricciones no son independientes; el análisis de trade-offs exige equilibrarlas (RC-ARQ05):

| # | Restricciones en tensión | Naturaleza del conflicto | Resolución propuesta en el Diseño |
|---|---|---|---|
| 1 | RC-T04 (Disponibilidad 99%) vs. RC-E01 (Costo) y RC-E04 (Tiempo) | Mayor disponibilidad exige redundancia (más costo y configuración) | Redundancia focalizada en el flujo crítico (Reservas y Catálogo). |
| 2 | RC-A01 (Redirigir a alternativas) vs. RC-ET02 (Sin sesgo comercial) | Redirigir turistas favorece económicamente a los operadores de esas zonas | El criterio de congestión se parametriza abiertamente y se explica al usuario (RC-ET01). |
| 3 | RC-T02 (Múltiples fuentes) vs. RC-N03 (Proteger información comercial) | Integrar fuentes externas eleva el riesgo de exposición cruzada de datos | Separación lógica multitenant en el esquema de base de datos. |
| 4 | RC-ARQ04 (Separación de componentes) vs. RC-E04 (Tiempo de 3 meses) | Una arquitectura de microservicios puros retrasa el desarrollo inicial | Se evaluará un Monolito Modular como punto de equilibrio entre separación y velocidad. |

---

### 4. Trazabilidad hacia Decisiones Arquitectónicas (ADRs)

| ADR candidato | Restricciones que lo condicionan directamente | Estado |
|---|---|---|
| ADR-01 Selección de Metodología | RC-E03, RC-E04 | Decidido (Scrum + ATAM-lite) |
| ADR-02 Estilo Arquitectónico | RC-ARQ04, RC-T04, RC-T05, RC-E03, RC-E04 | *En evaluación (Monolito modular vs Microservicios)* |
| ADR-03 Estrategia de Persistencia | RC-ARQ02, RC-E01, RC-E02 | *En diseño* |
| ADR-04 Comunicación e Integración | RC-ARQ03, RC-T02 | *En diseño* |
| ADR-05 Seguridad y Cumplimiento Normativo | RC-N01 a RC-N04, RC-ET03, RC-ET04 | *En diseño* |
| ADR-06 IA y Algoritmos Éticos | RC-ET01, RC-ET02, RC-A01 | *En diseño* |

> [!NOTE]
> Cada una de las restricciones aquí documentadas será evaluada sobre el prototipo final (60% implementado) utilizando la tabla de validación de diseño exigida en la sección "Validación del Diseño frente a Restricciones Definidas" de las instrucciones del proyecto.
