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
