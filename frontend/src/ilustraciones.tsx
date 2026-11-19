// Isotipo de SierraMar e íconos de trazo (SVG en línea: funcionan sin conexión en la PWA).

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

const TRAZOS = {
  lugar: <><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z" /><circle cx="12" cy="9.5" r="2.5" /></>,
  flecha: <path d="M5 12h14M13 6l6 6-6 6" />,
  escudo: <><path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6l-8-3Z" /><path d="m8.5 12 2.4 2.4 4.6-4.8" /></>,
  calendario: <><rect x="3.5" y="5" width="17" height="15.5" rx="2.5" /><path d="M3.5 10h17M8 3v4M16 3v4" /></>,
  hoja: <><path d="M5 19c0-8 5-14 15-15-1 10-7 15-15 15Z" /><path d="M5 19 13 11" /></>,
  ondas: <><path d="M3 9c2 0 2-1.5 4.5-1.5S9.5 9 12 9s2-1.5 4.5-1.5S18.5 9 21 9" /><path d="M3 15c2 0 2-1.5 4.5-1.5S9.5 15 12 15s2-1.5 4.5-1.5S18.5 15 21 15" /></>,
  reloj: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>,
  personas: <><circle cx="9" cy="8" r="3.2" /><path d="M3.5 19c.6-3.3 2.8-5 5.5-5s4.9 1.7 5.5 5" /><path d="M15.5 5.2a3 3 0 0 1 0 5.6M17.5 14.4c1.6.6 2.7 2.1 3 4.6" /></>,
  brujula: <><circle cx="12" cy="12" r="8.5" /><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z" /></>,
  ticket: <><path d="M4 7.5A1.5 1.5 0 0 1 5.5 6h13A1.5 1.5 0 0 1 20 7.5V10a2 2 0 0 0 0 4v2.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 16.5V14a2 2 0 0 0 0-4V7.5Z" /><path d="M14 6v12" strokeDasharray="2 2" /></>,
  panel: <><rect x="4" y="4" width="7" height="7" rx="1.5" /><rect x="13" y="4" width="7" height="4" rx="1.5" /><rect x="13" y="10" width="7" height="10" rx="1.5" /><rect x="4" y="13" width="7" height="7" rx="1.5" /></>,
  persona: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.8-3.8 3.6-6 7-6s6.2 2.2 7 6" /></>,
  chispa: <path d="M12 3.5 13.8 9l5.7 1.8-5.7 1.8L12 18.5l-1.8-5.9L4.5 10.8 10.2 9 12 3.5Z" />,
  sol: <><circle cx="12" cy="12" r="4" /><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" /></>,
  luna: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />,
  corazon: <path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.3a4.3 4.3 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20Z" />,
  nube: <path d="M7 18h10.5a4 4 0 0 0 .4-8 6 6 0 0 0-11.5 1.6A3.2 3.2 0 0 0 7 18Z" />,
  lluvia: <><path d="M7 14h10.5a3.5 3.5 0 0 0 .4-7 5.5 5.5 0 0 0-10.6 1.4A2.8 2.8 0 0 0 7 14Z" /><path d="M8 17.5 7 20M12 17.5 11 20M16 17.5 15 20" /></>,
  servidor: <><rect x="4" y="4" width="16" height="6.5" rx="1.8" /><rect x="4" y="13.5" width="16" height="6.5" rx="1.8" /><path d="M8 7.2h.01M8 16.7h.01" /></>,
  rayo: <path d="M13 3 5 13.5h6L10 21l8-10.5h-6L13 3Z" />,
  descargar: <><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5" /><path d="M5 19.5h14" /></>,
  voltear: <><path d="M4 12a8 8 0 0 1 13.7-5.6L20 8.7" /><path d="M20 4v4.7h-4.7" /><path d="M20 12a8 8 0 0 1-13.7 5.6L4 15.3" /><path d="M4 20v-4.7h4.7" /></>,
  cerrar: <path d="M6 6l12 12M18 6 6 18" />,
} as const;

export type NombreIcono = keyof typeof TRAZOS;

export function Icono({ n, tam = 20 }: { n: NombreIcono; tam?: number }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {TRAZOS[n]}
    </svg>
  );
}
