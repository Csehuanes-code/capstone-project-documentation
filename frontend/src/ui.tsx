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

export function Estado<T>({ carga, children }: {
  carga: { datos: T | null; error: string | null; cargando: boolean };
  children: (datos: T) => ReactNode;
}) {
  const { t } = useIdioma();
  if (carga.error) return <Aviso tipo="error">{carga.error}</Aviso>;
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
export function Contador({ valor }: { valor: number | null | undefined }) {
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
  return <>{valor == null ? "—" : mostrado}</>;
}
