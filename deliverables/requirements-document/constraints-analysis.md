## Análisis de Restricciones Técnicas, Económicas, Sociales, Normativas y Éticas

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Restricciones: 38](https://img.shields.io/badge/Restricciones-38-orange?style=flat-square)

> **Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta.

> [!NOTE]
> **Propósito de la sección:** en cumplimiento de `Diseño-de-Ingenieria.md` ("Análisis de restricciones técnicas, económicas, sociales, normativas y éticas explícitas"), esta sección (a) enumera el 100% de las restricciones de `Restricciones.md` y `Diseño-de-Ingenieria.md`, (b) las traduce a condiciones verificables, (c) analiza tensiones entre ellas y cuáles son realmente determinantes, (d) contrasta su factibilidad con cifras del proyecto y (e) las enlaza con las decisiones arquitectónicas (ADR) que condicionan. Además de las cinco categorías pedidas, incluye las **ambientales** y las **temporales**, porque `Restricciones.md` las declara explícitamente, y las **de proceso**, porque `Diseño-de-Ingenieria.md` las exige para el prototipo.

---

### 1. Metodología

#### 1.1 Clasificación y numeración

Cada restricción recibe un ID `RC-<tipo><nn>`:

| Prefijo | Tipo | Fuente |
|---|---|---|
| **T** | Técnica | `Restricciones.md` |
| **E** | Económica y temporal | `Restricciones.md` |
| **S** | Social | `Restricciones.md` |
| **A** | Ambiental | `Restricciones.md` |
| **N** | Normativa (N01–N04 del enunciado; N05–N07 **derivadas** por investigación) | `Restricciones.md` + normativa colombiana |
| **ET** | Ética | `Restricciones.md` |
| **P** | De proceso y entrega | `Diseño-de-Ingenieria.md` |
| **D** | Supuesto de dominio (no declarado, a validar) | Análisis del equipo |

Marcas de origen: **(E)** = explícita en el enunciado; **(Der)** = derivada de normativa o de otro documento del proyecto; **(Sup)** = supuesto del equipo.

#### 1.2 Atributos analizados por restricción

Interpretación operacionalizada (qué significa de forma verificable) · atributo o escenario asociado · impacto arquitectónico · riesgo si no se cumple. El análisis se resume en la sección 7 en la tabla *Restricción → Decisión → Evidencia → Resultado* que exige `Diseño-de-Ingenieria.md`.

---

### 2. Catálogo y análisis de restricciones

#### 2.1 Restricciones técnicas

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-T01 | Acceso desde dispositivos móviles y Web (E) | Mismas funciones críticas (consulta, reserva) en ambos canales; viewport desde 360 px | Capacidad de interacción; RI-01, RI-02 | Frontend adaptable o dos clientes sobre una API común; API sin lógica de presentación | Exclusión de turistas móviles (canal dominante en destino) |
| RC-T02 | Integración con múltiples fuentes de información (E) | Incorporar una fuente nueva sin tocar el núcleo | EC-INTEROP-01, EC-EVOL-01; RI-06, RF-CAT-19 | Capa de adaptadores; modelo canónico de datos | Ecosistema fragmentado (problema original) |
| RC-T03 | Alta concurrencia en temporadas turísticas (E) | p95 < 800 ms con 500 usuarios simultáneos | EC-DESM-01, EC-DISP-01; RNF-DESM-01 | Réplicas horizontales, caché de lecturas, control de concurrencia sobre cupos | Caída o sobreventa en temporada alta |
| RC-T04 | Disponibilidad mínima del 99% (E) | ≈ 7,3 h de indisponibilidad máxima/mes | EC-DISP-01/02; RNF-DISP-01 | Redundancia activa, balanceo, detección < 30 s, resiliencia ante pasarela | Incumplimiento del atributo prioritario |
| RC-T05 | Arquitectura preparada para crecimiento progresivo (E) | Escalado horizontal < 5 min; evolución sin reescribir el núcleo | EC-ESC-01, EC-EVOL-01 | Límites de módulo estrictos; posibilidad de extraer componentes | Rediseño al crecer la demanda |
| RC-T06 | Evaluar persistencia única o políglota y justificar (E) | ADR con comparación por tipo de dato, costo, complejidad y evolución | RNF-EVOL-01; RD-02, RD-03 | Decide motores de BD; define si hay catálogo documental/JSONB, caché y almacén vectorial | Complejidad operativa sin beneficio, o rigidez de esquema |
| RC-T07 | Mecanismos de comunicación entre componentes y fuentes externas, justificados (E) | ADR sobre estilo síncrono/asíncrono según interoperabilidad, rendimiento, seguridad y evolución | RI-04, RI-05, RI-07; RF-NOT-01 | Define REST/gRPC vs. eventos; contratos de integración | Acoplamiento fuerte o pérdida de mensajes |

#### 2.2 Restricciones económicas y temporales

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-E01 | Presupuesto máximo de USD 20.000 para infraestructura inicial (E) | Costo acumulado de infraestructura del piloto ≤ USD 20.000 | Costo | Descarta clústeres con malla de servicios; favorece contenedores gestionados | Inviabilidad del piloto |
| RC-E02 | Privilegiar software libre y nube de bajo costo (E) | Componentes de código abierto o de nivel gratuito/económico | Costo, sostenibilidad | Selección de BD, colas, observabilidad y *frameworks* | Dependencia de licencias costosas |
| RC-E03 | Equipo de cinco estudiantes (E) | Cinco roles fijos; carga y evaluación individual por rol | Mantenibilidad, factibilidad | Estilo arquitectónico y partición del trabajo (ver §6) | Sobrecarga o desbalance de responsabilidades |
| RC-E04 | Tiempo máximo de ejecución de tres meses (E) | 12 semanas, 6 sprints; cuatro documentos y prototipo | Factibilidad | Limita complejidad operativa; flujo crítico cerrado en sprint 6 | Prototipo incompleto |
| RC-E05 | Equilibrar costo, escalabilidad, seguridad y facilidad de mantenimiento (E) | Trade-offs documentados en ADR con puntaje ponderado | Todos | Obliga análisis explícito en cada ADR | Decisiones empíricas (prohibidas por `Fundamentacion-de-Decisiones.md`) |

#### 2.3 Restricciones sociales

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-S01 | Interfaces accesibles para distintos niveles de alfabetización digital (E) | Flujo de reserva ≤ 5 pantallas, lenguaje claro (meta a validar) | RNF-USA-03; SH-14 | Elección de *framework* UI y patrones de interacción simples | Abandono de usuarios y exclusión |
| RC-S02 | Disponibilidad en español e inglés (E) | 100% de cadenas y plantillas en ES/EN; cambio < 1 s | EC-MULTI-01; RNF-USA-02 | Internacionalización desde el diseño, incluidas notificaciones y contenido del catálogo | Turista internacional sin servicio |
| RC-S03 | Inclusión de pequeños operadores con recursos limitados (E) | Publicar oferta con formulario simple; alternativa a la integración técnica | RNF-USA-04; RF-CAT-08; SH-02 | Carga manual simplificada además de API/lote; bajo costo de adopción | Concentración de visibilidad en operadores grandes |
| RC-S04 | Accesibilidad para personas con discapacidad (E) | WCAG 2.1 AA en búsqueda, disponibilidad y reserva | EC-ACC-01; RNF-USA-01 | Componentes accesibles; pruebas con lector de pantalla y teclado | Incumplimiento legal y exclusión |

#### 2.4 Restricciones ambientales

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-A01 | Recomendar destinos alternativos para disminuir congestión (E) | Alternativa de menor congestión en recomendaciones con alerta activa | EC-SOST-01; RF-IA-05 | La IA consume datos de ocupación y umbrales | Persiste la concentración en pocos atractivos |
| RC-A02 | Reducir el impacto sobre ecosistemas sensibles (E) | Zonas sensibles con umbral propio y alerta | RF-ANA-03; CU-31 | Modelo de datos con zonificación por sensibilidad | Presión sobre áreas protegidas |
| RC-A03 | Difundir buenas prácticas ambientales (E) | Contenido ambiental en fichas y confirmaciones | Contenido; CU-07, CU-18 | Campo de contenido y plantillas de notificación | Cumplimiento solo declarativo |
| RC-A04 | Monitorear la capacidad de carga turística (E) | Indicador vs. umbral; alerta < 5 min al superar el 90% | EC-SOST-01; RNF-SOST-01 | Módulo de analítica con datos casi en tiempo real | Sobrecarga sin detección |

#### 2.5 Restricciones normativas

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-N01 | Protección de datos personales (E) | Minimización, cifrado en tránsito (TLS 1.3) y en reposo | RNF-SEG-02, 03; RD-04 | Seguridad transversal; datos sensibles aislados | Sanción y pérdida de confianza |
| RC-N02 | Cumplimiento de la Ley 1581 de 2012 (E) | Consentimiento registrado; derechos de acceso, rectificación, supresión; plazos de 10 y 15 días hábiles | EC-SEG-02; RF-USR-02, 15, 16 | Módulo de consentimiento y de solicitudes de titulares; auditoría de accesos | Incumplimiento legal; el prototipo no puede operar |
| RC-N03 | Protección de información comercial de operadores (E) | Cada prestador solo accede a sus tarifas, ventas y disponibilidad | RNF-SEG-04; RF-CAT-09, RF-PAG-08 | Aislamiento por propietario; RBAC con permisos por recurso | Fuga de información competitiva |
| RC-N04 | Gestión segura de autenticación y autorización (E) | Hash resistente, tokens de corta duración, RBAC, *rate limiting* | EC-SEG-01; RNF-SEG-01 | Gateway/módulo de identidad; WAF | Acceso no autorizado |
| RC-N05 | Registro Nacional de Turismo (RNT) y obligaciones de plataformas digitales (**Der**) | Verificar y mostrar el número de RNT de cada prestador; contrastarlo con el RNT al aprobar | RF-USR-18, 21; RF-CAT-10 | Campo RNT en el modelo de prestador; paso de verificación en onboarding | Habilitar oferta de prestadores sin registro habilitante |
| RC-N06 | Pagos: PCI-DSS delegado a pasarela certificada (**Der**) | El sistema nunca almacena datos de tarjeta | RF-PAG-02; RI-04 | Integración tokenizada mediante interfaz desacoplada | Incumplimiento PCI y riesgo financiero |
| RC-N07 | Accesibilidad web según referente estatal MinTIC (Resolución 1519 de 2020, Anexo 1) (**Der**) | Criterios WCAG AA evaluables en las pantallas clave | EC-ACC-01 | Mismo impacto que RC-S04; refuerza el criterio de aceptación | Plataforma de entidad pública no conforme |

> [!IMPORTANT]
> **Hallazgos de la investigación normativa (verificar vigencia antes de citar en el documento final).**
>
> - **RNT (RC-N05).** La Ley 2068 de 2020 (art. 38) y el Decreto 1836 de 2021 establecen obligaciones para los operadores de plataformas electrónicas de servicios turísticos, que incluyen inscribirse en el RNT, interoperar con él y hacer visible el número de inscripción de cada prestador; además, la inscripción en el RNT es requisito previo para que un prestador inicie operaciones. Se identificó un proyecto de decreto del Ministerio de Comercio, Industria y Turismo (publicado para comentarios en diciembre de 2025) que actualiza este régimen, por lo que debe confirmarse el texto vigente. En un piloto académico la interoperabilidad completa con el RNT puede estar fuera de alcance; el requisito mínimo adoptado es **verificar y mostrar el número** (RF-USR-21, RF-CAT-10).
> - **Registro Nacional de Bases de Datos (SIC).** Bajo el Decreto 090 de 2018, deben inscribirse las sociedades y entidades sin ánimo de lucro con activos totales superiores a 100.000 UVT y las personas jurídicas de naturaleza pública, independientemente de sus activos. Como el proyecto se asume como iniciativa de una entidad pública o mixta (género *Gobierno*, Laboratorio 1), la inscripción sería exigible en una operación real; no lo es para el prototipo académico, pero el diseño debe permitir exportar el inventario de bases de datos y finalidades. Las demás obligaciones de la Ley 1581 aplican aun si no hay obligación de registro.

#### 2.6 Restricciones éticas

| ID | Restricción (origen) | Interpretación verificable | Atributo / escenario | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|---|
| RC-ET01 | Recomendaciones de IA explicadas al usuario (E) | 100% de recomendaciones con criterio explicativo y registro de auditoría | EC-IA-01; RF-IA-02, 03 | Contrato de IA que devuelve explicación; log de decisiones | Decisiones opacas y pérdida de confianza |
| RC-ET02 | No favorecer sistemáticamente a un operador sin criterios explícitos (E) | Ponderaciones documentadas; auditoría trimestral | EC-IA-02; RF-CAT-03, RF-IA-06 | Modelo de recomendación y de orden de catálogo basado en reglas auditables | Sesgo comercial y daño a pequeños operadores |
| RC-ET03 | Protección de la privacidad de turistas (E) | Minimización; geolocalización y datos de uso solo con consentimiento | RD-04; RNF-SEG-03 | Datos de personalización separados del identificador cuando sea posible | Vigilancia no consentida |
| RC-ET04 | Transparencia en el tratamiento de datos (E) | Política de tratamiento visible; registro de accesos a datos personales | RNF-LOC-01; RF-USR-24 | Auditoría y portal de privacidad (CU-06) | Pérdida de confianza y de legitimidad |

#### 2.7 Restricciones de proceso y entrega

| ID | Restricción (origen) | Interpretación verificable | Impacto arquitectónico | Riesgo si no se cumple |
|---|---|---|---|---|
| RC-P01 | Paradigma orientado a objetos (`Diseño-de-Ingenieria.md`) | Modelo de dominio y código en clases; lenguaje OO | Elección de lenguaje y organización por capas/dominio (Clean Architecture en Lab. 1) | Inconsistencia con la rúbrica |
| RC-P02 | Base de datos definida por el equipo y justificada por restricciones técnicas y económicas | ADR de persistencia con respaldo económico y técnico | Enlaza con RC-T06 | Decisión sin sustento |
| RC-P03 | Considerar explícitamente costo, tiempo, conectividad y sostenibilidad | Cada ADR declara su efecto sobre las cuatro | ADR de estrategia de conectividad (RC-D01) | Decisiones parciales |
| RC-P04 | Prototipo con ≥ 60% de los casos de uso priorizados y al menos un flujo crítico completo | Ver §5.4 | Define el alcance mínimo de implementación (CU-11 como flujo crítico) | Calificación de implementación comprometida |
| RC-P05 | Método de evaluación arquitectónica seleccionado, justificado y aplicado | Método elegido (ATAM-lite en el plan) sobre los 15 EC | Los EC deben ser ejecutables sobre el prototipo | Validación sin método |
| RC-P06 | Cronograma, roles y distribución de responsabilidades (`Diseño-de-Ingenieria.md`) | Plan en `development-plan-and-budget.md` | Alineación de componentes con roles | Responsabilidades difusas |

#### 2.8 Supuestos de dominio

| ID | Supuesto (Sup) | Por qué importa | Cómo validarlo |
|---|---|---|---|
| RC-D01 | La cobertura móvil es intermitente en zonas naturales (Tayrona, Sierra Nevada) y en periodos de congestión de red | `Diseño-de-Ingenieria.md` exige una "estrategia de manejo de conectividad" pero `Restricciones.md` no define el escenario | Consultar con la entidad de gestión o el docente; definir qué funciones deben tolerar desconexión (p. ej., consulta de reserva ya confirmada y comprobante en caché) |

---

### 3. Tensiones entre restricciones

Las restricciones no son independientes; estas son las tensiones identificadas y cómo se resuelven o quedan abiertas.

| # | Restricciones en tensión | Naturaleza del conflicto | Resolución propuesta |
|---|---|---|---|
| 1 | RC-T04 (99%) vs. RC-E01/E04 (costo y tiempo) | Mayor disponibilidad exige redundancia, que cuesta más y toma más tiempo | Redundancia solo en el flujo crítico (Reservas); el costo es marginal frente al techo (ver §5.1) |
| 2 | RC-A01 (recomendar alternativas) vs. RC-ET02 (no favorecer operadores) | Redirigir turistas hacia zonas alternativas beneficia a los operadores de esas zonas | El criterio de congestión debe estar en el modelo documentado y explicarse al usuario; es un criterio explícito, no un sesgo oculto |
| 3 | RC-ET01 (explicar) vs. RC-ET03 (privacidad) | La explicación podría revelar datos personales o de otros usuarios | Explicaciones en términos de categorías de preferencia y congestión agregada, nunca de datos individuales de terceros |
| 4 | RC-T02 (múltiples fuentes) vs. RC-N03 (información comercial) | Integrar fuentes expone datos comerciales de prestadores | Solo fuentes autorizadas; aislamiento por prestador; origen registrado (RD-05) |
| 5 | RC-T03 (alta concurrencia) vs. RC-E04 (3 meses) | Diseñar y validar la carga consume tiempo del equipo | Prueba de carga acotada a catálogo y reservas (EC-DESM-01, EC-DISP-01) |
| 6 | RC-S04/N07 (WCAG AA) vs. RC-E04 | La accesibilidad es costosa si se añade al final | Se incorpora como criterio de la librería de UI desde el diseño de interfaces |
| 7 | RC-N02 (supresión de datos) vs. obligaciones contables de pagos | No se puede borrar una reserva con obligaciones activas | Ya previsto en CU-06 (informar plazo y razón); anonimizar tras el plazo legal |
| 8 | RC-E03 (asignación individual por rol) vs. RC-E04 y RC-T05 | Un estilo de componentes independientes favorece la evaluación individual pero encarece la operación | Ver §6 (decisión pendiente) |

---

### 4. Restricciones determinantes frente a las holgadas

No todas las restricciones pesan igual en la decisión. La clasificación se basa en el margen que deja cada una frente a las alternativas evaluadas.

| Clase | Restricciones | Evidencia |
|---|---|---|
| **Determinantes (activas)** | RC-E04 (tiempo), RC-E03 (equipo y evaluación individual), RC-T04 (99%), RC-N02 (Ley 1581), RC-ET01/ET02 (IA explicable y equitativa) | El tiempo del equipo, no el dinero, decide entre alternativas (`architectures-technical-details.md`, §C); Ley 1581 y ética de IA son innegociables |
| **Condicionantes (moldean el diseño)** | RC-T01–T03, T05–T07, S01–S04, A01–A04, N03–N04, P01–P05 | Se resuelven con decisiones de diseño y tácticas dentro del margen |
| **Holgadas (no activas)** | RC-E01 (presupuesto), RC-E02 | La infraestructura del piloto usa entre el 0,7% y el 3,5% del techo (ver §5.1) |
| **Supuestos a validar** | RC-D01, RC-N05 (alcance de interoperabilidad con RNT) | Requieren confirmación con docente o entidad |

**Conclusión:** el presupuesto no es la restricción que discrimina; sí lo son el tiempo, la composición del equipo y los requisitos de calidad no negociables. Esto debe reflejarse en cada ADR como "restricción que más influyó".

---

### 5. Factibilidad frente a las cifras del proyecto

#### 5.1 Presupuesto (RC-E01, RC-E02)

| Escenario | Infraestructura mensual | 3 meses | % del techo de USD 20.000 |
|---|---|---|---|
| Monolito modular + IA y Notificaciones extraídos | USD 48 – 122 | USD 144 – 366 | 0,7% – 1,8% |
| Microservicios ligeros (7 servicios) | USD 115 – 235 | USD 345 – 705 | 1,7% – 3,5% |

Fuente: `architectures-technical-details.md` y `development-plan-and-budget.md`. Ambas opciones caben con amplio margen; la pasarela de pagos es un costo variable de operación fuera del presupuesto de infraestructura. **Resultado: la restricción se cumple en cualquier alternativa.**

#### 5.2 Tiempo y equipo (RC-E03, RC-E04)

Capacidad nominal: 5 personas × 12 semanas = 60 personas-semana (sin ajustar por dedicación parcial).

| Alternativa | % esfuerzo en infraestructura | Personas-semana en infraestructura | Personas-semana en funcionalidad |
|---|---|---|---|
| Monolito modular híbrido | ≈ 15% | ≈ 9 | ≈ 51 |
| Microservicios ligeros | ≈ 32% | ≈ 19 | ≈ 41 |

**Resultado:** la diferencia (≈10 personas-semana) es el costo de la independencia entre servicios y el principal riesgo de tiempo; es un hecho cuantitativo que cualquier decisión debe asumir explícitamente.

#### 5.3 Disponibilidad y concurrencia (RC-T03, RC-T04)

- 99% mensual equivale a un máximo de ≈ 7,3 h de indisponibilidad (730 h/mes).
- Alcanzarlo en un piloto de bajo costo exige al menos dos réplicas del servicio crítico, balanceador, detección de fallos < 30 s y tolerancia a fallos de la pasarela (EC-DISP-01/02). Esto está contenido en el costo de §5.1.
- La disponibilidad de la pasarela externa y del proveedor cloud no está bajo control del equipo: se mitiga con reintentos, *circuit breaker* y degradación (reserva pendiente), y se documenta como riesgo residual.

#### 5.4 Alcance mínimo del prototipo (RC-P04)

`Diseño-de-Ingenieria.md` exige "mínimo el 60% de los casos de uso priorizados". El término *priorizados* admite dos lecturas, con distinto umbral:

| Lectura | Universo | 60% mínimo |
|---|---|---|
| Todos los casos de uso especificados | 34 CU | **21 CU** |
| Casos de uso de prioridad 4 y 5 | 18 CU (7 de prioridad 5 y 11 de prioridad 4) | **11 CU** |

> [!IMPORTANT]
> **Decisión pendiente:** confirmar con el docente cuál lectura aplica. Se recomienda planificar contra la lectura conservadora (21 CU) para los CU que comparten módulos con el flujo crítico (USR, CAT, RES, PAG), y tratar los demás como holgura. Los CU de prioridad 5 son los que sostienen CU-11 (flujo completo: inicio → procesamiento → persistencia → respuesta).

---

### 6. Impacto en decisiones arquitectónicas

#### 6.1 ADR condicionados por las restricciones

| ADR candidato | Restricciones que lo condicionan | Restricción más influyente | Estado |
|---|---|---|---|
| ADR-01 Metodología de desarrollo | RC-E03, E04, P05, P06 | RC-E04 | Decidido: Scrum + ATAM-lite (`development-plan-and-budget.md`) |
| ADR-02 Estilo arquitectónico | RC-E03, E04, T03, T04, T05, E05, P04 | RC-E03 / RC-E04 | **Abierto** (ver §6.2) |
| ADR-03 Persistencia | RC-T06, E01, E02, P02, N03 | RC-T06 | Propuesto: PostgreSQL con JSONB y *pgvector*; revisar si se justifica motor adicional |
| ADR-04 Comunicación e integración | RC-T02, T07, N06 | RC-T07 | Propuesto: REST síncrono + eventos para saga y notificaciones |
| ADR-05 Manejo de conectividad | RC-T01, D01, P03 | RC-D01 | **Abierto** (depende de validar el supuesto) |
| ADR-06 Seguridad y cumplimiento | RC-N01–N07, ET03, ET04 | RC-N02 | Propuesto |
| ADR-07 IA explicable y equitativa | RC-ET01, ET02, A01, A04 | RC-ET01 | Propuesto |
| ADR-08 Despliegue e infraestructura | RC-E01, E02, T03, T04 | RC-T04 | Propuesto: contenedores gestionados con réplicas |
| ADR-09 Frontend, accesibilidad e i18n | RC-S01, S02, S04, N07 | RC-S04 | Por iniciar |

#### 6.2 Divergencia de estilo arquitectónico (ADR-02)

Existen dos decisiones documentadas que parten de restricciones distintas:

| | Documentación general (`architectural-proposals.md`) | Laboratorio 1 (`theory-applied-to-project.md`) |
|---|---|---|
| Estilo | Monolito modular + IA y Notificaciones extraídos | Microservicios con API Gateway |
| Restricción que decide | RC-E04 (tiempo) y esfuerzo de infraestructura | RC-E03 (un componente por integrante, evaluación individual) |
| Puntaje técnico | Monolito 26 vs. microservicios 27 (7 criterios) | Monolito 20 vs. microservicios 17 (5 criterios) |
| Costo en tiempo | ≈ 9 personas-semana en infraestructura | ≈ 19 personas-semana |
| Riesgo principal | Escalar Catálogo por separado; menor evidencia de dominio de microservicios | No completar el alcance mínimo en 3 meses |

**Qué debe hacer el equipo antes del Documento de Diseño Arquitectónico Final:**

1. Confirmar con el docente si la evaluación individual por rol exige un servicio por integrante o si se satisface con **módulos con propietario** dentro de un monolito modular (con IA y Notificaciones como servicios independientes, que ya dan tres unidades desplegables).
2. Si la respuesta exige servicios separados, aceptar y planificar el sobrecosto de ≈10 personas-semana, reducir alcance de los CU de prioridad 2–3, o ambas.
3. Registrar la decisión en ADR-02 declarando explícitamente qué restricción pesó más, qué se gana y qué se sacrifica.

Ninguna de las dos opciones viola restricciones duras: ambas caben en presupuesto (§5.1) y pueden satisfacer EC-DISP-01 y EC-DESM-01. La diferencia está en el riesgo de tiempo.

---

### 7. Validación de restricciones (tabla base)

Esta tabla es el insumo de la sección *Validación del Diseño frente a Restricciones Definidas* de `Diseño-de-Ingenieria.md`. Las columnas *Evidencia* y *Resultado* se completan al evaluar el prototipo; todas inician como **Pendiente**.

| Restricción | Tipo | Decisión arquitectónica asociada | Evidencia prevista en implementación | Resultado |
|---|---|---|---|---|
| RC-T01 | Técnica | ADR-09 (frontend adaptable) | Capturas en móvil y web del flujo de reserva | Pendiente |
| RC-T02 | Técnica | ADR-04 (adaptadores de integración) | Ingesta de al menos una fuente externa de prueba | Pendiente |
| RC-T03 | Técnica | ADR-02, ADR-08 (réplicas, caché) | Prueba de carga EC-DESM-01 | Pendiente |
| RC-T04 | Técnica | ADR-08 (redundancia, detección de fallos) | Prueba de falla de réplica EC-DISP-01 | Pendiente |
| RC-T05 | Técnica | ADR-02 (límites de módulo) | Prueba de escalado EC-ESC-01 | Pendiente |
| RC-T06 | Técnica | ADR-03 | ADR con comparación y modelo de datos | Pendiente |
| RC-T07 | Técnica | ADR-04 | ADR y contratos de integración | Pendiente |
| RC-E01 | Económica | ADR-08 | Informe de costo de infraestructura del piloto | Pendiente |
| RC-E02 | Económica | ADR-03, ADR-08 | Inventario de componentes y licencias | Pendiente |
| RC-E03 | Económica/equipo | ADR-01, ADR-02 | Asignación de componentes por rol en el repositorio | Pendiente |
| RC-E04 | Temporal | ADR-01 | Cronograma ejecutado vs. planeado | Pendiente |
| RC-E05 | Económica | ADR-01 a ADR-09 | Puntaje ponderado en cada ADR | Pendiente |
| RC-S01 | Social | ADR-09 | Prueba de flujo con usuarios (RNF-USA-03) | Pendiente |
| RC-S02 | Social | ADR-09 | Verificación de 100% de cadenas ES/EN | Pendiente |
| RC-S03 | Social | ADR-04, ADR-09 | Alta de oferta por formulario simple | Pendiente |
| RC-S04 | Social | ADR-09 | Auditoría WCAG AA con teclado y lector de pantalla | Pendiente |
| RC-A01 | Ambiental | ADR-07 | Recomendación con alternativa bajo alerta | Pendiente |
| RC-A02 | Ambiental | ADR-03, ADR-07 | Zonas con umbral por sensibilidad | Pendiente |
| RC-A03 | Ambiental | ADR-09 | Contenido de buenas prácticas visible | Pendiente |
| RC-A04 | Ambiental | ADR-03 | Prueba EC-SOST-01 | Pendiente |
| RC-N01 | Normativa | ADR-06 | Inspección TLS y cifrado en reposo | Pendiente |
| RC-N02 | Normativa | ADR-06 | Consentimiento, solicitudes de titulares, plazos | Pendiente |
| RC-N03 | Normativa | ADR-06 | Prueba de aislamiento entre prestadores | Pendiente |
| RC-N04 | Normativa | ADR-06 | Prueba EC-SEG-01 | Pendiente |
| RC-N05 | Normativa | ADR-06 | Campo RNT en onboarding y ficha | Pendiente |
| RC-N06 | Normativa | ADR-04, ADR-06 | Inspección: ausencia de datos de tarjeta | Pendiente |
| RC-N07 | Normativa | ADR-09 | Criterios de la Resolución 1519 evaluados | Pendiente |
| RC-ET01 | Ética | ADR-07 | Prueba EC-IA-01 | Pendiente |
| RC-ET02 | Ética | ADR-07 | Auditoría EC-IA-02 | Pendiente |
| RC-ET03 | Ética | ADR-06, ADR-07 | Inspección de minimización de datos | Pendiente |
| RC-ET04 | Ética | ADR-06 | Política visible y log de accesos | Pendiente |
| RC-P01 | Proceso | ADR-02 | Modelo de clases y código OO | Pendiente |
| RC-P02 | Proceso | ADR-03 | ADR de persistencia | Pendiente |
| RC-P03 | Proceso | ADR-05 | Sección de costo/tiempo/conectividad/sostenibilidad en cada ADR | Pendiente |
| RC-P04 | Proceso | ADR-02 | CU implementados vs. umbral (§5.4) y demo de CU-11 | Pendiente |
| RC-P05 | Proceso | ADR-01 | Informe de evaluación sobre los 15 EC | Pendiente |
| RC-P06 | Proceso | ADR-01 | Cronograma y matriz de responsabilidades | Pendiente |
| RC-D01 | Supuesto | ADR-05 | Validación del supuesto y estrategia de conectividad | Pendiente |

---

### 8. Trazabilidad y cobertura

| Verificación | Resultado |
|---|---|
| Restricciones de `Restricciones.md` cubiertas (7 T + 5 E + 4 S + 4 A + 4 N + 4 ET = 28) | 28 de 28 |
| Restricciones derivadas de otros documentos o normativa (RC-N05, N06, N07) | 3 |
| Restricciones de proceso de `Diseño-de-Ingenieria.md` | 6 |
| Supuestos de dominio | 1 |
| **Total** | **38** |
| Restricciones con requisito, escenario o ADR asociado | 38 de 38 |

> [!NOTE]
> Cada restricción queda enlazada con un ADR candidato (§6.1) y con una fila de la tabla de validación (§7), cerrando la cadena exigida por `Fundamentacion-de-Decisiones.md`: *Necesidades del contexto → Requisitos y restricciones → Decisiones arquitectónicas → Evidencia en el prototipo*.

#### Puntos que requieren confirmación externa

1. Lectura de "casos de uso priorizados" (21 o 11 CU) con el docente (RC-P04).
2. Estilo arquitectónico y alcance de la evaluación individual por rol (ADR-02, §6.2).
3. Si el flujo crítico se evalúa con pago real, simulado o excluido (ver observación 2 de `requirements-specification.md`).
4. Vigencia del régimen del RNT y alcance de la interoperabilidad en el piloto (RC-N05).
5. Escenario de conectividad esperado en destino (RC-D01).
