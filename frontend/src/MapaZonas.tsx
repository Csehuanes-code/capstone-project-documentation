// Mapa ilustrado de las zonas de Santa Marta, coloreadas por su nivel de ocupación (dato de IA,
// que lo recibe de Analítica). Las coordenadas vienen de Catálogo; si faltan, se usan las de referencia.
import type { Zona } from "./api";
import { useIdioma } from "./idioma";

const REFERENCIA: Record<string, [number, number]> = {
  rodadero: [11.2006, -74.2296], centro: [11.2408, -74.211], taganga: [11.2672, -74.1907],
  tayrona: [11.33, -74.035], "los-naranjos": [11.3, -73.92], minca: [11.143, -74.119],
};
const LIMITES = { latMax: 11.37, latMin: 11.1, lonMin: -74.27, lonMax: -73.87 };
const ANCHO = 1000;
const ALTO = 560;

export const COLOR_NIVEL: Record<string, string> = {
  tranquila: "#3ddc97", moderada: "#f5a245", muy_concurrida: "#ff5a4f", desconocida: "#9db4b2",
};
const TEXTO_NIVEL: Record<string, [string, string]> = {
  tranquila: ["Tranquila", "Quiet"], moderada: ["Moderada", "Moderate"], muy_concurrida: ["Saturada", "Crowded"], desconocida: ["Sin datos", "No data"],
};

export interface EstadoZona { nivel: string; ocupacion: number | null }

function proyectar(lat: number, lon: number): [number, number] {
  const x = ((lon - LIMITES.lonMin) / (LIMITES.lonMax - LIMITES.lonMin)) * ANCHO;
  const y = ((LIMITES.latMax - lat) / (LIMITES.latMax - LIMITES.latMin)) * ALTO;
  return [Math.round(x), Math.round(y)];
}

// Costa estilizada: la tierra queda al sur y al oriente, el mar Caribe al norte y al occidente.
const COSTA = "M0 430 C40 410 70 380 88 352 C100 330 112 300 128 278 C140 262 150 250 170 236 C182 226 186 210 200 202 "
  + "C230 186 262 176 300 160 C340 142 380 120 430 104 C480 88 520 74 566 66 C600 60 630 70 668 86 C710 104 744 116 790 122 "
  + "C840 128 870 120 910 126 C950 132 975 140 1000 146 L1000 560 L0 560 Z";

const LADO_ETIQUETA: Record<string, "derecha" | "izquierda" | "abajo"> = { tayrona: "izquierda", "los-naranjos": "derecha" };

const MONTANAS: [number, number, number][] = [
  [560, 360, 120], [660, 330, 150], [770, 350, 140], [880, 320, 160], [720, 440, 110], [470, 440, 90], [940, 430, 110],
];

export default function MapaZonas({ zonas, estados, onElegir, elegida }: {
  zonas: Zona[];
  estados: Record<string, EstadoZona>;
  onElegir: (zonaId: string) => void;
  elegida?: string;
}) {
  const { idioma } = useIdioma();
  const en = idioma === "en";
  const puntos = zonas
    .map((z) => {
      const ref = REFERENCIA[z.codigo];
      const lat = (z as Zona & { latitud?: number | null }).latitud ?? ref?.[0];
      const lon = (z as Zona & { longitud?: number | null }).longitud ?? ref?.[1];
      if (lat == null || lon == null) return null;
      const [x, y] = proyectar(lat, lon);
      return { z, x, y, estado: estados[z.id] ?? { nivel: "desconocida", ocupacion: null } };
    })
    .filter((p): p is NonNullable<typeof p> => p !== null);

  return (
    <div className="mapa">
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img"
        aria-label={en ? "Map of Santa Marta areas colored by occupancy" : "Mapa de las zonas de Santa Marta coloreadas por ocupación"}>
        <defs>
          <linearGradient id="mapa-mar" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#0c3a52" />
            <stop offset="1" stopColor="#0a2130" />
          </linearGradient>
          <linearGradient id="mapa-tierra" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#1f5a4c" />
            <stop offset="1" stopColor="#123a33" />
          </linearGradient>
          <radialGradient id="mapa-brillo" cx=".3" cy=".2" r=".7">
            <stop offset="0" stopColor="#5fd3c6" stopOpacity=".35" />
            <stop offset="1" stopColor="#5fd3c6" stopOpacity="0" />
          </radialGradient>
          <filter id="mapa-sombra" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="6" stdDeviation="8" floodColor="#000" floodOpacity=".35" />
          </filter>
        </defs>
        <rect width={ANCHO} height={ALTO} fill="url(#mapa-mar)" />
        <rect width={ANCHO} height={ALTO} fill="url(#mapa-brillo)" />
        {[0, 1, 2, 3].map((i) => (
          <path key={i} d={`M${-40 + i * 30} ${110 + i * 70} q60 -14 120 0 t120 0 t120 0`} fill="none" stroke="#5fd3c6" strokeOpacity=".14" strokeWidth="2" />
        ))}
        <text x="70" y="120" fill="#7fe3d7" fillOpacity=".5" fontSize="22" fontStyle="italic" fontFamily="Space Grotesk, sans-serif" letterSpacing="6">MAR CARIBE</text>
        <path d={COSTA} fill="url(#mapa-tierra)" filter="url(#mapa-sombra)" />
        <path d={COSTA} fill="none" stroke="#7fe3d7" strokeOpacity=".55" strokeWidth="2.5" />
        {MONTANAS.map(([x, y, s], i) => (
          <g key={i} opacity=".9">
            <path d={`M${x - s / 2} ${y + s * .45} L${x} ${y - s * .45} L${x + s / 2} ${y + s * .45} Z`} fill="#2c6b5c" />
            <path d={`M${x - s * .14} ${y - s * .17} L${x} ${y - s * .45} L${x + s * .14} ${y - s * .17} L${x + s * .05} ${y - s * .22} L${x - s * .04} ${y - s * .15} Z`} fill="#eef7f4" opacity=".85" />
          </g>
        ))}
        <text x="610" y="250" fill="#cfe9e3" fillOpacity=".4" fontSize="18" fontFamily="Space Grotesk, sans-serif" letterSpacing="5">SIERRA NEVADA</text>
        {puntos.map(({ z, x, y, estado }) => {
          const color = COLOR_NIVEL[estado.nivel] ?? COLOR_NIVEL.desconocida;
          const nombre = en ? z.nombre_en : z.nombre_es;
          const pct = estado.ocupacion != null ? `${Math.round(estado.ocupacion * 100)} %` : "—";
          // Lado de la etiqueta: a la derecha del punto, salvo donde chocaría con la zona vecina.
          const lado = LADO_ETIQUETA[z.codigo] ?? (x > ANCHO * 0.72 ? "izquierda" : "derecha");
          const derecha = lado === "izquierda";
          const dx = lado === "abajo" ? -88 : derecha ? x - 18 - x : 18;
          const dy = lado === "abajo" ? 20 : -22;
          const activa = elegida === z.id;
          return (
            <g key={z.id} className={`mapa-pin${estado.nivel === "muy_concurrida" ? " peligro" : ""}`} tabIndex={0} role="button"
              aria-label={`${nombre}: ${TEXTO_NIVEL[estado.nivel]?.[en ? 1 : 0] ?? ""} ${pct}`}
              onClick={() => onElegir(z.id)} onKeyDown={(e) => e.key === "Enter" && onElegir(z.id)}>
              <circle className="onda" cx={x} cy={y} r="14" fill={color} opacity=".6" />
              <circle className="nucleo" cx={x} cy={y} r={activa ? 13 : 10} fill={color} stroke="#0a2130" strokeWidth="3" />
              <g transform={`translate(${x + dx} ${y + dy})`}>
                <rect x={derecha ? -176 : 0} y="0" width="176" height="46" rx="12" fill="#0a2130" fillOpacity=".78" stroke={activa ? color : "#ffffff"} strokeOpacity={activa ? 1 : .18} />
                <text x={derecha ? -164 : 12} y="20" fill="#ffffff" fontSize="15" fontWeight="600" fontFamily="Space Grotesk, sans-serif">{nombre}</text>
                <text x={derecha ? -164 : 12} y="37" fill={color} fontSize="12.5" fontFamily="Inter, sans-serif">{TEXTO_NIVEL[estado.nivel]?.[en ? 1 : 0]} · {pct}</text>
              </g>
            </g>
          );
        })}
      </svg>
      <div className="mapa-cabecera abajo">
        <span className="sobretitulo">{en ? "Live occupancy" : "Ocupación en vivo"}</span>
        <h2>{en ? "Where is it quieter today?" : "¿Dónde hay menos gente hoy?"}</h2>
        <p>{en
          ? "Each area is compared with its daily load capacity. Tap one to see its experiences."
          : "Cada zona se compara con su capacidad de carga diaria. Toca una para ver sus experiencias."}</p>
      </div>
      <div className="mapa-leyenda" style={{ right: "auto", left: "clamp(1rem, 3vw, 1.6rem)", bottom: "auto", top: "clamp(1rem, 3vw, 1.6rem)" }}>
        {(["tranquila", "moderada", "muy_concurrida"] as const).map((n) => (
          <span key={n}><i style={{ background: COLOR_NIVEL[n] }} />{TEXTO_NIVEL[n][en ? 1 : 0]}</span>
        ))}
      </div>
    </div>
  );
}
