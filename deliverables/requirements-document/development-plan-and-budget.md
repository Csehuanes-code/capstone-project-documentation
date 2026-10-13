## Plan, Cronograma y Presupuesto de Desarrollo

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Metodología: Scrum + ATAM-lite](https://img.shields.io/badge/Metodolog%C3%ADa-Scrum_%2B_ATAM--lite-orange?style=flat-square)

> **Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta.

> [!NOTE]
> **Propósito de la sección:** en cumplimiento de `Diseño-de-Ingenieria.md` ("Condiciones de Desarrollo" y "Documento de Requerimientos"), esta sección selecciona y justifica el proceso de desarrollo, define actividades, artefactos, responsables nominales y mecanismos de revisión arquitectónica, y presenta el cronograma y el presupuesto de desarrollo para las 12 semanas del proyecto.

---

### 1. Selección y Justificación del Proceso de Desarrollo

#### 1.1 Proceso seleccionado

Se adopta un proceso **híbrido: Scrum adaptado + revisiones arquitectónicas ligeras tipo ATAM** (*Architecture Tradeoff Analysis Method*), estructurado en **seis (6) sprints de dos semanas** sobre un horizonte de 12 semanas.

| Criterio | Por qué se descarta la alternativa | Por qué se elige Scrum + ATAM-lite |
|---|---|---|
| Cascada pura (Waterfall) | Exige congelar requisitos antes de diseñar | Permite decidir la arquitectura de forma iterativa, con evidencia incremental |
| Scrum "puro" | Corre el riesgo de degradar el diseño en un "monolito desordenado" | Se añaden **revisiones ATAM-lite** al cierre de cada sprint |
| Kanban continuo | El curso exige cuatro documentos formales con fechas de entrega | Los sprints se alinean 1 a 1 con los documentos exigidos |

#### 1.2 Roles y responsabilidades sobre el proceso

En concordancia con las restricciones del proyecto y resolviendo la observación sobre la falta de asignación explícita del equipo, la distribución es la siguiente:


|---|---|---|
| **Líder técnico / Arquitecto** | [Carlos Sehuanes] | Facilita revisiones ATAM-lite; dueño de los ADR; resuelve bloqueos de diseño. |
| **Analista de requisitos** | [Luis Rincon] | Mantiene la trazabilidad Stakeholder ↔ Requisito ↔ Decisión ↔ Evidencia (RTM). |
| **Diseñador de datos** | [David Hasbum] | Propietario del modelo de datos (conceptual, lógico, persistencia). |
| **Desarrollador principal** | [Santiago Criollo] | Ejecuta el sprint backlog; estima el esfuerzo por historia; reporta avance. |
| **Responsable de validación** | [Julian Tobias] | Diseña escenarios de prueba de atributos de calidad; audita restricciones (QA). |

---

### 2. Actividades, Artefactos y Mecanismos de Revisión

| # | Actividad del proceso | Artefacto(s) producido(s) | Responsable principal | Mecanismo de revisión/validación |
|---|---|---|---|---|
| 1 | Elicitación y especificación de requisitos | `context.md`, `stakeholders.md`, `use-cases.md`, escenarios de calidad, análisis de restricciones | Analista de requisitos | Revisión cruzada por el Arquitecto + QA report interno |
| 2 | Investigación y comparación de arquitecturas | `architectural-proposals.md`, tabla comparativa ponderada, ADR de selección | Arquitecto | Sesión ATAM-lite |
| 3 | Diseño arquitectónico final | Modelo de datos, wireframes, diagramas, ADRs | Arquitecto + Diseñador de datos | Revisión de coherencia |
| 4 | Implementación del prototipo (núcleo) | Módulos Catálogo, Usuarios/Seguridad, Reservas/Disponibilidad | Desarrollador principal | Pull request review por el Arquitecto |
| 5 | Implementación del flujo crítico y componentes | Reserva end-to-end (CU-11), microservicios de IA y Notificaciones | Desarrollador principal + Arquitecto | Demo funcional en sprint review |
| 6 | Validación de atributos de calidad y restricciones | Resultados de escenarios medibles, tabla de validación de restricciones | Responsable de validación | Ejecución de los escenarios definidos; checklist de restricciones |
| 7 | Consolidación y sustentación | Documento Final, análisis comparativo | Todo el equipo | Sustentación ante el docente |

---

### 3. Cronograma (12 semanas / 6 sprints)

```plantuml
@startgantt
skinparam DefaultFontName Helvetica
Project starts at 2026-10-01
saturdays are closed
sundays are closed

-- Sprint 1: Requerimientos --
[Contexto y stakeholders] lasts 5 days
[Casos de uso] lasts 5 days
[Atributos de calidad y restricciones] lasts 5 days
[Contexto y stakeholders] -> [Casos de uso]
[Casos de uso] -> [Atributos de calidad y restricciones]

-- Sprint 2: Comparación y selección de arquitectura --
[Investigación de alternativas] lasts 5 days
[Tabla comparativa y trade-offs] lasts 5 days
[Investigación de alternativas] -> [Tabla comparativa y trade-offs]

-- Sprint 3-4: Diseño arquitectónico final --
[Modelo de datos] lasts 5 days
[Wireframes e interfaces] lasts 5 days
[Diagramas de paquetes y despliegue] lasts 5 days
[ADRs y revisión ATAM-lite] lasts 5 days
[Modelo de datos] -> [Wireframes e interfaces]
[Wireframes e interfaces] -> [Diagramas de paquetes y despliegue]
[Diagramas de paquetes y despliegue] -> [ADRs y revisión ATAM-lite]

-- Sprint 5: Implementación núcleo --
[Núcleo: Catálogo y Usuarios] lasts 5 days
[Núcleo: Disponibilidad y Reservas] lasts 5 days
[Núcleo: Catálogo y Usuarios] -> [Núcleo: Disponibilidad y Reservas]

-- Sprint 6: Flujo crítico, IA, Notificaciones y validación --
[Flujo crítico CU-11 end-to-end] lasts 4 days
[Microservicios IA y Notificaciones] lasts 4 days
[Validación de escenarios de calidad] lasts 3 days
[Documento final y sustentación] lasts 3 days
[Flujo crítico CU-11 end-to-end] -> [Microservicios IA y Notificaciones]
[Microservicios IA y Notificaciones] -> [Validación de escenarios de calidad]
[Validación de escenarios de calidad] -> [Documento final y sustentación]
@endgantt   
