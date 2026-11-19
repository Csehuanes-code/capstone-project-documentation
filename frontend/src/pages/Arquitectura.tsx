// "Arquitectura en vivo": los 5 microservicios, sus bases y el bus de eventos. Cada reserva real que
// registra Analítica se dibuja como mensajes que viajan por RabbitMQ (datos de /api/v1/analitica/actividad).
import { useEffect, useRef, useState } from "react";
import { api, type Comprobante, type Franja, type Oferta, type Zona } from "../api";
import { useActividad, hace, type ReservaReciente } from "../extras";
import { Icono, type NombreIcono } from "../ilustraciones";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { avisar, useCarga } from "../ui";

type Servicio = "auth" | "catalogo" | "reservas" | "ia" | "analitica";
type Nodo = Servicio | "pwa" | "gateway" | `${Servicio}-db` | "bus";

const X: Record<Servicio, number> = { auth: 110, catalogo: 305, reservas: 500, ia: 695, analitica: 890 };
const Y_SERV = 280;
const Y_DB = 392;
const Y_BUS = 522;

const SERVICIOS: Record<Servicio, {
  nombre: string; icono: NombreIcono; tec: string; db: string;
  hace: [string, string]; publica: string[]; consume: string[]; atributos: [string, string];
}> = {
  auth: {
    nombre: "Auth", icono: "escudo", tec: "FastAPI · Argon2id · JWT ES256", db: "auth_db",
    hace: ["Registro, inicio de sesión y verificación de prestadores (RNT). Firma tokens de 15 min que los demás validan solos con su clave pública.",
      "Sign-up, sign-in and operator verification (RNT). Signs 15-min tokens that the others verify on their own with its public key."],
    publica: ["auth.usuario.confirmado", "auth.prestador.verificacion_resuelta", "auth.notificacion.solicitada"], consume: [],
    atributos: ["Seguridad · disponibilidad (los demás no dependen de Auth en cada petición)", "Security · availability (others don't call Auth on every request)"],
  },
  catalogo: {
    nombre: "Catálogo", icono: "brujula", tec: "FastAPI · PostgreSQL", db: "catalogo_db",
    hace: ["Ofertas, tarifas, zonas y políticas de cancelación. Solo publican prestadores aprobados.",
      "Offers, prices, areas and cancellation policies. Only approved operators can publish."],
    publica: ["catalogo.oferta.publicada", "catalogo.oferta.actualizada", "catalogo.oferta.retirada"], consume: ["auth.prestador.verificacion_resuelta"],
    atributos: ["Modificabilidad · consistencia eventual hacia Reservas e IA", "Modifiability · eventual consistency to Booking and AI"],
  },
  reservas: {
    nombre: "Reservas", icono: "calendario", tec: "FastAPI · bloqueo de franja · outbox", db: "reservas_db",
    hace: ["Disponibilidad, pago simulado, comprobante, cancelaciones, lista de espera y disputas. Sin sobreventa ni cobros dobles (Idempotency-Key).",
      "Availability, simulated payment, receipt, cancellations, waiting list and disputes. No overbooking or double charges (Idempotency-Key)."],
    publica: ["reservas.reserva.confirmada", "reservas.cancelacion.pendiente", "reservas.disputa.abierta"], consume: ["catalogo.oferta.*", "auth.notificacion.solicitada"],
    atributos: ["Integridad · rendimiento (p95) · confiabilidad del pago", "Integrity · performance (p95) · payment reliability"],
  },
  ia: {
    nombre: "IA", icono: "chispa", tec: "FastAPI · recomendador explicable", db: "ia_db",
    hace: ["Recomendaciones con puntaje y desglose por criterio. Si una zona supera el 80 %, propone una alternativa más tranquila.",
      "Recommendations with a score and per-criterion breakdown. If an area goes over 80 %, it suggests a quieter alternative."],
    publica: [], consume: ["catalogo.oferta.*", "reservas.reserva.confirmada", "analitica.zona.ocupacion_actualizada"],
    atributos: ["Explicabilidad · degradación elegante (sigue respondiendo si Analítica cae)", "Explainability · graceful degradation (keeps answering if Analytics is down)"],
  },
  analitica: {
    nombre: "Analítica", icono: "panel", tec: "FastAPI · consumidor idempotente · outbox", db: "analitica_db",
    hace: ["Indicadores por zona, capacidad de carga, alertas al 90 % y exportación CSV. Publica la ocupación para la IA.",
      "Per-area indicators, load capacity, alerts at 90 % and CSV export. Publishes occupancy for the AI."],
    publica: ["analitica.zona.ocupacion_actualizada"], consume: ["reservas.reserva.confirmada"],
    atributos: ["Sostenibilidad del destino · idempotencia por evento_id", "Destination sustainability · idempotency by evento_id"],
  },
};

// Rutas por las que viajan los mensajes (también se dibujan como líneas).
const RUTAS: Record<string, string> = { "pwa-gateway": "M500 78 L500 132" };
for (const s of Object.keys(X) as Servicio[]) {
  const x = X[s];
  RUTAS[`gateway-${s}`] = `M500 184 C500 228 ${x} 222 ${x} ${Y_SERV - 32}`;
  RUTAS[`${s}-db`] = `M${x} ${Y_SERV + 32} L${x} ${Y_DB - 26}`;
  RUTAS[`${s}-bus`] = `M${x + 58} ${Y_SERV + 20} L${x + 58} ${Y_BUS - 14}`;
  RUTAS[`bus-${s}`] = `M${x + 58} ${Y_BUS - 14} L${x + 58} ${Y_SERV + 20}`;
}
const porBus = (de: Servicio, a: Servicio) => `M${X[de] + 58} ${Y_BUS} L${X[a] + 58} ${Y_BUS}`;

interface Pulso { id: number; d: string; color: string; inicio: number; dur: number; etiqueta?: string }
interface Destello { nodo: Nodo; hasta: number }
interface Registro { id: number; hora: string; texto: string; clave?: string; tipo: "http" | "evento" | "db" | "ia" }

const COLOR = { http: "#f5a245", reserva: "#ff7a59", ocupacion: "#5fd3c6", db: "#7fb7ff" };

export default function Arquitectura() {
  const { idioma } = useIdioma();
  const en = idioma === "en";
  const { usuario } = useSesion();
  const { datos, error } = useActividad(2000, 12);
  const zonas = useCarga(() => api<Zona[]>("/api/v1/catalogo/zonas"));
  const [pulsos, setPulsos] = useState<Pulso[]>([]);
  const [destellos, setDestellos] = useState<Destello[]>([]);
  const [registro, setRegistro] = useState<Registro[]>([]);
  const [ahora, setAhora] = useState(() => performance.now());
  const [elegido, setElegido] = useState<Servicio>("reservas");
  const [vistos, setVistos] = useState(0);
  const [latencia, setLatencia] = useState<number | null>(null);
  const [enviando, setEnviando] = useState(false);
  const conocidos = useRef<Set<string> | null>(null);
  const esperando = useRef<{ zona: string; hasta: number } | null>(null);
  const medidor = useRef<SVGPathElement>(null);
  const contador = useRef(0);

  // Bucle de animación: solo corre mientras hay pulsos o destellos vivos.
  useEffect(() => {
    let cuadro = 0;
    const vivo = () => {
      const t = performance.now();
      setAhora(t);
      if (pulsos.some((p) => p.inicio + p.dur > t) || destellos.some((d) => d.hasta > t)) cuadro = requestAnimationFrame(vivo);
    };
    cuadro = requestAnimationFrame(vivo);
    return () => cancelAnimationFrame(cuadro);
  }, [pulsos, destellos]);

  const anotar = (texto: string, tipo: Registro["tipo"], clave?: string, hora = new Date()) =>
    setRegistro((r) => [{ id: ++contador.current, hora: [hora.getHours(), hora.getMinutes(), hora.getSeconds()].map((n) => String(n).padStart(2, "0")).join(":"), texto, clave, tipo }, ...r].slice(0, 16));

  function programar(pasos: { en: number; d: string; color: string; dur?: number; etiqueta?: string; nodos?: Nodo[]; nota?: [string, Registro["tipo"], string?] }[]) {
    const base = performance.now();
    const menos = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    setPulsos((ps) => [...ps.filter((p) => p.inicio + p.dur > base),
      ...pasos.map((p) => ({ id: ++contador.current, d: p.d, color: p.color, inicio: base + (menos ? 0 : p.en), dur: menos ? 1 : p.dur ?? 650, etiqueta: p.etiqueta }))]);
    setDestellos((ds) => [...ds.filter((d) => d.hasta > base),
      ...pasos.flatMap((p) => (p.nodos ?? []).map((nodo) => ({ nodo, hasta: base + p.en + (p.dur ?? 650) + 900 })))]);
    pasos.forEach((p) => { if (p.nota) { const [t, tipo, clave] = p.nota; setTimeout(() => anotar(t, tipo, clave), menos ? 0 : p.en); } });
  }

  const tramoReserva = (zona: string, personas: number) => [
    { en: 0, d: RUTAS["pwa-gateway"], color: COLOR.http, nodos: ["pwa", "gateway"] as Nodo[],
      nota: [en ? "POST /api/v1/reservas over HTTPS (TLS 1.3) through Traefik" : "POST /api/v1/reservas por HTTPS (TLS 1.3) a través de Traefik", "http"] as [string, Registro["tipo"]] },
    { en: 550, d: RUTAS["gateway-reservas"], color: COLOR.http, nodos: ["reservas"] as Nodo[],
      nota: [en ? "Booking validates the JWT locally (Auth public key) and locks the slot" : "Reservas valida el JWT localmente (clave pública de Auth) y bloquea la franja", "http"] as [string, Registro["tipo"]] },
    { en: 1150, d: RUTAS["reservas-db"], color: COLOR.db, nodos: ["reservas-db"] as Nodo[],
      nota: [en ? `Payment approved: booking + outbox event saved in ONE transaction (${zona}, ${personas})` : `Pago aprobado: reserva + evento en el outbox, en UNA transacción (${zona}, ${personas} pers.)`, "db"] as [string, Registro["tipo"]] },
    { en: 1750, d: RUTAS["reservas-bus"], color: COLOR.reserva, etiqueta: "reservas.reserva.confirmada", nodos: ["bus"] as Nodo[],
      nota: [en ? "The relay publishes to the «turismo» exchange" : "El relevo publica en el exchange «turismo»", "evento", "reservas.reserva.confirmada"] as [string, Registro["tipo"], string] },
  ];
  const tramoConsumo = (r: ReservaReciente, desfase: number) => [
    { en: desfase, d: porBus("reservas", "ia"), color: COLOR.reserva, dur: 500 },
    { en: desfase, d: porBus("reservas", "analitica"), color: COLOR.reserva, dur: 900 },
    { en: desfase + 500, d: RUTAS["bus-ia"], color: COLOR.reserva, nodos: ["ia"] as Nodo[],
      nota: [en ? "AI consumes it: popularity +1 for the offer" : "IA lo consume: popularidad +1 para la oferta", "ia"] as [string, Registro["tipo"]] },
    { en: desfase + 900, d: RUTAS["bus-analitica"], color: COLOR.reserva, nodos: ["analitica"] as Nodo[],
      nota: [en ? `Analytics consumes it (idempotent by evento_id) · ${r.zona} +${r.personas} visitors` : `Analítica lo consume (idempotente por evento_id) · ${r.zona} +${r.personas} visitantes`, "evento"] as [string, Registro["tipo"]] },
    { en: desfase + 1500, d: RUTAS["analitica-db"], color: COLOR.db, nodos: ["analitica-db"] as Nodo[],
      nota: [en ? `Recomputes ${r.zona} occupancy against its load capacity` : `Recalcula la ocupación de ${r.zona} frente a su capacidad de carga`, "db"] as [string, Registro["tipo"]] },
    ...tramoOcupacion(r.zona, desfase + 2100),
  ];
  const tramoOcupacion = (zona: string, desfase: number, ocupacion?: number) => [
    { en: desfase, d: RUTAS["analitica-bus"], color: COLOR.ocupacion, etiqueta: "analitica.zona.ocupacion_actualizada", nodos: ["bus"] as Nodo[],
      nota: [en ? `Publishes ${zona} occupancy${ocupacion != null ? ` (${Math.round(ocupacion * 100)} %)` : ""}` : `Publica la ocupación de ${zona}${ocupacion != null ? ` (${Math.round(ocupacion * 100)} %)` : ""}`, "evento", "analitica.zona.ocupacion_actualizada"] as [string, Registro["tipo"], string] },
    { en: desfase + 600, d: porBus("analitica", "ia"), color: COLOR.ocupacion, dur: 600 },
    { en: desfase + 1200, d: RUTAS["bus-ia"], color: COLOR.ocupacion, nodos: ["ia", "ia-db"] as Nodo[],
      nota: [en ? "AI updates the area level: over 80 % it suggests quieter places" : "IA actualiza el nivel de la zona: sobre 80 % sugiere lugares más tranquilos", "ia"] as [string, Registro["tipo"]] },
  ];

  // Detecta reservas y publicaciones nuevas en cada consulta.
  useEffect(() => {
    if (!datos) return;
    if (conocidos.current === null) {
      conocidos.current = new Set([...datos.reservas.map((r) => r.evento_id), ...datos.ocupaciones.map((o) => o.evento_id)]);
      [...datos.reservas].reverse().slice(-5).forEach((r) =>
        anotar(en ? `History: booking in ${r.zona} (${r.personas}) · ${hace(r.procesado_en, en)}` : `Historial: reserva en ${r.zona} (${r.personas} pers.) · ${hace(r.procesado_en, en)}`, "evento", undefined, new Date(r.procesado_en)));
      return;
    }
    const nuevas = datos.reservas.filter((r) => !conocidos.current!.has(r.evento_id)).reverse();
    const nuevasOcup = datos.ocupaciones.filter((o) => !conocidos.current!.has(o.evento_id));
    nuevas.forEach((r) => conocidos.current!.add(r.evento_id));
    nuevasOcup.forEach((o) => conocidos.current!.add(o.evento_id));
    nuevas.forEach((r, i) => {
      const propia = esperando.current && esperando.current.zona === r.zona_id && esperando.current.hasta > Date.now();
      if (propia) esperando.current = null;
      programar(propia ? tramoConsumo(r, 0) : [...tramoReserva(r.zona, r.personas), ...tramoConsumo(r, 2350)].map((p) => ({ ...p, en: p.en + i * 600 })));
      const ocup = datos.ocupaciones.find((o) => o.zona_id === r.zona_id && o.publicado_en && o.ocurrido_en >= r.procesado_en);
      if (ocup?.publicado_en) setLatencia(new Date(ocup.publicado_en).getTime() - new Date(r.procesado_en).getTime());
    });
    // Publicaciones periódicas (recálculo de todas las zonas) sin una reserva detrás.
    const sueltas = nuevasOcup.filter((o) => !nuevas.some((r) => r.zona_id === o.zona_id));
    if (sueltas.length && !nuevas.length) {
      programar(tramoOcupacion(sueltas.length > 1 ? (en ? `${sueltas.length} areas` : `${sueltas.length} zonas`) : sueltas[0].zona_id, 0));
    }
    setVistos((v) => v + nuevas.length + nuevasOcup.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datos]);

  async function reservaDePrueba() {
    setEnviando(true);
    try {
      const { items } = await api<{ items: Oferta[] }>("/api/v1/catalogo/ofertas", { query: { limit: 50 } });
      for (const o of [...items].sort(() => Math.random() - 0.5)) {
        const franjas = await api<Franja[]>(`/api/v1/ofertas/${o.id}/disponibilidad`, { query: { personas: 1 } });
        const f = franjas.find((x) => x.cupo_disponible >= 1);
        if (!f) continue;
        const codigo = zonas.datos?.find((z) => z.id === o.zona_id)?.codigo ?? "";
        try {
          const r = await api<Comprobante>("/api/v1/reservas", {
            method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() },
            body: { franja_id: f.id, personas: 1, correo_turista: usuario?.email, idioma, datos_pago: { numero_tarjeta: "4111111111111111" }, acompanantes: [] },
          });
          if (!r.pago_aprobado) continue;
          esperando.current = { zona: codigo, hasta: Date.now() + 20000 };
          programar(tramoReserva(en ? o.nombre_en : o.nombre_es, 1));
          avisar(en ? `Test booking ${r.codigo} confirmed` : `Reserva de prueba ${r.codigo} confirmada`);
          return;
        } catch { /* sin tarifa o sin cupo: probar con otra */ }
      }
      avisar(en ? "No offer had available spots" : "Ninguna oferta tenía cupo disponible", "error");
    } catch (e) {
      avisar((e as Error).message, "error");
    } finally {
      setEnviando(false);
    }
  }

  const activo = (n: Nodo) => destellos.some((d) => d.nodo === n && d.hasta > ahora);
  const punto = (p: Pulso) => {
    const t = (ahora - p.inicio) / p.dur;
    const camino = medidor.current;
    if (t < 0 || t > 1 || !camino) return null;
    camino.setAttribute("d", p.d);
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    return camino.getPointAtLength(e * camino.getTotalLength());
  };
  const info = SERVICIOS[elegido];
  const pendientes = datos?.outbox_pendientes ?? null;
  const reservasRecientes = datos?.reservas.length ?? 0;

  return (
    <div className="apilado arquitectura">
      <header className="encabezado-panel aparece arquitectura-cabecera">
        <span className="sobretitulo"><span className="en-vivo" aria-hidden="true" />{en ? "Live architecture" : "Arquitectura en vivo"}</span>
        <h1>{en ? "Watch a booking travel through the system" : "Mira una reserva viajar por el sistema"}</h1>
        <p>{en
          ? "Five microservices, one database each, talking through RabbitMQ events. Every real booking processed by Analytics is drawn here as it happens."
          : "Cinco microservicios, una base de datos cada uno, que se hablan por eventos en RabbitMQ. Cada reserva real que procesa Analítica se dibuja aquí en el momento."}</p>
        <div className="fila" style={{ flexWrap: "wrap", gap: ".7rem" }}>
          {usuario?.rol === "turista" ? (
            <button className="boton-grande boton-sol" disabled={enviando} onClick={reservaDePrueba}>
              <Icono n="rayo" tam={18} /> {enviando ? (en ? "Booking…" : "Reservando…") : (en ? "Make a test booking" : "Lanzar una reserva de prueba")}
            </button>
          ) : (
            <span className="chip-vidrio">{en ? "Sign in as a tourist to launch a test booking, or book from another device and watch it arrive." : "Inicia sesión como turista para lanzar una reserva de prueba, o reserva desde otro dispositivo y mira cómo llega."}</span>
          )}
        </div>
      </header>

      <div className="kpis">
        <div className="kpi"><span>{en ? "Events seen (this session)" : "Eventos vistos (esta sesión)"}</span><b>{vistos}</b></div>
        <div className="kpi"><span>{en ? "Recent bookings" : "Reservas recientes"}</span><b>{reservasRecientes}</b></div>
        <div className="kpi"><span>{en ? "Analytics → AI propagation" : "Propagación Analítica → IA"}</span><b>{latencia == null ? "—" : latencia < 1000 ? `${latencia} ms` : `${(latencia / 1000).toFixed(1)} s`}</b></div>
        <div className="kpi"><span>{en ? "Outbox pending (Analytics)" : "Outbox pendiente (Analítica)"}</span><b>{pendientes ?? "—"}</b></div>
      </div>

      <div className="arquitectura-cuerpo">
        <div className="diagrama tarjeta" data-brillo="">
          {error && <span className="diagrama-estado">{en ? "Reconnecting…" : "Reconectando…"}</span>}
          <svg viewBox="0 0 1000 580" role="img" aria-label={en ? "Architecture diagram with live events" : "Diagrama de arquitectura con eventos en vivo"}>
            <defs>
              <filter id="brillo-nodo" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" /></filter>
              <linearGradient id="bus-grad" x1="0" x2="1"><stop offset="0" stopColor="#ff7a59" /><stop offset=".5" stopColor="#f5a245" /><stop offset="1" stopColor="#5fd3c6" /></linearGradient>
            </defs>
            <path ref={medidor} d="M0 0" fill="none" stroke="none" />
            {Object.entries(RUTAS).filter(([k]) => !k.startsWith("bus-")).map(([k, d]) => (
              <path key={k} d={d} className={`conexion${k.endsWith("-bus") ? " a-bus" : ""}`} />
            ))}

            {/* Bus de eventos */}
            <g className={`nodo-bus${activo("bus") ? " activo" : ""}`}>
              <rect x="40" y={Y_BUS - 14} width="920" height="28" rx="14" />
              <rect x="40" y={Y_BUS - 14} width="920" height="28" rx="14" className="bus-brillo" />
              <text x="500" y={Y_BUS + 44} textAnchor="middle">RabbitMQ · exchange «turismo» (topic) · {en ? "durable queues + DLQ" : "colas durables + DLQ"}</text>
            </g>

            {/* Cliente y gateway */}
            <Caja x={500} y={52} ancho={210} titulo="PWA · React" sub={en ? "browser / phone" : "navegador / celular"} icono="persona" activo={activo("pwa")} />
            <Caja x={500} y={158} ancho={230} titulo="Traefik" sub={en ? "gateway · TLS 1.3" : "gateway · TLS 1.3"} icono="escudo" activo={activo("gateway")} />

            {(Object.keys(X) as Servicio[]).map((s) => (
              <g key={s}>
                <Caja x={X[s]} y={Y_SERV} ancho={150} titulo={SERVICIOS[s].nombre} sub="FastAPI" icono={SERVICIOS[s].icono}
                  activo={activo(s)} elegido={elegido === s} onClick={() => setElegido(s)} />
                <Base x={X[s]} y={Y_DB} nombre={SERVICIOS[s].db} activo={activo(`${s}-db`)} />
              </g>
            ))}

            {pulsos.map((p) => {
              const q = punto(p);
              if (!q) return null;
              return (
                <g key={p.id} className="pulso">
                  <circle cx={q.x} cy={q.y} r="13" fill={p.color} opacity=".25" filter="url(#brillo-nodo)" />
                  <circle cx={q.x} cy={q.y} r="6.5" fill={p.color} stroke="#fff" strokeWidth="2" />
                  {p.etiqueta && <text x={q.x > 700 ? q.x - 12 : q.x + 12} y={q.y - 10} textAnchor={q.x > 700 ? "end" : "start"} className="pulso-etiqueta">{p.etiqueta}</text>}
                </g>
              );
            })}
          </svg>
          <div className="diagrama-leyenda">
            <span><i style={{ background: COLOR.http }} />HTTP</span>
            <span><i style={{ background: COLOR.db }} />{en ? "Database" : "Base de datos"}</span>
            <span><i style={{ background: COLOR.reserva }} />reservas.reserva.confirmada</span>
            <span><i style={{ background: COLOR.ocupacion }} />analitica.zona.ocupacion_actualizada</span>
          </div>
        </div>

        <aside className="pila arquitectura-lateral">
          <article className="tarjeta servicio-ficha" key={elegido}>
            <div className="fila" style={{ gap: ".7rem" }}>
              <span className="paso-icono" style={{ width: 48, height: 48, borderRadius: 16 }}><Icono n={info.icono} tam={22} /></span>
              <div><small className="tenue">{en ? "Microservice" : "Microservicio"}</small><h2 style={{ margin: 0, fontSize: "1.4rem" }}>{info.nombre}</h2></div>
            </div>
            <p style={{ margin: 0 }}>{info.hace[en ? 1 : 0]}</p>
            <div className="ficha-dato"><span>{en ? "Stack" : "Tecnología"}</span><b>{info.tec}</b></div>
            <div className="ficha-dato"><span>{en ? "Own database" : "Base propia"}</span><b>PostgreSQL · {info.db}</b></div>
            <div className="ficha-dato"><span>{en ? "Quality attributes" : "Atributos de calidad"}</span><b>{info.atributos[en ? 1 : 0]}</b></div>
            <div className="ficha-eventos">
              <span>{en ? "Publishes" : "Publica"}</span>
              {info.publica.length ? info.publica.map((e) => <code key={e} className="evento-pub">{e}</code>) : <small className="tenue">—</small>}
              <span>{en ? "Consumes" : "Consume"}</span>
              {info.consume.length ? info.consume.map((e) => <code key={e} className="evento-con">{e}</code>) : <small className="tenue">—</small>}
            </div>
            <small className="tenue">{en ? "Tap another service in the diagram." : "Toca otro servicio en el diagrama."}</small>
          </article>

          <article className="tarjeta bitacora">
            <strong><span className="en-vivo" aria-hidden="true" />{en ? "Event log" : "Bitácora de eventos"}</strong>
            {registro.length === 0 ? <small className="tenue">{en ? "Waiting for activity…" : "Esperando actividad…"}</small> : (
              <ol>
                {registro.map((r) => (
                  <li key={r.id} className={`bitacora-${r.tipo}`}>
                    <time>{r.hora}</time>
                    <span>{r.texto}{r.clave && <code>{r.clave}</code>}</span>
                  </li>
                ))}
              </ol>
            )}
          </article>
        </aside>
      </div>
    </div>
  );
}

function Caja({ x, y, ancho, titulo, sub, icono, activo, elegido, onClick }: {
  x: number; y: number; ancho: number; titulo: string; sub: string; icono: NombreIcono; activo: boolean; elegido?: boolean; onClick?: () => void;
}) {
  return (
    <g className={`nodo${activo ? " activo" : ""}${elegido ? " elegido" : ""}${onClick ? " clicable" : ""}`} transform={`translate(${x - ancho / 2} ${y - 30})`}
      onClick={onClick} onKeyDown={(e) => e.key === "Enter" && onClick?.()} tabIndex={onClick ? 0 : undefined} role={onClick ? "button" : undefined}>
      <rect className="nodo-halo" x="-6" y="-6" width={ancho + 12} height="72" rx="20" />
      <rect className="nodo-caja" width={ancho} height="60" rx="16" />
      <g transform="translate(14 18)" className="nodo-icono"><Icono n={icono} tam={24} /></g>
      <text x="48" y="27" className="nodo-titulo">{titulo}</text>
      <text x="48" y="45" className="nodo-sub">{sub}</text>
    </g>
  );
}

function Base({ x, y, nombre, activo }: { x: number; y: number; nombre: string; activo: boolean }) {
  return (
    <g className={`base${activo ? " activo" : ""}`} transform={`translate(${x - 44} ${y - 26})`}>
      <path d="M0 8 C0 -2 88 -2 88 8 L88 40 C88 50 0 50 0 40 Z" className="base-cuerpo" />
      <ellipse cx="44" cy="8" rx="44" ry="8" className="base-tapa" />
      <text x="44" y="66" textAnchor="middle" className="base-nombre">{nombre}</text>
    </g>
  );
}
