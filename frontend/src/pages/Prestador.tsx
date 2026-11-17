import { useState, type FormEvent } from "react";
import { api, INTERESES, pesos, type Comprobante, type Oferta, type TipoServicio, type Zona } from "../api";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, Estado, Insignia, tonoEstado, useCarga } from "../ui";

type Mensaje = { tipo: "ok" | "error"; texto: string } | null;

export default function Prestador() {
  const { idioma } = useIdioma();
  const { usuario } = useSesion();
  const [mensaje, setMensaje] = useState<Mensaje>(null);

  const zonas = useCarga(() => api<Zona[]>("/api/v1/catalogo/zonas"));
  const tipos = useCarga(() => api<TipoServicio[]>("/api/v1/catalogo/tipos-servicio"));
  const ofertas = useCarga(async () => {
    const r = await api<{ items: Oferta[] }>("/api/v1/catalogo/ofertas", { query: { limit: 100 } });
    return r.items.filter((o) => o.prestador_id === usuario?.id);
  });
  const reservas = useCarga(() => api<Comprobante[]>("/api/v1/prestador/reservas"));

  async function ejecutar(fn: () => Promise<unknown>, ok: string, despues?: () => void) {
    setMensaje(null);
    try {
      await fn();
      setMensaje({ tipo: "ok", texto: ok });
      despues?.();
    } catch (e) {
      setMensaje({ tipo: "error", texto: (e as Error).message });
    }
  }

  // --- verificación (CU-26) ---
  const [negocio, setNegocio] = useState({ business_name: "", nit: "", rnt: "" });
  // --- nueva oferta (CU-22, CU-24) ---
  const [nueva, setNueva] = useState({ nombre_es: "", nombre_en: "", descripcion_es: "", zona_id: "", duracion: 4, precio: 100000 });
  const [categorias, setCategorias] = useState<string[]>(["naturaleza"]);
  // --- franja ---
  const [franja, setFranja] = useState({ oferta_id: "", fecha: "", hora_inicio: "08:00", cupo_total: 10 });

  async function crearOferta(e: FormEvent) {
    e.preventDefault();
    const tour = tipos.datos?.find((t) => t.codigo === "tour");
    await ejecutar(async () => {
      const o = await api<Oferta>("/api/v1/catalogo/ofertas", {
        method: "POST",
        body: {
          tipo_servicio_id: tour?.id, zona_id: nueva.zona_id, nombre_es: nueva.nombre_es,
          nombre_en: nueva.nombre_en || nueva.nombre_es, descripcion_es: nueva.descripcion_es,
          descripcion_en: nueva.descripcion_es, estado: "publicada", indice_sostenibilidad: 0.8,
          atributos: { duracion_horas: nueva.duracion, nivel_dificultad: "media", categorias },
        },
      });
      const hoy = new Date();
      const enUnAno = new Date(hoy.getTime() + 365 * 864e5);
      await api(`/api/v1/catalogo/ofertas/${o.id}/tarifas`, {
        method: "POST",
        body: { temporada: "media", vigente_desde: hoy.toISOString().slice(0, 10),
                vigente_hasta: enUnAno.toISOString().slice(0, 10), precio_por_persona: nueva.precio, moneda: "COP" },
      });
      await api(`/api/v1/catalogo/ofertas/${o.id}/politica-cancelacion`, {
        method: "PUT", body: { horas_reembolso_total: 48, horas_reembolso_parcial: 24, porcentaje_reembolso_parcial: 50 },
      });
    }, "Oferta publicada. Catálogo avisa a IA y Reservas por RabbitMQ.", ofertas.recargar);
  }

  return (
    <div className="pila">
      <h1>Mi panel de prestador</h1>
      {mensaje && <Aviso tipo={mensaje.tipo}>{mensaje.texto}</Aviso>}

      <div className="columnas">
        <section className="pila">
          <h2>Mis ofertas</h2>
          <Estado carga={ofertas}>
            {(os) => os.length === 0 ? <Aviso>Aún no tienes ofertas publicadas.</Aviso> : (
              <div className="pila">
                {os.map((o) => (
                  <div key={o.id} className="tarjeta fila entre">
                    <span><strong>{idioma === "en" ? o.nombre_en : o.nombre_es}</strong>{" "}
                      {(o.atributos.categorias ?? []).map((c) => <Insignia key={c}>{c}</Insignia>)}</span>
                    <span>★ {o.calificacion_promedio.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            )}
          </Estado>

          <h2>Reservas recibidas</h2>
          <Estado carga={reservas}>
            {(rs) => rs.length === 0 ? <p className="tenue">Sin reservas todavía.</p> : (
              <div className="tabla-scroll">
                <table>
                  <thead><tr><th>Código</th><th>Experiencia</th><th>Fecha</th><th>Pers.</th><th>Total</th><th>Estado</th></tr></thead>
                  <tbody>
                    {rs.map((r) => (
                      <tr key={r.reserva_id}>
                        <td>{r.codigo}</td><td>{r.nombre_oferta}</td><td>{r.fecha_servicio} {r.hora_servicio}</td>
                        <td>{r.personas}</td><td>{pesos(r.total)}</td>
                        <td><Insignia tono={tonoEstado(r.estado)}>{r.estado}</Insignia></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Estado>
        </section>

        <aside className="pila">
          <form className="tarjeta formulario" onSubmit={(e) => { e.preventDefault();
            ejecutar(() => api("/api/v1/auth/prestadores/verificaciones", { method: "POST", body: { ...negocio, document_keys: [] } }),
              "Solicitud enviada. Cuando el administrador la apruebe podrás publicar."); }}>
            <strong>Verificación del negocio</strong>
            <small className="tenue">Necesaria para publicar ofertas (RF-USR-19).</small>
            <label>Nombre comercial<input required value={negocio.business_name} onChange={(e) => setNegocio({ ...negocio, business_name: e.target.value })} /></label>
            <div className="fila">
              <label>NIT<input required value={negocio.nit} onChange={(e) => setNegocio({ ...negocio, nit: e.target.value })} /></label>
              <label>RNT<input required value={negocio.rnt} onChange={(e) => setNegocio({ ...negocio, rnt: e.target.value })} /></label>
            </div>
            <button className="boton-secundario">Solicitar verificación</button>
          </form>

          <form className="tarjeta formulario" onSubmit={crearOferta}>
            <strong>Publicar una oferta</strong>
            <label>Nombre<input required minLength={2} value={nueva.nombre_es} onChange={(e) => setNueva({ ...nueva, nombre_es: e.target.value })} /></label>
            <label>Nombre en inglés<input value={nueva.nombre_en} onChange={(e) => setNueva({ ...nueva, nombre_en: e.target.value })} /></label>
            <label>Descripción<textarea rows={2} value={nueva.descripcion_es} onChange={(e) => setNueva({ ...nueva, descripcion_es: e.target.value })} /></label>
            <label>Zona
              <select required value={nueva.zona_id} onChange={(e) => setNueva({ ...nueva, zona_id: e.target.value })}>
                <option value="">Elige…</option>
                {zonas.datos?.map((z) => <option key={z.id} value={z.id}>{z.nombre_es}</option>)}
              </select>
            </label>
            <div className="chips">
              {INTERESES.map((i) => (
                <button type="button" key={i} className="chip" aria-pressed={categorias.includes(i)}
                  onClick={() => setCategorias((c) => c.includes(i) ? c.filter((x) => x !== i) : [...c, i])}>{i}</button>
              ))}
            </div>
            <div className="fila">
              <label>Duración (h)<input type="number" min={1} value={nueva.duracion} onChange={(e) => setNueva({ ...nueva, duracion: Number(e.target.value) })} /></label>
              <label>Precio por persona<input type="number" min={0} step={1000} value={nueva.precio} onChange={(e) => setNueva({ ...nueva, precio: Number(e.target.value) })} /></label>
            </div>
            <button disabled={categorias.length === 0}>Publicar</button>
          </form>

          <form className="tarjeta formulario" onSubmit={(e) => { e.preventDefault();
            ejecutar(() => api("/api/v1/prestador/franjas", { method: "POST", body: franja }), "Franja publicada en Reservas."); }}>
            <strong>Abrir una franja de disponibilidad</strong>
            <label>Oferta
              <select required value={franja.oferta_id} onChange={(e) => setFranja({ ...franja, oferta_id: e.target.value })}>
                <option value="">Elige…</option>
                {ofertas.datos?.map((o) => <option key={o.id} value={o.id}>{o.nombre_es}</option>)}
              </select>
            </label>
            <div className="fila">
              <label>Fecha<input type="date" required value={franja.fecha} onChange={(e) => setFranja({ ...franja, fecha: e.target.value })} /></label>
              <label>Hora<input type="time" required value={franja.hora_inicio} onChange={(e) => setFranja({ ...franja, hora_inicio: e.target.value })} /></label>
              <label>Cupos<input type="number" min={1} value={franja.cupo_total} onChange={(e) => setFranja({ ...franja, cupo_total: Number(e.target.value) })} /></label>
            </div>
            <button>Abrir franja</button>
          </form>
        </aside>
      </div>
    </div>
  );
}
