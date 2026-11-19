// Piezas compartidas de la capa "siguiente nivel": tema, favoritos, clima, actividad en vivo,
// recordatorios, galería a pantalla completa y animación de reacomodo de rejillas.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api, type Comprobante } from "./api";
import { Icono, type NombreIcono } from "./ilustraciones";
import { REFERENCIA } from "./MapaZonas";
import { avisar } from "./ui";

const menosMovimiento = () => Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
function leer(clave: string): string | null { try { return localStorage.getItem(clave); } catch { return null; } }
function guardar(clave: string, valor: string) { try { localStorage.setItem(clave, valor); } catch { /* modo privado */ } }

export function isoLocal(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** "hace 3 min" / "3 min ago" */
export function hace(iso: string, en: boolean) {
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 45) return en ? "just now" : "hace un momento";
  const m = Math.round(s / 60);
  if (m < 60) return en ? `${m} min ago` : `hace ${m} min`;
  const h = Math.round(m / 60);
  if (h < 24) return en ? `${h} h ago` : `hace ${h} h`;
  const d = Math.round(h / 24);
  return en ? `${d} d ago` : `hace ${d} d`;
}

// ---------------- Tema claro / oscuro ----------------

type Tema = "claro" | "oscuro";
const temaGuardado = (): Tema | null => { const t = leer("tema"); return t === "claro" || t === "oscuro" ? t : null; };

/** Se llama antes de pintar la app para que no parpadee el tema equivocado. */
export function aplicarTemaGuardado() {
  const t = temaGuardado();
  if (t) document.documentElement.dataset.tema = t;
}

export function BotonTema({ en }: { en: boolean }) {
  const [tema, setTema] = useState<Tema>(() => temaGuardado()
    ?? (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro"));
  const cambiar = () => {
    const nuevo: Tema = tema === "oscuro" ? "claro" : "oscuro";
    const aplicar = () => { document.documentElement.dataset.tema = nuevo; setTema(nuevo); };
    guardar("tema", nuevo);
    const doc = document as Document & { startViewTransition?: (cb: () => void) => unknown };
    if (doc.startViewTransition && !menosMovimiento()) doc.startViewTransition(aplicar); else aplicar();
  };
  const texto = tema === "oscuro" ? (en ? "Light mode" : "Modo claro") : (en ? "Dark mode" : "Modo oscuro");
  return (
    <button type="button" className="boton-tema" onClick={cambiar} aria-label={texto} title={texto}>
      <span key={tema} className="boton-tema-icono"><Icono n={tema === "oscuro" ? "sol" : "luna"} tam={18} /></span>
    </button>
  );
}

// ---------------- Favoritos (en este dispositivo) ----------------

const leerFavoritos = (): string[] => { try { return JSON.parse(leer("favoritos") ?? "[]") as string[]; } catch { return []; } };

export function useFavoritos() {
  const [lista, setLista] = useState<string[]>(leerFavoritos);
  useEffect(() => {
    const sync = () => setLista(leerFavoritos());
    window.addEventListener("sierramar:favoritos", sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener("sierramar:favoritos", sync); window.removeEventListener("storage", sync); };
  }, []);
  const alternar = useCallback((id: string) => {
    const actual = leerFavoritos();
    const quedo = !actual.includes(id);
    guardar("favoritos", JSON.stringify(quedo ? [...actual, id] : actual.filter((x) => x !== id)));
    window.dispatchEvent(new Event("sierramar:favoritos"));
    return quedo;
  }, []);
  return { favoritos: lista, esFavorito: (id: string) => lista.includes(id), alternar };
}

export function BotonFavorito({ id, nombre, en }: { id: string; nombre: string; en: boolean }) {
  const { esFavorito, alternar } = useFavoritos();
  const activo = esFavorito(id);
  const [pulso, setPulso] = useState(0);
  return (
    <button type="button" className={`boton-favorito${activo ? " activo" : ""}`} aria-pressed={activo}
      aria-label={activo ? (en ? `Remove ${nombre} from favorites` : `Quitar ${nombre} de favoritos`) : (en ? `Save ${nombre}` : `Guardar ${nombre}`)}
      onClick={(e) => {
        e.preventDefault(); e.stopPropagation();
        const quedo = alternar(id);
        setPulso((p) => p + 1);
        avisar(quedo ? (en ? `${nombre} saved to favorites` : `${nombre} guardada en favoritos`) : (en ? "Removed from favorites" : "Quitada de favoritos"));
      }}>
      <span key={pulso} className={`corazon${pulso ? " late" : ""}`}><Icono n="corazon" tam={20} /></span>
      {activo && pulso > 0 && <span key={`e${pulso}`} className="estallido" aria-hidden="true">{Array.from({ length: 8 }, (_, i) => <i key={i} />)}</span>}
    </button>
  );
}

// ---------------- Clima por zona (Open-Meteo, sin clave) ----------------

export interface Clima { temp: number; codigo: number }

export function useClima(): Record<string, Clima> {
  const [clima, setClima] = useState<Record<string, Clima>>(() => {
    try {
      const c = JSON.parse(sessionStorage.getItem("clima") ?? "null") as { en: number; datos: Record<string, Clima> } | null;
      return c && Date.now() - c.en < 30 * 60e3 ? c.datos : {};
    } catch { return {}; }
  });
  useEffect(() => {
    if (Object.keys(clima).length) return;
    const codigos = Object.keys(REFERENCIA);
    const lat = codigos.map((c) => REFERENCIA[c][0]).join(",");
    const lon = codigos.map((c) => REFERENCIA[c][1]).join(",");
    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,weather_code&timezone=America%2FBogota`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((js: { current: { temperature_2m: number; weather_code: number } }[] | { current: { temperature_2m: number; weather_code: number } }) => {
        const lista = Array.isArray(js) ? js : [js];
        const datos: Record<string, Clima> = {};
        lista.forEach((l, i) => { if (codigos[i] && l.current) datos[codigos[i]] = { temp: l.current.temperature_2m, codigo: l.current.weather_code }; });
        setClima(datos);
        try { sessionStorage.setItem("clima", JSON.stringify({ en: Date.now(), datos })); } catch { /* sin almacenamiento */ }
      })
      .catch(() => { /* sin conexión: simplemente no se muestra el clima */ });
  }, [clima]);
  return clima;
}

function describirClima(codigo: number, en: boolean): [NombreIcono, string] {
  if (codigo <= 1) return ["sol", en ? "Sunny" : "Soleado"];
  if (codigo <= 3) return ["nube", en ? "Partly cloudy" : "Parcialmente nublado"];
  if (codigo <= 48) return ["nube", en ? "Foggy" : "Neblina"];
  return ["lluvia", en ? "Rain" : "Lluvia"];
}

export function ChipClima({ clima, en, completo = false }: { clima?: Clima; en: boolean; completo?: boolean }) {
  if (!clima) return null;
  const [icono, texto] = describirClima(clima.codigo, en);
  return (
    <span className={`chip-clima clima-${icono}`} title={`${texto} · ${en ? "now" : "ahora"}`}>
      <Icono n={icono} tam={15} />{Math.round(clima.temp)}°{completo && <span> · {texto}</span>}
    </span>
  );
}

// ---------------- Actividad en vivo (Analítica) ----------------

export interface ReservaReciente { evento_id: string; zona_id: string; zona: string; personas: number; procesado_en: string }
export interface OcupacionPublicada { evento_id: string; zona_id: string; ocupacion: number; ocurrido_en: string; publicado_en: string | null }
export interface Actividad { reservas: ReservaReciente[]; ocupaciones: OcupacionPublicada[]; outbox_pendientes: number }

/** Consulta periódica de la actividad; se pausa con la pestaña oculta. */
export function useActividad(cadaMs: number, limite = 8) {
  const [datos, setDatos] = useState<Actividad | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let vivo = true;
    let t = 0;
    const consultar = async () => {
      if (!document.hidden) {
        try { const d = await api<Actividad>("/api/v1/analitica/actividad", { query: { limite } }); if (vivo) { setDatos(d); setError(false); } }
        catch { if (vivo) setError(true); }
      }
      if (vivo) t = window.setTimeout(consultar, cadaMs);
    };
    consultar();
    return () => { vivo = false; clearTimeout(t); };
  }, [cadaMs, limite]);
  return { datos, error };
}

/** Píldora flotante en la portada: "Alguien reservó en Minca · hace 3 min". */
export function AvisoReciente({ en }: { en: boolean }) {
  const { datos } = useActividad(20000, 5);
  const [i, setI] = useState(0);
  const [cerrado, setCerrado] = useState(() => { try { return sessionStorage.getItem("aviso-reciente") === "no"; } catch { return false; } });
  const recientes = (datos?.reservas ?? []).filter((r) => Date.now() - new Date(r.procesado_en).getTime() < 7 * 864e5);
  useEffect(() => {
    if (recientes.length < 2) return;
    const t = setInterval(() => setI((x) => x + 1), 6000);
    return () => clearInterval(t);
  }, [recientes.length]);
  if (cerrado || recientes.length === 0) return null;
  const r = recientes[i % recientes.length];
  return (
    <div className="aviso-reciente" role="status">
      <span className="aviso-reciente-punto" aria-hidden="true" />
      <span key={r.evento_id + i} className="aviso-reciente-texto">
        {en ? <>Someone booked in <b>{r.zona}</b></> : <>Alguien reservó en <b>{r.zona}</b></>}
        <small>{r.personas} {r.personas === 1 ? (en ? "guest" : "persona") : (en ? "guests" : "personas")} · {hace(r.procesado_en, en)}</small>
      </span>
      <button type="button" aria-label={en ? "Close" : "Cerrar"} onClick={() => { setCerrado(true); try { sessionStorage.setItem("aviso-reciente", "no"); } catch { /* */ } }}>
        <Icono n="cerrar" tam={14} />
      </button>
    </div>
  );
}

// ---------------- Recordatorios del navegador ----------------

async function notificar(titulo: string, cuerpo: string, url: string) {
  const opciones = { body: cuerpo, icon: "/icono.svg", badge: "/icono.svg", data: { url }, tag: url };
  const registro = await navigator.serviceWorker?.getRegistration?.();
  if (registro) await registro.showNotification(titulo, opciones);
  else new Notification(titulo, opciones);
}

/** Si el turista activó los avisos, al abrir la app le recuerda los tours de hoy y de mañana (una vez por día). */
export function useRecordatorios(activo: boolean, en: boolean, senal = 0) {
  useEffect(() => {
    if (!activo || typeof Notification === "undefined" || Notification.permission !== "granted") return;
    const hoy = isoLocal(new Date());
    const manana = isoLocal(new Date(Date.now() + 864e5));
    api<Comprobante[]>("/api/v1/reservas/mias").then((rs) => {
      for (const r of rs) {
        if (r.estado !== "confirmada" || (r.fecha_servicio !== hoy && r.fecha_servicio !== manana)) continue;
        const clave = `recordado:${r.reserva_id}:${hoy}`;
        if (leer(clave)) continue;
        guardar(clave, "1");
        const cuando = r.fecha_servicio === hoy ? (en ? "today" : "hoy") : (en ? "tomorrow" : "mañana");
        notificar(en ? `Your tour is ${cuando} 🌴` : `Tu tour es ${cuando} 🌴`,
          `${r.nombre_oferta} · ${r.hora_servicio.slice(0, 5)} · ${r.codigo}`, `/reservas/${r.reserva_id}`).catch(() => undefined);
      }
    }).catch(() => undefined);
  }, [activo, en, senal]);
}

export function BotonRecordatorios({ en }: { en: boolean }) {
  const soporta = typeof Notification !== "undefined";
  const [permiso, setPermiso] = useState(soporta ? Notification.permission : "denied");
  if (!soporta) return null;
  if (permiso === "granted") return <span className="chip-recordatorio activo"><Icono n="rayo" tam={15} />{en ? "Reminders on" : "Recordatorios activos"}</span>;
  return (
    <button type="button" className="boton-secundario chip-recordatorio" disabled={permiso === "denied"}
      title={permiso === "denied" ? (en ? "Notifications are blocked in this browser" : "Las notificaciones están bloqueadas en este navegador") : undefined}
      onClick={async () => {
        const p = await Notification.requestPermission();
        setPermiso(p);
        if (p === "granted") {
          notificar(en ? "Reminders on" : "Recordatorios activados",
            en ? "We'll remind you the day before each tour." : "Te avisaremos el día antes de cada tour.", "/mis-reservas").catch(() => undefined);
          window.dispatchEvent(new Event("sierramar:recordatorios"));
        }
      }}>
      <Icono n="rayo" tam={15} />{en ? "Remind me the day before" : "Avísame el día antes"}
    </button>
  );
}

// ---------------- Galería a pantalla completa ----------------

export function Galeria({ fotos, inicio, titulo, alCerrar }: { fotos: string[]; inicio: number; titulo: string; alCerrar: () => void }) {
  const [i, setI] = useState(inicio);
  const [dir, setDir] = useState(0);
  const toque = useRef<number | null>(null);
  const ir = useCallback((d: number) => { setDir(d); setI((x) => (x + d + fotos.length) % fotos.length); }, [fotos.length]);
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") alCerrar();
      if (e.key === "ArrowRight") ir(1);
      if (e.key === "ArrowLeft") ir(-1);
    };
    window.addEventListener("keydown", tecla);
    const previo = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", tecla); document.body.style.overflow = previo; };
  }, [alCerrar, ir]);
  return createPortal(
    <div className="galeria-completa" role="dialog" aria-modal="true" aria-label={titulo} onClick={alCerrar}
      onPointerDown={(e) => { toque.current = e.clientX; }}
      onPointerUp={(e) => {
        if (toque.current == null) return;
        const dx = e.clientX - toque.current;
        toque.current = null;
        if (Math.abs(dx) > 50) { e.stopPropagation(); ir(dx < 0 ? 1 : -1); }
      }}>
      <div className="galeria-barra" onClick={(e) => e.stopPropagation()}>
        <span>{titulo} · {i + 1} / {fotos.length}</span>
        <button type="button" onClick={alCerrar} aria-label="Cerrar"><Icono n="cerrar" /></button>
      </div>
      <img key={i} src={fotos[i]} alt={`${titulo} ${i + 1}`} className={dir > 0 ? "desde-derecha" : dir < 0 ? "desde-izquierda" : ""}
        onClick={(e) => e.stopPropagation()} draggable={false} />
      {fotos.length > 1 && <>
        <button type="button" className="galeria-flecha izq" aria-label="Anterior" onClick={(e) => { e.stopPropagation(); ir(-1); }}>‹</button>
        <button type="button" className="galeria-flecha der" aria-label="Siguiente" onClick={(e) => { e.stopPropagation(); ir(1); }}>›</button>
        <div className="galeria-miniaturas" onClick={(e) => e.stopPropagation()}>
          {fotos.map((f, n) => (
            <button key={f} type="button" aria-pressed={n === i} onClick={() => { setDir(n > i ? 1 : -1); setI(n); }}><img src={f} alt="" /></button>
          ))}
        </div>
      </>}
    </div>,
    document.body,
  );
}

// ---------------- Reacomodo animado (FLIP) ----------------

/** Los hijos con data-flip se deslizan a su nueva posición cuando cambia `clave`; los nuevos aparecen con un zoom. */
export function useFlip<T extends HTMLElement>(clave: unknown) {
  const ref = useRef<T>(null);
  const antes = useRef(new Map<string, { x: number; y: number }>());
  useLayoutEffect(() => {
    const cont = ref.current;
    if (!cont) return;
    const animar = !menosMovimiento() && typeof cont.animate === "function";
    const ahora = new Map<string, { x: number; y: number }>();
    let n = 0;
    for (const h of Array.from(cont.children) as HTMLElement[]) {
      const k = h.dataset.flip;
      if (!k) continue;
      const p = { x: h.offsetLeft, y: h.offsetTop };
      ahora.set(k, p);
      if (!animar || antes.current.size === 0) continue;
      const a = antes.current.get(k);
      if (a && (a.x !== p.x || a.y !== p.y)) {
        h.animate([{ transform: `translate(${a.x - p.x}px, ${a.y - p.y}px)` }, { transform: "none" }],
          { duration: 520, easing: "cubic-bezier(.2,.7,.2,1)" });
      } else if (!a) {
        h.animate([{ opacity: 0, transform: "scale(.9) translateY(14px)" }, { opacity: 1, transform: "none" }],
          { duration: 420, delay: 40 * n++, easing: "cubic-bezier(.2,.7,.2,1)", fill: "backwards" });
      }
    }
    antes.current = ahora;
  }, [clave]);
  return ref;
}
