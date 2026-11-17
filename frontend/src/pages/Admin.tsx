import { useState, type FormEvent } from "react";
import { api, pesos, type Alerta, type Disputa, type Indicador, type Verificacion } from "../api";
import { Aviso, Estado, Insignia, tonoEstado, useCarga } from "../ui";

const ZONAS = ["minca", "tayrona", "centro", "los-naranjos", "taganga", "rodadero"];
const iso = (d: Date) => d.toISOString().slice(0, 10);

export default function Admin() {
  const [mensaje, setMensaje] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const hoy = new Date();
  const [desde, setDesde] = useState(iso(hoy));
  const [hasta, setHasta] = useState(iso(new Date(hoy.getTime() + 30 * 864e5)));
  const [umbral, setUmbral] = useState({ zona_id: "tayrona", visitantes_maximos: 12 });

  const verificaciones = useCarga(() => api<Verificacion[]>("/api/v1/auth/admin/verificaciones", { query: { estado: "enviada" } }));
  const indicadores = useCarga(() => api<Indicador[]>("/api/v1/analitica/indicadores", { query: { desde, hasta } }), [desde, hasta]);
  const alertas = useCarga(() => api<Alerta[]>("/api/v1/analitica/alertas"));
  const disputas = useCarga(() => api<Disputa[]>("/api/v1/admin/disputas", { query: { estado: "en_revision" } }));

  async function ejecutar(fn: () => Promise<unknown>, ok: string, ...recargar: (() => void)[]) {
    setMensaje(null);
    try {
      await fn();
      setMensaje({ tipo: "ok", texto: ok });
      recargar.forEach((r) => r());
    } catch (e) {
      setMensaje({ tipo: "error", texto: (e as Error).message });
    }
  }

  const decidir = (v: Verificacion, decision: "aprobar" | "rechazar") => ejecutar(
    () => api(`/api/v1/auth/admin/verificaciones/${v.id}/decision`, {
      method: "POST", body: { decision, justification: decision === "aprobar" ? "RNT y documentos verificados." : "Documentos incompletos." },
    }),
    decision === "aprobar" ? `${v.business_name} aprobado: Catálogo lo habilita para publicar.` : `${v.business_name} rechazado.`,
    verificaciones.recargar,
  );

  const resolver = (d: Disputa, decision: "aprobada" | "rechazada") => ejecutar(
    () => api(`/api/v1/admin/disputas/${d.disputa_id}/resolver`, {
      method: "POST", body: { decision, justificacion: decision === "aprobada" ? "Cobro verificado como incorrecto." : "El cobro corresponde al servicio prestado." },
    }),
    `Disputa ${decision}.`, disputas.recargar,
  );

  return (
    <div className="pila">
      <h1>Administración</h1>
      {mensaje && <Aviso tipo={mensaje.tipo}>{mensaje.texto}</Aviso>}

      <h2>Verificación de prestadores</h2>
      <Estado carga={verificaciones}>
        {(vs) => vs.length === 0 ? <p className="tenue">No hay solicitudes pendientes.</p> : (
          <div className="pila">
            {vs.map((v) => (
              <div key={v.id} className="tarjeta fila entre">
                <span><strong>{v.business_name}</strong> · NIT {v.nit} · RNT {v.rnt}</span>
                <span className="fila">
                  <button onClick={() => decidir(v, "aprobar")}>Aprobar</button>
                  <button className="boton-secundario" onClick={() => decidir(v, "rechazar")}>Rechazar</button>
                </span>
              </div>
            ))}
          </div>
        )}
      </Estado>

      <h2>Indicadores y capacidad de carga</h2>
      <Estado carga={alertas}>
        {(as) => as.length > 0 && (
          <Aviso tipo="error">
            {as.map((a) => <div key={a.zona_id}>⚠ {a.zona_id}: {Math.round(Number(a.ocupacion) * 100)} % de la capacidad ({a.visitantes}/{a.umbral} visitantes)</div>)}
          </Aviso>
        )}
      </Estado>
      <div className="fila">
        <label>Desde<input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
        <label>Hasta<input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
        <a className="boton-secundario" href={`/api/v1/analitica/indicadores.csv?desde=${desde}&hasta=${hasta}`}
          onClick={async (e) => {
            e.preventDefault();
            const r = await fetch(e.currentTarget.href, { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } });
            const url = URL.createObjectURL(await r.blob());
            Object.assign(document.createElement("a"), { href: url, download: "indicadores.csv" }).click();
          }}>Exportar CSV</a>
      </div>
      <Estado carga={indicadores}>
        {(is) => is.length === 0 ? <p className="tenue">Sin reservas en el período.</p> : (
          <div className="tabla-scroll">
            <table>
              <thead><tr><th>Zona</th><th>Reservas</th><th>Visitantes</th><th>Ingresos</th><th>Concentración</th><th>Ocupación estimada</th></tr></thead>
              <tbody>
                {is.map((i) => (
                  <tr key={i.zona_id}>
                    <td>{i.zona_id}</td><td>{i.reservas_confirmadas}</td><td>{i.visitantes_reservados}</td>
                    <td>{pesos(i.ingresos_cop)}</td><td>{Math.round(i.concentracion * 100)} %</td>
                    <td>{i.ocupacion_estimada == null ? "—" : (
                      <Insignia tono={i.cerca_del_umbral ? "peligro" : "ok"}>{Math.round(i.ocupacion_estimada * 100)} % de {i.umbral_visitantes}</Insignia>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Estado>
      <form className="tarjeta formulario" onSubmit={(e: FormEvent) => { e.preventDefault();
        ejecutar(() => api("/api/v1/analitica/umbrales", { method: "PUT", body: { ...umbral, confirmar_advertencia: true } }),
          "Umbral guardado. Analítica publica la ocupación a IA.", indicadores.recargar, alertas.recargar); }}>
        <strong>Capacidad de carga por zona (CU-31)</strong>
        <div className="fila">
          <label>Zona<select value={umbral.zona_id} onChange={(e) => setUmbral({ ...umbral, zona_id: e.target.value })}>
            {ZONAS.map((z) => <option key={z}>{z}</option>)}</select></label>
          <label>Visitantes por día<input type="number" min={1} value={umbral.visitantes_maximos}
            onChange={(e) => setUmbral({ ...umbral, visitantes_maximos: Number(e.target.value) })} /></label>
          <button>Guardar umbral</button>
        </div>
      </form>

      <h2>Disputas de pago</h2>
      <Estado carga={disputas}>
        {(ds) => ds.length === 0 ? <p className="tenue">No hay disputas en revisión.</p> : (
          <div className="pila">
            {ds.map((d) => (
              <div key={d.disputa_id} className="tarjeta pila">
                <div className="fila entre"><Insignia tono={tonoEstado(d.estado)}>{d.estado}</Insignia><small className="tenue">{d.reserva_id}</small></div>
                <p style={{ margin: 0 }}>{d.motivo}</p>
                <div className="fila">
                  <button onClick={() => resolver(d, "aprobada")}>Aprobar y reembolsar</button>
                  <button className="boton-secundario" onClick={() => resolver(d, "rechazada")}>Rechazar</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Estado>
    </div>
  );
}
