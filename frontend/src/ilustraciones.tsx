// Ilustraciones propias en SVG: no dependen de fotos externas (funcionan sin conexión en la PWA).

/** Paisaje de la portada: la Sierra Nevada bajando hasta el mar Caribe. */
export function Paisaje() {
  return (
    <svg className="paisaje" viewBox="0 0 1440 560" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0c2a3a" />
          <stop offset=".55" stopColor="#14566a" />
          <stop offset="1" stopColor="#e9a65a" />
        </linearGradient>
        <linearGradient id="mar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1f9a93" />
          <stop offset="1" stopColor="#0b4f57" />
        </linearGradient>
        <radialGradient id="sol" cx=".5" cy=".5" r=".5">
          <stop offset="0" stopColor="#ffd28a" />
          <stop offset="1" stopColor="#f2a541" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="1440" height="560" fill="url(#cielo)" />
      <circle cx="1080" cy="300" r="190" fill="url(#sol)" opacity=".9" />
      <circle cx="1080" cy="300" r="62" fill="#ffd28a" />
      {/* picos nevados al fondo */}
      <path d="M0 330 L170 210 L260 265 L420 120 L520 205 L600 160 L760 300 L0 300Z" fill="#2c5f6f" opacity=".7" />
      <path d="M400 135 L420 120 L445 142 L432 150 L420 140 L410 152Z" fill="#f6f1e7" opacity=".9" />
      <path d="M590 168 L600 160 L615 175 L603 180Z" fill="#f6f1e7" opacity=".8" />
      {/* sierra media */}
      <path d="M0 380 C120 300 220 250 330 300 S540 240 640 300 S860 330 980 360 L1440 380 L1440 560 L0 560Z" fill="#1d4f50" />
      {/* bosque cercano */}
      <path d="M0 430 C150 360 260 380 380 410 S620 360 760 410 S980 440 1100 420 L1440 410 L1440 560 L0 560Z" fill="#163f3a" />
      {/* mar */}
      <path d="M0 470 C240 450 480 490 720 470 S1200 450 1440 470 L1440 560 L0 560Z" fill="url(#mar)" />
      <path d="M0 500 C240 485 480 515 720 500 S1200 485 1440 500" stroke="#7fd1c7" strokeWidth="2" fill="none" opacity=".5" />
      <path d="M0 528 C240 515 480 540 720 528 S1200 515 1440 528" stroke="#7fd1c7" strokeWidth="2" fill="none" opacity=".35" />
      {/* palmas */}
      {[140, 1290].map((x) => (
        <g key={x} transform={`translate(${x} 470)`} fill="#0d2f2c">
          <path d="M0 0 C4 -40 8 -70 4 -110" stroke="#0d2f2c" strokeWidth="6" fill="none" />
          <path d="M4 -110 C-30 -120 -55 -100 -70 -80 C-40 -98 -15 -102 4 -110Z" />
          <path d="M4 -110 C40 -125 70 -105 82 -86 C50 -104 25 -106 4 -110Z" />
          <path d="M4 -110 C-10 -140 -40 -150 -55 -145 C-30 -138 -12 -126 4 -110Z" />
          <path d="M4 -110 C20 -142 52 -150 66 -142 C42 -136 22 -126 4 -110Z" />
        </g>
      ))}
    </svg>
  );
}

const ESCENAS: Record<string, { fondo: [string, string]; dibujo: JSX.Element }> = {
  naturaleza: {
    fondo: ["#1e6b5c", "#a7d8b8"],
    dibujo: (
      <>
        <path d="M0 150 L70 70 L120 115 L180 50 L260 150Z" fill="#14514a" />
        <path d="M0 160 C60 130 120 140 160 150 S240 140 260 150 L260 200 L0 200Z" fill="#0f3e38" />
        <path d="M200 60 L200 150" stroke="#e3f1ee" strokeWidth="6" opacity=".8" />
        <path d="M196 60 C190 90 206 120 196 150" stroke="#b8e5ee" strokeWidth="3" fill="none" />
      </>
    ),
  },
  aventura: {
    fondo: ["#0f4c6e", "#5cb3c9"],
    dibujo: (
      <>
        <path d="M0 160 C70 140 120 175 190 150 S240 145 260 150 L260 200 L0 200Z" fill="#0b3550" />
        <path d="M40 160 C60 120 100 110 120 140" stroke="#f2a541" strokeWidth="5" fill="none" />
        <circle cx="180" cy="60" r="18" fill="#ffd28a" />
        <path d="M150 120 L170 95 L195 125Z" fill="#e3f1ee" opacity=".7" />
      </>
    ),
  },
  playa: {
    fondo: ["#f2b866", "#7fd1c7"],
    dibujo: (
      <>
        <circle cx="200" cy="58" r="22" fill="#fff1c9" />
        <path d="M0 130 C80 120 160 140 260 125 L260 200 L0 200Z" fill="#2aa198" />
        <path d="M0 165 C80 150 160 175 260 160 L260 200 L0 200Z" fill="#f6e3bd" />
        <path d="M50 165 C54 140 56 120 52 96" stroke="#5a3d23" strokeWidth="4" fill="none" />
        <path d="M52 96 C30 90 18 100 10 112 C28 102 40 100 52 96Z M52 96 C76 88 92 98 98 110 C80 100 66 98 52 96Z" fill="#1e6b5c" />
      </>
    ),
  },
  cultura: {
    fondo: ["#c46a3a", "#f2c27a"],
    dibujo: (
      <>
        <path d="M60 170 L60 90 L130 55 L200 90 L200 170Z" fill="#f6f1e7" />
        <path d="M105 170 L105 125 C105 112 155 112 155 125 L155 170Z" fill="#7a3b22" />
        <rect x="122" y="60" width="16" height="30" fill="#f6f1e7" />
        <path d="M118 62 L130 44 L142 62Z" fill="#d9643a" />
        <rect x="0" y="170" width="260" height="30" fill="#8a4a2b" />
      </>
    ),
  },
  historia: {
    fondo: ["#6b4a2e", "#d9a86a"],
    dibujo: (
      <>
        <path d="M30 170 L30 100 L230 100 L230 170Z" fill="#f2deb4" />
        {[50, 90, 130, 170, 210].map((x) => <rect key={x} x={x - 6} y="100" width="12" height="70" fill="#d9bf8f" />)}
        <path d="M20 100 L130 60 L240 100Z" fill="#b98a55" />
        <rect x="0" y="170" width="260" height="30" fill="#4a321f" />
      </>
    ),
  },
  gastronomia: {
    fondo: ["#7a3e22", "#e8a35d"],
    dibujo: (
      <>
        <ellipse cx="130" cy="140" rx="90" ry="30" fill="#f6f1e7" />
        <ellipse cx="130" cy="132" rx="70" ry="20" fill="#e8c27a" />
        <path d="M95 128 C110 112 150 112 168 128 C150 138 110 138 95 128Z" fill="#c4562c" />
        <circle cx="80" cy="125" r="9" fill="#5a9a3a" />
        <path d="M200 60 C205 75 195 85 200 100" stroke="#fff" strokeWidth="3" fill="none" opacity=".6" />
      </>
    ),
  },
};

/** Portada ilustrada de una oferta según su primera categoría. */
export function Portada({ categoria, alto = 170 }: { categoria?: string; alto?: number }) {
  const escena = ESCENAS[categoria ?? ""] ?? ESCENAS.naturaleza;
  const id = `g-${categoria ?? "def"}`;
  return (
    <svg className="portada" viewBox="0 0 260 200" preserveAspectRatio="xMidYMid slice" style={{ height: alto }} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={escena.fondo[0]} />
          <stop offset="1" stopColor={escena.fondo[1]} />
        </linearGradient>
      </defs>
      <rect width="260" height="200" fill={`url(#${id})`} />
      {escena.dibujo}
    </svg>
  );
}

export function Isotipo({ tam = 36 }: { tam?: number }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="46" fill="#0c2a3a" />
      <circle cx="64" cy="35" r="11" fill="#f2a541" />
      <path d="M16 66 L39 32 L52 50 L60 41 L84 66Z" fill="#e3f1ee" />
      <path d="M12 70 q10 -7 19 0 t19 0 t19 0 t19 0 v8 q-38 14 -76 0z" fill="#3fb5ad" />
    </svg>
  );
}
