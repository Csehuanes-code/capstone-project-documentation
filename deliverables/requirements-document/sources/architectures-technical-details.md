# Detalle Técnico de las Arquitecturas Principales Seleccionadas
## Plataforma Digital de Turismo Santa Marta

Este documento profundiza las dos propuestas que quedaron mejor posicionadas en el comparativo previo:

- **Arquitectura Principal (recomendada): Monolito Modular con Extracción Quirúrgica de Servicios (Híbrida)**
- **Arquitectura Alternativa Viable: Microservicios Ligeros Acotados (5-7 servicios)**

Para cada una se detalla: tecnologías por componente, tipo de base de datos, seguridad, pasarela de pagos, ventajas/desventajas y costos económicos y de implementación. Al final se presenta un resumen comparativo de costos.

---

# A. ARQUITECTURA PRINCIPAL — Monolito Modular + Extracción Quirúrgica

## A.1 Visión general

Un núcleo desplegado como una sola aplicación de backend (monolito modular), con módulos internos estrictamente separados por dominio, y dos componentes extraídos como microservicios independientes porque tienen necesidades de escalamiento/tecnología claramente distintas: **IA** y **Notificaciones**.

```
                         ┌───────────────────────────┐
                         │      API Gateway / BFF     │
                         │  (auth, rate limit, TLS)   │
                         └─────────────┬─────────────┘
                                       │
              ┌────────────────────────┴──────────────────────────┐
              │                NÚCLEO — MONOLITO MODULAR           │
              │  ┌───────────┐ ┌───────────┐ ┌───────────┐        │
              │  │ Catálogo  │ │ Reservas/ │ │ Usuarios/ │        │
              │  │           │ │Disponib.  │ │ Seguridad │        │
              │  └───────────┘ └───────────┘ └───────────┘        │
              │  ┌───────────┐ ┌───────────┐                      │
              │  │Financiero/│ │ Analítica/│                      │
              │  │  Pagos    │ │ Reportes  │                      │
              │  └───────────┘ └───────────┘                      │
              │        Base de datos única (PostgreSQL,           │
              │        un esquema por módulo)                     │
              └────────────────┬────────────────┬──────────────────┘
                       eventos  │                │  eventos
                                ▼                ▼
                    ┌───────────────────┐  ┌───────────────────┐
                    │  Microservicio IA │  │ Microservicio      │
                    │  (recomendación/  │  │ Notificaciones      │
                    │   chatbot)        │  │ (correo/alertas)    │
                    └───────────────────┘  └───────────────────┘
```

## A.2 Detalle por sección/módulo

### A.2.1 Módulo Catálogo (dentro del monolito)
- **Función:** atractivos, actividades, eventos, prestadores turísticos, fichas de pequeños/medianos operadores.
- **Tipo de base de datos:** dentro de PostgreSQL se recomienda usar el tipo de columna **JSONB** para los atributos variables de cada atractivo (un hotel tiene atributos distintos a un tour de senderismo), evitando así introducir un motor NoSQL aparte solo para esto. Si en producción el volumen de búsquedas de texto libre crece mucho, se puede añadir **Elasticsearch/OpenSearch** solo para búsqueda, sin mover el dato maestro.
- **Tecnología sugerida:** backend en Node.js (NestJS) o Java (Spring Boot) según la fortaleza del equipo; ORM tipo Prisma/TypeORM o Hibernate.
- **Ventaja:** cambios de esquema (nuevos tipos de atractivo) sin necesitar migración estructural gracias a JSONB.
- **Desventaja:** consultas complejas sobre campos JSONB son algo más lentas que columnas nativas; requiere índices GIN bien diseñados.

### A.2.2 Módulo Disponibilidad y Reservas (dentro del monolito)
- **Función:** consulta de cupos/horarios, creación de reservas, orquestación del flujo reserva→pago→confirmación.
- **Tipo de base de datos:** **PostgreSQL relacional puro** (no NoSQL): las reservas necesitan integridad referencial fuerte y transacciones ACID (no se puede "casi" reservar un cupo).
- **Patrón de consistencia:** **Saga orquestada** (un coordinador interno, no un event bus complejo, porque al vivir en el mismo proceso que Catálogo/Usuarios puede usar transacciones locales reales; solo cruza a eventos asíncronos cuando llama a Pagos o dispara Notificaciones).
- **Ventaja:** al estar en el mismo monolito que Usuarios y Catálogo, la mayoría de la lógica de reserva es una transacción de base de datos normal, mucho más simple que una saga distribuida completa.
- **Desventaja:** si a futuro Reservas necesita escalar de forma muy distinta a Catálogo, habrá que extraerlo (posible en el roadmap, no en el piloto).

### A.2.3 Módulo Usuarios y Seguridad (dentro del monolito)
- **Función:** registro/login de turistas, operadores y administradores; control de roles.
- **Seguridad a implementar:**
  - **Autenticación:** OAuth2 / OpenID Connect con tokens **JWT** de corta duración + *refresh tokens*.
  - **Autorización:** **RBAC** (turista / operador / administrador de destino), con posibilidad de permisos granulares por módulo (p. ej. un operador solo edita su propio catálogo).
  - **Almacenamiento de contraseñas:** hashing con **Argon2id** (o bcrypt como alternativa más simple).
  - **Transporte:** TLS 1.3 obligatorio en todo el tráfico (HTTPS), certificados gestionados vía Let's Encrypt o el balanceador cloud.
  - **Protección perimetral:** rate limiting en el API Gateway, WAF básico (Cloudflare o el WAF gestionado del proveedor cloud) para mitigar fuerza bruta y bots en temporada alta.
  - **Cumplimiento normativo:** registro de consentimiento y política de tratamiento de datos conforme a la **Ley 1581 de 2012**; cifrado en reposo de datos personales sensibles; trazabilidad (logs de acceso a datos personales) para auditoría.
- **Ventaja:** un único punto de verdad para identidad simplifica enormemente la autorización cruzada entre módulos (comparado con tener que replicar/validar tokens entre varios microservicios).
- **Desventaja:** este módulo se vuelve crítico — su caída afecta a todo el sistema; se mitiga con réplicas del monolito detrás de un balanceador.

### A.2.4 Módulo Financiero / Pagos (dentro del monolito, con pasarela externa)
- **Decisión clave:** **no se construye una pasarela de pagos propia** (fuera de alcance y de las restricciones normativas/PCI-DSS). Se integra una pasarela certificada existente.
- **Pasarela recomendada:** **Wompi** (de Bancolombia) o **ePayco**, por ser opciones colombianas con soporte de PSE, tarjetas y billeteras (Nequi/Daviplata), y comisiones competitivas para pymes/operadores turísticos pequeños. Como referencia de mercado 2026: comisión por tarjeta entre ~2,8% y 3,5% + IVA + un cargo fijo (~COP 600-700) por transacción, y PSE más económico (~1,3%-2%). Se sugiere dejar la integración desacoplada (patrón *adapter*) para poder cambiar de pasarela sin tocar el resto del módulo.
- **Manejo de datos de tarjeta:** el sistema **nunca almacena datos de tarjeta**; se usa *tokenización* del lado de la pasarela (checkout embebido o redirección), de modo que el cumplimiento PCI-DSS recae en el proveedor certificado, no en el prototipo.
- **Función adicional:** cálculo y liquidación de comisiones a operadores (marketplace básico), con registro contable auditable.
- **Ventaja:** tiempo de implementación bajo (SDK/API ya documentada) y cumplimiento normativo delegado al proveedor certificado.
- **Desventaja:** dependencia de un tercero (disponibilidad de la pasarela) y costo variable por transacción que crece con el volumen.

### A.2.5 Módulo Analítica / Reportes (dentro del monolito)
- **Función:** indicadores de ocupación, demanda por atractivo, comportamiento estacional, para apoyar planificación turística.
- **Tipo de almacenamiento:** vistas materializadas o tablas de agregación sobre el mismo PostgreSQL (evita introducir un data warehouse aparte en el piloto). Si el volumen de eventos crece, se puede alimentar después una base analítica ligera (p. ej. **ClickHouse** o **BigQuery**) sin rediseñar el resto.
- **Ventaja:** cero infraestructura adicional en el piloto.
- **Desventaja:** reportes muy pesados pueden competir por recursos con el tráfico transaccional; se mitiga con réplicas de solo lectura.

### A.2.6 Microservicio de IA (extraído)
- **Función a elegir (una de las 4 alternativas del enunciado):** recomendación personalizada, clasificación de opiniones, predicción de ocupación, o chatbot turístico.
- **Por qué se extrae:** su carga de cómputo (inferencia de modelo) y su ciclo de actualización (reentrenar/reajustar el modelo) son distintos al resto del sistema; además, aislarlo facilita el requisito ético de **explicabilidad** (registrar qué señales explican cada recomendación) sin mezclar esa lógica con el resto del dominio.
- **Tecnología sugerida:** Python (FastAPI) + librería según el caso (scikit-learn/LightGBM para predicción o clasificación; embeddings + búsqueda vectorial ligera —p. ej. **pgvector** dentro de PostgreSQL, o Chroma/FAISS local— para recomendación o chatbot con contexto controlado).
- **Base de datos:** vectorial ligera (pgvector es la opción de menor costo porque reutiliza el mismo motor PostgreSQL) o documental si el caso de uso es clasificación de comentarios.
- **Explicabilidad:** cada respuesta de IA debe devolver junto al resultado los criterios que la explican (p. ej. "se recomienda por: preferencias de naturaleza + baja congestión actual"), guardados en un log de auditoría de decisiones.
- **Ventaja:** se puede actualizar/reentrenar sin tocar ni redesplegar el núcleo del sistema.
- **Desventaja:** es el componente con mayor riesgo técnico y de tiempo del proyecto; se recomienda acotar el alcance a un caso de uso simple y bien delimitado (p. ej. recomendación basada en reglas + similitud, no un modelo generativo complejo).

### A.2.7 Microservicio de Notificaciones (extraído)
- **Función:** correos de confirmación de reserva, alertas de disponibilidad, comunicación multilenguaje (ES/EN).
- **Por qué se extrae:** es naturalmente asíncrono (no debe bloquear la transacción de reserva) y se beneficia de una cola de mensajes propia.
- **Tecnología sugerida:** cola ligera (RabbitMQ gestionado o el servicio de colas del proveedor cloud) + proveedor de envío de correo transaccional (SendGrid/Amazon SES) con soporte de plantillas multilenguaje.
- **Ventaja:** reintentos automáticos ante fallos de envío sin afectar la reserva ya confirmada.
- **Desventaja:** introduce el primer punto real de comunicación asíncrona del sistema, que el equipo debe aprender a monitorear (colas atascadas, mensajes fallidos).

## A.3 Ventajas y desventajas globales de la Arquitectura Principal

| Ventajas | Desventajas |
|---|---|
| Menor curva de aprendizaje: 3 de los 5 roles del equipo trabajan sobre una sola base de código | Escalar Catálogo de forma independiente de Reservas no es posible sin extraer el módulo |
| Una sola base de datos relacional para el núcleo → transacciones ACID reales, sin sagas distribuidas complejas | El núcleo es un punto único de fallo si no se replica correctamente |
| IA y Notificaciones aisladas → no arriesgan la estabilidad del núcleo ni bloquean transacciones | Requiere disciplina de diseño (límites de módulo estrictos) para no degradar en "monolito desordenado" |
| Menor costo de infraestructura y de operación (menos piezas que monitorear) | Menos "vistoso" como caso de estudio de microservicios puros si la rúbrica valora fuertemente ese estilo |
| Camino de evolución claro: cada módulo puede extraerse después si el crecimiento real lo justifica | — |

## A.4 Costos — Arquitectura Principal

### A.4.1 Costos de infraestructura (mensual, escenario piloto)

| Recurso | Opción sugerida | Costo aproximado/mes (piloto, bajo tráfico) |
|---|---|---|
| Cómputo del núcleo (2 réplicas pequeñas) | VM/contenedor gestionado (p. ej. AWS Fargate, DigitalOcean App Platform) | USD 20 – 40 |
| Base de datos PostgreSQL gestionada | RDS/DO Managed DB (instancia pequeña) | USD 15 – 30 |
| Microservicio IA (cómputo bajo demanda) | Contenedor pequeño o función serverless | USD 5 – 15 |
| Microservicio Notificaciones + cola | Cola gestionada (SQS/CloudAMQP free/starter) + contenedor pequeño | USD 5 – 10 |
| Almacenamiento de objetos (imágenes de atractivos) | S3/Cloud Storage | USD 2 – 5 |
| Certificados TLS / dominio | Let's Encrypt (gratis) + dominio | USD 1 – 2/mes (dominio anual prorrateado) |
| Envío de correo transaccional | SendGrid/SES nivel gratuito o inicial | USD 0 – 10 |
| Monitoreo básico | Herramienta gratuita/open source (Grafana Cloud free tier) | USD 0 – 10 |
| **Subtotal infraestructura piloto** | | **≈ USD 48 – 122/mes** |

Con créditos educativos habituales (AWS Educate, Google Cloud for Education, Azure for Students, GitHub Student Pack), este costo real durante los 3 meses del proyecto puede quedar en **USD 0** o muy cercano, quedando el presupuesto de USD 20.000 casi íntegro como margen para imprevistos, herramientas de diseño o eventual hosting posterior al piloto.

### A.4.2 Costos por transacción (pasarela de pagos)

| Concepto | Wompi/ePayco (referencia 2026) |
|---|---|
| Tarjeta de crédito/débito | ~2,8% – 3,5% + IVA + ~COP 600-700 fijo por transacción |
| PSE (transferencia bancaria) | ~1,3% – 2% |
| Sin costo fijo mensual de la pasarela para volúmenes pyme | — |

Es un **costo variable de operación real**, no un costo de infraestructura del prototipo; se debe modelar como parte del caso de negocio, no del presupuesto de los USD 20.000 de infraestructura piloto.

### A.4.3 Costos de implementación (esfuerzo del equipo, 3 meses / 5 personas)

Estimación orientativa de distribución de esfuerzo (en % del tiempo total del equipo durante las 12 semanas), asumiendo dedicación estudiantil parcial:

| Frente de trabajo | % esfuerzo estimado | Responsable típico |
|---|---|---|
| Especificación de requisitos y modelado (casos de uso, ADRs) | 15% | Analista + Arquitecto |
| Núcleo monolito modular (Catálogo, Reservas, Usuarios, Financiero, Analítica) | 40% | Desarrollador principal + Arquitecto |
| Integración de pasarela de pagos | 8% | Desarrollador principal |
| Microservicio de IA | 15% | Todo el equipo (apoyo puntual) o rol asignado ad hoc |
| Microservicio de Notificaciones | 7% | Desarrollador principal |
| Seguridad transversal (auth, RBAC, TLS, cumplimiento Ley 1581) | 8% | Responsable de calidad/seguridad |
| Pruebas, validación de escenarios de calidad y despliegue | 7% | Responsable de validación y calidad |

Al no requerir orquestación de contenedores compleja (Kubernetes) ni una malla de servicios, el equipo dedica más horas a funcionalidad de negocio que a "infraestructura de infraestructura" — la razón central por la que esta opción es viable en 3 meses.

---

# B. ARQUITECTURA ALTERNATIVA VIABLE — Microservicios Ligeros Acotados

## B.1 Visión general

Mismo dominio funcional que la propuesta A, pero cada módulo (Catálogo, Reservas, Usuarios, Financiero, IA, Notificaciones, Analítica) es un **servicio independiente**, cada uno con su propia base de datos, detrás de un API Gateway, comunicados por REST/gRPC (síncrono) y un bus de eventos (asíncrono) para el saga de reservas.

```
        ┌─────────────────────────────┐
        │  API Gateway (Kong/Traefik) │
        └───────────────┬─────────────┘
     ┌─────────┬─────────┼─────────┬─────────┬─────────┬─────────┐
     ▼         ▼         ▼         ▼         ▼         ▼         ▼
 Catálogo  Reservas   Usuarios  Financiero    IA     Notific.  Analítica
 (Mongo)  (Postgres) (Postgres) (Postgres) (pgvector) (cola)   (Postgres)
     └─────────┴─────────┴────eventos (bus de mensajes)─┴─────────┘
```

## B.2 Detalle por servicio

### B.2.1 Servicio Catálogo
- **Base de datos:** **MongoDB** (documental) — se justifica aquí, a diferencia de la propuesta A, porque al ser un servicio propio no comparte instancia de PostgreSQL con nadie y el atributo variable por tipo de atractivo encaja de forma natural en documentos.
- **Tecnología:** Node.js/NestJS o Python/FastAPI.
- **Ventaja:** escalado de lectura independiente en temporada alta (los atractivos se consultan mucho más de lo que se modifican).
- **Desventaja:** duplica el trabajo de mantener un motor de base de datos adicional (backups, monitoreo, actualizaciones) solo para este servicio.

### B.2.2 Servicio Reservas/Disponibilidad
- **Base de datos:** PostgreSQL, propia (no compartida).
- **Patrón:** **Saga orquestada** de verdad (a través de red): el propio servicio de Reservas actúa como orquestador, llamando de forma síncrona a Usuarios (validar identidad) y Financiero (autorizar pago), y emitiendo eventos para Notificaciones y Analítica.
- **Ventaja:** aislamiento total de fallos: un pico de tráfico en Catálogo no compromete la capacidad de completar reservas.
- **Desventaja:** cada llamada entre servicios añade latencia de red y un nuevo punto de fallo (se mitiga con *circuit breakers* y *timeouts*, que el equipo debe implementar y probar).

### B.2.3 Servicio Usuarios y Seguridad
- Igual que en la propuesta A (JWT/OAuth2, RBAC, Argon2id, TLS, WAF, cumplimiento Ley 1581), pero aquí **cada microservicio debe validar el token de forma independiente** (o delegarlo en el Gateway), lo que exige una librería/middleware compartido y bien versionado para no duplicar bugs de seguridad entre servicios.

### B.2.4 Servicio Financiero/Pagos
- Misma pasarela recomendada (Wompi/ePayco) y mismas comisiones de mercado (sección A.2.4), pero aislado en su propio servicio con su propia base de datos PostgreSQL — refuerza el aislamiento de datos financieros/sensibles, lo cual es un plus real de seguridad frente a la propuesta A.

### B.2.5 Servicio de IA
- Igual planteamiento técnico que en A.2.6, pero con la ventaja de que su escalado (por ejemplo, autoscaling a cero cuando no hay tráfico) es más limpio al ser un servicio nativamente independiente desde el día uno.

### B.2.6 Servicio de Notificaciones
- Igual que A.2.7, con la diferencia de que en esta arquitectura la cola de eventos ya es el mecanismo de comunicación estándar entre todos los servicios, no una excepción.

### B.2.7 Servicio de Analítica/Reportes
- Se alimenta por eventos de todos los demás servicios (patrón *event sourcing* parcial); requiere un almacén propio (PostgreSQL o ClickHouse) y un mecanismo de reconciliación si algún evento se pierde.

## B.3 Ventajas y desventajas globales de la Arquitectura Alternativa

| Ventajas | Desventajas |
|---|---|
| Aislamiento de fallos real: un servicio caído no tumba a los demás | Requiere API Gateway, bus de eventos, *service discovery* y observabilidad distribuida desde el primer sprint |
| Escalado independiente por servicio (útil si Catálogo tiene picos muy distintos a Reservas) | Depuración de errores cruza varios servicios y logs — más lenta con un equipo sin experiencia previa |
| Persistencia políglota "natural" (Mongo para catálogo, Postgres para lo transaccional) | Backups, migraciones y monitoreo se multiplican por cada base de datos |
| Cada servicio se puede desplegar y actualizar sin afectar a los demás | Mayor superficie de configuración de seguridad (n servicios validando tokens en vez de uno) |
| Encaja mejor si la rúbrica busca explícitamente demostrar dominio de microservicios | Alto riesgo de no completar el 100% del alcance en 3 meses con 5 personas |

## B.4 Costos — Arquitectura Alternativa

### B.4.1 Costos de infraestructura (mensual, escenario piloto)

| Recurso | Costo aproximado/mes |
|---|---|
| 7 servicios en contenedores pequeños (orquestación ligera, no Kubernetes completo) | USD 60 – 100 |
| PostgreSQL gestionado (Reservas, Usuarios, Financiero, Analítica — puede compartirse instancia con esquemas distintos para bajar costo) | USD 20 – 35 |
| MongoDB gestionado (Catálogo) | USD 10 – 25 |
| Bus de mensajes gestionado (RabbitMQ/CloudAMQP o SQS) | USD 10 – 20 |
| API Gateway gestionado o autoalojado (Kong/Traefik) | USD 0 – 15 |
| Observabilidad (logs y trazas distribuidas — imprescindible aquí, no opcional) | USD 10 – 25 |
| Almacenamiento de objetos, dominio, TLS, correo | USD 5 – 15 |
| **Subtotal infraestructura piloto** | **≈ USD 115 – 235/mes** |

Aproximadamente **2 a 2.5 veces más caro** que la propuesta A incluso en su versión "ligera", principalmente por la duplicación de motores de base de datos y la necesidad de observabilidad distribuida desde el inicio. Sigue estando muy por debajo del techo de USD 20.000, pero exige más tiempo de aprendizaje que dinero.

### B.4.2 Costos de implementación (esfuerzo del equipo)

| Frente de trabajo | % esfuerzo estimado |
|---|---|
| Especificación y modelado | 12% |
| Infraestructura compartida: Gateway, bus de eventos, observabilidad, CI/CD por servicio | 20% |
| Desarrollo de los 7 servicios (funcionalidad de negocio) | 40% |
| Integración de pasarela de pagos | 6% |
| Seguridad transversal (auth distribuida, RBAC, TLS, Ley 1581) | 10% |
| Pruebas de integración entre servicios y validación de escenarios de calidad | 12% |

El punto crítico frente a la propuesta A: **20% del tiempo total se va en infraestructura compartida antes de escribir la primera línea de lógica de negocio**, tiempo que en la propuesta A se invierte directamente en funcionalidad.

---

# C. Resumen Comparativo de Costos

| Rubro | A. Monolito Modular + Extracción | B. Microservicios Ligeros |
|---|---|---|
| Infraestructura piloto (mensual) | USD 48 – 122 | USD 115 – 235 |
| Motores de base de datos a mantener | 1 relacional + 1 vectorial ligero (mismo motor) | 2-3 motores distintos (relacional, documental, vectorial) |
| % de tiempo del equipo en infraestructura vs. funcionalidad | ~15% infraestructura / 85% funcionalidad | ~32% infraestructura / 68% funcionalidad |
| Riesgo de no completar el 60% mínimo de casos de uso en 3 meses | Bajo | Medio-alto |
| Costo de la pasarela de pagos | Igual en ambas: ~2,8%-3,5% + IVA + fijo por transacción (tarjeta); ~1,3%-2% (PSE) | Igual |
| Margen frente al techo de USD 20.000 | Amplio | Amplio, pero con menos margen de tiempo del equipo |

**Conclusión:** ambas caben cómodamente en el presupuesto económico de USD 20.000 (que está pensado para infraestructura, no para nómina), por lo que la variable que realmente decide entre A y B es el **tiempo del equipo**, no el dinero. La Arquitectura Principal (A) libera más horas para funcionalidad de negocio y reduce el riesgo de no llegar al 60% de casos de uso exigido; la Arquitectura Alternativa (B) es viable si el equipo tiene ya experiencia previa con contenedores/mensajería y quiere demostrar explícitamente dominio de microservicios distribuidos como parte de la sustentación.
