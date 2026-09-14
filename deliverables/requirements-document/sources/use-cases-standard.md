# Investigación: Especificación de Casos de Uso bajo ISO/IEC/IEEE 29148:2018 y Diagramación con Mermaid

**Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta
**Documento de referencia cruzada:** `Fundamentacion-de-Decisiones.md`, `Objetivos.md`, `Restricciones.md`, `Descripcion-General.md`, `Diseño-de-Ingenieria.md`

---

## 1. Propósito y alcance

Este documento consolida la investigación necesaria para definir los **Casos de Uso** del proyecto, en coherencia con el rigor metodológico exigido en `Fundamentacion-de-Decisiones.md` (trazabilidad ADR, estándar ISO/IEC/IEEE 29148:2018, ausencia de decisiones empíricas). Cubre dos frentes:

1. **Fundamentación normativa** — qué exige ISO/IEC/IEEE 29148:2018 (y los marcos UML/RUP que lo complementan) respecto a la identificación, especificación, desarrollo y descripción de casos de uso.
2. **Herramienta de representación** — cómo modelar esos casos de uso como diagramas mediante Mermaid (`usecase-beta`), incluyendo su sintaxis oficial vigente.

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

## 5. Investigación: Diagramas de Casos de Uso con Mermaid

### 5.1 Estado del soporte oficial

Mermaid incorporó un tipo de diagrama nativo de **Use Case Diagram** a partir de la versión **12.0.0**, bajo la palabra clave `usecase-beta` (aún en beta). Antes de esa versión, el tipo no existía de forma nativa (existía una solicitud abierta en el repositorio oficial desde 2023), por lo que cualquier proyecto que use una versión anterior de Mermaid deberá actualizar la librería o simular el diagrama con `flowchart`.

### 5.2 Sintaxis base

```mermaid
usecase-beta
    direction LR

    actor Turista
    actor Operador
    actor Admin
    actor IA(("Servicio de IA"))

    systemBoundary Plataforma["Plataforma Turística Santa Marta"]
        ConsultarDisponibilidad(Consultar disponibilidad)
        Reservar[Reservar actividad]
        Autenticar(Autenticarse)
        Recomendar(Generar recomendación)
        GestionarOferta[Gestionar oferta turística]
    end

    Turista --> ConsultarDisponibilidad
    Turista --> Reservar
    Operador --> GestionarOferta
    Admin --> GestionarOferta

    Reservar ..> Autenticar : include
    ConsultarDisponibilidad ..> Recomendar : extend
    Recomendar --> IA
```

### 5.3 Reglas de sintaxis clave (documentación oficial mermaid.js.org)

- **Palabra clave de inicio:** `usecase-beta`. Cada sentencia debe ir en su propia línea física.
- **Dirección del layout:** `direction` con `TD`, `TB`, `BT`, `LR` o `RL`.
- **Identificadores:** actores, casos de uso, boundaries y nodos comparten un espacio de nombres único, con patrón `[A-Za-z0-9_]+` (pueden iniciar con dígito).
- **Forma de los casos de uso:** paréntesis `( )` para elipse (forma clásica UML), corchetes `[ ]` para rectángulo. Un endpoint de relación sin declaración explícita se interpreta automáticamente como caso de uso elíptico; en cambio, **los actores siempre requieren una declaración explícita** `actor ID`, nunca se infieren por posición.
- **Etiquetas con identificador propio:** `Login("Sign in")` asigna el identificador estable `Login` con etiqueta visible "Sign in". Una declaración entre comillas sin identificador (p. ej. `"Reset password"`) genera un identificador determinístico reemplazando caracteres no alfanuméricos por `_`.
- **Variantes de actor:** además del actor "palito" estándar, se admite `type: hollow`, `type: awesome` o `icon: <nombre>` (requiere registrar el paquete de íconos).
- **Elementos de negocio y estereotipos:** `business: true` agrega la barra diagonal convencional UML a actores u óvalos de caso de uso; un estereotipo `<<...>>` puede colocarse antes de una clase `:::`.
- **Fronteras del sistema (`systemBoundary`):** agrupan actores y casos de uso bajo un límite visual con título opcional; son de un solo nivel (no anidables) y solo pueden contener actores/casos de uso.
- **Relaciones — asociaciones simples:** siete operadores de asociación sólida disponibles (flechas con distintos marcadores); pueden llevar etiqueta, y una etiqueta que contenga literalmente la palabra "include" o "extend" **no** activa semántica UML — sigue siendo una asociación ordinaria.
- **Relaciones UML explícitas:** para semántica formal deben usarse operadores dedicados: **include** y **extend** requieren que ambos extremos sean casos de uso; **generalización** requiere que ambos extremos sean del mismo tipo (dos actores o dos casos de uso), apuntando del elemento especializado al general.
- **Notas:** se adjuntan a un único actor o caso de uso mediante una línea punteada; no pueden apuntar a boundaries, tablas JSON u otras notas.
- **Tablas JSON embebidas:** permiten anexar metadatos tabulares (p. ej. atributos de un caso de uso) directamente en el diagrama.
- **Estilos:** `classDef`, `class`, `style` y el sufijo `:::` permiten personalizar colores; existen variables de tema específicas (`usecaseActorBkg`, `usecaseBkg`, `usecaseIncludeLine`, `usecaseExtendLine`, entre otras).
- **Tema y layout por defecto:** desde 12.0.0 el diagrama usa el tema `redux-color`, el estilo `neo` y el motor de layout **ELK** (no Dagre) por defecto; ambos son configurables.
- **Migración desde PlantUML:** Mermaid no soporta separadores con título, alias `as`, bloques `skinparam`, `<style>`, `allowmixing`, hints de dirección (`left`/`right`/`up`/`down`), ni notas independientes o multi-destino — estos elementos generan error de parseo y deben reescribirse con la sintaxis nativa descrita arriba.

### 5.4 Recomendación de aplicación al proyecto

Para el documento de Casos de Uso se recomienda:

1. Un **diagrama general** (`usecase-beta`, `direction LR`) con todos los actores y los casos de uso núcleo agrupados en un `systemBoundary` único ("Plataforma Turística Santa Marta"), mostrando las relaciones `include`/`extend` principales (autenticación incluida, recomendación de IA como extensión).
2. **Diagramas específicos por subsistema** (opcional) si el número de casos de uso crece — p. ej. un boundary para "Gestión de Reservas" y otro para "Módulo de IA" — evitando saturar un único diagrama.
3. Verificar la versión de Mermaid usada por el visor/editor del equipo (Markdown renderer, VS Code, GitHub, etc.), dado que `usecase-beta` requiere **Mermaid ≥ 12.0.0**; de no estar disponible, usar el diagrama como especificación textual (Sección 4) mientras se actualiza la herramienta.

---

## 6. Síntesis y trazabilidad

| Fuente | Aporta a los Casos de Uso |
|---|---|
| ISO/IEC/IEEE 29148:2018 | Ubicación formal de los casos de uso en el proceso de requisitos (OpsCon/StRS), criterios de calidad de cada especificación. |
| UML (include/extend/generalización) | Semántica de reutilización y variación entre casos de uso. |
| Plantilla RUP/Cockburn | Estructura textual completa (flujo básico, alternos, excepciones). |
| Mermaid `usecase-beta` (≥12.0.0) | Representación gráfica normalizada y versionable en el mismo repositorio de documentación Markdown del proyecto. |

Este documento queda listo para servir de base al desarrollo del **Documento de Casos de Uso** exigido en `Diseño-de-Ingenieria.md` ("Documento de Requerimientos" → "Diagramas de casos de USO" y "Especificación de requerimientos (ISO/IEC/IEEE 29148:2018)").