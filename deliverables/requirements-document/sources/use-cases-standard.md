# Investigación: Especificación de Casos de Uso bajo ISO/IEC/IEEE 29148:2018 y Diagramación con PlantUML

**Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta
**Documento de referencia cruzada:** `Fundamentacion-de-Decisiones.md`, `Objetivos.md`, `Restricciones.md`, `Descripcion-General.md`, `Diseño-de-Ingenieria.md`

---

## 1. Propósito y alcance

Este documento consolida la investigación necesaria para definir los **Casos de Uso** del proyecto, en coherencia con el rigor metodológico exigido en `Fundamentacion-de-Decisiones.md` (trazabilidad ADR, estándar ISO/IEC/IEEE 29148:2018, ausencia de decisiones empíricas). Cubre dos frentes:

1. **Fundamentación normativa** — qué exige ISO/IEC/IEEE 29148:2018 (y los marcos UML/RUP que lo complementan) respecto a la identificación, especificación, desarrollo y descripción de casos de uso.
2. **Herramienta de representación** — cómo modelar esos casos de uso como diagramas mediante PlantUML (`.puml`), incluyendo su sintaxis oficial y estándar UML.

El resultado es una **plantilla unificada** y una **guía de elección/priorización**, listas para aplicarse al documento de Casos de Uso del proyecto.

---

## 2. Fundamentación normativa: ISO/IEC/IEEE 29148:2018

### 2.1 Qué es y qué exige el estándar

ISO/IEC/IEEE 29148:2018 (*Systems and Software Engineering — Life Cycle Processes — Requirements Engineering*) es el estándar internacional vigente para ingeniería de requisitos a lo largo del ciclo de vida de sistemas y software. No es un estándar exclusivo de casos de uso, pero **define el marco dentro del cual los casos de uso se producen, documentan y verifican**. Se apoya en tres pilares:

- **Procesos de requisitos** (Cláusula 6): Análisis de Negocio/Misión, Definición de Necesidades y Requisitos de Stakeholders, y Definición de Requisitos del Sistema.
- **Elementos de información** (Cláusula 7): un conjunto de documentos tipificados — entre ellos **BRS** (Business Requirements Specification), **StRS** (Stakeholder Requirements Specification), **OpsCon** (Operational Concept), **SyRS** (System Requirements Specification) y **SRS** (Software Requirements Specification).
- **Criterios de calidad de requisitos** (Cláusula 5): 9 características para un requisito individual (no ambiguo, completo, singular, factible, verificable, correcto, conforme, no redundante, actualizado) y 5 para el conjunto de requisitos.

### 2.2 Dónde entran los casos de uso en el estándar

El estándar sitúa los casos de uso dentro del proceso de **Definición de Necesidades y Requisitos de Stakeholders** (cláusula 6.3.1). Sus resultados esperados incluyen identificar a los stakeholders del sistema y definir el contexto de uso de las capacidades (usuarios, tareas, entorno organizacional, técnico y físico); a partir de ahí se desarrollan **escenarios (casos de uso, historias de usuario, etc.)** para analizar el comportamiento operacional del sistema desde la perspectiva del usuario.

En este mismo nivel, el estándar da lugar al documento **OpsCon** (Concepto Operacional), heredero conceptual del ConOps (IEEE 1362). El OpsCon reúne precisamente los casos de uso, actores y escenarios operacionales que describen cómo los distintos tipos de usuario interactúan con el sistema en su contexto real, antes de derivar los requisitos formales del sistema (SyRS) y del software (SRS).

**Implicación para el proyecto:** los Casos de Uso de la plataforma turística deben:
- Derivarse directamente de los stakeholders ya identificados en el registro preliminar de 14 actores.
- Servir de puente trazable entre `Objetivos.md`/`Descripcion-General.md` (necesidades del contexto) y las decisiones arquitectónicas ya tomadas (Arquitectura A, monolito modular con IA y Notificaciones como microservicios).
- Expresarse de forma que sean **verificables** — cada caso de uso debe poder convertirse en un escenario de prueba concreto (alineado con el numeral "Diagramas de casos de uso" y "Especificación de requerimientos (ISO/IEC/IEEE 29148:2018)" exigidos en `Diseño-de-Ingenieria.md`).

### 2.3 Criterios de calidad aplicables a un caso de uso individual

Aunque el estándar formula estas características para "requisitos", son directamente aplicables a la redacción de cada caso de uso y a cada paso de su flujo:

| Característica ISO 29148 | Aplicación al caso de uso |
|---|---|
| No ambiguo | Un único actor y un único objetivo por caso de uso; lenguaje declarativo, no interpretativo. |
| Completo | Incluye flujo básico, alternos, excepciones, pre/postcondiciones — sin pasos implícitos. |
| Singular | Un caso de uso = una meta observable del actor (no mezclar "reservar" y "pagar" si son metas separables). |
| Factible | Realizable con la arquitectura y presupuesto ya definidos (restricción de USD 20.000 y 3 meses). |
| Verificable | Cada flujo puede convertirse en un caso de prueba o criterio de aceptación medible. |
| Correcto | Refleja fielmente la necesidad relevada del stakeholder, no una suposición del equipo. |
| Conforme | Sigue la estructura y terminología de la plantilla adoptada (ver sección 4). |
| No redundante | No se duplica funcionalidad ya cubierta por otro caso de uso (usar `include` para lo compartido). |
| Actualizado | Vinculado a la matriz de trazabilidad (RTM) y revisado ante cambios en restricciones u objetivos. |

### 2.4 Notación complementaria: UML y sus relaciones formales

ISO/IEC/IEEE 29148:2018 recomienda notaciones estandarizadas (UML) para el modelado de casos de uso, sin prescribir una sintaxis gráfica propia. El modelo UML de casos de uso —ampliamente adoptado en la práctica y coherente con RUP/Cockburn— define:

- **Actor:** rol externo (persona, sistema u organización) que interactúa con el sistema para lograr un objetivo. Puede ser **primario** (inicia el caso de uso) o **secundario/de soporte** (participa pero no lo inicia, p. ej. una pasarela de pago).
- **Asociación (comunicación):** vínculo entre actor y caso de uso.
- **Include (`«include»`):** el caso de uso base **siempre** incorpora el comportamiento del caso de uso incluido; se usa para factorizar funcionalidad común entre varios casos de uso (p. ej. "Autenticarse" incluido por "Reservar Actividad" y por "Gestionar Perfil de Operador").
- **Extend (`«extend»`):** el caso de uso de extensión añade comportamiento **opcional y condicional** al caso base, activado en un punto de extensión definido (p. ej. "Aplicar Recomendación de IA" extiende a "Consultar Atractivos" solo si el usuario acepta recomendaciones personalizadas).
- **Generalización:** una variante especializa a un caso de uso o actor más general (p. ej. "Operador Pequeño/Mediano" como especialización de "Prestador de Servicios Turísticos", coherente con la restricción social de inclusión de pequeños operadores).

Estas relaciones deben usarse con disciplina: **`include`** para eliminar duplicación (autenticación, notificación, registro de auditoría), **`extend`** para comportamiento opcional sin sobrecargar el flujo principal, y **generalización** para variantes de actor o de caso de uso sin duplicar especificaciones completas.

---

## 3. Plantilla unificada de Especificación de Caso de Uso

Síntesis de ISO/IEC/IEEE 29148:2018 (estructura de información y calidad de requisitos), UML/RUP (relaciones y flujo de eventos) y la plantilla clásica de Cockburn (adoptada ampliamente en la industria). Cada caso de uso del proyecto debe documentarse con estos campos:

| Campo | Descripción |
|---|---|
| **ID** | Identificador único (p. ej. `CU-01`), consistente con la RTM. |
| **Nombre** | Frase verbo-sustantivo (p. ej. "Reservar Actividad Turística"). |
| **Actor(es) primario(s)** | Quien inicia el caso de uso y persigue el objetivo. |
| **Actor(es) secundario(s)** | Sistemas o roles de soporte (pasarela de pago, servicio de IA, notificaciones). |
| **Descripción/Resumen** | 2-3 líneas del propósito del caso de uso. |
| **Prioridad** | Escala 1-5, alineada al 60% mínimo de casos de uso priorizados exigido en `Diseño-de-Ingenieria.md`. |
| **Disparador (Trigger)** | Evento que inicia el caso de uso. |
| **Precondiciones** | Estado del sistema que debe cumplirse antes de ejecutar el caso de uso. |
| **Postcondiciones (éxito)** | Estado resultante tras una ejecución exitosa. |
| **Flujo Básico (Main Success Scenario)** | Secuencia numerada de interacciones actor↔sistema en el camino feliz. |
| **Flujos Alternos** | Variantes válidas que no son error (p. ej. "3a. Usuario elige método de pago alterno"). |
| **Flujos de Excepción** | Manejo de errores y condiciones anómalas (p. ej. cupo agotado, fallo de pasarela de pago). |
| **Requisitos no funcionales asociados** | Atributos de calidad relevantes (disponibilidad ≥99%, tiempo de respuesta bajo alta concurrencia, explicabilidad de IA). |
| **Relaciones** | `include`/`extend`/generalización con otros casos de uso. |
| **Reglas de negocio / restricciones** | Ej.: cumplimiento Ley 1581 de 2012, no favorecimiento sistemático de un operador en recomendaciones de IA. |
| **Trazabilidad** | Referencia a objetivo específico y restricción de `Objetivos.md`/`Restricciones.md`. |

---

## 4. Guía de elección y priorización de Casos de Uso para el proyecto

Con base en `Descripcion-General.md`, `Objetivos.md` y `Restricciones.md`, los casos de uso deben agruparse por actor y priorizarse según impacto arquitectónico (coherente con la exigencia de "al menos un flujo completo crítico" del 60% de implementación mínima):

**Actores candidatos** (a validar contra el registro de 14 stakeholders ya elaborado):
- Turista/Visitante (actor primario)
- Prestador de Servicios Turísticos (operador pequeño/mediano — generalización de "Prestador")
- Administrador de la Plataforma
- Servicio de IA (actor secundario/sistema de soporte — recomendación, clasificación o predicción)
- Pasarela de Pago (Wompi/ePayco — actor secundario)
- Servicio de Notificaciones (SendGrid/SES — actor secundario)

**Casos de uso núcleo sugeridos** (candidatos al flujo crítico completo):
1. Consultar disponibilidad de servicios/actividades.
2. Reservar actividad turística (flujo crítico: inicio → procesamiento → persistencia → respuesta).
3. Registrar y gestionar oferta de un prestador de servicios.
4. Generar recomendación personalizada (extiende la consulta, usa el servicio de IA).
5. Consultar indicadores/reportes de demanda (actor: entidad/operador).
6. Autenticarse y gestionar perfil (caso `include` transversal).

---

## 5. Modelado y Diagramación de Casos de Uso con PlantUML

### 5.1 Adopción de PlantUML (puml)

PlantUML constituye el estándar adoptado en el proyecto para el modelado visual de casos de uso. A diferencia de librerías con soporte de versiones inconsistente o en fase experimental en visores Markdown estándar, PlantUML ofrece una implementación madura y exhaustiva del estándar UML (soportando paquetes, alias, jerarquías de generalización, estereotipos formales y personalización de estilos mediante `skinparam`), garantizando estabilidad, renderizado determinístico y amplia integración con herramientas de desarrollo y documentación.

### 5.2 Sintaxis base

```plantuml
@startuml
left to right direction

' --- ESTILOS VISUALES LÍMPIOS ---
skinparam shadowing false
skinparam DefaultFontName Helvetica

actor Turista
actor "Prestador Turístico" as Operador
actor Admin
actor "Servicio de IA" as IA

rectangle "Plataforma Turística Santa Marta" {
    usecase "Autenticarse" as Autenticar
    usecase "Consultar disponibilidad" as ConsultarDisponibilidad
    usecase "Reservar actividad" as Reservar
    usecase "Generar recomendación" as Recomendar
    usecase "Gestionar oferta turística" as GestionarOferta
}

Turista --> ConsultarDisponibilidad
Turista --> Reservar
Operador --> GestionarOferta
Admin --> GestionarOferta

Reservar ..> Autenticar : <<include>>
ConsultarDisponibilidad ..> Recomendar : <<extend>>
Recomendar --> IA
@enduml
```

### 5.3 Reglas de sintaxis y buenas prácticas en PlantUML

- **Delimitadores de bloque:** Apertura mediante `@startuml` (con identificador opcional) y cierre mediante `@enduml`. En documentos Markdown se encapsulan en bloques de código delimitados por ````plantuml`.
- **Dirección del layout:** Configuración `left to right direction` para disponer horizontalmente actores y frontera del sistema, optimizando la legibilidad en pantallas y documentos paginados.
- **Declaración explícita de actores:** Definición mediante `actor Nombre` o etiquetas extendidas con alias: `actor "Nombre Extendido" as Alias`.
- **Frontera del sistema y modularización:** Uso de `rectangle "Sistema" { ... }` para delimitar el alcance de la plataforma y `package "Módulo" { ... }` para estructurar funcionalmente los casos de uso internos.
- **Declaración de casos de uso:** Definición mediante `usecase "Descripción de la acción" as Alias`.
- **Relaciones formales UML:**
  - *Asociación simple:* `Actor --> CasoUso`
  - *Inclusión:* `CasoBase ..> CasoIncluido : <<include>>`
  - *Extensión:* `CasoBase ..> CasoExtendido : <<extend>>`
  - *Generalización / Especialización:* `SubActor -|> SuperActor` o `SubCaso -|> SuperCaso`
- **Estilos y consistencia visual (`skinparam`):** Se aplica `skinparam shadowing false` junto con paletas cromáticas diferenciadas por actor/rol para asegurar claridad visual y consistencia con los demás diagramas arquitectónicos del proyecto (DCA, arquetipos, componentes).

### 5.4 Recomendación de aplicación al proyecto

Para el documento de Casos de Uso del proyecto se recomienda:

1. **Diagramas modulares por actor primario:** Dado el volumen de casos de uso (34 casos de uso especificados), se definen tres diagramas dedicados (Turista, Prestador de Servicios Turísticos, Administrador) que aíslan sus subsistemas y evitan diagramas saturados.
2. **Reutilización y factores comunes:** Modelar `Autenticarse` como caso de uso transversal referenciado mediante relaciones `<<include>>` desde los flujos que exigen sesión activa.
3. **Compatibilidad y versionamiento:** El código fuente PlantUML se versiona directamente embebido en el archivo Markdown de requisitos (`use-cases.md`), permitiendo auditoría y control de cambios en Git sin depender de artefactos binarios externos.

---

## 6. Síntesis y trazabilidad

| Fuente | Aporta a los Casos de Uso |
|---|---|
| ISO/IEC/IEEE 29148:2018 | Ubicación formal de los casos de uso en el proceso de requisitos (OpsCon/StRS), criterios de calidad de cada especificación. |
| UML (include/extend/generalización) | Semántica de reutilización y variación entre casos de uso. |
| Plantilla RUP/Cockburn | Estructura textual completa (flujo básico, alternos, excepciones). |
| PlantUML (`.puml`) | Representación gráfica normalizada, modular y versionable en el repositorio de documentación del proyecto bajo notación estándar UML. |

Este documento queda listo para servir de base al desarrollo del **Documento de Casos de Uso** exigido en `Diseño-de-Ingenieria.md` ("Documento de Requerimientos" → "Diagramas de casos de USO" y "Especificación de requerimientos (ISO/IEC/IEEE 29148:2018)").