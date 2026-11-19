import { useMemo, useState, type FormEvent } from "react";
import { api, INTERESES, pesos, type Comprobante, type Oferta, type TipoServicio, type Zona } from "../api";
import { foto, fotosDeOferta } from "../fotos";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, avisar, Contador, Estado, Insignia, tonoEstado, useCarga, Vacio } from "../ui";
import { Barras, Dona } from "../graficas";
import { isoLocal } from "../extras";

type Mensaje = { tipo: "ok" | "error"; texto: string } | null;
type Pestana = "publicar" | "franja" | "verificacion";

export default function Prestador() {
  const { idioma } = useIdioma();
  const { usuario } = useSesion();
  const [mensaje, setMensaje] = useState<Mensaje>(null);
  const [pestana, setPestana] = useState<Pestana>("publicar");

  const zonas = useCarga(() => api<Zona[]>("/api/v1/catalogo/zonas"));
  const tipos = useCarga(() => api<TipoServicio[]>("/api/v1/catalogo/tipos-servicio"));
  const ofertas = useCarga(async () => {
    const r = await api<{ items: Oferta[] }>("/api/v1/catalogo/ofertas", { query: { limit: 100 } });
    return r.items.filter((o) => o.prestador_id === usuario?.id);
  });
  const reservas = useCarga(() => api<Comprobante[]>("/api/v1/prestador/reservas"));

  const resumen = useMemo(() => {
    const confirmadas = (reservas.datos ?? []).filter((r) => r.estado === "confirmada");
    return {
      confirmadas: confirmadas.length,
      personas: confirmadas.reduce((s, r) => s + r.personas, 0),
      ingresos: confirmadas.reduce((s, r) => s + Number(r.total), 0),
    };
  }, [reservas.datos]);
  // Viajeros por día (próximas dos semanas) y ventas por experiencia, para las gráficas.
  const porDia = useMemo(() => {
    const conf = (reservas.datos ?? []).filter((r) => r.estado === "confirmada");
    return Array.from({ length: 14 }, (_, i) => {
      const d = new Date(Date.now() + i * 864e5);
      const f = isoLocal(d);
      return { clave: f, etiqueta: i === 0 ? "Hoy" : `${d.getDate()}/${d.getMonth() + 1}`, valor: conf.filter((r) => r.fecha_servicio === f).reduce((s, r) => s + r.personas, 0), resaltar: i === 0 };
    });
  }, [reservas.datos]);
  const porOferta = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of reservas.datos ?? []) if (r.estado === "confirmada") m.set(r.nombre_oferta, (m.get(r.nombre_oferta) ?? 0) + Number(r.total));
    return [...m.entries()].sort((a, b) => b[1] - a[1]).map(([nombre, valor]) => ({ clave: nombre, etiqueta: nombre, valor }));
  }, [reservas.datos]);
  const codigoZona = (id: string) => zonas.datos?.find((z) => z.id === id)?.codigo;

  async function ejecutar(fn: () => Promise<unknown>, ok: string, despues?: () => void) {
    setMensaje(null);
    try {
      await fn();
      avisar(ok);
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

  const PESTANAS: [Pestana, string][] = [["publicar", "Publicar oferta"], ["franja", "Abrir horarios"], ["verificacion", "Verificación"]];

  return (
    <div className="apilado">
      <header className="encabezado-panel aparece">
        <img src={foto("pueblito")} alt="" />
        <span className="sobretitulo">Panel del prestador</span>
        <h1>Tu negocio en SierraMar</h1>
        <p>Publica experiencias, abre horarios con cupos reales y sigue tus reservas. Cada cambio llega a la IA y a Reservas por eventos.</p>
      </header>
      {mensaje && <Aviso tipo={mensaje.tipo}>{mensaje.texto}</Aviso>}

      <div className="kpis">
        <div className="kpi"><span>Ofertas publicadas</span><b><Contador valor={ofertas.datos?.length} /></b></div>
        <div className="kpi"><span>Reservas confirmadas</span><b><Contador valor={reservas.datos ? resumen.confirmadas : null} /></b></div>
        <div className="kpi"><span>Viajeros</span><b><Contador valor={reservas.datos ? resumen.personas : null} /></b></div>
        <div className="kpi"><span>Ventas confirmadas</span><b><Contador valor={reservas.datos ? resumen.ingresos : null} formato={(n) => pesos(n).replace(" COP", "")} /></b></div>
      </div>

      {reservas.datos && reservas.datos.length > 0 && (
        <div className="graficas-fila">
          <div className="tarjeta"><Barras titulo="Viajeros por día · próximas 2 semanas" datos={porDia} /></div>
          {porOferta.length > 0 && (
            <div className="tarjeta">
              <Dona titulo="Ventas por experiencia" unidad="en ventas" centro={resumen.ingresos >= 1e6 ? `$${(resumen.ingresos / 1e6).toFixed(1)} M` : `$${Math.round(resumen.ingresos / 1e3)} mil`}
                partes={porOferta} />
            </div>
          )}
        </div>
      )}

      <section className="apilado">
        <div><span className="sobretitulo">Catálogo</span><h2>Mis ofertas</h2></div>
        <Estado carga={ofertas}>
          {(os) => os.length === 0 ? <Aviso>Aún no tienes ofertas publicadas.</Aviso> : (
            <div className="mis-ofertas">
              {os.map((o) => (
                <article key={o.id} className="tarjeta mi-oferta aparece">
                  <div className="foto"><img src={fotosDeOferta(o, codigoZona(o.zona_id))[0]} alt="" loading="lazy" /></div>
                  <div>
                    <strong>{idioma === "en" ? o.nombre_en : o.nombre_es}</strong>
                    <div className="fila">{(o.atributos.categorias ?? []).map((c) => <Insignia key={c}>{c}</Insignia>)}</div>
                    <small className="tenue">★ {o.total_calificaciones ? o.calificacion_promedio.toFixed(1) : "Sin calificaciones"}{o.atributos.duracion_horas ? ` · ${o.atributos.duracion_horas} h` : ""}</small>
                  </div>
                </article>
              ))}
            </div>
          )}
        </Estado>
      </section>

      <section className="apilado">
        <div><span className="sobretitulo">Reservas</span><h2>Reservas recibidas</h2></div>
        <Estado carga={reservas}>
          {(rs) => rs.length === 0 ? <Vacio titulo="Sin reservas todavía"><p>Abre horarios en la pestaña de abajo para empezar a recibir viajeros.</p></Vacio> : (
            <div className="tarjeta tabla-scroll" style={{ padding: ".4rem 1rem" }}>
              <table>
                <thead><tr><th>Código</th><th>Experiencia</th><th>Fecha</th><th>Pers.</th><th>Total</th><th>Estado</th></tr></thead>
                <tbody>
                  {rs.map((r) => (
                    <tr key={r.reserva_id}>
                      <td style={{ fontFamily: "ui-monospace, monospace" }}>{r.codigo}</td><td>{r.nombre_oferta}</td>
                      <td>{r.fecha_servicio} {r.hora_servicio.slice(0, 5)}</td>
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

      <section className="apilado">
        <div><span className="sobretitulo">Gestión</span><h2>Administra tu oferta</h2></div>
        <div className="pestanas" role="tablist" aria-label="Formularios del prestador">
          {PESTANAS.map(([id, texto]) => (
            <button key={id} type="button" role="tab" aria-selected={pestana === id} onClick={() => setPestana(id)}>{texto}</button>
          ))}
        </div>

        {pestana === "publicar" && (
          <form className="tarjeta formulario pagina" onSubmit={crearOferta}>
            <strong>Publicar una oferta</strong>
            <div className="campos">
              <label>Nombre<input required minLength={2} value={nueva.nombre_es} onChange={(e) => setNueva({ ...nueva, nombre_es: e.target.value })} /></label>
              <label>Nombre en inglés<input value={nueva.nombre_en} onChange={(e) => setNueva({ ...nueva, nombre_en: e.target.value })} /></label>
            </div>
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
            <div className="campos">
              <label>Duración (h)<input type="number" min={1} value={nueva.duracion} onChange={(e) => setNueva({ ...nueva, duracion: Number(e.target.value) })} /></label>
              <label>Precio por persona<input type="number" min={0} step={1000} value={nueva.precio} onChange={(e) => setNueva({ ...nueva, precio: Number(e.target.value) })} /></label>
            </div>
            <button disabled={categorias.length === 0}>Publicar</button>
          </form>
        )}

        {pestana === "franja" && (
          <form className="tarjeta formulario pagina" onSubmit={(e) => { e.preventDefault();
            ejecutar(() => api("/api/v1/prestador/franjas", { method: "POST", body: franja }), "Franja publicada en Reservas."); }}>
            <strong>Abrir una franja de disponibilidad</strong>
            <label>Oferta
              <select required value={franja.oferta_id} onChange={(e) => setFranja({ ...franja, oferta_id: e.target.value })}>
                <option value="">Elige…</option>
                {ofertas.datos?.map((o) => <option key={o.id} value={o.id}>{o.nombre_es}</option>)}
              </select>
            </label>
            <div className="campos">
              <label>Fecha<input type="date" required value={franja.fecha} onChange={(e) => setFranja({ ...franja, fecha: e.target.value })} /></label>
              <label>Hora<input type="time" required value={franja.hora_inicio} onChange={(e) => setFranja({ ...franja, hora_inicio: e.target.value })} /></label>
            </div>
            <label>Cupos<input type="number" min={1} value={franja.cupo_total} onChange={(e) => setFranja({ ...franja, cupo_total: Number(e.target.value) })} /></label>
            <button>Abrir franja</button>
          </form>
        )}

        {pestana === "verificacion" && (
          <form className="tarjeta formulario pagina" onSubmit={(e) => { e.preventDefault();
            ejecutar(() => api("/api/v1/auth/prestadores/verificaciones", { method: "POST", body: { ...negocio, document_keys: [] } }),
              "Solicitud enviada. Cuando el administrador la apruebe podrás publicar."); }}>
            <strong>Verificación del negocio</strong>
            <small className="tenue">Necesaria para publicar ofertas (RF-USR-19). El administrador revisa tu RNT.</small>
            <label>Nombre comercial<input required value={negocio.business_name} onChange={(e) => setNegocio({ ...negocio, business_name: e.target.value })} /></label>
            <div className="campos">
              <label>NIT<input required value={negocio.nit} onChange={(e) => setNegocio({ ...negocio, nit: e.target.value })} /></label>
              <label>RNT<input required value={negocio.rnt} onChange={(e) => setNegocio({ ...negocio, rnt: e.target.value })} /></label>
            </div>
            <button>Solicitar verificación</button>
          </form>
        )}
      </section>
    </div>
  );
}
