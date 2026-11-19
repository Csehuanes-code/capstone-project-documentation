import { useMemo, useState, type FormEvent } from "react";
import { api, pesos, type Alerta, type Disputa, type Indicador, type Verificacion, type Zona } from "../api";
import { foto } from "../fotos";
import { Aviso, avisar, Estado, Insignia, tonoEstado, useCarga } from "../ui";

const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Color de la barra según qué tan cerca está la zona de su capacidad de carga (alerta al 90 %). */
function colorOcupacion(r: number | null) {
  if (r == null) return "var(--tenue)";
  if (r >= 0.9) return "linear-gradient(90deg, #f5a245, #e2583d)";
  if (r >= 0.6) return "linear-gradient(90deg, #5fd3c6, #f5a245)";
  return "linear-gradient(90deg, #0b8f8a, #5fd3c6)";
}

export default function Admin() {
  const [mensaje, setMensaje] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const hoy = new Date();
  const [desde, setDesde] = useState(iso(hoy));
  const [hasta, setHasta] = useState(iso(new Date(hoy.getTime() + 30 * 864e5)));
  const [umbral, setUmbral] = useState({ zona_id: "tayrona", visitantes_maximos: 12 });

  const zonas = useCarga(() => api<Zona[]>("/api/v1/catalogo/zonas"));
  const verificaciones = useCarga(() => api<Verificacion[]>("/api/v1/auth/admin/verificaciones", { query: { estado: "enviada" } }));
  const indicadores = useCarga(() => api<Indicador[]>("/api/v1/analitica/indicadores", { query: { desde, hasta } }), [desde, hasta]);
  const alertas = useCarga(() => api<Alerta[]>("/api/v1/analitica/alertas"));
  const disputas = useCarga(() => api<Disputa[]>("/api/v1/admin/disputas", { query: { estado: "en_revision" } }));

  // Analítica identifica las zonas por su código; aquí se muestra el nombre que tiene en Catálogo.
  const nombreZona = (codigo: string) => zonas.datos?.find((z) => z.codigo === codigo)?.nombre_es ?? codigo;
  const totales = useMemo(() => (indicadores.datos ?? []).reduce(
    (t, i) => ({ reservas: t.reservas + i.reservas_confirmadas, visitantes: t.visitantes + i.visitantes_reservados, ingresos: t.ingresos + Number(i.ingresos_cop) }),
    { reservas: 0, visitantes: 0, ingresos: 0 }), [indicadores.datos]);

  async function ejecutar(fn: () => Promise<unknown>, ok: string, ...recargar: (() => void)[]) {
    setMensaje(null);
    try {
      await fn();
      avisar(ok);
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
    <div className="apilado">
      <header className="encabezado-panel aparece">
        <img src={foto("sierra")} alt="" />
        <span className="sobretitulo">Administración · Analítica</span>
        <h1>Capacidad de carga del destino</h1>
        <p>Cada reserva confirmada llega a Analítica por un evento. Analítica compara los visitantes de cada zona con su capacidad diaria, avisa al 90 % y le pasa la ocupación a la IA para que proponga zonas más tranquilas.</p>
      </header>
      {mensaje && <Aviso tipo={mensaje.tipo}>{mensaje.texto}</Aviso>}

      <Estado carga={alertas}>
        {(as) => as.length > 0 && (
          <div className="pila">
            {as.map((a) => (
              <div key={a.zona_id} className="alerta-viva" role="alert">
                <span className="punto" aria-hidden="true" />
                <span><b>{nombreZona(a.zona_id)}</b> está al <b>{Math.round(Number(a.ocupacion) * 100)} %</b> de su capacidad ({a.visitantes} de {a.umbral} visitantes). La IA ya está proponiendo alternativas.</span>
              </div>
            ))}
          </div>
        )}
      </Estado>

      <div className="kpis">
        <div className="kpi"><span>Reservas</span><b>{totales.reservas}</b></div>
        <div className="kpi"><span>Visitantes</span><b>{totales.visitantes}</b></div>
        <div className="kpi"><span>Ingresos</span><b>{pesos(totales.ingresos).replace(" COP", "")}</b></div>
        <div className="kpi"><span>Zonas con umbral</span><b>{(indicadores.datos ?? []).filter((i) => i.umbral_visitantes != null).length}</b></div>
      </div>

      <section className="apilado">
        <div className="encabezado-seccion" style={{ margin: 0 }}>
          <div>
            <span className="sobretitulo">Indicadores por zona</span>
            <h2>Ocupación frente a capacidad</h2>
          </div>
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
        </div>
        <Estado carga={indicadores}>
          {(is) => is.length === 0 ? <Aviso>Sin reservas en el período.</Aviso> : (
            <div className="zonas-panel">
              {is.map((i) => {
                const r = i.ocupacion_estimada;
                return (
                  <article key={i.zona_id} className={`zona-tarjeta aparece${i.cerca_del_umbral ? " peligro" : ""}`}>
                    <div className="fila entre">
                      <h3>{nombreZona(i.zona_id)}</h3>
                      {r != null && <Insignia tono={r >= 0.9 ? "peligro" : r >= 0.6 ? "alerta" : "ok"}>{r >= 0.9 ? "Saturada" : r >= 0.6 ? "Moderada" : "Tranquila"}</Insignia>}
                    </div>
                    <div className="zona-porcentaje">{r == null ? "—" : `${Math.round(r * 100)} %`}<small>{i.umbral_visitantes != null ? `de ${i.umbral_visitantes} visitantes/día` : "sin umbral"}</small></div>
                    <div className="capacidad" role="img" aria-label={r == null ? "Sin umbral configurado" : `${Math.round(r * 100)} % de la capacidad`}>
                      <span style={{ width: `${Math.min(100, Math.round((r ?? 0) * 100))}%`, background: colorOcupacion(r) }} />
                      <i title="Alerta al 90 %" />
                    </div>
                    <div className="zona-cifras">
                      <span><b>{i.reservas_confirmadas}</b>reservas</span>
                      <span><b>{i.visitantes_reservados}</b>visitantes</span>
                      <span><b>{Math.round(i.concentracion * 100)} %</b>del total</span>
                    </div>
                    <small className="tenue">{pesos(i.ingresos_cop)} en ingresos</small>
                  </article>
                );
              })}
            </div>
          )}
        </Estado>
        <form className="tarjeta formulario" onSubmit={(e: FormEvent) => { e.preventDefault();
          ejecutar(() => api("/api/v1/analitica/umbrales", { method: "PUT", body: { ...umbral, confirmar_advertencia: true } }),
            "Umbral guardado. Analítica publica la ocupación a IA.", indicadores.recargar, alertas.recargar); }}>
          <strong>Capacidad de carga por zona (CU-31)</strong>
          <div className="fila">
            <label>Zona<select value={umbral.zona_id} onChange={(e) => setUmbral({ ...umbral, zona_id: e.target.value })}>
              {(zonas.datos ?? []).map((z) => <option key={z.codigo} value={z.codigo}>{z.nombre_es}</option>)}</select></label>
            <label>Visitantes por día<input type="number" min={1} value={umbral.visitantes_maximos}
              onChange={(e) => setUmbral({ ...umbral, visitantes_maximos: Number(e.target.value) })} /></label>
            <button>Guardar umbral</button>
          </div>
        </form>
      </section>

      <section className="apilado">
        <div><span className="sobretitulo">Auth</span><h2>Verificación de prestadores</h2></div>
        <Estado carga={verificaciones}>
          {(vs) => vs.length === 0 ? <Aviso>No hay solicitudes pendientes.</Aviso> : (
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
      </section>

      <section className="apilado">
        <div><span className="sobretitulo">Reservas</span><h2>Disputas de pago</h2></div>
        <Estado carga={disputas}>
          {(ds) => ds.length === 0 ? <Aviso>No hay disputas en revisión.</Aviso> : (
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
      </section>
    </div>
  );
}
