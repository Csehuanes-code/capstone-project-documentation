import { createContext, useContext, useState, type ReactNode } from "react";

// Español e inglés en toda la interfaz (RC-S02). Los servicios también responden en ambos.
const textos = {
  es: {
    explorar: "Explorar", paraTi: "Para ti", misReservas: "Mis reservas", panel: "Mi panel",
    admin: "Administración", entrar: "Iniciar sesión", salir: "Salir", registro: "Crear cuenta",
    lema: "Turismo regenerativo en la ciudad más antigua de Colombia",
    subtitulo: "Reserva experiencias con operadores verificados, con cupos reales y sin sobreventa.",
    intereses: "¿Qué te interesa?", recomendar: "Ver recomendaciones",
    porQue: "¿Por qué veo esto?", alternativa: "Alternativa a una zona saturada",
    catalogo: "Catálogo", todasZonas: "Todas las zonas", todasCategorias: "Todas las categorías",
    verDetalle: "Ver detalle", porPersona: "por persona", disponibilidad: "Disponibilidad",
    sinCupos: "No hay cupos para esa fecha.", cupos: "cupos", reservar: "Reservar", personas: "Personas",
    correo: "Correo", tarjeta: "Tarjeta (simulada)", acompanantes: "Acompañantes (opcional, separados por coma)",
    pagar: "Pagar y reservar", confirmada: "Reserva confirmada", comprobante: "Comprobante",
    cancelar: "Cancelar reserva", listaEspera: "Unirme a la lista de espera", politica: "Política de cancelación",
    cargando: "Cargando…", vacio: "Todavía no hay nada aquí.", total: "Total", estado: "Estado",
    fecha: "Fecha", zona: "Zona", guardar: "Guardar", clave: "Contraseña", rol: "Tipo de cuenta",
    turista: "Turista", prestador: "Prestador de servicios", consentimiento: "Acepto la política de tratamiento de datos (Ley 1581)",
    revisaCorreo: "Te enviamos un correo para confirmar la cuenta. Ábrelo en Mailpit (localhost:8025).",
    cuentaConfirmada: "Cuenta confirmada. Ya puedes iniciar sesión.",
  },
  en: {
    explorar: "Explore", paraTi: "For you", misReservas: "My bookings", panel: "My dashboard",
    admin: "Administration", entrar: "Sign in", salir: "Sign out", registro: "Create account",
    lema: "Regenerative tourism in Colombia's oldest city",
    subtitulo: "Book experiences with verified operators, real availability and no overbooking.",
    intereses: "What are you into?", recomendar: "See recommendations",
    porQue: "Why am I seeing this?", alternativa: "Alternative to a crowded area",
    catalogo: "Catalog", todasZonas: "All areas", todasCategorias: "All categories",
    verDetalle: "View details", porPersona: "per person", disponibilidad: "Availability",
    sinCupos: "No spots for that date.", cupos: "spots", reservar: "Book", personas: "Guests",
    correo: "Email", tarjeta: "Card (simulated)", acompanantes: "Companions (optional, comma separated)",
    pagar: "Pay and book", confirmada: "Booking confirmed", comprobante: "Receipt",
    cancelar: "Cancel booking", listaEspera: "Join the waitlist", politica: "Cancellation policy",
    cargando: "Loading…", vacio: "Nothing here yet.", total: "Total", estado: "Status",
    fecha: "Date", zona: "Area", guardar: "Save", clave: "Password", rol: "Account type",
    turista: "Tourist", prestador: "Service provider", consentimiento: "I accept the data processing policy",
    revisaCorreo: "We sent you an email to confirm your account. Open it in Mailpit (localhost:8025).",
    cuentaConfirmada: "Account confirmed. You can sign in now.",
  },
} as const;

export type Idioma = keyof typeof textos;
type Clave = keyof (typeof textos)["es"];

const Contexto = createContext<{ idioma: Idioma; t: (c: Clave) => string; cambiar: () => void } | null>(null);

export function ProveedorIdioma({ children }: { children: ReactNode }) {
  const [idioma, setIdioma] = useState<Idioma>((localStorage.getItem("idioma") as Idioma) || "es");
  const cambiar = () => {
    const nuevo = idioma === "es" ? "en" : "es";
    localStorage.setItem("idioma", nuevo);
    document.documentElement.lang = nuevo;
    setIdioma(nuevo);
  };
  return <Contexto.Provider value={{ idioma, t: (c) => textos[idioma][c], cambiar }}>{children}</Contexto.Provider>;
}

export function useIdioma() {
  const c = useContext(Contexto);
  if (!c) throw new Error("useIdioma fuera del proveedor");
  return c;
}
