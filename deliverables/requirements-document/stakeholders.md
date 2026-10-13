## Identificación de Stakeholders

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Framework: TOGAF & BABOK](https://img.shields.io/badge/Framework-TOGAF_%7C_BABOK-orange?style=flat-square)

> [!NOTE]
> **Propósito de la Sección:** En cumplimiento con el estándar **ISO/IEC/IEEE 29148:2018** y los lineamientos de arquitectura, esta sección identifica, clasifica y especifica a todas las partes interesadas (stakeholders) que tienen un impacto o interés en la *Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta*. 

---

### Matriz General de Clasificación de Stakeholders

La siguiente matriz mapea a los actores clave basándose en el diagrama de cebolla (nivel de involucramiento) y la matriz de Poder/Interés (TOGAF) para definir su estrategia de gestión, sin descartar entidades normativas ni sistemas automatizados externos.

| ID | Stakeholder | Categoría (ISO 29148) | Capa de Interacción (Onion) | Poder / Interés (TOGAF) |
| :--- | :--- | :--- | :--- | :--- |
| **SH-01** | **Turista Nacional / Internacional** | Usuario final | Unidad afectada | Bajo / Alto (Mantener informado) |
| **SH-02** | **Pequeño/Mediano Prestador Turístico** | Usuario final / Cliente | Unidad afectada | Bajo / Alto (Mantener informado) |
| **SH-03** | **Hotel/Operador Establecido** | Usuario final / Cliente | Unidad afectada | Medio / Alto (Mantener informado) |
| **SH-04** | **Administrador de la Plataforma** | Operador | Núcleo | Alto / Alto (Gestionar de cerca) |
| **SH-05** | **Equipo de Desarrollo (5 roles)** | Desarrollador | Núcleo | Alto / Alto (Gestionar de cerca) |
| **SH-06** | **Docente Evaluador / Comité Académico**| Adquirente / Patrocinador | Organización | Alto / Alto (Gestionar de cerca) |
| **SH-07** | **Entidad de Gestión del Destino** | Patrocinador | Organización | Alto / Medio (Mantener satisfecho) |
| **SH-08** | **Autoridad Ambiental (Tayrona)** | Organismo Regulador | Entorno externo | Alto / Bajo (Mantener satisfecho) |
| **SH-09** | **Autoridad de Protección de Datos** | Organismo Regulador | Entorno externo | Alto / Bajo (Mantener satisfecho) |
| **SH-10** | **Proveedor Cloud / Infraestructura** | Organización Proveedora | Entorno externo | Medio / Bajo (Monitorear) |
| **SH-11** | **MinTIC (Referente MAE)** | Organismo Normativo | Entorno externo | Bajo / Bajo (Monitorear) |
| **SH-12** | **Servicio Externo de Pagos/Reservas** | Sistema Externo | Entorno externo | Medio / Medio (Gestionar de cerca) |
| **SH-13** | **Servicio de IA de Recomendación** | Componente del Sistema | Núcleo | N/A (Mapeado en Modelo C4) |
| **SH-14** | **Usuarios con Discapacidad / Baja Alfabetización** | Usuario final (Transversal)| Unidad afectada | Bajo / Alto (Mantener informado) |

---

### Especificación Detallada de Stakeholders (Fichas Técnicas)

#### SH-01: Turista Nacional / Internacional
* **Rol RACI:** Consultado (C) / Informado (I)
* **Elemento C4 (Contexto):** Actor Externo `[Persona: Turista]`
* **Necesidades y Contexto de uso:** Requiere consultar disponibilidad, planificar y gestionar reservas de forma unificada y confiable, especialmente en picos de demanda.
* **Activo a Proteger (NIST):** Datos personales, información financiera y geolocalización.
* **Accesibilidad (W3C WCAG):** Cumplimiento mínimo AA en interfaces de búsqueda y reserva.
* **Requisitos Derivados (ISO 29148):** RNF-DISP-01 (Disponibilidad ≥99%), RNF-USA-02 (Soporte Multilenguaje ES/EN), RNF-DESM-01 (Tiempos de respuesta p95 < 800ms).
* **ADRs de Impacto:** Estrategia de escalabilidad, Modelo de persistencia para lecturas rápidas.
* **Filas RTM:** Trazabilidad directa con CU-01 a CU-18, y CU-21.

#### SH-02: Pequeño/Mediano Prestador Turístico
* **Rol RACI:** Consultado (C)
* **Elemento C4 (Contexto):** Actor Externo `[Persona: Operador Turístico]`
* **Necesidades y Contexto de uso:** Requiere visibilidad e inclusión digital sin barreras tecnológicas altas.
* **Activo a Proteger (NIST):** Información comercial (tarifas, disponibilidad, reputación).
* **Accesibilidad (W3C WCAG):** Interfaz de gestión de inventario con cumplimiento AA e interacciones simplificadas.
* **Requisitos Derivados (ISO 29148):** RF-CAT-08 (Formulario de gestión simplificado), RF-IA-06 (Equidad algorítmica sin sesgo comercial).
* **ADRs de Impacto:** Diseño de API de integración, Selección del modelo de IA explicable.
* **Filas RTM:** Trazabilidad con CU-22, CU-24, CU-25, CU-26.

#### SH-03: Hotel/Operador Establecido
* **Rol RACI:** Consultado (C)
* **Elemento C4 (Contexto):** Actor Externo `[Persona: Operador Mayor]`
* **Necesidades y Contexto de uso:** Sincronización masiva de inventarios y datos estadísticos de ocupación.
* **Activo a Proteger (NIST):** Bases de datos de clientes, integridad de las transacciones comerciales.
* **Accesibilidad (W3C WCAG):** Nivel A/AA en paneles de control y métricas.
* **Requisitos Derivados (ISO 29148):** RF-CAT-11 (Sincronización de inventario por lote), RNF-INT-01 (Procesamiento masivo de registros).
* **ADRs de Impacto:** Estrategia de comunicación entre sistemas y balanceo de carga.
* **Filas RTM:** Trazabilidad con CU-23, CU-24, CU-25.

#### SH-04: Administrador de la Plataforma
* **Rol RACI:** Responsable (R) / Aprobador (A)
* **Elemento C4 (Contexto):** Actor Interno `[Persona: Admin Sistema]`
* **Necesidades y Contexto de uso:** Monitoreo del sistema, gestión de accesos y métricas de gobernanza.
* **Activo a Proteger (NIST):** Integridad del sistema, bases de datos centrales, llaves de API.
* **Accesibilidad (W3C WCAG):** Cumplimiento AA en dashboards administrativos.
* **Requisitos Derivados (ISO 29148):** RF-ANA-01 (Cálculo de indicadores turísticos), RF-OPS-01 (Monitoreo de salud), RF-USR-24 (Log de auditoría).
* **ADRs de Impacto:** Arquitectura de seguridad y control de acceso, Herramientas de telemetría.
* **Filas RTM:** Trazabilidad directa con CU-27 a CU-34.

#### SH-05: Equipo de Desarrollo (5 roles)
* **Rol RACI:** Responsable (R)
* **Elemento C4 (Contexto):** Actor Interno `[Persona: Equipo Dev]`
* **Necesidades y Contexto de uso:** Creación y mantenimiento de la arquitectura, requiriendo entornos limpios y pipelines estables.
* **Activo a Proteger (NIST):** Código fuente, credenciales de infraestructura, variables de entorno.
* **Accesibilidad (W3C WCAG):** N/A para el código, pero responsables de implementar los estándares.
* **Requisitos Derivados (ISO 29148):** RNF-MANT-01 (Cobertura de pruebas y ciclo de despliegue < 15 min).
* **ADRs de Impacto:** Selección metodológica, estándares de control de versiones.
* **Filas RTM:** Trazable a NFRs de Mantenibilidad e Integración Continua.

#### SH-06: Docente Evaluador / Comité Académico
* **Rol RACI:** Aprobador (A) / Informado (I)
* **Elemento C4 (Contexto):** Actor Externo `[Persona: Evaluador]`
* **Necesidades y Contexto de uso:** Verificación del rigor ingenieril, trazabilidad de requerimientos a arquitectura.
* **Activo a Proteger (NIST):** Trazabilidad de decisiones, integridad de la evaluación académica.
* **Accesibilidad (W3C WCAG):** N/A.
* **Requisitos Derivados (ISO 29148):** RC-P04 (Implementar mínimo el 60% de los CUs), RC-P05 (Evaluación arquitectónica justificada).
* **ADRs de Impacto:** Transversales a todo el proyecto.
* **Filas RTM:** Trazable con todas las actas de ADRs y tabla de validación de restricciones.

#### SH-07: Entidad de Gestión del Destino
* **Rol RACI:** Informado (I) / Consultado (C)
* **Elemento C4 (Contexto):** Actor Externo `[Organización: Entidad Turismo]`
* **Necesidades y Contexto de uso:** Apoyo en planificación territorial mediante indicadores de movilidad y ocupación.
* **Activo a Proteger (NIST):** Confidencialidad de la data macroeconómica y estratégica.
* **Accesibilidad (W3C WCAG):** Reportes generados en formatos accesibles (AA).
* **Requisitos Derivados (ISO 29148):** RF-ANA-01 (Exportación de indicadores de concentración y demanda), RF-ANA-02 (Reportes accesibles).
* **ADRs de Impacto:** Modelo de datos analítico vs. transaccional.
* **Filas RTM:** Trazabilidad con CU-30.

#### SH-08: Autoridad Ambiental (Tayrona)
* **Rol RACI:** Informado (I)
* **Elemento C4 (Contexto):** Entidad Externa Normativa
* **Necesidades y Contexto de uso:** Controlar el impacto ambiental mitigando la concentración turística.
* **Activo a Proteger (NIST):** Información de capacidad de carga de ecosistemas sensibles.
* **Accesibilidad (W3C WCAG):** N/A.
* **Requisitos Derivados (ISO 29148):** RF-ANA-05 (Alerta de superación de capacidad de carga al 90%), RF-IA-05 (Redirección a zonas alternativas de menor congestión).
* **ADRs de Impacto:** Lógica del motor de recomendación orientada a sostenibilidad.
* **Filas RTM:** Trazabilidad con CU-31 y CU-21.

#### SH-09: Autoridad de Protección de Datos (Ley 1581)
* **Rol RACI:** Aprobador regulatorio implícito (A) / Informado (I)
* **Elemento C4 (Contexto):** Entidad Externa Normativa
* **Necesidades y Contexto de uso:** Cumplimiento estricto del hábeas data en el ecosistema.
* **Activo a Proteger (NIST):** Privacidad ciudadana, consentimientos firmados.
* **Accesibilidad (W3C WCAG):** N/A.
* **Requisitos Derivados (ISO 29148):** RNF-SEG-03 (Cifrado en reposo de datos personales sensibles), RF-USR-15 (Solicitudes de acceso, rectificación, eliminación o portabilidad).
* **ADRs de Impacto:** Estrategia criptográfica y TDE.
* **Filas RTM:** Trazabilidad con CU-01, CU-06, CU-33.

#### SH-10: Proveedor Cloud / Infraestructura
* **Rol RACI:** Consultado (C)
* **Elemento C4 (Contexto):** Sistema Externo `[Plataforma: Cloud Provider]`
* **Necesidades y Contexto de uso:** Proveer instancias de procesamiento y bases de datos ajustadas a la demanda y presupuesto.
* **Activo a Proteger (NIST):** Integridad de la infraestructura, mitigación de ataques DDoS.
* **Accesibilidad (W3C WCAG):** N/A.
* **Requisitos Derivados (ISO 29148):** RNF-ESC-01 (Escalado horizontal en < 5 minutos sin pérdida de solicitudes).
* **ADRs de Impacto:** Elección de modelo de despliegue (IaaS vs PaaS).
* **Filas RTM:** Trazabilidad con CU-32.

#### SH-11: MinTIC (Referente MAE)
* **Rol RACI:** Informado (I)
* **Elemento C4 (Contexto):** Entidad Externa Normativa
* **Necesidades y Contexto de uso:** Fomentar estándares de arquitectura empresarial (MAE) y gobierno digital.
* **Activo a Proteger (NIST):** Estándares de interoperabilidad estatal.
* **Accesibilidad (W3C WCAG):** N/A.
* **Requisitos Derivados (ISO 29148):** RNF-USA-01 (Cumplimiento de la Resolución 1519 de 2020 de MinTIC referente a WCAG AA).
* **ADRs de Impacto:** Definición del estilo arquitectónico base.
* **Filas RTM:** Trazabilidad transversal en la selección de tecnologías web (ADR-09).

#### SH-12: Servicio Externo de Pagos/Reservas
* **Rol RACI:** Informado (I) / Consultado (C)
* **Elemento C4 (Contexto):** Sistema Externo `[Sistema: Pasarela de Pagos]`
* **Necesidades y Contexto de uso:** Procesamiento seguro de transacciones monetarias sin comprometer la PCI-DSS de la pasarela original.
* **Activo a Proteger (NIST):** Datos financieros confidenciales, tokens de transacción.
* **Accesibilidad (W3C WCAG):** N/A.
* **Requisitos Derivados (ISO 29148):** RF-PAG-01 (Delegación de PCI-DSS, cero captura de tarjetas localmente), RF-PAG-04 (Reintentos con Circuit Breaker ante fallos).
* **ADRs de Impacto:** Estrategias de resiliencia (Circuit Breaker, Retries).
* **Filas RTM:** Trazabilidad directa con CU-16, CU-17 y CU-34.

#### SH-13: Servicio de IA de Recomendación
* **Rol RACI:** N/A (Sistema Automatizado)
* **Elemento C4 (Contexto):** Componente Interno / Externo (dependiendo del despliegue)
* **Necesidades y Contexto de uso:** Recibir data de contexto limpia para generar sugerencias de rutas y atractivos.
* **Activo a Proteger (NIST):** Modelos de inferencia y pesos de los algoritmos.
* **Accesibilidad (W3C WCAG):** N/A.
* **Requisitos Derivados (ISO 29148):** RNF-IA-01 (Criterio explicativo verificable en el 100% de las sugerencias), RF-IA-01 (Recomendación basada en preferencias del turista).
* **ADRs de Impacto:** Elección de arquitectura orientada a servicios/microservicios.
* **Filas RTM:** Trazabilidad directa con CU-21.

#### SH-14: Usuarios con Discapacidad / Baja Alfabetización
* **Rol RACI:** Consultado (C)
* **Elemento C4 (Contexto):** Subgrupo Transversal `[Persona: Turista/Operador]`
* **Necesidades y Contexto de uso:** Experiencia sin barreras cognitivas, motoras o visuales.
* **Activo a Proteger (NIST):** Autonomía, usabilidad y equidad.
* **Accesibilidad (W3C WCAG):** Nivel AA estricto en el 100% de la UI/UX.
* **Requisitos Derivados (ISO 29148):** RNF-USA-01 (Cumplimiento WCAG 2.1 nivel AA evaluable), RF-USR-14 (Alto contraste y tamaño de fuente).
* **ADRs de Impacto:** Selección del framework de Frontend y librerías UI.
* **Filas RTM:** Trazabilidad con CU-05 y transversal a las interfaces de CU-07, CU-11 y CU-22.
