import { useState } from "react";
import { Link } from "react-router-dom";
import { api, pesos, type Comprobante, type EntradaListaEspera } from "../api";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, Estado, Insignia, tonoEstado, useCarga } from "../ui";

const ESTADOS = ["", "confirmada", "pendiente_pago", "cancelada", "expirada", "cancelacion_pendiente"];

export default function MisReservas() {
  const { t, idioma } = useIdioma();
  const { usuario } = useSesion();
  const [estado, setEstado] = useState("");
  const [mensaje, setMensaje] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const reservas = useCarga(() => api<Comprobante[]>("/api/v1/reservas/mias", { query: { estado } }), [estado]);
  const lista = useCarga(() => api<EntradaListaEspera[]>("/api/v1/lista-espera/mias"));

  async function confirmarCupo(e: EntradaListaEspera) {
    setMensaje(null);
    try {
      const r = await api<Comprobante>("/api/v1/reservas", {
        method: "POST", headers: { "Idempotency-Key": `lista-${e.entrada_id}` },
        body: { franja_id: e.franja_id, personas: e.personas, correo_turista: usuario?.email || "turista@turismo.co",
                idioma, entrada_lista_espera_id: e.entrada_id, datos_pago: { numero_tarjeta: "4111111111111111" } },
      });
      setMensaje({ tipo: r.pago_aprobado ? "ok" : "error", texto: idioma === "en" ? r.mensaje_en : r.mensaje_es });
      reservas.recargar(); lista.recargar();
    } catch (err) {
      setMensaje({ tipo: "error", texto: (err as Error).message });
    }
  }

  async function retirarse(e: EntradaListaEspera) {
    await api(`/api/v1/lista-espera/${e.entrada_id}`, { method: "DELETE" });
    lista.recargar();
  }

  return (
    <div className="pila">
      <div className="fila entre">
        <h1>{t("misReservas")}</h1>
        <select value={estado} onChange={(e) => setEstado(e.target.value)} aria-label={t("estado")}>
          {ESTADOS.map((s) => <option key={s} value={s}>{s || "Todas"}</option>)}
        </select>
      </div>
      {mensaje && <Aviso tipo={mensaje.tipo}>{mensaje.texto}</Aviso>}
      <Estado carga={reservas}>
        {(rs) => rs.length === 0 ? <Aviso>{t("vacio")} <Link to="/">{t("explorar")}</Link></Aviso> : (
          <div className="rejilla">
            {rs.map((r) => (
              <Link key={r.reserva_id} to={`/reservas/${r.reserva_id}`} className="tarjeta pila" style={{ textDecoration: "none", color: "inherit" }}>
                <div className="fila entre"><strong>{r.nombre_oferta}</strong><Insignia tono={tonoEstado(r.estado)}>{r.estado}</Insignia></div>
                <span className="tenue">{r.codigo} · {r.fecha_servicio} {r.hora_servicio} · {r.personas} pers.</span>
                <strong>{pesos(r.total, r.moneda)}</strong>
              </Link>
            ))}
          </div>
        )}
      </Estado>

      <h2>Lista de espera</h2>
      <Estado carga={lista}>
        {(es) => es.length === 0 ? <p className="tenue">{t("vacio")}</p> : (
          <div className="pila">
            {es.map((e) => (
              <div key={e.entrada_id} className="tarjeta fila entre">
                <span>
                  <Insignia tono={tonoEstado(e.estado)}>{e.estado}</Insignia>{" "}
                  {e.personas} pers.{e.posicion ? ` · posición ${e.posicion}` : ""}
                  {e.oferta_expira_en && ` · confirma antes de ${new Date(e.oferta_expira_en).toLocaleTimeString()}`}
                </span>
                <span className="fila">
                  {e.estado === "ofrecida" && <button onClick={() => confirmarCupo(e)}>Confirmar cupo y pagar</button>}
                  {["esperando", "ofrecida"].includes(e.estado) && (
                    <button className="boton-secundario" onClick={() => retirarse(e)}>Salir de la lista</button>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </Estado>
    </div>
  );
}
