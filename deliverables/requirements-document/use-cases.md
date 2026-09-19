## Especificación de Casos de Uso

![Status: Piloto](https://img.shields.io/badge/Status-Piloto-blue?style=flat-square) ![Contexto: Académico](https://img.shields.io/badge/Contexto-Acad%C3%A9mico-lightgrey?style=flat-square) ![Estándar: ISO 29148](https://img.shields.io/badge/Est%C3%A1ndar-ISO%2F29148-success?style=flat-square) ![Notación: UML](https://img.shields.io/badge/Notaci%C3%B3n-UML_%7C_Mermaid-orange?style=flat-square)

> [!NOTE]
> **Propósito de la Sección:** En cumplimiento con **ISO/IEC/IEEE 29148:2018** y la plantilla unificada definida en `use-cases-standard.md` (síntesis ISO 29148 + UML/RUP + Cockburn), esta sección identifica, prioriza y especifica los Casos de Uso de la *Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta*. Cada caso de uso se deriva del registro de 14 stakeholders (`stakeholders.md`) y queda trazado a `Objetivos.md` y `Restricciones.md`.

> [!IMPORTANT]
> **Corrección de alcance:** una primera versión de este documento (14 casos de uso) cubría solo el núcleo transaccional. Tras revisar sistemas comparables del dominio (ver benchmarking abajo) y volver a recorrer `Descripcion-General.md`, `Objetivos.md` y el registro completo de 14 stakeholders, se identificaron flujos secundarios pero necesarios que estaban ausentes (recuperación de cuenta, favoritos/itinerarios, lista de espera, disputas de pago, moderación de contenido, verificación de prestadores, monitoreo operativo, integraciones externas). Esta versión los incorpora, ampliando el total a **34 casos de uso** organizados en 6 módulos/actores.

---

### Nota metodológica: benchmarking de proyectos similares

Se revisaron plataformas y trabajos académicos comparables del dominio turístico para contrastar cobertura de actores y casos de uso:

- **Sistemas de reserva de viajes/hoteles**: además del núcleo búsqueda→reserva→pago, incorporan de forma consistente *gestión de cuenta* (recuperación de contraseña, historial de reservas), *gestión de disputas/reembolsos* como caso de uso independiente del pago inicial, y *lista de espera* cuando el cupo solicitado está agotado.
- **Sistemas de gestión turística con back-office** (tipo *Tourism Management System*): el rol administrador no se limita a usuarios e indicadores; incluye *verificación/aprobación de nuevos operadores*, *moderación de contenido* (reseñas, fotos) y *gestión de agentes/paquetes*, roles que en nuestro registro de stakeholders corresponden al Administrador de la Plataforma (SH-04).
- **Sistemas inteligentes de información turística con recomendación híbrida**: junto al motor de recomendación, suelen documentarse como casos de uso separados —aunque mutuamente excluyentes en su implementación— la clasificación automática de opiniones, la predicción de ocupación y el chatbot turístico, ya que `Descripcion-General.md` plantea estas cuatro alternativas de IA como opciones, no como funciones simultáneas.
- **Plataformas con integración de operadores grandes vs. pequeños**: documentan *onboarding/verificación* del prestador como un caso de uso propio, previo a "Gestionar oferta turística", y separan la *sincronización batch* (operadores grandes) de la carga manual (pequeños operadores) — ya reflejado en la versión anterior y mantenido aquí.
- **Requisitos normativos del proyecto no cubiertos por los sistemas de referencia**: ningún sistema comercial consultado modela explícitamente "ejercer derechos de datos personales" (habeas data) o "configurar umbrales de capacidad de carga por zona" como casos de uso propios — se agregan aquí porque `Restricciones.md` los exige explícitamente (Ley 1581 de 2012; restricciones ambientales) y deben quedar trazables igual que cualquier otro caso de uso.

---

### Matriz General de Casos de Uso

| ID | Caso de Uso | Actor Primario | Actor(es) Secundario(s) | Módulo Arquitectónico | Prioridad |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CU-01** | Registrarse en la Plataforma | Turista / Prestador | Notificaciones | Usuarios y Seguridad | 5 |
| **CU-02** | Autenticarse | Todos los roles | — | Usuarios y Seguridad | 5 |
| **CU-03** | Recuperar Contraseña | Turista / Prestador / Administrador | Notificaciones | Usuarios y Seguridad | 4 |
| **CU-04** | Gestionar Perfil y Preferencias | Turista / Prestador | — | Usuarios y Seguridad | 4 |
| **CU-05** | Configurar Idioma y Accesibilidad | Turista | — | Usuarios y Seguridad | 3 |
| **CU-06** | Ejercer Derechos de Datos Personales (Habeas Data) | Turista / Prestador | Administrador | Usuarios y Seguridad | 4 |
| **CU-07** | Consultar Catálogo de Atractivos, Actividades y Servicios | Turista | — | Catálogo | 5 |
| **CU-08** | Consultar Disponibilidad de un Servicio | Turista | — | Disponibilidad y Reservas | 5 |
| **CU-09** | Guardar Atractivo en Lista de Favoritos | Turista | — | Catálogo | 2 |
| **CU-10** | Crear Itinerario Personalizado Multi-Servicio | Turista | — | Catálogo / Disponibilidad y Reservas | 3 |
| **CU-11** | Reservar Actividad Turística | Turista | Pagos, Notificaciones | Disponibilidad y Reservas | 5 (crítico) |
| **CU-12** | Reservar en Grupo/Familia | Turista | Pagos, Notificaciones | Disponibilidad y Reservas | 3 |
| **CU-13** | Unirse a Lista de Espera | Turista | Notificaciones | Disponibilidad y Reservas | 3 |
| **CU-14** | Cancelar Reserva | Turista | Pagos, Notificaciones | Disponibilidad y Reservas | 4 |
| **CU-15** | Consultar Historial de Reservas | Turista | — | Disponibilidad y Reservas | 3 |
| **CU-16** | Procesar Pago de Reserva | Turista | Pasarela de Pago | Financiero/Pagos | 5 |
| **CU-17** | Solicitar Reembolso o Disputa de Pago | Turista | Pasarela de Pago, Administrador | Financiero/Pagos | 3 |
| **CU-18** | Recibir Notificación de Evento | Turista / Prestador | Servicio de Notificaciones | Notificaciones | 4 |
| **CU-19** | Calificar y Comentar Experiencia | Turista | Analítica | Catálogo / Analítica | 3 |
| **CU-20** | Responder a Calificaciones y Comentarios | Prestador | — | Catálogo | 2 |
| **CU-21** | Generar Recomendación Personalizada | Turista | Servicio de IA | IA | 4 |
| **CU-22** | Gestionar Oferta Turística | Pequeño/Mediano Prestador | — | Catálogo | 5 |
| **CU-23** | Sincronizar Inventario en Lote | Hotel/Operador Establecido | — | Catálogo | 3 |
| **CU-24** | Configurar Política de Cancelación y Precios Estacionales | Prestador | — | Catálogo / Disponibilidad y Reservas | 3 |
| **CU-25** | Consultar Reporte de Ventas y Comisiones | Prestador | Financiero/Pagos | Analítica / Financiero | 3 |
| **CU-26** | Solicitar Verificación como Prestador (Onboarding) | Prestador | Administrador | Usuarios y Seguridad | 4 |
| **CU-27** | Gestionar Usuarios, Roles y Accesos | Administrador | — | Usuarios y Seguridad | 4 |
| **CU-28** | Verificar y Aprobar Nuevos Prestadores | Administrador | — | Usuarios y Seguridad | 4 |
| **CU-29** | Moderar Contenido (Reseñas y Fotos) | Administrador | — | Catálogo / Analítica | 3 |
| **CU-30** | Consultar Indicadores y Monitorear Capacidad de Carga | Administrador | Entidad de Gestión del Destino, Autoridad Ambiental | Analítica/Reportes | 4 |
| **CU-31** | Configurar Umbrales de Capacidad de Carga por Zona | Administrador | Autoridad Ambiental | Analítica/Reportes | 3 |
| **CU-32** | Monitorear Salud y Disponibilidad del Sistema | Administrador | Proveedor Cloud | Transversal (observabilidad) | 4 |
| **CU-33** | Revisar Log de Auditoría de Seguridad | Administrador | — | Usuarios y Seguridad | 3 |
| **CU-34** | Gestionar Integraciones y Llaves de API Externas | Administrador | Servicio Externo de Pagos/Reservas | Usuarios y Seguridad / API Gateway | 2 |

> [!NOTE]
> `Descripcion-General.md` exige elegir **una única** funcionalidad de IA entre cuatro alternativas. CU-21 especifica la opción de **recomendación personalizada** como la seleccionada por el proyecto. Las tres alternativas no elegidas (chatbot, clasificación de opiniones, predicción de ocupación) se documentan de forma resumida en el **Anexo A**, para dejar constancia de que fueron consideradas y por qué no se desarrollan en paralelo.

---

### Diagramas de Casos de Uso (Mermaid `usecase-beta`)

Dado el volumen de casos de uso, se documentan tres diagramas —uno por actor primario— más un grupo transversal de "Usuarios y Seguridad" referenciado por `include` en los tres.

#### Diagrama 1 — Turista

@startuml
left to right direction

' --- ESTILOS VISUALES LÍMPIOS ---
skinparam shadowing false
skinparam DefaultFontName Helvetica
skinparam usecase {
    BackgroundColor #F8F9FA
    BorderColor #0D6EFD
    ArrowColor #6C757D
}
skinparam actor {
    BackgroundColor #E9ECEF
    BorderColor #0D6EFD
}
skinparam rectangle {
    BorderColor #343A40
    BackgroundColor Transparent
}
skinparam package {
    BackgroundColor #FFFFFF
    BorderColor #DEE2E6
}

' --- ACTORES ---
actor Turista
actor "Servicio de IA" as IA
actor "Pasarela de Pago" as Pagos
actor "Notificaciones" as Notif

' --- FRONTERA DEL SISTEMA Y MÓDULOS ---
rectangle "Plataforma Turística Santa Marta — Turista" {
    
    usecase "Autenticarse" as Autenticar

    package "1. Gestión de Cuenta" {
        usecase "Registrarse" as Registrar
        usecase "Recuperar contraseña" as Recuperar
        usecase "Gestionar perfil" as Perfil
        usecase "Configurar idioma" as Idioma
        usecase "Ejercer derechos (Habeas Data)" as Habeas
    }

    package "2. Exploración y Descubrimiento" {
        usecase "Consultar catálogo" as Catalogo
        usecase "Consultar disponibilidad" as Disponibilidad
        usecase "Guardar en favoritos" as Favoritos
        usecase "Recomendar personalizado" as Recomendar
    }

    package "3. Reservas y Pagos" {
        usecase "Crear itinerario" as Itinerario
        usecase "Reservar actividad" as Reservar
        usecase "Reservar en grupo" as ReservarGrupo
        usecase "Unirse a lista de espera" as ListaEspera
        usecase "Cancelar reserva" as Cancelar
        usecase "Procesar pago" as Pagar
        usecase "Solicitar reembolso/disputa" as Disputa
    }

    package "4. Seguimiento e Interacción" {
        usecase "Consultar historial" as Historial
        usecase "Notificar evento" as Notificar
        usecase "Calificar experiencia" as Calificar
    }
}

' --- RELACIONES DEL ACTOR PRINCIPAL ---
Turista --> Registrar
Turista --> Recuperar
Turista --> Perfil
Turista --> Idioma
Turista --> Habeas

Turista --> Catalogo
Turista --> Disponibilidad
Turista --> Favoritos

Turista --> Itinerario
Turista --> Reservar
Turista --> ReservarGrupo
Turista --> ListaEspera
Turista --> Cancelar
Turista --> Disputa

Turista --> Historial
Turista --> Calificar

' --- DEPENDENCIAS (INCLUDE) ---
Registrar ..> Autenticar : <<include>>
Reservar ..> Autenticar : <<include>>
Cancelar ..> Autenticar : <<include>>
ReservarGrupo ..> Reservar : <<include>>

Reservar ..> Pagar : <<include>>
Cancelar ..> Pagar : <<include>>
Disputa ..> Pagar : <<include>>

Reservar ..> Notificar : <<include>>
Cancelar ..> Notificar : <<include>>
ListaEspera ..> Notificar : <<include>>

' --- EXTENSIONES (EXTEND) ---
Catalogo ..> Recomendar : <<extend>>
Disponibilidad ..> Recomendar : <<extend>>
Disponibilidad ..> ListaEspera : <<extend>>

' --- RELACIONES CON SISTEMAS EXTERNOS ---
Pagar --> Pagos
Notificar --> Notif
Recomendar --> IA

@enduml

#### Diagrama 2 — Prestador de Servicios Turísticos

@startuml
left to right direction

' --- ESTILOS VISUALES LÍMPIOS ---
skinparam shadowing false
skinparam DefaultFontName Helvetica
skinparam usecase {
    BackgroundColor #F8F9FA
    BorderColor #198754
    ArrowColor #6C757D
}
skinparam actor {
    BackgroundColor #E9ECEF
    BorderColor #198754
}
skinparam package {
    BackgroundColor #FFFFFF
    BorderColor #DEE2E6
}

' --- ACTORES ---
actor Prestador
actor "Hotel/Operador Establecido" as Hotel
actor Admin

Hotel -|> Prestador

' --- FRONTERA DEL SISTEMA Y MÓDULOS ---
rectangle "Plataforma Turística Santa Marta — Prestador" {

    usecase "Autenticarse" as Autenticar2

    package "1. Onboarding" {
        usecase "Registrarse" as Registrar2
        usecase "Solicitar verificación" as Onboarding
    }

    package "2. Gestión Operativa" {
        usecase "Gestionar oferta turística" as GestionarOferta
        usecase "Sincronizar inventario en lote" as SincronizarLote
        usecase "Configurar políticas y precios" as ConfigurarPoliticas
    }

    package "3. Rendimiento y Feedback" {
        usecase "Consultar reporte de ventas" as Reportes
        usecase "Responder calificaciones" as Responder
    }
}

' --- RELACIONES ---
Prestador --> Registrar2
Prestador --> Onboarding
Prestador --> GestionarOferta
Prestador --> ConfigurarPoliticas
Prestador --> Reportes
Prestador --> Responder

Hotel --> SincronizarLote

Registrar2 ..> Autenticar2 : <<include>>
Onboarding ..> Autenticar2 : <<include>>
GestionarOferta ..> Autenticar2 : <<include>>

SincronizarLote -|> GestionarOferta
Onboarding --> Admin

@enduml

#### Diagrama 3 — Administrador de la Plataforma

@startuml
left to right direction

' --- ESTILOS VISUALES LÍMPIOS ---
skinparam shadowing false
skinparam DefaultFontName Helvetica
skinparam usecase {
    BackgroundColor #F8F9FA
    BorderColor #DC3545
    ArrowColor #6C757D
}
skinparam actor {
    BackgroundColor #E9ECEF
    BorderColor #DC3545
}
skinparam package {
    BackgroundColor #FFFFFF
    BorderColor #DEE2E6
}

' --- ACTORES ---
actor Admin
actor "Proveedor Cloud" as Cloud
actor "Entidad de Gestión del Destino" as Entidad
actor "Autoridad Ambiental" as Ambiental
actor "Servicio Externo de Pagos" as Pagos2

' --- FRONTERA DEL SISTEMA Y MÓDULOS ---
rectangle "Plataforma Turística Santa Marta — Administrador" {

    usecase "Autenticarse" as Autenticar3

    package "1. Control de Accesos" {
        usecase "Gestionar usuarios y accesos" as GestionarUsuarios
        usecase "Verificar y aprobar prestadores" as AprobarPrestadores
    }

    package "2. Gobernanza y Moderación" {
        usecase "Moderar contenido" as Moderar
        usecase "Consultar indicadores" as Indicadores
        usecase "Configurar umbrales de carga" as Umbrales
    }

    package "3. Infraestructura e Integración" {
        usecase "Monitorear salud del sistema" as Monitorear
        usecase "Revisar log de auditoría" as Auditoria
        usecase "Gestionar integraciones API" as Integraciones
    }
}

' --- RELACIONES ---
Admin --> GestionarUsuarios
Admin --> AprobarPrestadores
Admin --> Moderar
Admin --> Indicadores
Admin --> Umbrales
Admin --> Monitorear
Admin --> Auditoria
Admin --> Integraciones

GestionarUsuarios ..> Autenticar3 : <<include>>
AprobarPrestadores ..> Autenticar3 : <<include>>
Indicadores ..> Autenticar3 : <<include>>

Indicadores --> Entidad
Umbrales --> Ambiental
Monitorear --> Cloud
Integraciones --> Pagos2

@enduml

*Nota de compatibilidad:* estos diagramas usan la sintaxis nativa `usecase-beta` de Mermaid (≥ 12.0.0). Si el visor Markdown del equipo no soporta esa versión, la Matriz General y las fichas de la siguiente sección son la fuente de verdad equivalente en formato textual.

---

## Especificación Detallada de Casos de Uso (Fichas Técnicas)

> [!IMPORTANT]
> Siguiendo la lección aprendida en `stakeholders-quality-assurance-report.md` (documentar el 100% de los elementos identificados, no solo un subconjunto "crítico"), **las 34 filas de la matriz se especifican íntegramente a continuación**.

### Módulo Usuarios y Seguridad

#### CU-01: Registrarse en la Plataforma
* **Actor primario:** Turista / Pequeño-Mediano Prestador / Hotel-Operador Establecido.
* **Actor(es) secundario(s):** Servicio de Notificaciones.
* **Descripción:** Permite crear una cuenta aceptando la política de tratamiento de datos personales.
* **Prioridad:** 5.
* **Disparador:** El usuario selecciona "Crear cuenta".
* **Precondiciones:** No existe cuenta previa con el mismo correo.
* **Postcondiciones:** Cuenta creada con rol asignado; consentimiento de datos registrado (Ley 1581).
* **Flujo básico:** 1) Selecciona tipo de cuenta. 2) Sistema muestra formulario y política de datos. 3) Usuario ingresa datos y acepta la política. 4) Sistema valida unicidad del correo. 5) Sistema crea la cuenta y dispara CU-18. 6) Confirma el registro.
* **Flujos alternos:** 3a. Selecciona idioma de interfaz antes de continuar.
* **Flujos de excepción:** 4a. Correo ya registrado → ofrece CU-03. 3a. No acepta la política → bloquea la creación.
* **RNF asociados:** Cumplimiento Ley 1581; accesibilidad WCAG AA; disponibilidad ≥99%.
* **Relaciones:** `include` CU-02 tras el registro.
* **Reglas de negocio:** No se opera sin consentimiento registrado.
* **Trazabilidad:** `Restricciones.md` (Ley 1581); Stakeholders SH-01, SH-02, SH-03.

#### CU-02: Autenticarse
* **Actor primario:** Cualquier rol registrado.
* **Actor(es) secundario(s):** Módulo Usuarios y Seguridad (OAuth2/JWT, RBAC).
* **Descripción:** Verifica identidad y determina permisos por rol.
* **Prioridad:** 5.
* **Disparador:** Acceso a una funcionalidad que exige sesión.
* **Precondiciones:** Cuenta activa (CU-01).
* **Postcondiciones:** Token JWT emitido; acceso autorizado según rol.
* **Flujo básico:** 1) Ingresa credenciales. 2) Sistema valida hash Argon2id. 3) Emite JWT con claims de rol. 4) Registra el acceso en auditoría. 5) Redirige a la vista del rol.
* **Flujos alternos:** 1a. "Recordar sesión" extiende el refresh token.
* **Flujos de excepción:** 2a. Credenciales inválidas → mensaje genérico + rate limiting. 2b. Cuenta bloqueada → deniega y explica desbloqueo.
* **RNF asociados:** TLS 1.3; WAF y rate limiting; disponibilidad ≥99%; auditoría (NIST SP 800-160).
* **Relaciones:** `include` transversal (CU-01, CU-11, CU-12, CU-14, CU-21 con historial, CU-22 a CU-34 cuando aplica autenticación de rol).
* **Reglas de negocio:** Permisos resueltos exclusivamente por RBAC.
* **Trazabilidad:** `Restricciones.md` (autenticación y autorización segura); Stakeholders SH-04, SH-05.

#### CU-03: Recuperar Contraseña
* **Actor primario:** Turista / Prestador / Administrador.
* **Actor(es) secundario(s):** Servicio de Notificaciones.
* **Descripción:** Permite restablecer el acceso a la cuenta cuando el usuario olvida su contraseña.
* **Prioridad:** 4.
* **Disparador:** El usuario selecciona "Olvidé mi contraseña" en la pantalla de acceso.
* **Precondiciones:** Existe una cuenta asociada al correo indicado.
* **Postcondiciones:** La contraseña queda actualizada y las sesiones activas anteriores se invalidan.
* **Flujo básico:** 1) Usuario ingresa su correo. 2) Sistema genera un token de restablecimiento de un solo uso con expiración corta. 3) Sistema envía el enlace vía CU-18. 4) Usuario define una nueva contraseña. 5) Sistema aplica hashing Argon2id y confirma el cambio.
* **Flujos alternos:** Ninguno relevante.
* **Flujos de excepción:** 1a. El correo no existe en el sistema → se muestra un mensaje neutro (no revela si la cuenta existe, mitigación de enumeración). 2a. El token expiró → se solicita reiniciar el proceso.
* **RNF asociados:** Expiración corta del token (mitigación de fuerza bruta); TLS 1.3; trazabilidad de auditoría.
* **Relaciones:** `include` CU-18.
* **Reglas de negocio:** Un token de restablecimiento es de un solo uso y expira en un plazo corto definido por el equipo.
* **Trazabilidad:** `Restricciones.md` (gestión segura de autenticación); Stakeholder SH-01.

#### CU-04: Gestionar Perfil y Preferencias
* **Actor primario:** Turista / Prestador.
* **Actor(es) secundario(s):** Ninguno.
* **Descripción:** Permite actualizar datos personales/de contacto y preferencias de viaje (categorías de interés) usadas para personalización.
* **Prioridad:** 4.
* **Disparador:** El usuario accede a "Mi perfil".
* **Precondiciones:** Usuario autenticado (CU-02).
* **Postcondiciones:** El perfil queda actualizado y disponible para CU-21 (recomendación).
* **Flujo básico:** 1) Usuario abre su perfil. 2) Sistema muestra los datos actuales. 3) Usuario edita datos de contacto y/o preferencias. 4) Sistema valida y guarda los cambios.
* **Flujos alternos:** 3a. El usuario actualiza únicamente sus preferencias de recomendación sin tocar datos de contacto.
* **Flujos de excepción:** 4a. Formato inválido en un campo → se resalta el campo sin perder el resto de la información.
* **RNF asociados:** Accesibilidad WCAG AA; cifrado en reposo de datos personales sensibles.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** El correo de acceso solo puede cambiarse mediante verificación adicional.
* **Trazabilidad:** `Objetivos.md` (preferencias del visitante); Stakeholder SH-01.

#### CU-05: Configurar Idioma y Accesibilidad
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Ninguno.
* **Descripción:** Permite seleccionar el idioma de la interfaz (ES/EN) y activar ajustes de accesibilidad (alto contraste, tamaño de fuente, compatibilidad con lector de pantalla).
* **Prioridad:** 3.
* **Disparador:** El usuario abre el menú de configuración de idioma/accesibilidad.
* **Precondiciones:** Ninguna (disponible sin autenticación, y persistente si el usuario está autenticado).
* **Postcondiciones:** La preferencia queda aplicada a la sesión actual y, si el usuario está autenticado, guardada en su perfil.
* **Flujo básico:** 1) Usuario abre el menú de configuración. 2) Selecciona idioma y/o ajustes de accesibilidad. 3) Sistema aplica el cambio de inmediato en la interfaz. 4) Si el usuario está autenticado, el sistema persiste la preferencia en su perfil (CU-04).
* **Flujos alternos:** Ninguno relevante.
* **Flujos de excepción:** Ninguna condición de error relevante (operación puramente local/idempotente).
* **RNF asociados:** Cumplimiento WCAG AA; soporte multilenguaje ES/EN transversal a toda la plataforma.
* **Relaciones:** Puede incluir a CU-04 cuando el usuario está autenticado.
* **Reglas de negocio:** Ninguna.
* **Trazabilidad:** `Restricciones.md` (Restricciones Sociales — multilenguaje, accesibilidad); Stakeholder SH-14.

#### CU-06: Ejercer Derechos de Datos Personales (Habeas Data)
* **Actor primario:** Turista / Prestador.
* **Actor(es) secundario(s):** Administrador de la Plataforma (atiende solicitudes que requieren intervención manual).
* **Descripción:** Permite al titular de datos consultar, rectificar, actualizar o solicitar la eliminación de su información personal, conforme a la Ley 1581 de 2012.
* **Prioridad:** 4.
* **Disparador:** El usuario accede a "Privacidad y datos" desde su perfil.
* **Precondiciones:** Usuario autenticado.
* **Postcondiciones:** La solicitud queda registrada y, según el tipo, ejecutada automáticamente o encolada para atención del administrador.
* **Flujo básico:** 1) Usuario selecciona el tipo de solicitud (acceso, rectificación, eliminación, portabilidad). 2) Sistema muestra el resumen de los datos que posee sobre el usuario. 3) Usuario confirma la solicitud. 4) El sistema ejecuta automáticamente las solicitudes de acceso/portabilidad, o encola las de eliminación para revisión administrativa. 5) El sistema notifica al usuario el resultado o el plazo estimado.
* **Flujos alternos:** 4a. El usuario solicita exportar sus datos en un formato portable (JSON/CSV).
* **Flujos de excepción:** 4a. La eliminación no puede ejecutarse de inmediato por obligaciones contables/legales (reservas activas) → el sistema informa el plazo y la razón.
* **RNF asociados:** Cumplimiento estricto de la Ley 1581 de 2012; trazabilidad de auditoría de cada solicitud.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** Toda solicitud de datos personales debe quedar registrada con marca de tiempo y resolución, independientemente de si se ejecuta de forma automática o manual.
* **Trazabilidad:** `Restricciones.md` (Restricciones Normativas — Ley 1581); Stakeholder SH-09.

### Módulo Catálogo

#### CU-07: Consultar Catálogo de Atractivos, Actividades y Servicios
* **Actor primario:** Turista.
* **Descripción:** Explorar y filtrar atractivos, actividades, eventos y prestadores, de forma multilenguaje.
* **Prioridad:** 5.
* **Disparador:** El turista accede a la sección de exploración.
* **Precondiciones:** Ninguna (acceso público).
* **Postcondiciones:** Listado de resultados filtrados visible.
* **Flujo básico:** 1) Ingresa criterios. 2) Sistema consulta Catálogo (JSONB + índices GIN). 3) Presenta resultados. 4) Selecciona un resultado.
* **Flujos alternos:** 1a. Sin filtros → listado general por relevancia.
* **Flujos de excepción:** 2a. Sin resultados → sugiere CU-21.
* **RNF asociados:** Tiempo de respuesta ágil en alta concurrencia; WCAG AA; multilenguaje.
* **Relaciones:** Extendido por CU-21.
* **Reglas de negocio:** El orden no debe favorecer sistemáticamente a un operador.
* **Trazabilidad:** `Descripcion-General.md` (visibilidad de pequeños prestadores); Stakeholders SH-01, SH-02, SH-14.

#### CU-08: Consultar Disponibilidad de un Servicio
* **Actor primario:** Turista.
* **Descripción:** Verificar cupos, horarios y condiciones vigentes antes de reservar.
* **Prioridad:** 5.
* **Disparador:** Selecciona "Ver disponibilidad" desde CU-07.
* **Precondiciones:** El servicio existe y está activo.
* **Postcondiciones:** Cupos y horarios disponibles visibles en tiempo real.
* **Flujo básico:** 1) Indica fecha(s) y personas. 2) Sistema consulta estado transaccional (PostgreSQL ACID). 3) Presenta horarios/cupos y precio. 4) Procede a CU-11 o continúa explorando.
* **Flujos alternos:** 3a. Sugiere fechas cercanas si está agotado.
* **Flujos de excepción:** 2a. Servicio desactivado → informa y sugiere similares.
* **RNF asociados:** Disponibilidad ≥99%; consistencia bajo alta concurrencia.
* **Relaciones:** Precede a CU-11; extendido por CU-21; extiende a CU-13 cuando el cupo está agotado.
* **Reglas de negocio:** El cupo mostrado debe reflejar el estado real al momento de la consulta.
* **Trazabilidad:** `Restricciones.md` (disponibilidad ≥99%, alta concurrencia); Stakeholder SH-01.

#### CU-09: Guardar Atractivo en Lista de Favoritos
* **Actor primario:** Turista.
* **Descripción:** Permite marcar atractivos o servicios de interés para consultarlos posteriormente sin repetir la búsqueda.
* **Prioridad:** 2.
* **Disparador:** El turista selecciona el ícono de favorito sobre un resultado del catálogo.
* **Precondiciones:** Usuario autenticado.
* **Postcondiciones:** El atractivo queda asociado a la lista de favoritos del usuario.
* **Flujo básico:** 1) Usuario marca/desmarca un atractivo como favorito desde CU-07. 2) Sistema actualiza la lista asociada al perfil. 3) Usuario consulta su lista de favoritos en cualquier momento.
* **Flujos alternos:** 3a. Desde la lista de favoritos, accede directamente a CU-08 de uno de los ítems guardados.
* **Flujos de excepción:** Ninguna condición de error relevante.
* **RNF asociados:** Persistencia ligera; accesibilidad del control de marcado.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** Ninguna.
* **Trazabilidad:** `Objetivos.md` (selección de actividades según preferencias); Stakeholder SH-01.

#### CU-10: Crear Itinerario Personalizado Multi-Servicio
* **Actor primario:** Turista.
* **Descripción:** Permite combinar varios atractivos/actividades en un plan de viaje organizado por día, facilitando la planificación de una estadía completa.
* **Prioridad:** 3.
* **Disparador:** El turista selecciona "Crear itinerario" desde su perfil o desde el catálogo.
* **Precondiciones:** Usuario autenticado; existe al menos un atractivo/actividad disponible para agregar.
* **Postcondiciones:** El itinerario queda guardado con los servicios seleccionados organizados por fecha/orden.
* **Flujo básico:** 1) Usuario crea un nuevo itinerario y le asigna un nombre y rango de fechas. 2) Usuario agrega atractivos/actividades desde el catálogo (CU-07) o desde sus favoritos (CU-09) a días específicos del itinerario. 3) Sistema valida que no existan solapamientos evidentes de horario entre actividades del mismo día. 4) Usuario guarda el itinerario.
* **Flujos alternos:** 2a. El usuario reordena las actividades dentro de un mismo día.
* **Flujos de excepción:** 3a. Se detecta solapamiento de horario → el sistema advierte al usuario sin bloquear el guardado (la decisión final es del turista).
* **RNF asociados:** Accesibilidad WCAG AA en la vista de itinerario; multilenguaje.
* **Relaciones:** `include` CU-02; se apoya en CU-07 y CU-09; puede derivar en múltiples ejecuciones de CU-11.
* **Reglas de negocio:** Un itinerario no reserva automáticamente los servicios incluidos; es una guía de planificación.
* **Trazabilidad:** `Objetivos.md` (selección de actividades y atractivos de acuerdo con preferencias y disponibilidad); Stakeholder SH-01.

### Módulo Disponibilidad y Reservas

#### CU-11: Reservar Actividad Turística
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Servicio de Pagos, Servicio de Notificaciones.
* **Descripción:** Completa la reserva de una actividad, orquestando verificación de cupo, pago y confirmación. **Flujo crítico completo** exigido en `Diseño-de-Ingenieria.md`.
* **Prioridad:** 5 (crítica).
* **Disparador:** Confirma "Reservar" sobre un cupo disponible (CU-08).
* **Precondiciones:** Autenticado (CU-02); existe cupo disponible.
* **Postcondiciones:** Reserva "confirmada"; cupo decrementado; notificación disparada.
* **Flujo básico:** 1) Revisa resumen. 2) Sistema bloquea temporalmente el cupo (saga orquestada). 3) Invoca CU-16. 4) Persiste la reserva confirmada y libera el bloqueo. 5) Dispara CU-18. 6) Muestra comprobante.
* **Flujos alternos:** 1a. Aplica código promocional.
* **Flujos de excepción:** 2a. Cupo agotado entre consulta y confirmación → cancela y ofrece CU-13. 3a. Pago rechazado/timeout → compensación (libera cupo), sin cobrar.
* **RNF asociados:** Disponibilidad ≥99%; consistencia transaccional; PCI-DSS delegado.
* **Relaciones:** `include` CU-02, CU-16, CU-18.
* **Reglas de negocio:** No se almacenan datos de tarjeta; el cupo se libera si el pago no se confirma a tiempo.
* **Trazabilidad:** `Diseño-de-Ingenieria.md` (flujo crítico obligatorio); Stakeholders SH-01, SH-12.

#### CU-12: Reservar en Grupo/Familia
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Servicio de Pagos, Servicio de Notificaciones.
* **Descripción:** Permite reservar cupos para varias personas en una misma transacción, con datos individuales opcionales por acompañante.
* **Prioridad:** 3.
* **Disparador:** El turista indica más de un cupo al iniciar CU-11.
* **Precondiciones:** Existen cupos suficientes para el número de personas solicitado.
* **Postcondiciones:** Una única reserva queda asociada a múltiples cupos/personas.
* **Flujo básico:** 1) El turista indica el número de acompañantes. 2) Ingresa (opcionalmente) datos básicos de cada acompañante. 3) El sistema ejecuta CU-11 reservando todos los cupos como una unidad atómica. 4) Se emite un único comprobante de reserva grupal.
* **Flujos alternos:** 2a. El turista omite los datos de acompañantes si el operador no los exige.
* **Flujos de excepción:** 3a. No hay cupos suficientes para todo el grupo → el sistema informa el máximo disponible y ofrece dividir la reserva o unirse a CU-13.
* **RNF asociados:** Atomicidad de la reserva grupal (todo o nada); disponibilidad ≥99%.
* **Relaciones:** `include` CU-11.
* **Reglas de negocio:** Una reserva grupal se cancela como unidad, salvo que el operador permita cancelaciones parciales.
* **Trazabilidad:** `Objetivos.md` (gestión de reservas de actividades turísticas); Stakeholder SH-01.

#### CU-13: Unirse a Lista de Espera
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Servicio de Notificaciones.
* **Descripción:** Permite registrar interés en un servicio sin cupo disponible, para ser notificado si se libera uno.
* **Prioridad:** 3.
* **Disparador:** El turista selecciona "Unirme a la lista de espera" ante un cupo agotado (CU-08/CU-11).
* **Precondiciones:** El servicio consultado no tiene cupo disponible en la fecha solicitada.
* **Postcondiciones:** El turista queda registrado en la lista de espera del servicio/fecha.
* **Flujo básico:** 1) El turista confirma su interés e indica la fecha deseada. 2) El sistema lo registra en la lista de espera, en orden de llegada. 3) Cuando se libera un cupo (por cancelación, CU-14), el sistema notifica al primero en la lista mediante CU-18 con un plazo limitado para confirmar. 4) Si el turista confirma a tiempo, el sistema ejecuta CU-11 con el cupo reservado.
* **Flujos alternos:** 3a. El turista declina o no responde a tiempo → el sistema ofrece el cupo al siguiente en la lista.
* **Flujos de excepción:** Ninguna condición de error adicional relevante.
* **RNF asociados:** Notificación oportuna (no bloqueante); trazabilidad del orden de la lista.
* **Relaciones:** Extiende a CU-08; `include` CU-18; puede derivar en CU-11.
* **Reglas de negocio:** El cupo liberado se ofrece estrictamente en el orden de la lista de espera.
* **Trazabilidad:** `Descripcion-General.md` (mecanismos para seleccionar actividades de acuerdo con disponibilidad); Stakeholder SH-01.

#### CU-14: Cancelar Reserva
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Pasarela de Pago, Servicio de Notificaciones.
* **Descripción:** Cancela una reserva vigente dentro de las condiciones establecidas.
* **Prioridad:** 4.
* **Disparador:** Selecciona "Cancelar reserva" desde CU-15.
* **Precondiciones:** Autenticado; reserva confirmada asociada a su cuenta.
* **Postcondiciones:** Reserva "cancelada"; cupo liberado (activa potencialmente CU-13).
* **Flujo básico:** 1) Selecciona la reserva. 2) Sistema valida política de cancelación. 3) Invoca CU-16 (reembolso) si aplica. 4) Libera el cupo. 5) Dispara CU-18.
* **Flujos alternos:** 2a. Fuera de plazo → informa penalización.
* **Flujos de excepción:** 3a. Reembolso falla → "cancelación pendiente" y aviso a CU-27.
* **RNF asociados:** Consistencia transaccional; auditoría; disponibilidad ≥99%.
* **Relaciones:** `include` CU-02, CU-16, CU-18.
* **Reglas de negocio:** Las políticas de cancelación son definidas por el operador dentro de límites de la plataforma.
* **Trazabilidad:** `Objetivos.md` (gestionar reservas); Stakeholder SH-01.

#### CU-15: Consultar Historial de Reservas
* **Actor primario:** Turista.
* **Descripción:** Permite ver reservas pasadas, activas y canceladas, como punto de entrada a otros casos de uso (cancelar, calificar, disputar).
* **Prioridad:** 3.
* **Disparador:** El turista accede a "Mis reservas".
* **Precondiciones:** Usuario autenticado.
* **Postcondiciones:** Se visualiza el listado de reservas con su estado actual.
* **Flujo básico:** 1) El usuario accede a "Mis reservas". 2) El sistema consulta las reservas asociadas a su cuenta. 3) El sistema presenta el listado clasificado por estado (próximas, completadas, canceladas). 4) El usuario selecciona una reserva para ver el detalle o ejecutar una acción (CU-14, CU-17, CU-19).
* **Flujos alternos:** 3a. El usuario filtra por rango de fechas o por prestador.
* **Flujos de excepción:** 2a. No existen reservas registradas → el sistema muestra un estado vacío con sugerencia de explorar el catálogo (CU-07).
* **RNF asociados:** Tiempo de respuesta ágil; accesibilidad WCAG AA.
* **Relaciones:** `include` CU-02; punto de entrada a CU-14, CU-17, CU-19.
* **Reglas de negocio:** Ninguna.
* **Trazabilidad:** `Objetivos.md` (consultar disponibilidad/gestión de reservas); Stakeholder SH-01.

### Módulo Financiero/Pagos

#### CU-16: Procesar Pago de Reserva
* **Actor primario:** Turista (indirecto, vía CU-11/CU-12/CU-14).
* **Actor(es) secundario(s):** Pasarela de Pago (Wompi/ePayco).
* **Descripción:** Ejecuta el cobro o reembolso asociado a una reserva mediante una pasarela certificada.
* **Prioridad:** 5.
* **Disparador:** Invocación desde CU-11, CU-12 o CU-14.
* **Precondiciones:** Existe una reserva en proceso o confirmada asociada.
* **Postcondiciones:** Transacción registrada de forma auditable; comisión calculada.
* **Flujo básico:** 1) Construye solicitud de cobro/reembolso (adapter). 2) Redirige/embebe checkout tokenizado. 3) Pasarela procesa y retorna resultado. 4) Registra el resultado y calcula comisión. 5) Retorna el resultado al caso invocador.
* **Flujos alternos:** 3a. Pago vía PSE.
* **Flujos de excepción:** 3a. Timeout/error → reintentos con circuit breaker; si persiste, marca fallida.
* **RNF asociados:** PCI-DSS delegado; trazabilidad contable; resiliencia ante fallos de terceros.
* **Relaciones:** Incluido por CU-11, CU-12, CU-14; incluido por CU-17.
* **Reglas de negocio:** Nunca se almacenan datos de tarjeta; comisiones auditables.
* **Trazabilidad:** `architectures-technical-details.md` (Módulo Financiero); Stakeholder SH-12.

#### CU-17: Solicitar Reembolso o Disputa de Pago
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Pasarela de Pago, Administrador de la Plataforma.
* **Descripción:** Permite al turista reportar un cobro incorrecto o no reconocido, distinto de una cancelación estándar (CU-14), para su revisión manual.
* **Prioridad:** 3.
* **Disparador:** El turista selecciona "Reportar un problema con mi pago" desde CU-15.
* **Precondiciones:** Existe una transacción de pago asociada a la cuenta del turista.
* **Postcondiciones:** La disputa queda registrada con estado "en revisión" y asignada al administrador.
* **Flujo básico:** 1) El turista describe el motivo de la disputa y adjunta evidencia si aplica. 2) El sistema registra el caso y notifica al administrador. 3) El administrador revisa el caso contra el registro transaccional. 4) El administrador aprueba (invoca CU-16 en modo reembolso) o rechaza la disputa con justificación. 5) El sistema notifica al turista la resolución (CU-18).
* **Flujos alternos:** 3a. El administrador solicita información adicional al turista antes de resolver.
* **Flujos de excepción:** 4a. La pasarela rechaza el reembolso solicitado → el administrador gestiona el caso de forma manual con el proveedor.
* **RNF asociados:** Trazabilidad de auditoría completa del caso; tiempo máximo de respuesta definido por política interna.
* **Relaciones:** `include` CU-02, CU-18; puede incluir CU-16.
* **Reglas de negocio:** Toda disputa debe resolverse con una justificación registrada, aprobada o rechazada.
* **Trazabilidad:** `Restricciones.md` (protección de información financiera); Stakeholder SH-01, SH-12.

### Módulo Notificaciones

#### CU-18: Recibir Notificación de Evento
* **Actor primario:** Turista / Prestador (receptores).
* **Actor(es) secundario(s):** Servicio de Notificaciones (RabbitMQ + SendGrid/SES).
* **Descripción:** Envía comunicaciones automáticas de forma asíncrona y multilenguaje, sin bloquear la transacción que las origina.
* **Prioridad:** 4.
* **Disparador:** Eventos emitidos por CU-01, CU-03, CU-11, CU-12, CU-13, CU-14 o CU-17.
* **Precondiciones:** El destinatario tiene un canal de contacto válido registrado.
* **Postcondiciones:** El mensaje se entrega en el idioma configurado del usuario.
* **Flujo básico:** 1) El módulo de origen publica un evento en la cola. 2) El microservicio de Notificaciones selecciona la plantilla según tipo de evento e idioma. 3) Envía el mensaje vía proveedor transaccional. 4) Registra el estado de entrega.
* **Flujos alternos:** 2a. Usuario con inglés configurado → plantilla en inglés.
* **Flujos de excepción:** 3a. Envío falla → reintentos automáticos sin afectar la transacción de origen.
* **RNF asociados:** Comunicación asíncrona no bloqueante; reintentos automáticos; multilenguaje ES/EN.
* **Relaciones:** Incluido por CU-01, CU-03, CU-11, CU-12, CU-13, CU-14, CU-17.
* **Reglas de negocio:** El fallo de notificación nunca revierte una transacción ya persistida.
* **Trazabilidad:** `architectures-technical-details.md` (Microservicio de Notificaciones); Stakeholder SH-01.

### Módulo Catálogo / Reputación

#### CU-19: Calificar y Comentar Experiencia
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Módulo Analítica.
* **Descripción:** Permite calificar y comentar una actividad reservada y completada.
* **Prioridad:** 3.
* **Disparador:** Accede a "Calificar" desde CU-15.
* **Precondiciones:** Reserva en estado "completada".
* **Postcondiciones:** Comentario y calificación asociados públicamente al servicio.
* **Flujo básico:** 1) Selecciona reserva completada. 2) Sistema presenta formulario de calificación. 3) Envía calificación. 4) Sistema valida ausencia de duplicado y persiste. 5) Actualiza el indicador agregado de reputación.
* **Flujos alternos:** 2a. Adjunta fotografías.
* **Flujos de excepción:** 4a. Duplicado → rechaza y ofrece editar la existente.
* **RNF asociados:** Moderación básica (ver CU-29); accesibilidad WCAG AA.
* **Relaciones:** `include` CU-02; puede activar CU-29.
* **Reglas de negocio:** Solo puede calificar quien reservó y completó la actividad.
* **Trazabilidad:** `Descripcion-General.md` (indicadores de demanda); Stakeholder SH-01, SH-07.

#### CU-20: Responder a Calificaciones y Comentarios
* **Actor primario:** Prestador.
* **Descripción:** Permite al prestador responder públicamente a las reseñas recibidas sobre su servicio, fortaleciendo la relación con el turista y su reputación.
* **Prioridad:** 2.
* **Disparador:** El prestador accede a la sección de reseñas de su oferta.
* **Precondiciones:** Existe al menos una calificación/comentario asociado a un servicio del prestador.
* **Postcondiciones:** La respuesta queda publicada de forma visible junto al comentario original.
* **Flujo básico:** 1) El prestador revisa las calificaciones recibidas. 2) Selecciona una y redacta una respuesta. 3) El sistema valida la respuesta contra las reglas de moderación básicas. 4) Publica la respuesta.
* **Flujos alternos:** Ninguno relevante.
* **Flujos de excepción:** 3a. La respuesta contiene contenido inapropiado detectado por las reglas de moderación → se envía a revisión manual (CU-29) antes de publicarse.
* **RNF asociados:** Moderación básica de contenido; tiempos de publicación razonables.
* **Relaciones:** `include` CU-02; relacionado con CU-19 y CU-29.
* **Reglas de negocio:** Un prestador solo puede responder a reseñas de su propia oferta.
* **Trazabilidad:** `stakeholders.md` (SH-02, SH-03 — visibilidad y relación con el turista).

### Módulo IA

#### CU-21: Generar Recomendación Personalizada
* **Actor primario:** Turista.
* **Actor(es) secundario(s):** Servicio de IA (microservicio desacoplado).
* **Descripción:** Genera sugerencias ajustadas a preferencias del turista y a criterios de sostenibilidad, con explicación asociada.
* **Prioridad:** 4.
* **Disparador:** Sin resultados satisfactorios en CU-07/CU-08, o solicitud explícita.
* **Precondiciones:** Existen datos suficientes de preferencias o contexto.
* **Postcondiciones:** El turista recibe recomendaciones con su explicación, registrada en auditoría.
* **Flujo básico:** 1) Solicita recomendación. 2) Sistema envía contexto al microservicio de IA. 3) IA calcula sugerencias y criterios explicativos. 4) Sistema presenta recomendaciones con explicación en lenguaje simple. 5) Registra la recomendación en el log de auditoría.
* **Flujos alternos:** 1a. Sistema ofrece recomendación proactiva ante alta congestión detectada.
* **Flujos de excepción:** 3a. IA no responde a tiempo → fallback a resultados por popularidad.
* **RNF asociados:** Explicabilidad obligatoria; ausencia de sesgo comercial sistemático; disponibilidad de respaldo (fallback).
* **Relaciones:** `extend` de CU-07, CU-08; `include` CU-02 para personalización con historial.
* **Reglas de negocio:** Ninguna recomendación puede omitir su explicación asociada.
* **Trazabilidad:** `Restricciones.md` (explicabilidad, redistribución de congestión); Stakeholders SH-02, SH-08, SH-13.

### Actor: Prestador de Servicios Turísticos

#### CU-22: Gestionar Oferta Turística
* **Actor primario:** Pequeño/Mediano Prestador (generaliza también al Hotel/Operador Establecido).
* **Descripción:** Alta, edición o baja de atractivos/actividades/servicios, con interfaz simplificada.
* **Prioridad:** 5.
* **Disparador:** Accede al panel "Mi oferta".
* **Precondiciones:** Autenticado y verificado como operador (CU-26/CU-28).
* **Postcondiciones:** El servicio queda visible/actualizado en el Catálogo.
* **Flujo básico:** 1) Selecciona "Agregar" o edita uno existente. 2) Sistema presenta formulario simplificado (JSONB). 3) Completa la información. 4) Sistema valida y guarda. 5) Confirma publicación.
* **Flujos alternos:** 2a. Reutiliza una plantilla previa.
* **Flujos de excepción:** 4a. Datos incompletos → resalta campos faltantes sin perder lo ingresado.
* **RNF asociados:** Interfaz WCAG AA para baja alfabetización digital; API disponible para operadores con capacidad técnica propia.
* **Relaciones:** `include` CU-02; especializado por CU-23.
* **Reglas de negocio:** Un operador solo edita su propio catálogo.
* **Trazabilidad:** `Descripcion-General.md` (incorporación de pequeños prestadores); Stakeholder SH-02.

#### CU-23: Sincronizar Inventario en Lote
* **Actor primario:** Hotel/Operador Establecido (especialización de Prestador).
* **Descripción:** Sincroniza de forma masiva disponibilidad y datos de ocupación, evitando la carga manual.
* **Prioridad:** 3.
* **Disparador:** Ejecuta una carga programada o manual (API/archivo).
* **Precondiciones:** Cuenta con credenciales de integración o archivo válido.
* **Postcondiciones:** Inventario actualizado masivamente y de forma consistente.
* **Flujo básico:** 1) Envía el lote (API o archivo). 2) Sistema valida formato e integridad. 3) Aplica actualizaciones en batch. 4) Genera reporte de resultados.
* **Flujos alternos:** 1a. Consulta el estado de una sincronización previa.
* **Flujos de excepción:** 2a. Registros con errores de formato → procesa los válidos y reporta los rechazados.
* **RNF asociados:** Endpoints seguros de alta capacidad; procesamiento eficiente sin degradar el núcleo transaccional.
* **Relaciones:** Especializa CU-22; `include` CU-02.
* **Reglas de negocio:** Una sincronización fallida no deja el catálogo parcialmente inconsistente.
* **Trazabilidad:** `stakeholders.md` (SH-03); `Restricciones.md` (crecimiento progresivo).

#### CU-24: Configurar Política de Cancelación y Precios Estacionales
* **Actor primario:** Prestador.
* **Descripción:** Permite definir las reglas de cancelación/penalización de un servicio y ajustar precios según temporada o demanda.
* **Prioridad:** 3.
* **Disparador:** El prestador accede a "Configuración" desde su panel de oferta (CU-22).
* **Precondiciones:** El prestador tiene al menos un servicio publicado.
* **Postcondiciones:** Las políticas y precios quedan actualizados y se aplican a nuevas reservas.
* **Flujo básico:** 1) El prestador selecciona un servicio. 2) Define plazos y penalizaciones de cancelación. 3) Define rangos de precio por temporada/fecha. 4) El sistema valida que las políticas estén dentro de los límites configurados por la plataforma. 5) Guarda los cambios.
* **Flujos alternos:** 3a. El prestador aplica un descuento temporal para redistribuir demanda hacia fechas de baja ocupación.
* **Flujos de excepción:** 4a. La política definida excede los límites permitidos por la plataforma → el sistema rechaza el cambio y explica el límite.
* **RNF asociados:** Validación de reglas de negocio configurables por la plataforma; auditoría de cambios de precio.
* **Relaciones:** `include` CU-02; relacionado con CU-22.
* **Reglas de negocio:** Las políticas de cancelación y precio deben respetar los límites máximos definidos por la plataforma (protección al turista).
* **Trazabilidad:** `Diseño-de-Ingenieria.md` (Documento Comparación — trade-offs de negocio); Stakeholder SH-02, SH-03.

#### CU-25: Consultar Reporte de Ventas y Comisiones
* **Actor primario:** Prestador.
* **Actor(es) secundario(s):** Módulo Financiero/Pagos.
* **Descripción:** Permite al prestador visualizar sus ventas, reservas y comisiones liquidadas en un período determinado.
* **Prioridad:** 3.
* **Disparador:** El prestador accede a "Mis reportes" desde su panel.
* **Precondiciones:** El prestador tiene al menos una reserva confirmada en el período consultado.
* **Postcondiciones:** Se presenta el reporte con el detalle de ventas y comisiones.
* **Flujo básico:** 1) El prestador selecciona el período a consultar. 2) El sistema consulta el módulo Financiero y las vistas de agregación de Analítica. 3) El sistema presenta el detalle de reservas, montos y comisiones retenidas. 4) El prestador puede exportar el reporte.
* **Flujos alternos:** 1a. Filtra por servicio específico dentro de su oferta.
* **Flujos de excepción:** 2a. No hay datos para el período → informa la ausencia de resultados.
* **RNF asociados:** Los reportes no deben competir por recursos con el tráfico transaccional (réplicas de solo lectura); accesibilidad AA.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** Un prestador solo accede a los datos de sus propias ventas y comisiones.
* **Trazabilidad:** `architectures-technical-details.md` (liquidación de comisiones); Stakeholder SH-02, SH-03.

#### CU-26: Solicitar Verificación como Prestador (Onboarding)
* **Actor primario:** Prestador.
* **Actor(es) secundario(s):** Administrador de la Plataforma.
* **Descripción:** Permite a un nuevo prestador enviar la documentación e información requerida para ser verificado y habilitado a publicar oferta (CU-22).
* **Prioridad:** 4.
* **Disparador:** El prestador completa CU-01 con rol "operador" y accede al flujo de verificación.
* **Precondiciones:** Cuenta de prestador creada pero no verificada.
* **Postcondiciones:** La solicitud queda registrada con estado "pendiente de verificación", a la espera de CU-28.
* **Flujo básico:** 1) El prestador ingresa datos del negocio (nombre comercial, tipo de servicio, documentos básicos). 2) El sistema valida el formato de la información. 3) El sistema envía la solicitud a la cola de verificación del administrador. 4) El sistema notifica al prestador que su solicitud está en revisión.
* **Flujos alternos:** 1a. El prestador guarda su solicitud como borrador para completarla después.
* **Flujos de excepción:** 2a. Documentación incompleta → el sistema indica los campos/documentos faltantes.
* **RNF asociados:** Cifrado en reposo de la documentación cargada; trazabilidad del proceso de verificación.
* **Relaciones:** `include` CU-02; precede a CU-28.
* **Reglas de negocio:** Un prestador no puede publicar oferta (CU-22) hasta ser verificado.
* **Trazabilidad:** `Descripcion-General.md` (incorporación de pequeños y medianos prestadores); Stakeholder SH-02, SH-04.

### Actor: Administrador de la Plataforma

#### CU-27: Gestionar Usuarios, Roles y Accesos
* **Actor primario:** Administrador.
* **Descripción:** Supervisa cuentas, asigna/revoca roles y actúa ante incidentes de seguridad.
* **Prioridad:** 4.
* **Disparador:** Accede al panel de gobernanza de usuarios.
* **Precondiciones:** Autenticado con rol de administración.
* **Postcondiciones:** Cambios de rol/estado aplicados y auditados.
* **Flujo básico:** 1) Busca una cuenta. 2) Sistema presenta el detalle (rol, estado, accesos). 3) Modifica rol o bloquea/reactiva. 4) Sistema aplica y audita el cambio.
* **Flujos alternos:** 1a. Filtra por estado de cuenta.
* **Flujos de excepción:** 3a. Modificación sobre su propia cuenta de administración → exige doble confirmación.
* **RNF asociados:** Auditoría completa (NIST SP 800-160); dashboard WCAG AA.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** Todo cambio de rol o bloqueo queda auditado con responsable y marca de tiempo.
* **Trazabilidad:** `stakeholders.md` (SH-04); `Restricciones.md` (autenticación y autorización segura).

#### CU-28: Verificar y Aprobar Nuevos Prestadores
* **Actor primario:** Administrador.
* **Descripción:** Revisa las solicitudes de onboarding (CU-26) y decide si aprueba, rechaza o solicita información adicional a un nuevo prestador.
* **Prioridad:** 4.
* **Disparador:** Llega una nueva solicitud a la cola de verificación (CU-26).
* **Precondiciones:** Existe al menos una solicitud pendiente de verificación.
* **Postcondiciones:** La cuenta del prestador queda "verificada" (habilitada para CU-22) o "rechazada" con motivo.
* **Flujo básico:** 1) El administrador revisa la solicitud y la documentación asociada. 2) Verifica la coherencia de la información del negocio. 3) Aprueba o rechaza la solicitud con una justificación. 4) El sistema notifica al prestador la decisión (CU-18) y, si fue aprobada, habilita CU-22.
* **Flujos alternos:** 3a. El administrador solicita información adicional antes de decidir, devolviendo la solicitud al prestador.
* **Flujos de excepción:** 3a. La documentación resulta insuficiente de forma reiterada → el administrador rechaza definitivamente la solicitud.
* **RNF asociados:** Trazabilidad de auditoría de cada decisión; tiempo de respuesta razonable definido por política interna.
* **Relaciones:** `include` CU-02; posterior a CU-26.
* **Reglas de negocio:** Ninguna cuenta de prestador puede publicar oferta sin verificación previa aprobada.
* **Trazabilidad:** `stakeholders.md` (SH-04, rol Aprobador); Stakeholder SH-02.

#### CU-29: Moderar Contenido (Reseñas y Fotos)
* **Actor primario:** Administrador.
* **Descripción:** Revisa contenido generado por usuarios (calificaciones, comentarios, fotografías, respuestas de prestadores) señalado como potencialmente inapropiado.
* **Prioridad:** 3.
* **Disparador:** Un contenido es reportado por otro usuario o marcado automáticamente por reglas básicas de moderación (CU-19/CU-20).
* **Precondiciones:** Existe contenido pendiente de revisión en la cola de moderación.
* **Postcondiciones:** El contenido queda publicado, editado u oculto, según la decisión del administrador.
* **Flujo básico:** 1) El administrador revisa el contenido señalado. 2) Evalúa contra las políticas de uso de la plataforma. 3) Decide mantener, ocultar o eliminar el contenido. 4) El sistema registra la decisión y notifica al autor si el contenido fue removido.
* **Flujos alternos:** 3a. El administrador solicita al autor modificar el contenido en lugar de eliminarlo directamente.
* **Flujos de excepción:** Ninguna condición de error adicional relevante.
* **RNF asociados:** Trazabilidad de las decisiones de moderación; tiempos de respuesta razonables para no afectar la confianza del usuario.
* **Relaciones:** `include` CU-02; se activa desde CU-19 y CU-20.
* **Reglas de negocio:** Toda remoción de contenido debe quedar justificada y notificada al autor.
* **Trazabilidad:** `Restricciones.md` (transparencia y protección de la privacidad de los turistas); Stakeholder SH-04.

#### CU-30: Consultar Indicadores y Monitorear Capacidad de Carga
* **Actor primario:** Administrador.
* **Actor(es) secundario(s):** Entidad de Gestión del Destino, Autoridad Ambiental (informados).
* **Descripción:** Genera indicadores de ocupación, demanda y concentración turística para apoyar la planificación del destino.
* **Prioridad:** 4.
* **Disparador:** Solicita el reporte periódico de indicadores.
* **Precondiciones:** Existen datos transaccionales suficientes.
* **Postcondiciones:** Reporte generado en formato accesible.
* **Flujo básico:** 1) Selecciona período y zonas de interés. 2) Sistema consulta vistas materializadas de Analítica. 3) Calcula indicadores de ocupación, demanda y concentración. 4) Presenta el reporte resaltando zonas cercanas a su umbral (CU-31). 5) Exporta/comparte el reporte.
* **Flujos alternos:** 4a. Sugiere activar CU-21 hacia zonas de menor congestión.
* **Flujos de excepción:** 2a. Datos insuficientes → informa la limitación.
* **RNF asociados:** Reportes en formatos accesibles (AA); réplicas de solo lectura para no competir con el tráfico transaccional.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** El umbral de capacidad de carga por zona es configurable (CU-31).
* **Trazabilidad:** `Descripcion-General.md` (indicadores para planificación); `Restricciones.md` (monitoreo de capacidad de carga); Stakeholders SH-07, SH-08.

#### CU-31: Configurar Umbrales de Capacidad de Carga por Zona
* **Actor primario:** Administrador.
* **Actor(es) secundario(s):** Autoridad Ambiental (criterio de referencia).
* **Descripción:** Permite definir, por zona o atractivo, el umbral de visitantes a partir del cual se considera riesgo de sobrecarga ambiental.
* **Prioridad:** 3.
* **Disparador:** El administrador accede a "Configuración de sostenibilidad".
* **Precondiciones:** Existe una zonificación o clasificación de atractivos por sensibilidad ambiental.
* **Postcondiciones:** Los umbrales quedan definidos y disponibles para CU-30 y CU-21.
* **Flujo básico:** 1) El administrador selecciona una zona o atractivo. 2) Define el umbral máximo recomendado de visitantes por período. 3) El sistema guarda el umbral y lo vincula al cálculo de indicadores (CU-30). 4) El sistema habilita la alerta correspondiente cuando el indicador se acerque al umbral.
* **Flujos alternos:** 2a. El administrador importa umbrales recomendados por la Autoridad Ambiental como valores de referencia.
* **Flujos de excepción:** 2a. El umbral definido es inconsistente con datos históricos (muy por debajo de la ocupación habitual) → el sistema advierte antes de guardar.
* **RNF asociados:** Trazabilidad de cambios en los umbrales; alineación con criterios de la Autoridad Ambiental.
* **Relaciones:** `include` CU-02; alimenta a CU-30 y CU-21.
* **Reglas de negocio:** Los umbrales deben revisarse periódicamente en coordinación con la Autoridad Ambiental.
* **Trazabilidad:** `Restricciones.md` (Restricciones Ambientales); Stakeholder SH-08.

#### CU-32: Monitorear Salud y Disponibilidad del Sistema
* **Actor primario:** Administrador (rol operativo/técnico).
* **Actor(es) secundario(s):** Proveedor Cloud.
* **Descripción:** Permite supervisar el estado operativo de la plataforma (disponibilidad, latencia, colas de mensajes) para sostener el objetivo de disponibilidad ≥99%.
* **Prioridad:** 4.
* **Disparador:** El administrador accede al panel de monitoreo, o el sistema dispara una alerta automática.
* **Precondiciones:** La herramienta de observabilidad está integrada con el núcleo y los microservicios.
* **Postcondiciones:** El estado del sistema queda visible y las alertas relevantes, registradas.
* **Flujo básico:** 1) El administrador accede al dashboard de monitoreo. 2) El sistema muestra métricas clave (uptime, latencia, estado de la cola de Notificaciones, uso de recursos). 3) El administrador identifica anomalías o revisa alertas activas. 4) El administrador escala el incidente si corresponde (p. ej. contacto con el Proveedor Cloud).
* **Flujos alternos:** 3a. El sistema notifica proactivamente al administrador ante una caída de disponibilidad por debajo del umbral definido.
* **Flujos de excepción:** 4a. La causa raíz está fuera del control de la plataforma (falla del proveedor cloud) → el administrador documenta el incidente y da seguimiento con el proveedor.
* **RNF asociados:** Observabilidad básica (Grafana/herramienta equivalente); soporte directo al atributo de calidad de disponibilidad ≥99%.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** Todo incidente que afecte la disponibilidad debe quedar registrado para el informe de validación de restricciones exigido en `Diseño-de-Ingenieria.md`.
* **Trazabilidad:** `Restricciones.md` (disponibilidad mínima del 99%); Stakeholder SH-10.

#### CU-33: Revisar Log de Auditoría de Seguridad
* **Actor primario:** Administrador.
* **Descripción:** Permite revisar los registros de auditoría de accesos, cambios de rol y decisiones de IA, con fines de trazabilidad y cumplimiento normativo.
* **Prioridad:** 3.
* **Disparador:** El administrador accede a "Auditoría" o investiga un incidente reportado.
* **Precondiciones:** Existen eventos registrados en el log de auditoría (generados por CU-02, CU-27, CU-21, entre otros).
* **Postcondiciones:** El administrador obtiene la evidencia de auditoría solicitada.
* **Flujo básico:** 1) El administrador define el rango de fechas y el tipo de evento a auditar. 2) El sistema consulta el log de auditoría correspondiente. 3) El sistema presenta los eventos encontrados con su detalle (usuario, acción, marca de tiempo). 4) El administrador exporta el resultado si se requiere para un proceso de cumplimiento.
* **Flujos alternos:** 1a. El administrador filtra específicamente por eventos de recomendación de IA (trazabilidad de explicabilidad).
* **Flujos de excepción:** 2a. No existen eventos para los criterios indicados → informa la ausencia de resultados.
* **RNF asociados:** Integridad e inmutabilidad de los registros de auditoría (NIST SP 800-160).
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** Los registros de auditoría no pueden modificarse ni eliminarse manualmente.
* **Trazabilidad:** `Restricciones.md` (trazabilidad de auditoría); Stakeholder SH-09.

#### CU-34: Gestionar Integraciones y Llaves de API Externas
* **Actor primario:** Administrador.
* **Actor(es) secundario(s):** Servicio Externo de Pagos/Reservas (u otros sistemas externos integrados).
* **Descripción:** Permite administrar las credenciales e integraciones con sistemas externos (pasarela de pago, redes sociales, sistemas de reserva de terceros), incluyendo su activación, rotación y revocación.
* **Prioridad:** 2.
* **Disparador:** El administrador necesita habilitar, rotar o revocar una integración externa.
* **Precondiciones:** Autenticado con rol de administración; existe o se requiere una integración con un sistema externo.
* **Postcondiciones:** La integración queda activa, actualizada o revocada, según la acción realizada.
* **Flujo básico:** 1) El administrador accede al panel de integraciones. 2) Selecciona el sistema externo a configurar. 3) Ingresa o rota las credenciales/llaves de API. 4) El sistema valida la conexión con el proveedor externo. 5) El sistema confirma la integración activa.
* **Flujos alternos:** 3a. El administrador revoca una integración existente por sospecha de compromiso de credenciales.
* **Flujos de excepción:** 4a. La validación de conexión falla → el sistema informa el error sin exponer las credenciales en el mensaje.
* **RNF asociados:** Almacenamiento seguro de credenciales (secretos cifrados); trazabilidad de rotación de llaves.
* **Relaciones:** `include` CU-02.
* **Reglas de negocio:** Las credenciales de integraciones externas nunca se muestran en texto plano una vez guardadas.
* **Trazabilidad:** `architectures-technical-details.md` (integración de pasarela de pagos como patrón *adapter*); Stakeholder SH-10, SH-12.

---

## Anexo A: Casos de Uso Alternativos de Funcionalidad de IA (mutuamente excluyentes con CU-21)

`Descripcion-General.md` exige elegir **una sola** funcionalidad de IA. Se documentan de forma resumida las tres alternativas no seleccionadas, para dejar constancia de que fueron evaluadas:

| ID | Caso de Uso | Actor Primario | Resumen |
| :--- | :--- | :--- | :--- |
| **CU-A1** | Interactuar con Chatbot Turístico | Turista | Responde preguntas del turista basándose en información previamente registrada y controlada de la plataforma (atractivos, horarios, políticas), en lugar de generar sugerencias proactivas. |
| **CU-A2** | Clasificar Automáticamente Opiniones de Visitantes | Administrador (consumidor del resultado) | Etiqueta automáticamente las reseñas de CU-19 por sentimiento/categoría, apoyando a CU-29 (moderación) y a CU-30 (indicadores de satisfacción). |
| **CU-A3** | Predecir Ocupación o Demanda de un Atractivo | Administrador / Prestador (consumidores del resultado) | Estima la demanda esperada de un atractivo en un rango de fechas, alimentando a CU-30 (indicadores) y a CU-31 (umbrales de capacidad de carga). |

Si el equipo decide cambiar la funcionalidad de IA seleccionada, el caso de uso correspondiente de este anexo debe desarrollarse con el mismo nivel de detalle que CU-21, y este último pasaría a documentarse aquí como alternativa no elegida.

---

## Síntesis de Cobertura y Trazabilidad

| Atributo de calidad / Restricción priorizada | Casos de Uso que lo materializan |
| :--- | :--- |
| Disponibilidad ≥99% / alta concurrencia estacional | CU-08, CU-11, CU-12, CU-14, CU-16, CU-32 |
| Explicabilidad de IA / no sesgo comercial | CU-21 |
| Cumplimiento Ley 1581 de 2012 | CU-01, CU-06, CU-27, CU-33, CU-34 |
| Multilenguaje ES/EN | CU-05, CU-07, CU-18 |
| Accesibilidad WCAG AA | CU-01, CU-04, CU-05, CU-07, CU-10, CU-15, CU-19, CU-22, CU-27, CU-30 |
| Inclusión de pequeños/medianos prestadores | CU-22, CU-23, CU-26 |
| Turismo sostenible / capacidad de carga | CU-21, CU-30, CU-31 |
| Gobernanza y confianza de la plataforma | CU-26, CU-28, CU-29, CU-33, CU-34 |
| Flujo crítico completo (60% mínimo exigido) | CU-11 (inicio → procesamiento → persistencia → respuesta) |

Esta tabla cierra la trazabilidad exigida por `Diseño-de-Ingenieria.md` entre restricciones/atributos de calidad y los casos de uso que los materializan, y queda lista para alimentar la Matriz de Trazabilidad de Requisitos (RTM) y los diagramas de secuencia del Documento de Diseño Arquitectónico Final.