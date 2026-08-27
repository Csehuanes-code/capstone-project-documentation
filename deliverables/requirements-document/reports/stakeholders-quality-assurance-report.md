**REPORTE DE ASEGURAMIENTO DE CALIDAD (QA) - INGENIERÍA DE REQUISITOS**

**Documento evaluado:** `stakeholders.md`
**Documento base (Criterios de Aceptación):** `fundamentos stakeholders.md`
**Estándares aplicados:** ISO/IEC/IEEE 29148:2018, TOGAF, IIBA/BABOK, NIST SP 800-160, W3C WCAG, MinTIC (MAE), C4 Model.
**Evaluador:** Senior QA Analyst

---

### 1. RESUMEN EJECUTIVO

El documento `stakeholders.md` presenta un esfuerzo inicial sólido para alinear la identificación de los interesados con el marco normativo exigido. Se evidencia una correcta apropiación de los conceptos de TOGAF (Matriz Poder/Interés), BABOK (Diagrama de Cebolla y RACI), NIST (Activos a proteger) y Modelo C4.

Sin embargo, el documento **NO CUMPLE** con el rigor exhaustivo exigido por la fundamentación, presentando omisiones críticas en la completitud del listado de stakeholders, la estructura de las fichas de especificación (faltan campos obligatorios como la RTM) y la cobertura de documentación (se omitieron stakeholders no humanos y normativos, y no se documentaron todos los actores identificados).

**Nivel de Cumplimiento General: ⚠️ Parcial (Requiere Refactorización)**

---

### 2. ANÁLISIS DETALLADO POR SECCIONES

#### Sección 1: Matriz General de Clasificación de Stakeholders

*Evaluación de la identificación y clasificación general.*

* ✅ **QUÉ SÍ CUMPLE:**
* **Categorización ISO 29148:** Utiliza correctamente los roles estándar (Usuario final, Operador, Desarrollador, Adquirente, Organismo Regulador, etc.).
* **BABOK (Onion Diagram):** Clasifica adecuadamente a los actores en las capas de Unidad afectada, Núcleo, Organización y Entorno externo.
* **TOGAF (Matriz):** Define correctamente la estrategia de involucramiento basada en Poder/Interés (Gestionar de cerca, Mantener informado, etc.).


* ❌ **QUÉ NO CUMPLE (Omisiones Críticas):**
* **Pérdida de Stakeholders:** El documento base listaba 14 stakeholders (incluyendo sistemas no humanos y entidades clave recomendadas). El documento evaluado solo lista 11.
* *Faltan:* **MinTIC** (Referente MAE normativo), **Servicio externo de pagos/reservas** (Sistema externo - C4) y **Servicio de IA de recomendación** (Componente interno). Según la directiva de la ISO 29148 en la base: *"ningún actor debe descartarse por obvio ni por estar fuera del software en sí"*.


* 💡 **CÓMO MEJORAR:** Integrar a los 3 stakeholders faltantes a la matriz. En arquitectura de software moderna (y C4), los sistemas externos con los que se interactúa son stakeholders válidos con necesidades técnicas específicas.

#### Sección 2: Especificación Detallada de Stakeholders (Fichas Técnicas)

*Evaluación de las fichas de requisitos por actor.*

* ✅ **QUÉ SÍ CUMPLE:**
* **NIST SP 800-160:** Excelente inclusión del campo "Activo a Proteger" orientando los requisitos hacia la ciberseguridad (ej. integridad del sistema, datos personales).
* **Modelo C4:** Integra explícitamente el mapeo al diagrama de contexto (`[Persona: Turista]`, `Entidad Externa Normativa`), cerrando la brecha entre requisitos y arquitectura.
* **RACI & ADRs:** Identifica correctamente los niveles de responsabilidad (BABOK) y vincula las necesidades con Decisiones Arquitectónicas (ADRs).


* ❌ **QUÉ NO CUMPLE:**
* **Cobertura Incompleta:** La fundamentación dicta explícitamente que *"cada stakeholder del proyecto debe documentarse con esta ficha mínima"*. El documento evaluado solo documenta 5 actores ("críticos"), ignorando a los otros 6 listados en su propia matriz. Para cumplir con ISO 29148, **todos** deben ser especificados.
* **Campos Faltantes en la Plantilla Integrada:** La fundamentación exige 12 campos por ficha. Al revisar las fichas presentadas, faltan campos exigidos:
1. **Fila(s) correspondientes en la RTM:** Totalmente ausente. Esto rompe la trazabilidad bidireccional exigida ("Instrumento de cierre del ciclo").
2. **Requisitos de accesibilidad/inclusión (W3C WCAG):** Solo se incluyó implícitamente en el SH-11, pero la plantilla exige que sea un campo evaluado para los demás usuarios finales (ej. Turista SH-01 o Prestador SH-02).




* 💡 **CÓMO MEJORAR:**
* Expandir la Sección 2 para incluir **todas** las filas de la Matriz General.
* Agregar explícitamente el campo `Filas RTM:` a cada ficha (pueden dejarse como `[Por definir en fase de pruebas]` si aún no hay IDs de prueba, pero el campo debe existir).
* Agregar el campo `Accesibilidad (W3C):` a las fichas de actores humanos.



---

### 3. REPORTE DE HALLAZGOS Y NO CONFORMIDADES (GAP ANALYSIS)

| Criterio Base (`fundamentos.md`) | Estado en `stakeholders.md` | Severidad | Comentario del QA |
| --- | --- | --- | --- |
| **Identificación exhaustiva (ISO 29148)** | ❌ No Cumple | Alta | Faltan MinTIC y sistemas automatizados externos (Pagos, IA). |
| **Clasificación TOGAF / BABOK** | ✅ Cumple | N/A | Las clasificaciones de la matriz coinciden con el estándar. |
| **Documentación de CADA stakeholder** | ❌ No Cumple | Crítica | Solo se documentaron 5 de 11. Se deben documentar todos mediante las fichas. |
| **Plantilla unificada de 12 campos** | ⚠️ Parcial | Media | La matriz general (Tabla 1) tiene 5 campos y las fichas (Sección 2) tienen 6 campos. Total = 11. Falta RTM. |
| **Trazabilidad RTM** | ❌ No Cumple | Crítica | No hay mención a la Matriz de Trazabilidad de Requisitos (RTM). |
| **W3C WCAG (Accesibilidad)** | ⚠️ Parcial | Baja | Tratado como un actor separado (SH-11) en lugar de un atributo transversal (campo de la ficha) para todos los usuarios. |
| **Protección de Activos (NIST)** | ✅ Cumple | N/A | Correctamente documentado en los actores desarrollados. |

---

### 4. CONCLUSIÓN Y DICTAMEN

**Dictamen: RECHAZADO EN SU VERSIÓN ACTUAL. DEBE SER CORREGIDO.**

**Plan de Acción inmediato para el Analista/Arquitecto:**

1. **Restaurar los stakeholders eliminados:** Añadir los sistemas (Pagos, IA) y a MinTIC a la matriz de la Sección 1.
2. **Completar las fichas:** Crear las fichas técnicas para el 100% de los stakeholders listados en la Sección 1 (incluyendo desarrolladores, entidad de gestión, etc.), no solo los "críticos".
3. **Actualizar la estructura de las fichas:** Añadir las líneas `Requisitos W3C:` y `Trazabilidad RTM:` a todas las fichas de la Sección 2 para cumplir estrictamente con la plantilla integrada de la fundamentación.
