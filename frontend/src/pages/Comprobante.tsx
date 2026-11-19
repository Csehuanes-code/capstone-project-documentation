import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { createPortal } from "react-dom";
import qrcode from "qrcode-generator";
import { api, pesos, type Comprobante } from "../api";
import { fotosDeOferta } from "../fotos";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, Estado, Insignia, tonoEstado, useCarga } from "../ui";

/** QR del comprobante como SVG (un rectángulo por módulo oscuro). */
function CodigoQR({ texto }: { texto: string }) {
  const svg = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(texto);
    qr.make();
    const n = qr.getModuleCount();
    const partes: string[] = [];
    for (let f = 0; f < n; f++) for (let c = 0; c < n; c++) if (qr.isDark(f, c)) partes.push(`M${c} ${f}h1v1h-1z`);
    return { n, d: partes.join("") };
  }, [texto]);
  return (
    <div className="qr">
      <svg viewBox={`0 0 ${svg.n} ${svg.n}`} shapeRendering="crispEdges" role="img" aria-label={`Código QR: ${texto}`}>
        <path d={svg.d} fill="#0a2130" />
      </svg>
    </div>
  );
}

const COLORES_CONFETI = ["#0b8f8a", "#5fd3c6", "#f5a245", "#ff7a59", "#ffd89c"];

/** Celebración breve al llegar desde el pago aprobado. */
function Celebracion({ codigo, alCerrar }: { codigo: string; alCerrar: () => void }) {
  useEffect(() => { const t = setTimeout(alCerrar, 2600); return () => clearTimeout(t); }, [alCerrar]);
  // Se monta en <body>: dentro de la página animada, el fondo fijo quedaría recortado a su caja.
  return createPortal(
    <div className="celebracion" onClick={alCerrar} role="status">
      <div className="celebracion-caja">
        <div className="confeti" aria-hidden="true">
          {Array.from({ length: 26 }, (_, i) => (
            <i key={i} style={{ left: `${(i * 37) % 100}%`, background: COLORES_CONFETI[i % COLORES_CONFETI.length], animationDelay: `${(i % 7) * 90}ms` }} />
          ))}
        </div>
        <svg className="check" viewBox="0 0 100 100" aria-hidden="true">
          <circle cx="50" cy="50" r="45" />
          <path d="M30 52 L44 66 L71 37" />
        </svg>
        <h2>¡Reserva confirmada!</h2>
        <p className="tenue" style={{ margin: 0 }}>Tu código es <b className="codigo" style={{ fontSize: "1.1rem" }}>{codigo}</b>. También te lo enviamos por correo.</p>
      </div>
    </div>,
    document.body,
  );
}

export default function ComprobantePagina() {
  const { id = "" } = useParams();
  const ubicacion = useLocation();
  const [celebrar, setCelebrar] = useState(Boolean((ubicacion.state as { nueva?: boolean } | null)?.nueva));
  const { t, idioma } = useIdioma();
  const { usuario } = useSesion();
  const [mensaje, setMensaje] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [motivo, setMotivo] = useState("");
  const [puntaje, setPuntaje] = useState(5);
  const [comentario, setComentario] = useState("");

  const reserva = useCarga(() => api<Comprobante>(`/api/v1/reservas/${id}`), [id]);
  const esTurista = usuario?.rol === "turista";
  const estadoParaCalificar = useCarga(
    () => (esTurista ? api<{ estado: string }>(`/api/v1/reservas/${id}/estado`) : Promise.resolve({ estado: "" })),
    [id, esTurista],
  );

  async function accion(fn: () => Promise<unknown>, ok: string) {
    setMensaje(null);
    try {
      await fn();
      setMensaje({ tipo: "ok", texto: ok });
      reserva.recargar();
    } catch (e) {
      setMensaje({ tipo: "error", texto: (e as Error).message });
    }
  }

  return (
    <Estado carga={reserva}>
      {(r) => (
        <div className="columnas">
          {celebrar && <Celebracion codigo={r.codigo} alCerrar={() => setCelebrar(false)} />}
          <section className="tarjeta ticket aparece">
            <div className="ticket-foto">
              <img src={fotosDeOferta({ nombre_es: r.nombre_oferta })[0]} alt="" />
              <div>
                <span className="sobretitulo" style={{ color: "var(--sol-claro)" }}>{t("comprobante")}</span>
                <h1>{r.nombre_oferta}</h1>
              </div>
            </div>
            <div className="pase">
            <div>
            <div className="ticket-cuerpo">
              <div className="fila entre">
                <Insignia tono={tonoEstado(r.estado)}>{r.estado}</Insignia>
                <span className="tenue" style={{ fontSize: ".85rem" }}>{r.fecha_servicio} · {r.hora_servicio.slice(0, 5)}</span>
              </div>
              <p style={{ margin: 0 }}>{idioma === "en" ? r.mensaje_en : r.mensaje_es}</p>
            </div>
            <div className="ticket-corte" />
            <div className="ticket-cuerpo">
            <table>
              <tbody>
                <tr><th>Experiencia</th><td><Link to={`/ofertas/${r.oferta_id}`}>{r.nombre_oferta}</Link></td></tr>
                <tr><th>{t("fecha")}</th><td>{r.fecha_servicio} · {r.hora_servicio}</td></tr>
                <tr><th>{t("personas")}</th><td>{r.personas}{r.acompanantes.length > 0 && ` (${r.acompanantes.join(", ")})`}</td></tr>
                {r.punto_encuentro && <tr><th>Punto de encuentro</th><td>{r.punto_encuentro}</td></tr>}
                <tr><th>{t("total")}</th><td><strong>{pesos(r.total, r.moneda)}</strong> ({pesos(r.precio_unitario)} × {r.personas})</td></tr>
                {r.referencia_pago && <tr><th>Pago</th><td>{r.referencia_pago}</td></tr>}
                {r.monto_reembolso && Number(r.monto_reembolso) > 0 && <tr><th>Reembolso</th><td>{pesos(r.monto_reembolso)}</td></tr>}
                <tr><th>{t("politica")}</th><td>{idioma === "en" ? r.politica_cancelacion.descripcion_en : r.politica_cancelacion.descripcion_es}</td></tr>
              </tbody>
            </table>
            </div>
            </div>
            <aside className="pase-talon">
              <span className="etiqueta" style={{ fontSize: ".7rem", letterSpacing: ".16em", textTransform: "uppercase", color: "var(--tenue)", fontWeight: 700 }}>{idioma === "en" ? "Show at check-in" : "Presenta al llegar"}</span>
              <CodigoQR texto={`${window.location.origin}/reservas/${r.reserva_id} · ${r.codigo}`} />
              <div className="codigo">{r.codigo}</div>
              <small className="tenue">{r.personas} {r.personas === 1 ? "persona" : "personas"} · {pesos(r.total, r.moneda)}</small>
            </aside>
            </div>
          </section>

          {esTurista && (
            <aside className="pila">
              {mensaje && <Aviso tipo={mensaje.tipo}>{mensaje.texto}</Aviso>}
              {["confirmada", "pendiente_pago"].includes(r.estado) && (
                <div className="tarjeta pila">
                  <strong>{t("cancelar")}</strong>
                  <p className="tenue" style={{ margin: 0 }}>Se aplica la política copiada al reservar; el cupo se libera para la lista de espera.</p>
                  <button className="boton-peligro" onClick={() => window.confirm("¿Cancelar la reserva?") &&
                    accion(() => api(`/api/v1/reservas/${id}/cancelar`, { method: "POST" }), "Reserva cancelada.")}>
                    {t("cancelar")}
                  </button>
                </div>
              )}
              {estadoParaCalificar.datos?.estado === "completada" && (
                <form className="tarjeta formulario" onSubmit={(e: FormEvent) => { e.preventDefault();
                  accion(() => api(`/api/v1/catalogo/ofertas/${r.oferta_id}/calificaciones`, {
                    method: "POST", body: { reserva_id: r.reserva_id, puntaje, comentario } }), "¡Gracias por tu calificación!"); }}>
                  <strong>Califica la experiencia</strong>
                  <label>Puntaje
                    <select value={puntaje} onChange={(e) => setPuntaje(Number(e.target.value))}>
                      {[5, 4, 3, 2, 1].map((p) => <option key={p} value={p}>{"★".repeat(p)}</option>)}
                    </select>
                  </label>
                  <label>Comentario<textarea value={comentario} onChange={(e) => setComentario(e.target.value)} rows={3} /></label>
                  <button>Enviar</button>
                </form>
              )}
              {r.pago_aprobado && (
                <form className="tarjeta formulario" onSubmit={(e: FormEvent) => { e.preventDefault();
                  accion(() => api(`/api/v1/reservas/${id}/disputas`, { method: "POST", body: { motivo } }),
                    "Disputa registrada; un administrador la revisará."); }}>
                  <strong>¿Un cobro incorrecto?</strong>
                  <label>Describe el problema<textarea minLength={10} required value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} /></label>
                  <button className="boton-secundario">Abrir disputa</button>
                </form>
              )}
            </aside>
          )}
        </div>
      )}
    </Estado>
  );
}
