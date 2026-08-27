## Especificación de Contexto del Proyecto

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Arquitectura: Diseño](https://img.shields.io/badge/Fase-Dise%C3%B1o_Arquitect%C3%B3nico-success?style=flat-square)

> **Proyecto:** Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta.

---

### Entorno Operativo
Santa Marta es uno de los principales destinos turísticos del Caribe colombiano, atrayendo a miles de visitantes nacionales e internacionales hacia atractivos ecológicos, culturales y de playa (como el Parque Tayrona y la Sierra Nevada). El entorno operativo involucra a turistas, entidades de gestión del destino, y prestadores de servicios de diversos tamaños y capacidades tecnológicas.

### Situación Actual y Deficiencias (Estado *As-Is*)

> [!WARNING]
> **El Problema Central:** Actualmente, el ecosistema de información turística de la ciudad se encuentra altamente fragmentado y distribuido en múltiples plataformas independientes (hoteles, redes sociales, sistemas aislados) que manejan diferentes estructuras de datos y niveles de actualización.

Esta fragmentación desencadena las siguientes problemáticas críticas que justifican el proyecto:

*   **Sostenibilidad:** Concentración excesiva de turistas en zonas específicas, lo que amenaza la capacidad de carga del destino.
*   **Visibilidad:** Baja inclusión digital de los pequeños y medianos prestadores de servicios turísticos.
*   **Gestión de Demanda:** Ausencia de un mecanismo centralizado, confiable y escalable para consultar disponibilidad y gestionar reservas, especialmente durante picos de alta demanda.
*   **Gobernanza:** Carencia de indicadores consolidados que apoyen la planificación turística por parte de las entidades gestoras.

### Concepto de la Solución (Estado *To-Be*)

> [!IMPORTANT]
> **Objetivo Arquitectónico:** Se requiere el diseño de un prototipo funcional de una plataforma digital inteligente que centralice, integre y gestione la oferta turística de manera interoperable.

El sistema actuará como un ecosistema unificado que integrará múltiples fuentes heterogéneas de datos, permitiendo a los turistas consultar disponibilidad, realizar reservas y recibir recomendaciones personalizadas basadas en inteligencia artificial.

### Restricciones del Contexto (Límites Arquitectónicos)

El diseño e implementación de la solución están estrictamente condicionados por las siguientes restricciones del entorno operativo, las cuales guiarán las decisiones de arquitectura de software:

| Categoría | Especificación de la Restricción |
| :--- | :--- |
| **Técnicas** | El sistema debe soportar alta concurrencia garantizando una disponibilidad mínima del **99%**. |
| **Económicas** | Se debe diseñar como un escenario piloto con un presupuesto máximo de **USD 20.000** para infraestructura, priorizando software libre y nube de bajo costo. |
| **Sociales y Ambientales** | Debe ser multilenguaje, accesible para usuarios con baja alfabetización digital y personas con discapacidad. Debe promover el turismo sostenible controlando la capacidad de carga y redistribuyendo la congestión. |
| **Normativas y Éticas** | Obligatoriedad de cumplimiento de la **Ley 1581 de 2012** (Protección de datos). Debe proveer transparencia y explicabilidad en las recomendaciones generadas por algoritmos, evitando el sesgo comercial. |
