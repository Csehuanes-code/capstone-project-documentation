// Cliente HTTP único: todo pasa por el gateway (misma URL que la página).
// El token de Auth viaja en Authorization; cada servicio lo valida por su cuenta (ADR-06).

export class ApiError extends Error {
  constructor(public status: number, message: string, public body: unknown) {
    super(message);
  }
}

let token: string | null = localStorage.getItem("token");
export const setToken = (t: string | null) => {
  token = t;
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
};
export const getToken = () => token;

function mensaje(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => e?.msg ?? JSON.stringify(e)).join("; ");
  }
  return `Error ${status}`;
}

export async function api<T = unknown>(
  ruta: string,
  opciones: { method?: string; body?: unknown; headers?: Record<string, string>; query?: Record<string, unknown> } = {},
): Promise<T> {
  const qs = opciones.query
    ? "?" + new URLSearchParams(
        Object.entries(opciones.query)
          .filter(([, v]) => v !== undefined && v !== null && v !== "")
          .map(([k, v]) => [k, String(v)]),
      ).toString()
    : "";
  const headers: Record<string, string> = { ...(opciones.headers ?? {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opciones.body !== undefined) headers["Content-Type"] = "application/json";
  const r = await fetch(ruta + qs, {
    method: opciones.method ?? "GET",
    headers,
    body: opciones.body !== undefined ? JSON.stringify(opciones.body) : undefined,
  });
  const texto = await r.text();
  let body: unknown = null;
  try {
    body = texto ? JSON.parse(texto) : null;
  } catch {
    body = texto;
  }
  // 402 (pago rechazado) también trae comprobante: se devuelve como respuesta válida.
  if (!r.ok && r.status !== 402) throw new ApiError(r.status, mensaje(body, r.status), body);
  return body as T;
}

// --- Tipos de las respuestas que usa la interfaz ------------------------------------------

export type Rol = "turista" | "prestador" | "administrador";

export interface Zona { id: string; codigo: string; nombre_es: string; nombre_en: string }
export interface TipoServicio { id: string; codigo: string; nombre_es: string; nombre_en: string }
export interface Oferta {
  id: string; zona_id: string; tipo_servicio_id: string; prestador_id: string | null;
  nombre_es: string; nombre_en: string; descripcion_es: string; descripcion_en: string;
  atributos: { categorias?: string[]; duracion_horas?: number; [k: string]: unknown };
  estado: string; calificacion_promedio: number; total_calificaciones: number;
}
export interface Tarifa { temporada: string; precio_por_persona: number; moneda: string; vigente_desde: string; vigente_hasta: string }
export interface Politica { horas_reembolso_total: number; horas_reembolso_parcial: number; porcentaje_reembolso_parcial: number }
export interface DetalleOferta { oferta: Oferta; zona: Zona | null; tarifas: Tarifa[]; politica_cancelacion: Politica | null }
export interface Franja { id: string; oferta_id: string; zona_id: string; fecha: string; hora_inicio: string; cupo_total: number; cupo_disponible: number }
export interface Comprobante {
  reserva_id: string; codigo: string; estado: string; oferta_id: string; nombre_oferta: string; zona_id: string;
  prestador_nombre: string; prestador_contacto: string; punto_encuentro: string;
  fecha_servicio: string; hora_servicio: string; personas: number; acompanantes: string[];
  precio_unitario: string; total: string; moneda: string; pago_aprobado: boolean; referencia_pago: string | null;
  monto_reembolso: string | null; mensaje_es: string; mensaje_en: string;
  politica_cancelacion: { descripcion_es: string; descripcion_en: string };
}
export interface Aporte { criterio: string; etiqueta: string; peso: number; valor: number; aporte: number }
export interface ItemRecomendado {
  posicion: number; oferta_id: string; nombre: string; puntaje: number; motivo: string; explicacion: string;
  calificacion_promedio: number; numero_resenas: number;
  zona: { id: string; nombre: string | null; ocupacion: number | null; nivel: string };
  desglose: Aporte[]; alternativa_de: { nombre: string; zona: string | null } | null;
}
export interface Recomendacion { id: string; version_pesos: number; items: ItemRecomendado[] }
export interface EntradaListaEspera { entrada_id: string; franja_id: string; personas: number; estado: string; posicion: number | null; oferta_expira_en: string | null }
export interface Verificacion { id: string; provider_id: string; business_name: string; nit: string; rnt: string; status: string; justification: string | null }
export interface Indicador {
  zona_id: string; reservas_confirmadas: number; visitantes_reservados: number; ingresos_cop: number;
  concentracion: number; umbral_visitantes: number | null; ocupacion_estimada: number | null; cerca_del_umbral: boolean;
}
export interface Alerta { zona_id: string; ocupacion: number; visitantes: number; umbral: number; creada_en: string }
export interface Disputa { disputa_id: string; reserva_id: string; estado: string; motivo: string; justificacion: string | null; monto_reembolso: string | null }

export const INTERESES = ["naturaleza", "cultura", "gastronomia", "historia", "playa", "aventura"] as const;

export function pesos(valor: number | string, moneda = "COP"): string {
  return `$${Number(valor).toLocaleString("es-CO", { maximumFractionDigits: 0 })} ${moneda}`;
}
