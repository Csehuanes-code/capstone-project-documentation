# Fundamentación Estandarizada para la Identificación y Definición de Stakeholders
## Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta

Este documento consolida, bajo los criterios de rigor ingenieril exigidos en `Fundamentacion-de-Decisiones.md`, el marco normativo internacional aplicable a la identificación, clasificación, especificación y trazabilidad de stakeholders. Cada estándar se acompaña de su aplicación concreta al proyecto, de modo que este documento pueda incorporarse directamente a la sección "Identificación de stakeholders" del Documento de Requerimientos.

---

## 1. Base normativa central: ISO/IEC/IEEE 29148:2018

### 1.1 Definición formal de stakeholder

El estándar, heredando la definición de ISO/IEC/IEEE 15288:2015, define stakeholder como el individuo u organización que tiene un derecho, participación, reclamo o interés en un sistema o en que este posea características que satisfagan sus necesidades y expectativas. <cite index="13-1">La norma aclara que los stakeholders incluyen, entre otros, a usuarios finales, organizaciones usuarias finales, patrocinadores, desarrolladores, productores, entrenadores, mantenedores, quienes disponen del sistema, adquirentes, clientes, operadores, organizaciones proveedoras, acreditadores y organismos reguladores</cite>. Un mismo actor puede ejercer simultáneamente varios roles (por ejemplo, usuario y operador).

**Aplicación al proyecto:** ningún actor debe descartarse por "obvio" ni por estar fuera del software en sí (p. ej. un ente regulador ambiental o un organismo de protección de datos son stakeholders válidos aunque nunca usen la plataforma).

### 1.2 El proceso "Stakeholder Needs and Requirements Definition"

<cite index="8-1">Este proceso, definido en la cláusula 6.3.1 de IEEE 29148-2018 y ampliado desde ISO/IEC/IEEE 15288:2015, tiene como propósito definir los requisitos de los stakeholders para un sistema que provea las capacidades que necesitan los usuarios y demás interesados en un entorno definido</cite>. Sus resultados esperados (outcomes) son directamente aplicables como checklist de esta fase:

1. <cite index="8-1">Se identifican los stakeholders del sistema — el proceso debe explorar activamente nuevos stakeholders potenciales, no limitarse a los ya conocidos de fases previas</cite>.
2. <cite index="8-1">Se definen las características requeridas y el contexto de uso de las capacidades, incluyendo las características de los usuarios, las tareas y el entorno organizacional, técnico y físico</cite>.
3. <cite index="8-1">Se establece la trazabilidad de los requisitos de los stakeholders hacia los propios stakeholders y sus necesidades, y se vincula con los requisitos de negocio o misión</cite>.
4. Posteriormente, en la definición de requisitos de sistema, <cite index="8-1">se transforma la vista orientada al usuario en una vista técnica de solución, definiendo las características y requisitos funcionales y de desempeño desde la perspectiva del proveedor, evitando implicar una implementación específica salvo que una restricción de nivel superior lo exija</cite>.

**Aplicación al proyecto:** el ejercicio de identificación de stakeholders no puede ser un listado estático hecho una sola vez; debe repetirse como actividad iterativa dentro del proceso de diseño que el equipo debe justificar (ver `Diseño-de-Ingenieria.md`, "Condiciones de Desarrollo"), y cada stakeholder identificado debe quedar enlazado a al menos un requisito trazable.

### 1.3 Documentos normativos asociados

<cite index="9-1">El estándar define plantillas documentales predefinidas, entre ellas la Stakeholder Requirements Specification (StRS), que describe los requisitos de los stakeholders; la System Requirements Specification (SyRS); la Software Requirements Specification (SRS); y el System Operational Concept (OpsCon), que describe las necesidades de los stakeholders</cite>. <cite index="12-1">El estándar especifica también elementos de contenido obligatorio (identificación, portada, definiciones, referencias, acrónimos) y guía sobre estructura y presentación del contenido, cubriendo fundamentos como roles de stakeholder, transformación de necesidades en requisitos, atributos de requisitos individuales y de conjuntos de requisitos, y criterios de lenguaje y claridad</cite>.

**Aplicación al proyecto:** se recomienda que el equipo produzca formalmente un **StRS** (Stakeholder Requirements Specification) como documento previo y diferenciado del SRS, dado que el proyecto exige explícitamente casos de uso, atributos de calidad como escenarios medibles y trazabilidad de restricciones — todos elementos propios del StRS bajo 29148.

---

## 2. TOGAF / The Open Group — Gestión y priorización de stakeholders

TOGAF aporta la técnica que falta en 29148: **cómo priorizar y gestionar** a los stakeholders ya identificados, no solo cómo especificarlos.

### 2.1 Identificación amplia

<cite index="16-1">La primera tarea es hacer una lluvia de ideas sobre quiénes son los principales stakeholders de la arquitectura, considerando a todas las personas afectadas por ella, que tienen influencia o poder sobre ella, o que tienen interés en su éxito o fracaso; esto puede incluir altos ejecutivos, roles de la organización del proyecto, roles de la organización cliente, desarrolladores del sistema, socios de alianza, proveedores, operaciones de TI y clientes</cite>.

### 2.2 Matriz Poder / Interés

<cite index="16-1">Los stakeholders identificados pueden ubicarse en una matriz de poder/interés, la cual indica además la estrategia de involucramiento a adoptar con cada uno</cite>. Las cuatro estrategias resultantes son:

- <cite index="21-1">Alto poder, alto interés: gestionar de cerca, mediante registros de incidencias y cambios, y reuniones de estado</cite>.
- <cite index="21-1">Alto poder, bajo interés: mantener satisfecho, mediante comité directivo o actualizaciones a junta directiva</cite>.
- <cite index="21-1">Bajo poder, alto interés: mantener informado, mediante actualizaciones directas, en video o por correo</cite>.
- <cite index="21-1">Bajo poder, bajo interés: monitorear, mediante correos o informes de estado</cite>.

### 2.3 Concerns, viewpoints y views

<cite index="16-1">Para cada stakeholder se deben identificar los catálogos, matrices y diagramas que el ejercicio de arquitectura debe producir y validar con él</cite>. Esto conecta directamente el registro de stakeholders con los artefactos de diseño exigidos en `Diseño-de-Ingenieria.md` (diagrama de paquetes, diagrama de despliegue, wireframes).

**Aplicación al proyecto — Matriz Poder/Interés propuesta:**

| Cuadrante | Stakeholders del proyecto |
|---|---|
| Alto poder / Alto interés (gestionar de cerca) | Docente evaluador, Líder técnico/Arquitecto del equipo, entidad de turismo local (si se simula como patrocinador) |
| Alto poder / Bajo interés (mantener satisfecho) | Autoridad ambiental / entidad reguladora (Ley 1581, capacidad de carga), MinTIC como referente normativo |
| Bajo poder / Alto interés (mantener informado) | Turistas, pequeños y medianos prestadores de servicios |
| Bajo poder / Bajo interés (monitorear) | Redes sociales / portales externos integrados como fuentes de datos |

---

## 3. IIBA / BABOK — Técnicas de análisis y clasificación de stakeholders

### 3.1 Definición amplia de stakeholder para efectos de análisis

<cite index="30-1">Un stakeholder es un individuo o grupo con el que un analista de negocio interactúa directa o indirectamente</cite>, más amplio que la noción de "usuario del sistema".

### 3.2 Técnicas formales (10.43 Stakeholder List, Map, or Personas)

<cite index="26-1">Las listas, mapas y personas de stakeholders ayudan al analista a comprender a los interesados y sus características, asegurando que se identifiquen todas las posibles fuentes de requisitos</cite>. Las técnicas específicas son:

- **Matriz de stakeholders**: <cite index="26-1">mapea el nivel de influencia del stakeholder contra su nivel de interés</cite> (equivalente operativo a la matriz poder/interés de TOGAF).
- **Diagrama de cebolla (Onion Diagram)**: <cite index="26-1">indica qué tan involucrados están los stakeholders con la solución</cite>, organizándolos en capas concéntricas de cercanía. Sus capas, según el modelo popularizado por Alexander/Robertson y adoptado por IIBA, son:
  - <cite index="31-1">Círculo central: el producto/servicio/sistema mismo y el equipo de proyecto directamente involucrado en crearlo (capa "Solution Delivery")</cite>.
  - <cite index="31-1">Área de negocio impactada: individuos o grupos que trabajan directamente con el sistema una vez entregado — usuarios finales, mesa de ayuda, equipos de mantenimiento, roles cuyo trabajo cambia con la solución (capa "Affected Organizational Unit")</cite>.
  - <cite index="31-1">Organización anfitriona: stakeholders que se benefician del desarrollo aunque no estén en el área operativa directa — patrocinadores, ejecutivos, expertos de dominio (capa "Organization/Enterprise")</cite>.
  - Una capa externa adicional cubre entidades reguladoras, sistemas externos con los que se interfaz, y el entorno amplio.
- **Matriz RACI**: <cite index="28-1">clasifica al stakeholder según cuatro tipos de responsabilidad sobre la iniciativa: Responsable, Aprobador (Accountable), Consultado e Informado</cite>.
- **Personas**: <cite index="26-1">un personaje ficticio narrado en primera persona que representa a un grupo de stakeholders y ayuda a que sus necesidades se perciban como reales para quienes diseñan la solución</cite>, e <cite index="26-1">identifica a las personas específicas que deben involucrarse en las actividades de elicitación de requisitos</cite>.

**Aplicación al proyecto — Diagrama de cebolla propuesto:**

- **Núcleo (equipo de solución):** los cinco roles del equipo (Líder técnico/Arquitecto, Analista de requisitos, Diseñador de datos, Desarrollador principal, Responsable de calidad).
- **Unidad organizacional afectada:** turistas (usuarios finales), pequeños y medianos operadores turísticos, administradores de contenido/atractivos, soporte técnico de la plataforma.
- **Organización/empresa anfitriona:** entidad gestora del destino turístico (simulada), patrocinadores académicos, docente evaluador.
- **Entorno externo:** MinTIC (normativa de arquitectura empresarial), Superintendencia de Industria y Comercio (Ley 1581 de 2012), autoridad ambiental (Parque Tayrona/Sierra Nevada), proveedores de servicios cloud, sistemas externos de reserva/pago que se integran.

---

## 4. NIST SP 800-160 — Stakeholders desde la perspectiva de seguridad y protección de activos

<cite index="65-1">El objetivo es abordar los problemas de seguridad desde la perspectiva de las necesidades de protección, preocupaciones y requisitos de los stakeholders, usando procesos de ingeniería establecidos para asegurar que dichas necesidades se aborden con el rigor apropiado, de manera temprana</cite>. <cite index="67-1">La ingeniería de seguridad de sistemas se centra en la protección de los activos del stakeholder y del sistema, con el fin de controlar la pérdida de activos y sus consecuencias asociadas</cite>, mediante la eliminación o reducción de vulnerabilidades. <cite index="66-1">Comprender las necesidades de protección de activos de los stakeholders —incluyendo activos que poseen y activos que no poseen pero deben proteger— y expresarlas mediante requisitos de seguridad bien definidos es una inversión en el éxito de la misión de la organización</cite>.

**Aplicación al proyecto:** para cada stakeholder identificado se debe documentar explícitamente qué "activo" protege o le preocupa proteger, no solo qué funcionalidad requiere. Ejemplos directos para este proyecto:

- **Turista**: activo = sus datos personales y de geolocalización (relevante para Ley 1581 de 2012).
- **Pequeño operador turístico**: activo = su información comercial (tarifas, disponibilidad, reputación) — restricción ética ya identificada en `Restricciones.md` sobre no favorecer sistemáticamente a un operador.
- **Administrador de la plataforma**: activo = la integridad y disponibilidad del sistema durante temporada alta (99% de disponibilidad exigido).
- **Entidad reguladora**: activo = cumplimiento normativo y trazabilidad de auditoría.

---

## 5. W3C — Stakeholders con necesidades de accesibilidad

<cite index="73-1">Las Web Content Accessibility Guidelines (WCAG), desarrolladas por la Web Accessibility Initiative del W3C, son el estándar internacional de referencia para el diseño de sitios y aplicaciones accesibles a personas con una amplia gama de discapacidades</cite>. <cite index="77-1">Cubren discapacidades visuales, auditivas, físicas, del habla, cognitivas, de lenguaje, de aprendizaje y neurológicas, y también mejoran habitualmente la usabilidad para el conjunto de usuarios, incluidos adultos mayores con capacidades cambiantes</cite>. Los criterios de conformidad se organizan en niveles de prioridad (A, AA, AAA).

**Aplicación al proyecto:** esto formaliza técnicamente la restricción social ya definida en `Restricciones.md` ("Accesibilidad para personas con discapacidad", "Interfaces accesibles para usuarios con distintos niveles de alfabetización digital"). Se recomienda declarar explícitamente el **nivel de conformidad WCAG objetivo (mínimo AA)** como atributo de calidad medible y como criterio de aceptación en la validación de interfaces, no solo como intención declarativa.

---

## 6. MinTIC Colombia — Marco de Arquitectura Empresarial del Estado (MAE)

<cite index="54-1">Los sistemas de información deben tener la capacidad de responder a las necesidades de información de los diferentes actores interesados, ser escalables, interoperables y cumplir con los lineamientos del modelo de seguridad y privacidad de la información y el Marco de Referencia de Arquitectura TI</cite>. <cite index="58-1">La Arquitectura de Sistemas de Información identifica las necesidades a partir de los requerimientos que surgen de la Arquitectura Institucional y de la Arquitectura de Información, considerando a los actores que interactúan con el sistema, los subsistemas y componentes candidatos, sus relaciones, atributos, integraciones y las intervenciones requeridas (crear, evolucionar, integrar, eliminar)</cite>. <cite index="60-1">Se recomienda comprender los actores y grupos de interés con los que se intercambia información y los flujos correspondientes, analizando las intervenciones que requieren los sistemas de información para garantizar que evolucionen alineados con la estrategia de la entidad</cite>.

**Aplicación al proyecto:** aunque el proyecto es un prototipo académico y no una entidad pública sujeta al MAE, este marco es la referencia local pertinente porque:
1. Usa terminología directamente aplicable ("actores y grupos de interés", no solo "usuarios").
2. Vincula explícitamente la identificación de actores con la interoperabilidad y la evolución sin romper el núcleo del sistema — exactamente lo exigido en `Descripcion-General.md` ("facilitar la evolución e incorporación futura de nuevos servicios, operadores y fuentes de información sin requerir modificaciones significativas en el núcleo").
3. Aporta legitimidad metodológica si el proyecto se presenta como un piloto con vocación de adopción por un actor público/mixto de turismo.

---

## 7. Modelo C4 — Los stakeholders como elemento formal del Diagrama de Contexto

<cite index="42-1">El nivel de Contexto del modelo C4 muestra el panorama general: el sistema y todo lo que lo rodea. Sus elementos son personas (usuarios, roles) y otros sistemas con los que el software interactúa, con el propósito de ilustrar quién usa el sistema y cómo encaja en el entorno más amplio; su audiencia es todo el mundo, desde stakeholders de negocio hasta desarrolladores</cite>. <cite index="39-1">Estos niveles ayudan a comunicar ideas abstractas de forma visual y desde distintos puntos de vista, de modo que gerentes, ejecutivos y otros stakeholders clave —que no necesariamente quieren ver un diagrama técnico detallado del código— puedan entender la arquitectura</cite>.

**Aplicación al proyecto:** el **Diagrama de Contexto (Nivel 1 de C4)** debe construirse tomando como insumo directo el registro de stakeholders, y no al revés. Cada persona/rol externo identificado en el StRS (turista, operador, administrador) y cada sistema externo (pasarela de pagos, servicio de mapas, redes sociales integradas, motor de recomendación de IA) debe aparecer como un elemento explícito en ese diagrama, sirviendo como puente entre el análisis de requisitos (29148) y el diseño arquitectónico exigido en `Diseño-de-Ingenieria.md`.

---

## 8. ADR (Architecture Decision Records) — Trazabilidad de decisiones hacia los stakeholders

<cite index="45-1">Las decisiones arquitectónicas deben estar orientadas por el negocio; para demostrar responsabilidad (accountability), es necesario mapear explícitamente las decisiones hacia los objetivos o requisitos, aunque en la práctica resulta más conveniente referenciar una matriz de trazabilidad que enumerar los requisitos relacionados directamente en cada ADR</cite>. <cite index="45-1">Cada decisión arquitectónica puede evaluarse según su contribución a cada requisito, y si una decisión no contribuye a satisfacer ningún requisito, no debería tomarse</cite>.

**Aplicación al proyecto:** cada ADR del proyecto (selección de estilo arquitectónico, tipo de base de datos, estrategia de comunicación, etc., exigidos en `Diseño-de-Ingenieria.md`) debe incluir un campo **"Stakeholders impactados"** explícito, además del campo de requisitos relacionados, cerrando así la cadena exigida en `Fundamentacion-de-Decisiones.md`: *Necesidades del Contexto → Requisitos y Restricciones → Decisiones Arquitectónicas → Evidencia en la Implementación*.

---

## 9. Matriz de Trazabilidad de Requisitos (RTM) — Instrumento de cierre del ciclo

<cite index="46-1">Una Matriz de Trazabilidad de Requisitos (RTM) es un documento que mapea y traza los requisitos del usuario con los casos de prueba correspondientes</cite>, y <cite index="46-1">típicamente incluye el identificador del requisito, su descripción, su fuente, los casos de prueba asociados y su estado</cite>. <cite index="53-1">Es más útil cuando un proyecto tiene muchos stakeholders, alcance cambiante, entregas entre distintos equipos, evidencia regulatoria o riesgo de implementación</cite> — exactamente el perfil de este proyecto. <cite index="47-1">Existen tres tipos de trazabilidad: hacia adelante (conecta requisitos con entregables), hacia atrás (traza entregables de vuelta a los requisitos) y bidireccional (cubre ambas direcciones)</cite>.

**Aplicación al proyecto:** se recomienda extender la columna "Fuente" de la RTM para que apunte directamente al **stakeholder** que originó cada requisito (no solo a "el documento de requisitos" en general), habilitando así **trazabilidad bidireccional Stakeholder ↔ Requisito ↔ Decisión Arquitectónica (ADR) ↔ Evidencia de Implementación**, que es precisamente la tabla de validación de restricciones que exige `Diseño-de-Ingenieria.md`.

---

## 10. Síntesis: plantilla integrada para especificar cada stakeholder

Combinando los ocho marcos anteriores, cada stakeholder del proyecto debe documentarse con esta ficha mínima:

| Campo | Fuente normativa |
|---|---|
| ID y nombre del stakeholder | ISO 29148 (StRS) |
| Categoría/rol (usuario final, operador, adquirente, regulador, etc.) | ISO 29148 §3.1.28 |
| Capa del diagrama de cebolla (núcleo / unidad afectada / organización / entorno) | IIBA BABOK 10.43 |
| Cuadrante poder/interés y estrategia de involucramiento | TOGAF ADM Fase A |
| Necesidades, preocupaciones y contexto de uso | ISO 29148 §6.3.1 |
| Activo que protege o le preocupa proteger | NIST SP 800-160 |
| Requisitos derivados (funcionales y de calidad, como escenarios medibles) | ISO 29148 / `Objetivos.md` |
| Requisitos de accesibilidad/inclusión aplicables (si corresponde) | W3C WCAG |
| Rol RACI frente a las decisiones del proyecto | IIBA BABOK |
| Elemento correspondiente en el Diagrama de Contexto (persona o sistema externo) | Modelo C4 |
| ADR(s) que lo impactan | ADR |
| Fila(s) correspondientes en la RTM | RTM |

### Registro preliminar de stakeholders propuesto para el proyecto

| Stakeholder | Categoría (ISO 29148) | Capa (Onion) | Poder/Interés (TOGAF) |
|---|---|---|---|
| Turista nacional/internacional | Usuario final | Unidad afectada | Bajo/Alto — mantener informado |
| Pequeño/mediano prestador turístico | Usuario final / cliente | Unidad afectada | Bajo/Alto — mantener informado |
| Hotel, restaurante u operador establecido | Usuario final / cliente | Unidad afectada | Medio/Alto |
| Administrador de la plataforma | Operador | Núcleo | Alto/Alto — gestionar de cerca |
| Equipo de desarrollo (5 roles) | Desarrollador | Núcleo | Alto/Alto — gestionar de cerca |
| Docente evaluador / comité académico | Acreedor/patrocinador (adquirente) | Organización | Alto/Alto — gestionar de cerca |
| Entidad de gestión del destino turístico (simulada) | Adquirente/patrocinador | Organización | Alto/Medio — mantener satisfecho |
| Autoridad ambiental (Tayrona/Sierra Nevada) | Organismo regulador | Entorno externo | Alto/Bajo — mantener satisfecho |
| Autoridad de protección de datos (Ley 1581) | Organismo regulador/acreditador | Entorno externo | Alto/Bajo — mantener satisfecho |
| MinTIC (referente MAE, no obligante) | Organismo normativo | Entorno externo | Bajo/Bajo — monitorear |
| Proveedor cloud / infraestructura | Organización proveedora | Entorno externo | Medio/Bajo |
| Servicio externo de pagos/reservas | Sistema externo (no humano) | Entorno externo | Medio/Medio |
| Servicio de IA de recomendación (interno, componente desacoplado) | Componente del sistema | Núcleo | N/A — se documenta como elemento del Diagrama de Contexto C4 |
| Usuarios con discapacidad o baja alfabetización digital | Usuario final (transversal) | Unidad afectada | Bajo/Alto — mantener informado |

Esta tabla es un punto de partida: cada fila debe ampliarse con las columnas completas de la sección 10 antes de incorporarse al Documento de Requerimientos, y debe validarse mediante al menos una ronda de elicitación (entrevista, encuesta o taller) por cada categoría, tal como recomienda BABOK para la técnica de personas.

---

## Referencias consultadas

- ISO/IEC/IEEE 29148:2018 — Systems and software engineering — Life cycle processes — Requirements engineering.
- The Open Group, *TOGAF Standard* — Stakeholder Management (ADM Techniques, Fase A).
- IIBA, *BABOK Guide v3* — 2.4 Stakeholders; 10.43 Stakeholder List, Map, or Personas.
- NIST SP 800-160 Vol. 1 — Engineering Trustworthy Secure Systems.
- W3C — Web Content Accessibility Guidelines (WCAG) 2.1/3.0.
- MinTIC Colombia — Modelo de Arquitectura Empresarial (MAE), dominio Sistemas de Información.
- C4 Model (Simon Brown) — Nivel 1: Diagrama de Contexto.
- Architecture Decision Records (ADR) — plantilla Tyree & Akerman.
- Requirements Traceability Matrix (RTM) — prácticas de trazabilidad forward/backward/bidireccional.
