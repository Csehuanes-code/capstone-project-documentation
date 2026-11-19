import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { createPortal } from "react-dom";
import qrcode from "qrcode-generator";
import { api, pesos, type Comprobante } from "../api";
import { fotosDeOferta } from "../fotos";
import { BotonRecordatorios } from "../extras";
import { Icono } from "../ilustraciones";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, avisar, Estado, Insignia, tonoEstado, useCarga } from "../ui";

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

/** Dibuja el pase (foto, datos y QR) en un canvas y lo descarga como PNG. */
async function descargarPase(r: Comprobante, foto: string, textoQR: string, en: boolean) {
  const W = 720, H = 1080, M = 40;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const g = c.getContext("2d")!;
  await document.fonts?.ready;
  const titulos = '"Space Grotesk", Inter, sans-serif';
  // Fondo y tarjeta
  g.fillStyle = "#061218"; g.fillRect(0, 0, W, H);
  g.save();
  g.beginPath(); g.roundRect(M, M, W - 2 * M, H - 2 * M, 36); g.clip();
  g.fillStyle = "#0c2a3a"; g.fillRect(M, M, W - 2 * M, H - 2 * M);
  // Foto (recorte tipo cover)
  const img = new Image();
  img.src = foto;
  await img.decode().catch(() => undefined);
  const altoFoto = 470;
  if (img.naturalWidth) {
    const escala = Math.max((W - 2 * M) / img.naturalWidth, altoFoto / img.naturalHeight);
    const w = img.naturalWidth * escala, h = img.naturalHeight * escala;
    g.drawImage(img, M + (W - 2 * M - w) / 2, M + (altoFoto - h) / 2, w, h);
  }
  const sombra = g.createLinearGradient(0, M + 200, 0, M + altoFoto);
  sombra.addColorStop(0, "rgba(12,42,58,0)"); sombra.addColorStop(1, "rgba(12,42,58,1)");
  g.fillStyle = sombra; g.fillRect(M, M, W - 2 * M, altoFoto);
  // Marca
  g.fillStyle = "#ffffff"; g.font = "700 30px " + titulos; g.fillText("Sierra", M + 34, M + 64);
  const ancho = g.measureText("Sierra").width;
  g.fillStyle = "#f5a245"; g.fillText("Mar", M + 34 + ancho, M + 64);
  g.fillStyle = "rgba(255,255,255,.75)"; g.font = "600 17px Inter, sans-serif";
  g.fillText(en ? "TRAVEL PASS" : "PASE DE VIAJE", M + 34, M + 92);
  // Nombre (con salto de línea)
  g.fillStyle = "#ffffff"; g.font = "700 44px " + titulos;
  const lineas: string[] = [];
  let linea = "";
  for (const p of r.nombre_oferta.split(" ")) {
    const prueba = linea ? linea + " " + p : p;
    if (g.measureText(prueba).width > W - 2 * M - 68 && linea) { lineas.push(linea); linea = p; } else linea = prueba;
  }
  lineas.push(linea);
  const ultimas = lineas.slice(-2);
  ultimas.forEach((l, i) => g.fillText(l, M + 34, M + altoFoto - 30 - (ultimas.length - 1 - i) * 50));
  // Datos
  const datos: [string, string][] = [[en ? "DATE" : "FECHA", r.fecha_servicio], [en ? "TIME" : "HORA", r.hora_servicio.slice(0, 5)], [en ? "GUESTS" : "PERSONAS", String(r.personas)]];
  datos.forEach(([k, v], i) => {
    const x = M + 34 + i * 205;
    g.fillStyle = "rgba(255,255,255,.6)"; g.font = "600 15px Inter, sans-serif"; g.fillText(k, x, M + altoFoto + 46);
    g.fillStyle = "#ffffff"; g.font = "700 28px " + titulos; g.fillText(v, x, M + altoFoto + 82);
  });
  // Corte punteado
  g.strokeStyle = "rgba(255,255,255,.25)"; g.setLineDash([10, 10]); g.lineWidth = 2;
  g.beginPath(); g.moveTo(M + 30, M + altoFoto + 118); g.lineTo(W - M - 30, M + altoFoto + 118); g.stroke(); g.setLineDash([]);
  g.restore();
  g.fillStyle = "#061218";
  [M, W - M].forEach((x) => { g.beginPath(); g.arc(x, M + altoFoto + 118, 18, 0, Math.PI * 2); g.fill(); });
  // QR
  const qr = qrcode(0, "M"); qr.addData(textoQR); qr.make();
  const n = qr.getModuleCount(), lado = 270, celda = lado / n, qx = (W - lado) / 2, qy = M + altoFoto + 150;
  g.fillStyle = "#ffffff"; g.beginPath(); g.roundRect(qx - 18, qy - 18, lado + 36, lado + 36, 20); g.fill();
  g.fillStyle = "#0a2130";
  for (let f = 0; f < n; f++) for (let k = 0; k < n; k++) if (qr.isDark(f, k)) g.fillRect(qx + k * celda, qy + f * celda, Math.ceil(celda), Math.ceil(celda));
  g.textAlign = "center"; g.fillStyle = "#ffd89c"; g.font = "700 34px ui-monospace, Consolas, monospace";
  g.fillText(r.codigo, W / 2, qy + lado + 70);
  g.fillStyle = "rgba(255,255,255,.65)"; g.font = "500 17px Inter, sans-serif";
  g.fillText(en ? "Show this code at check-in · Santa Marta" : "Presenta este código al llegar · Santa Marta", W / 2, qy + lado + 104);
  const blob = await new Promise<Blob | null>((ok) => c.toBlob(ok, "image/png"));
  if (!blob) throw new Error(en ? "Could not create the image" : "No se pudo generar la imagen");
  const url = URL.createObjectURL(blob);
  Object.assign(document.createElement("a"), { href: url, download: "pase-" + r.codigo + ".png" }).click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/** Pase tipo billetera: al tocarlo gira y muestra el QR; se puede descargar como imagen. */
function PaseViaje({ r, en }: { r: Comprobante; en: boolean }) {
  const [vuelta, setVuelta] = useState(false);
  const [bajando, setBajando] = useState(false);
  const foto = fotosDeOferta({ nombre_es: r.nombre_oferta })[0];
  const textoQR = window.location.origin + "/reservas/" + r.reserva_id + " · " + r.codigo;
  const girar = () => setVuelta((v) => !v);
  return (
    <div className="pase-viaje-zona aparece">
      <div className={"pase-viaje" + (vuelta ? " volteado" : "")} role="button" tabIndex={0} aria-pressed={vuelta}
        aria-label={vuelta ? (en ? "Show front" : "Ver frente del pase") : (en ? "Show QR code" : "Ver código QR")}
        onClick={girar} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); girar(); } }}>
        <div className="pase-cara pase-frente">
          <img src={foto} alt="" />
          <div className="pase-cara-texto">
            <span className="pase-marca">Sierra<b>Mar</b> · {en ? "Travel pass" : "Pase de viaje"}</span>
            <strong>{r.nombre_oferta}</strong>
            <div className="pase-datos">
              <span><small>{en ? "Date" : "Fecha"}</small>{r.fecha_servicio}</span>
              <span><small>{en ? "Time" : "Hora"}</small>{r.hora_servicio.slice(0, 5)}</span>
              <span><small>{en ? "Guests" : "Pers."}</small>{r.personas}</span>
            </div>
            <span className="pase-codigo">{r.codigo}</span>
          </div>
          <span className="pase-pista"><Icono n="voltear" tam={14} />{en ? "Tap to flip" : "Toca para girar"}</span>
        </div>
        <div className="pase-cara pase-reverso">
          <CodigoQR texto={textoQR} />
          <span className="pase-codigo">{r.codigo}</span>
          <small>{en ? "Show this code at check-in" : "Presenta este código al llegar"}</small>
        </div>
      </div>
      <div className="fila" style={{ justifyContent: "center", flexWrap: "wrap" }}>
        <button type="button" className="boton-secundario" onClick={girar}><Icono n="voltear" tam={16} /> {vuelta ? (en ? "Front" : "Ver frente") : (en ? "Show QR" : "Ver QR")}</button>
        <button type="button" className="boton-secundario" disabled={bajando} onClick={async () => {
          setBajando(true);
          try { await descargarPase(r, foto, textoQR, en); avisar(en ? "Pass downloaded" : "Pase descargado"); }
          catch (e) { avisar((e as Error).message, "error"); }
          finally { setBajando(false); }
        }}><Icono n="descargar" tam={16} /> {en ? "Download pass" : "Descargar pase"}</button>
      </div>
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
      avisar(ok);
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

          <aside className="pila">
              <PaseViaje r={r} en={idioma === "en"} />
              {esTurista && r.estado === "confirmada" && <div className="fila" style={{ justifyContent: "center" }}><BotonRecordatorios en={idioma === "en"} /></div>}
              {esTurista && <>
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
              </>}
            </aside>
        </div>
      )}
    </Estado>
  );
}
