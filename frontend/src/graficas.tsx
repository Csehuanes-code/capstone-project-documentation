// Gráficas SVG animadas y livianas para los paneles (sin librerías externas).
import { useEffect, useState } from "react";

export const PALETA_ZONAS: Record<string, string> = {
  tayrona: "#0b8f8a", minca: "#f5a245", centro: "#9b6bd6", taganga: "#2f8fd6", "los-naranjos": "#ff7a59", rodadero: "#e05d8a",
};
const RESPALDO = ["#0b8f8a", "#f5a245", "#2f8fd6", "#ff7a59", "#2e9d63", "#9b6bd6", "#5fd3c6"];

/** Se vuelve true un instante después de montar: dispara las transiciones CSS de entrada. */
function useMontado() {
  const [listo, setListo] = useState(false);
  useEffect(() => { const t = requestAnimationFrame(() => setListo(true)); return () => cancelAnimationFrame(t); }, []);
  return listo;
}

export interface Parte { clave: string; etiqueta: string; valor: number; color?: string }

/** Dona con leyenda: cada segmento se dibuja en orden. */
export function Dona({ partes, titulo, centro, unidad }: { partes: Parte[]; titulo: string; centro: string; unidad: string }) {
  const listo = useMontado();
  const total = partes.reduce((s, p) => s + p.valor, 0) || 1;
  const R = 70;
  const C = 2 * Math.PI * R;
  let acumulado = 0;
  return (
    <figure className="grafica dona">
      <svg viewBox="0 0 200 200" role="img" aria-label={`${titulo}: ${partes.map((p) => `${p.etiqueta} ${p.valor}`).join(", ")}`}>
        <circle cx="100" cy="100" r={R} fill="none" stroke="var(--superficie-2)" strokeWidth="26" />
        {partes.map((p, i) => {
          const largo = (p.valor / total) * C;
          const inicio = acumulado;
          acumulado += largo;
          return (
            <circle key={p.clave} cx="100" cy="100" r={R} fill="none" strokeWidth="26" strokeLinecap="butt"
              stroke={p.color ?? PALETA_ZONAS[p.clave] ?? RESPALDO[i % RESPALDO.length]}
              strokeDasharray={`${listo ? Math.max(0, largo - 2) : 0} ${C}`} strokeDashoffset={-inicio}
              transform="rotate(-90 100 100)" style={{ transition: `stroke-dasharray .9s cubic-bezier(.2,.7,.2,1) ${i * 120}ms` }} />
          );
        })}
        <text x="100" y="96" textAnchor="middle" className="dona-centro">{centro}</text>
        <text x="100" y="120" textAnchor="middle" className="dona-unidad">{unidad}</text>
      </svg>
      <figcaption>
        <strong>{titulo}</strong>
        <ul>
          {partes.map((p, i) => (
            <li key={p.clave}>
              <i style={{ background: p.color ?? PALETA_ZONAS[p.clave] ?? RESPALDO[i % RESPALDO.length] }} />
              <span>{p.etiqueta}</span><b>{Math.round((p.valor / total) * 100)} %</b>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}

/** Barras verticales que crecen desde abajo, con el valor encima. */
export function Barras({ datos, titulo, formato = String }: {
  datos: { clave: string; etiqueta: string; valor: number; resaltar?: boolean }[]; titulo: string; formato?: (n: number) => string;
}) {
  const listo = useMontado();
  const max = Math.max(1, ...datos.map((d) => d.valor));
  return (
    <figure className="grafica barras">
      <figcaption><strong>{titulo}</strong></figcaption>
      <div className="barras-area" role="img" aria-label={`${titulo}: ${datos.map((d) => `${d.etiqueta} ${formato(d.valor)}`).join(", ")}`}>
        {datos.map((d, i) => (
          <div key={d.clave} className={`barra-col${d.resaltar ? " resaltada" : ""}`}>
            <span className="barra-valor">{d.valor ? formato(d.valor) : ""}</span>
            <span className="barra-relleno" style={{ height: listo ? `${(d.valor / max) * 100}%` : "0%", transitionDelay: `${i * 45}ms` }} />
            <small>{d.etiqueta}</small>
          </div>
        ))}
      </div>
    </figure>
  );
}
