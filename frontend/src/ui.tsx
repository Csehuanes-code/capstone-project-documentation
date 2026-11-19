import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useIdioma } from "./idioma";

/** Carga datos de la API y expone {datos, error, cargando, recargar}. */
export function useCarga<T>(cargar: () => Promise<T>, deps: unknown[] = []) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const recargar = useCallback(() => {
    setCargando(true);
    setError(null);
    cargar()
      .then(setDatos)
      .catch((e: Error) => setError(e.message))
      .finally(() => setCargando(false));
  }, deps);
  useEffect(() => { recargar(); }, [recargar]);
  return { datos, error, cargando, recargar };
}

export function Aviso({ tipo = "info", children }: { tipo?: "info" | "ok" | "error"; children: ReactNode }) {
  return <div className={`aviso aviso-${tipo}`} role={tipo === "error" ? "alert" : "status"}>{children}</div>;
}

/** Estado vacío o de error con una ilustración: más amable que un texto suelto. */
export function Vacio({ tipo = "vacio", titulo, children }: { tipo?: "vacio" | "error" | "favoritos"; titulo: string; children?: ReactNode }) {
  return (
    <div className={`vacio vacio-${tipo}`} role={tipo === "error" ? "alert" : "status"}>
      <svg viewBox="0 0 200 140" aria-hidden="true">
        <defs>
          <linearGradient id={`vacio-cielo-${tipo}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={tipo === "error" ? "#5b6b78" : "#bfeee7"} />
            <stop offset="1" stopColor={tipo === "error" ? "#9aa9b3" : "#fff3dc"} />
          </linearGradient>
        </defs>
        <rect x="10" y="8" width="180" height="124" rx="28" fill={`url(#vacio-cielo-${tipo})`} />
        {tipo === "error" ? (
          <g className="vacio-nube">
            <path d="M62 70h70a18 18 0 0 0 2-36 26 26 0 0 0-50 6 15 15 0 0 0-22 30Z" fill="#eef3f6" />
            <path d="M104 74 92 96h12l-6 20 20-28h-12l8-14Z" fill="#f5a245" className="vacio-rayo" />
          </g>
        ) : (
          <g>
            <circle cx="146" cy="42" r="14" fill="#f5a245" className="vacio-sol" />
            {tipo === "favoritos"
              ? <path d="M100 104s-26-16-26-35a14 14 0 0 1 26-8 14 14 0 0 1 26 8c0 19-26 35-26 35Z" fill="none" stroke="#ff7a59" strokeWidth="5" strokeLinejoin="round" className="vacio-corazon" />
              : <>
                  <path d="M62 104c2-22 10-38 18-48" stroke="#7a5a3a" strokeWidth="5" fill="none" strokeLinecap="round" />
                  <g className="vacio-palma" fill="#2e9d63">
                    <path d="M80 56c-12-8-26-6-32 2 12-2 22 0 32-2Z" /><path d="M80 56c4-14 16-20 26-18-10 6-18 10-26 18Z" />
                    <path d="M80 56c12-4 24 0 30 8-12-2-20-4-30-8Z" /><path d="M80 56c-8 4-14 14-14 22 6-8 10-14 14-22Z" />
                  </g>
                  <ellipse cx="78" cy="106" rx="34" ry="7" fill="#e8d3a8" />
                </>}
            <path d="M10 112c20-8 40 8 60 0s40-8 60 0 40 8 60 0v20H10Z" fill="#5fd3c6" opacity=".8" className="vacio-ola" />
          </g>
        )}
      </svg>
      <strong>{titulo}</strong>
      {children && <div className="vacio-texto">{children}</div>}
    </div>
  );
}

export function Estado<T>({ carga, children }: {
  carga: { datos: T | null; error: string | null; cargando: boolean; recargar?: () => void };
  children: (datos: T) => ReactNode;
}) {
  const { t, idioma } = useIdioma();
  if (carga.error) return (
    <Vacio tipo="error" titulo={idioma === "en" ? "We couldn't load this" : "No pudimos cargar esto"}>
      <p>{carga.error}</p>
      {carga.recargar && <button type="button" className="boton-secundario" onClick={carga.recargar}>{idioma === "en" ? "Try again" : "Reintentar"}</button>}
    </Vacio>
  );
  if (carga.cargando && carga.datos === null) return (
    <div className="esqueletos" role="status" aria-label={t("cargando")}>
      {[0, 1, 2].map((i) => <div key={i} className="esqueleto" aria-hidden="true"><i /><i /><i /><i /></div>)}
    </div>
  );
  if (carga.datos === null) return null;
  return <>{children(carga.datos)}</>;
}

export function Insignia({ children, tono = "neutro" }: { children: ReactNode; tono?: "neutro" | "ok" | "alerta" | "peligro" }) {
  return <span className={`insignia insignia-${tono}`}>{children}</span>;
}

export function tonoEstado(estado: string): "neutro" | "ok" | "alerta" | "peligro" {
  if (["confirmada", "aprobada", "listo", "completada"].includes(estado)) return "ok";
  if (["pendiente_pago", "enviada", "en_revision", "esperando", "ofrecida", "cancelacion_pendiente"].includes(estado)) return "alerta";
  if (["cancelada", "expirada", "rechazada"].includes(estado)) return "peligro";
  return "neutro";
}

// ---------------- Notificaciones flotantes ----------------

type Toast = { id: number; texto: string; tipo: "ok" | "error" };

/** Muestra una notificación flotante desde cualquier parte de la app. */
export function avisar(texto: string, tipo: "ok" | "error" = "ok") {
  window.dispatchEvent(new CustomEvent<Omit<Toast, "id">>("sierramar:toast", { detail: { texto, tipo } }));
}

export function Toasts() {
  const [lista, setLista] = useState<Toast[]>([]);
  useEffect(() => {
    let n = 0;
    const escuchar = (e: Event) => {
      const { texto, tipo } = (e as CustomEvent<Omit<Toast, "id">>).detail;
      const id = ++n;
      setLista((l) => [...l.slice(-2), { id, texto, tipo }]);
      setTimeout(() => setLista((l) => l.filter((t) => t.id !== id)), 4200);
    };
    window.addEventListener("sierramar:toast", escuchar);
    return () => window.removeEventListener("sierramar:toast", escuchar);
  }, []);
  return (
    <div className="toasts" role="status" aria-live="polite">
      {lista.map((t) => (
        <div key={t.id} className={`toast toast-${t.tipo}`} onClick={() => setLista((l) => l.filter((x) => x.id !== t.id))}>
          <span className="toast-icono" aria-hidden="true">{t.tipo === "ok" ? "✓" : "!"}</span>
          <span>{t.texto}</span>
          <i className="toast-barra" aria-hidden="true" />
        </div>
      ))}
    </div>
  );
}

// ---------------- Contador animado ----------------

/** Número que sube desde 0 hasta el valor real (sin animación si el usuario pide menos movimiento). */
export function Contador({ valor, formato = String }: { valor: number | null | undefined; formato?: (n: number) => string }) {
  const [mostrado, setMostrado] = useState(0);
  useEffect(() => {
    if (valor == null) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) { setMostrado(valor); return; }
    const inicio = performance.now();
    let cuadro = 0;
    const paso = (ahora: number) => {
      const t = Math.min(1, (ahora - inicio) / 1400);
      setMostrado(Math.round(valor * (1 - Math.pow(1 - t, 3))));
      if (t < 1) cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro);
  }, [valor]);
  return <>{valor == null ? "—" : formato(mostrado)}</>;
}
