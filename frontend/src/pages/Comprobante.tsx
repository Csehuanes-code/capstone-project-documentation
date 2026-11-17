import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, pesos, type Comprobante } from "../api";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, Estado, Insignia, tonoEstado, useCarga } from "../ui";

export default function ComprobantePagina() {
  const { id = "" } = useParams();
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
          <section className="tarjeta pila">
            <div className="fila entre">
              <h1 style={{ margin: 0 }}>{t("comprobante")}</h1>
              <Insignia tono={tonoEstado(r.estado)}>{r.estado}</Insignia>
            </div>
            <div className="codigo">{r.codigo}</div>
            <p>{idioma === "en" ? r.mensaje_en : r.mensaje_es}</p>
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
