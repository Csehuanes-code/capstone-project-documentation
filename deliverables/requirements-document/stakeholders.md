## Identificación de Stakeholders

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Framework: TOGAF & BABOK](https://img.shields.io/badge/Framework-TOGAF_%7C_BABOK-orange?style=flat-square)

> [!NOTE]
> **Propósito de la Sección:** En cumplimiento con el estándar **ISO/IEC/IEEE 29148:2018** y los lineamientos de arquitectura, esta sección identifica, clasifica y especifica a todas las partes interesadas (stakeholders) que tienen un impacto o interés en la *Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta*. 

---

### 1. Matriz General de Clasificación de Stakeholders

La siguiente matriz mapea a los actores clave basándose en el diagrama de cebolla (nivel de involucramiento) y la matriz de Poder/Interés para definir su estrategia de gestión.

| ID | Stakeholder | Categoría (ISO 29148) | Capa de Interacción (Onion) | Poder / Interés (TOGAF) |
| :--- | :--- | :--- | :--- | :--- |
| **SH-01** | 🎒 **Turista Nacional / Internacional** | Usuario final | Unidad afectada | Bajo / Alto (Mantener informado) |
| **SH-02** | 🏪 **Pequeño/Mediano Prestador Turístico** | Usuario final / Cliente | Unidad afectada | Bajo / Alto (Mantener informado) |
| **SH-03** | 🏨 **Hotel/Operador Establecido** | Usuario final / Cliente | Unidad afectada | Medio / Alto (Mantener informado) |
| **SH-04** | ⚙️ **Administrador de la Plataforma** | Operador | Núcleo | Alto / Alto (Gestionar de cerca) |
| **SH-05** | 💻 **Equipo de Desarrollo (5 roles)** | Desarrollador | Núcleo | Alto / Alto (Gestionar de cerca) |
| **SH-06** | 🎓 **Docente Evaluador / Comité Académico**| Adquirente / Patrocinador | Organización | Alto / Alto (Gestionar de cerca) |
| **SH-07** | 🏛️ **Entidad de Gestión del Destino** | Patrocinador | Organización | Alto / Medio (Mantener satisfecho) |
| **SH-08** | 🌿 **Autoridad Ambiental (Tayrona)** | Organismo Regulador | Entorno externo | Alto / Bajo (Mantener satisfecho) |
| **SH-09** | ⚖️ **Autoridad de Protección de Datos** | Organismo Regulador | Entorno externo | Alto / Bajo (Mantener satisfecho) |
| **SH-10** | ☁️ **Proveedor Cloud / Infraestructura** | Organización Proveedora | Entorno externo | Medio / Bajo (Monitorear) |
| **SH-11** | ♿ **Usuarios con Discapacidad / Baja Alfabetización** | Usuario final (Transversal)| Unidad afectada | Bajo / Alto (Mantener informado) |

---

### 2. Especificación Detallada de Stakeholders Críticos (Fichas Técnicas)

> [!IMPORTANT]
> A continuación se detallan las fichas de los actores primarios y reguladores con mayor impacto arquitectónico en el sistema, integrando necesidades, protección de activos (NIST) y trazabilidad.

#### 🎒 SH-01: Turista Nacional / Internacional
* **Rol RACI:** Consultado (C) / Informado (I)
* **Elemento C4 (Contexto):** Actor Externo `[Persona: Turista]`
* **Necesidades y Contexto de uso:** Requiere consultar disponibilidad, planificar y gestionar reservas de forma unificada y confiable, especialmente en picos de demanda.
* **Activo a Proteger (NIST):** Datos personales, información financiera y datos de geolocalización.
* **Requisitos Derivados:** Disponibilidad del 99%, soporte multilenguaje (español/inglés), tiempos de respuesta ágiles bajo alta concurrencia.
* **ADRs de Impacto:** Estrategia de escalabilidad, Modelo de persistencia para lecturas rápidas.

#### 🏪 SH-02: Pequeño/Mediano Prestador Turístico
* **Rol RACI:** Consultado (C)
* **Elemento C4 (Contexto):** Actor Externo `[Persona: Operador Turístico]`
* **Necesidades y Contexto de uso:** Requiere visibilidad e inclusión en el ecosistema digital para ofertar sus servicios sin barreras tecnológicas altas.
* **Activo a Proteger (NIST):** Información comercial (tarifas, disponibilidad, reputación).
* **Requisitos Derivados:** Interfaces de gestión simplificadas, equidad algorítmica (transparencia en las recomendaciones de IA sin sesgo comercial).
* **ADRs de Impacto:** Diseño de API de integración, Selección del modelo de IA explicable.

#### ⚙️ SH-04: Administrador de la Plataforma
* **Rol RACI:** Responsable (R) / Aprobador (A)
* **Elemento C4 (Contexto):** Actor Interno `[Persona: Admin Sistema]`
* **Necesidades y Contexto de uso:** Necesita monitorear la salud del sistema, gestionar accesos, y obtener indicadores consolidados para la gobernanza de los datos.
* **Activo a Proteger (NIST):** Integridad del sistema, bases de datos centrales, llaves de acceso a integraciones (pagos/nube).
* **Requisitos Derivados:** Dashboards de monitoreo de capacidad de carga, trazabilidad de auditoría, gestión de roles y permisos.
* **ADRs de Impacto:** Arquitectura de seguridad y control de acceso, Herramientas de telemetría/observabilidad.

#### ⚖️ SH-09: Autoridad de Protección de Datos (Ley 1581)
* **Rol RACI:** Informado (I) / Aprobador regulatorio implícito (A)
* **Elemento C4 (Contexto):** Entidad Externa Normativa
* **Necesidades y Contexto de uso:** Exige el cumplimiento estricto de la ley de hábeas data para el tratamiento de información de turistas y operadores.
* **Activo a Proteger (NIST):** Privacidad de la información ciudadana, trazabilidad del consentimiento.
* **Requisitos Derivados:** Cifrado de datos en tránsito y reposo, mecanismos de anonimización, flujos explícitos de aceptación de términos.
* **ADRs de Impacto:** Estrategia de seguridad (Criptografía), Selección del motor de base de datos (Soporte TDE).

#### ♿ SH-11: Usuarios con Discapacidad / Baja Alfabetización Digital
* **Rol RACI:** Consultado (C)
* **Elemento C4 (Contexto):** Subgrupo de Actor Externo `[Persona: Turista / Operador]`
* **Necesidades y Contexto de uso:** Interacción intuitiva y sin fricciones visuales/cognitivas para navegar y consumir servicios.
* **Activo a Proteger (NIST):** Integridad y autonomía en la experiencia de usuario.
* **Requisitos Derivados:** Cumplimiento de accesibilidad W3C WCAG (mínimo nivel AA), diseño UX/UI adaptativo e inclusivo.
* **ADRs de Impacto:** Estándares de diseño de frontend, Selección de frameworks UI accesibles.
