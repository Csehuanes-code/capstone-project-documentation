# Propuestas Arquitectónicas — Plataforma Digital de Turismo Santa Marta

## 0. Nota metodológica

Este documento sintetiza investigación reciente (2025–2026) sobre estilos arquitectónicos, patrones de integración de IA, persistencia políglota y arquitecturas orientadas a eventos, y la cruza con las restricciones ya definidas del proyecto: equipo de 5 personas, 3 meses, presupuesto de USD 20.000 para infraestructura piloto, disponibilidad ≥99%, alta concurrencia estacional, multilenguaje, IA explicable y Ley 1581 de 2012. Estructura: (1) contexto de la industria, (2) opciones arquitectónicas con una **principal** y variantes/subcategorías, (3) dos alternativas adicionales obligatorias por la guía, (4) tabla comparativa ponderada, (5) recomendación justificada con trade-offs.

---

## 1. Contexto: qué dice la evidencia reciente

**Microservicios vs. monolito modular.** La tendencia de la industria en 2025–2026 se ha movido hacia la cautela frente a microservicios completos para equipos pequeños. Un análisis reciente reporta que <cite index="8-1">alrededor del 42% de las organizaciones que adoptaron microservicios han consolidado al menos parte de esos servicios de vuelta en unidades más grandes, principalmente por complejidad de depuración, sobrecarga operativa y latencia de red</cite>. Otro análisis de costos totales estima que <cite index="11-1">un monolito modular cuesta entre 1.100 y 2.300 USD/mes frente a 4.200–8.500 USD/mes de un esquema de 10-15 microservicios equivalente, sin contar el personal adicional de plataforma que suelen requerir estos últimos</cite>. La recomendación consolidada para productos nuevos es <cite index="9-1">comenzar con un monolito modular y migrar a microservicios solo cuando el número de equipos y la necesidad de escalar de forma desigual lo justifiquen</cite>, especialmente en equipos por debajo de cierto tamaño <cite index="13-1">(bajo 15-20 desarrolladores, el monolito modular suele ser la estrategia más rápida, económica y con menor sobrecarga cognitiva)</cite>.

**IA como servicio desacoplado.** Cuando la IA no es el núcleo del sistema, el patrón dominante es tratarla como un servicio de dominio independiente conectado por contratos claros. La literatura describe sistemas donde <cite index="15-1">servicios específicos de dominio (modelo de recomendación, búsqueda, perfil de usuario) se conectan mediante servicios de infraestructura como orquestador de flujos, monitoreo y registro de modelos, comunicándose vía REST/gRPC</cite>, y recomienda <cite index="17-1">incrustar los modelos como microservicios con contratos claros, monitoreo, mecanismos de respaldo (fallback) y auditabilidad</cite>, lo que encaja directamente con el requisito ético de explicabilidad del proyecto.

**Concurrencia y reservas.** Para los flujos de disponibilidad/reserva, el patrón recomendado ante fallas parciales es el **saga**: <cite index="20-1">en sistemas de reserva distribuidos no es posible envolver todo en una única transacción ACID cuando cada servicio (precios, inventario, pagos, notificaciones) tiene su propia base de datos, por lo que el patrón saga descompone la transacción en pasos locales que publican eventos, con transacciones compensatorias si algo falla</cite>. La elección entre orquestación y coreografía es central: <cite index="27-1">la coreografía da bajo acoplamiento pero dificulta visualizar y depurar el flujo de negocio, mientras que un enfoque orquestado permite inspeccionar el estado del saga en cualquier momento, forzar el orden y centralizar la compensación</cite>. Para un equipo pequeño y un plazo de 3 meses, **orquestación simple** es más manejable que coreografía pura.

**Persistencia políglota.** No es gratuita: <cite index="30-1">la decisión de tecnología de persistencia debe derivarse de los requisitos del dominio y no de la familiaridad del equipo o el camino de menor resistencia</cite>, y la recomendación práctica para equipos pequeños es <cite index="34-1">empezar con bases de datos de propósito general e introducir motores especializados solo cuando sea realmente necesario</cite>, apoyándose en patrones como saga y composición de API para no perder consistencia funcional.

---

## 2. Propuesta Principal (la solicitada): Microservicios ligeros orientados a dominio con IA desacoplada

### 2.1 Idea general

Un **API Gateway** único como puerta de entrada (auth, rate limiting, enrutamiento) frente a un conjunto **reducido y deliberado** de microservicios de dominio — no 15-20 servicios, sino entre 5 y 7, que es lo que un equipo de 5 personas puede operar con calidad en 3 meses:

| Módulo/microservicio | Responsabilidad | Persistencia sugerida |
|---|---|---|
| **Catálogo** | Atractivos, actividades, eventos, prestadores | Documental (MongoDB) — esquema variable por tipo de atractivo |
| **Disponibilidad y Reservas** | Consulta y gestión de disponibilidad, orquestación de saga de reserva | Relacional (PostgreSQL) — consistencia fuerte |
| **Usuarios y Seguridad** | Autenticación, autorización, roles (turista/operador/admin) | Relacional (PostgreSQL) |
| **Financiero/Pagos** | Procesamiento de pagos, comisiones a operadores | Relacional (PostgreSQL) — requisito de auditabilidad |
| **IA (recomendación o chatbot)** | Funcionalidad de IA elegida, con capa de explicabilidad | Según el caso (vectorial/documental) + registro de modelo |
| **Notificaciones** | Correos, alertas de disponibilidad, avisos multilenguaje | Cola de mensajes + almacenamiento ligero |
| **Analítica/Reportes** | Indicadores de demanda para planificación turística | Almacén analítico ligero (o vistas materializadas sobre PostgreSQL) |

Comunicación síncrona (REST/gRPC) para consultas, y un **bus de eventos** ligero (p. ej. RabbitMQ o un servicio gestionado equivalente) para el saga de reservas y para alimentar Analítica e IA sin acoplarlas a los demás servicios.

### 2.2 Subcategorías / variantes de la propuesta principal

**Variante A1 — Microservicios "enterprise" con Kubernetes + Service Mesh (Istio).**
Ofrece autoscaling fino, observabilidad avanzada y despliegue canario. **No recomendada para este proyecto**: requiere personal de plataforma dedicado y varios meses de curva de aprendizaje —justo lo que el presupuesto y el plazo no permiten.

**Variante A2 — Microservicios ligeros con contenedores + Gateway simple (RECOMENDADA como forma de implementar la propuesta principal).**
Docker Compose (o un orquestador gestionado de bajo costo tipo Render/Railway/ECS Fargate) en lugar de Kubernetes completo; un gateway simple (Traefik/Kong) en vez de service mesh; 5-7 servicios como máximo; saga **orquestada** (no coreografiada) para mantener la trazabilidad depurable con un equipo pequeño.

**Variante A3 — Microservicios serverless (funciones gestionadas: AWS Lambda/Cloud Functions + BD gestionada).**
Atractiva por costo variable (pagas por uso) y cero administración de servidores, útil si la demanda es muy estacional (como el turismo de Santa Marta). Riesgos: cold starts para el chatbot de IA, mayor dependencia de un proveedor cloud, y las sagas de larga duración (reserva con pasos de pago) son más difíciles de orquestar en funciones efímeras sin un motor de workflows adicional (p. ej. Step Functions), lo que añade curva de aprendizaje.

---

## 3. Alternativas adicionales (obligatorias por la guía del curso)

### Alternativa B — Monolito Modular orientado a dominios (con IA como único servicio externo)

**Estilo:** un solo desplegable, organizado internamente en módulos con límites estrictos (Catálogo, Reservas, Usuarios, Financiero, Notificaciones, Analítica), cada uno con su propio esquema dentro de la misma base de datos. Solo la IA se extrae como microservicio aparte, porque su ciclo de vida (entrenamiento/actualización de modelo) y su carga de cómputo son muy distintos al resto.

- **Idea general de estructura:** capas + módulos de dominio internos, comunicándose por interfaces en memoria (no red), con un único punto de despliegue.
- **Ventaja principal:** bajísima complejidad operativa y de depuración; encaja con un equipo de 5 personas y 3 meses, y con evidencia de que <cite index="10-1">un modular monolith ofrece la mayoría de los beneficios organizativos de los microservicios —razonamiento independiente por dominio, propiedad clara, pruebas rápidas dentro del dominio— sin la complejidad operativa de servicios distribuidos</cite>.
- **Desventaja principal:** escala como una sola unidad; si Catálogo necesita picos de tráfico muy distintos a Reservas, no se puede escalar de forma independiente, y migrar a microservicios completos más adelante exige disciplina previa en los límites de módulo.

### Alternativa C — Cliente-Servidor en 3 capas tradicional (presentación / lógica / datos) con IA como servicio externo consumido por API

**Estilo:** arquitectura en capas clásica, una sola base de código de backend, un frontend web/móvil que consume una API REST monolítica.

- **Idea general de estructura:** capa de presentación (web/app) → capa de lógica de negocio (todas las reglas del dominio turístico juntas) → capa de datos (una sola base relacional).
- **Ventaja principal:** la más rápida y barata de construir; mínima curva de aprendizaje para un equipo de estudiantes; encaja perfectamente en 3 meses.
- **Desventaja principal:** no separa módulos internamente (riesgo de "bola de lodo"), dificulta demostrar mantenibilidad/evolutividad y aislamiento de fallos —atributos de calidad que la asignatura exige evaluar explícitamente—, y compromete la disponibilidad ≥99% porque un fallo en cualquier funcionalidad puede tumbar todo el sistema.

---

## 4. Tabla comparativa (formato exigido por la guía)

Ponderación 1 (bajo) a 5 (alto). Para Costo y Complejidad, un puntaje más alto es **peor** (se penaliza), por lo que en el puntaje final se invierten.

| Criterio (peso) | A2. Microservicios ligeros (principal) | A3. Microservicios serverless | B. Monolito modular | C. Capas tradicional |
|---|---|---|---|---|
| Costo relativo | Medio (3) | Bajo-medio (2) | Bajo (1) | Bajo (1) |
| Tiempo de implementación (3 meses disponibles) | Alto riesgo (4) | Alto riesgo (4) | Bajo riesgo (2) | Muy bajo riesgo (1) |
| Escalabilidad | Alta (5) | Alta (5) | Media (3) | Baja (2) |
| Seguridad (aislamiento, control de acceso) | Alta (4) | Media-alta (4) | Media (3) | Media (2) |
| Complejidad técnica para el equipo | Alta (4) | Alta (5) | Media (2) | Baja (1) |
| Disponibilidad (aislamiento de fallos) | Alta (5) | Alta (4) | Media (3) | Baja (2) |
| Facilidad de evolución (nuevos operadores/servicios) | Alta (5) | Alta (4) | Media-alta (4) | Baja (2) |

**Puntaje ponderado orientativo** (Costo y Complejidad invertidos: 6 − valor; el resto tal cual; suma simple sobre 7 criterios, máximo 35):

- **A2. Microservicios ligeros:** (6-3)+(6-4)+5+4+(6-4)+5+5 = **27**
- **A3. Microservicios serverless:** (6-2)+(6-4)+5+4+(6-5)+4+4 = **24**
- **B. Monolito modular:** (6-1)+(6-2)+3+3+(6-2)+3+4 = **26**
- **C. Capas tradicional:** (6-1)+(6-1)+2+2+(6-1)+2+2 = **21**

A2 y B quedan muy cerca (27 vs. 26): la diferencia real está en **cuánto tiempo del equipo se va en infraestructura vs. en funcionalidad**, dado el plazo de 3 meses.

---

## 5. Recomendación y análisis de trade-offs

**Recomendación pragmática para este proyecto (equipo de 5, 3 meses, USD 20.000):**

1. **Núcleo del sistema como Monolito Modular** (Alternativa B) para Catálogo, Disponibilidad/Reservas, Usuarios y Financiero: un solo repositorio, módulos con contratos internos estrictos (para poder extraerlos después sin reescribir), una sola base de datos relacional (PostgreSQL) con esquemas separados por módulo.
2. **Extraer como microservicios reales solo los componentes con necesidades claramente distintas**: (a) el módulo de **IA** (recomendación/chatbot/predicción/clasificación — el que el equipo elija), porque su carga de cómputo, ciclo de actualización de modelo y necesidad de explicabilidad son diferentes al resto; y (b) **Notificaciones**, porque es naturalmente asíncrono y se beneficia de una cola de mensajes independiente.
3. Esto es, en la práctica, la **Variante A2 aplicada de forma selectiva** (patrón *strangler* / extracción quirúrgica) en lugar de microservicios "por defecto" para todo: se obtiene desacoplamiento real donde más se necesita (IA, escalabilidad estacional) sin pagar el costo operativo completo de una malla de microservicios que, según la evidencia revisada, <cite index="12-1">introduce alrededor de 25% de sobrecarga de recursos solo por complejidad operativa y puede reducir la velocidad de entrega de funcionalidades entre 20% y 40% en equipos pequeños o medianos</cite>.

**Cómo influyeron las restricciones:**
- *Económicas:* con USD 20.000 y software libre/cloud de bajo costo, un clúster Kubernetes con service mesh (Variante A1) es inviable; un monolito modular + 2 servicios extraídos cabe cómodo en el presupuesto (una sola base de datos gestionada, un contenedor para el core, un contenedor pequeño para IA, una cola de mensajes gestionada económica).
- *Temporales:* 3 meses con roles fijos (arquitecto, analista, diseñador de datos, desarrollador, QA) no alcanzan para la curva de aprendizaje de orquestación de contenedores a gran escala; el monolito modular permite entregar el flujo crítico completo (consulta → reserva → pago → confirmación) con menor riesgo de no terminar a tiempo.
- *Calidad prioritaria (disponibilidad ≥99%, escalabilidad estacional):* se resuelve igual, porque el cuello de botella real en temporada alta suele ser Catálogo/Disponibilidad (lectura intensiva) — se puede escalar horizontalmente el propio monolito (varias réplicas detrás de un balanceador) y usar caché (Redis) para las consultas más frecuentes, sin necesitar microservicios independientes para eso.
- *Qué se sacrifica:* con el monolito modular se pierde la posibilidad de escalar Catálogo de forma totalmente independiente de Reservas dentro del mismo proceso; se compensa con caché y réplicas horizontales del monolito completo, que es más barato que operar un clúster de microservicios.
- *Qué se gana:* el equipo entrega un ADR claro y defendible ("empezamos modular, extrajimos IA y Notificaciones por razones técnicas explícitas, no por moda arquitectónica"), lo cual es exactamente el tipo de decisión justificada y trazable que pide la rúbrica de evaluación.

**Si el equipo prefiere sostener la narrativa de "microservicios" como estilo principal** (por ejemplo, porque el enunciado del proyecto lo sugiere explícitamente como ejemplo), la Variante A2 sigue siendo defendible: basta con **limitar el número de servicios a los 5-7 listados en la sección 2.1**, usar orquestación de saga (no coreografía) para mantener la depurabilidad con un equipo pequeño, y documentar en el ADR por qué se descartaron A1 (sobrecosto operativo) y A3 (dificultad de sagas de larga duración en funciones efímeras).

---

## 6. Registro de decisiones sugerido (para el ADR del documento final)

| Decisión | Alternativas consideradas | Elegida | Motivo principal |
|---|---|---|---|
| Estilo arquitectónico | Monolito modular / Microservicios completos / Capas tradicional / Híbrido | Híbrido (B + extracción quirúrgica) o A2 acotado | Balance costo-tiempo-escalabilidad bajo restricciones del equipo |
| Persistencia | Única (PostgreSQL) vs. políglota | Políglota acotada: PostgreSQL (transaccional) + documental (catálogo) + caché (Redis) | Los datos de catálogo son heterogéneos; el resto requiere ACID |
| Comunicación entre módulos/servicios | Síncrona pura vs. híbrida (síncrona + eventos) | Híbrida: REST para consultas, eventos para saga de reservas | Reservas requiere compensación ante fallos parciales |
| Orquestación del saga | Coreografía vs. orquestación | Orquestación | Mayor trazabilidad y depurabilidad con equipo pequeño |
| Infraestructura de despliegue | Kubernetes+mesh vs. contenedores ligeros vs. serverless | Contenedores ligeros gestionados | Ajuste a presupuesto y curva de aprendizaje de 3 meses |

---

### Fuentes consultadas
- Java Code Geeks, "Microservices vs. Monoliths in 2026" — javacodegeeks.com
- Unico Connect, "Monolith vs Microservices in 2026" — unicoconnect.com
- CodingDroplets, "Monolith vs Modular Monolith vs Microservices in .NET 2026" — codingdroplets.com
- HustleToAI, "Microservices vs Modular Monolith: The 2026 Reality Check" — hustletoai.com
- ByteIota, "Modular Monolith: 42% Ditch Microservices in 2026" — byteiota.com
- CreateBytes, "Monolith vs Microservices for Startups: The 2026 Guide" — createbytes.com
- Medium (Meeran Malik), "Microservices Architecture for AI Applications" — medium.com
- Blocshop, "AI integrations in microservices" — blocshop.cz
- DEV Community (airtruffle), "Event-Driven Microservices for Booking Systems" — dev.to
- The Backend Developers, "Event-Driven Architecture: Saga Patterns, Outboxes..." — thebackenddevelopers.substack.com
- Medium (Hossein Nejati Javaremi), "Polyglot Persistence" — medium.com
- DataExpert.io, "Polyglot Persistence: Database Per Service Pattern" — dataexpert.io
