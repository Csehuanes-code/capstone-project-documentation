import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, INTERESES, pesos, type DetalleOferta, type ItemRecomendado, type Oferta, type Recomendacion, type Zona } from "../api";
import { FOTO_ZONA, LEMA_ZONA, foto, fotosDeOferta } from "../fotos";
import { Icono } from "../ilustraciones";
import { useIdioma } from "../idioma";
import { Aviso, Estado, Insignia, useCarga } from "../ui";

const NIVEL: Record<string, "ok" | "alerta" | "peligro" | "neutro"> = {
  tranquila: "ok", moderada: "alerta", muy_concurrida: "peligro", desconocida: "neutro",
};
const NIVEL_TEXTO: Record<string, [string, string]> = {
  tranquila: ["Zona tranquila", "Quiet area"],
  moderada: ["Aforo moderado", "Moderate crowds"],
  muy_concurrida: ["Zona saturada", "Crowded area"],
};
const CATEGORIA_EN: Record<string, string> = {
  naturaleza: "nature", cultura: "culture", gastronomia: "food", historia: "history", playa: "beach", aventura: "adventure",
};
// Orden de la franja de destinos: el primero va en grande.
const ORDEN_ZONAS = ["tayrona", "minca", "centro", "taganga", "los-naranjos", "rodadero"];

interface Popular { oferta_id: string; zona: { nivel: string; ocupacion: number | null }; reservas_confirmadas: number }
interface OfertaEnriquecida extends Oferta { desde: number | null; moneda: string; fotos: string[] }

function TarjetaRecomendada({ item, zonaCodigo }: { item: ItemRecomendado; zonaCodigo?: string }) {
  const { t } = useIdioma();
  const [imagen] = fotosDeOferta({ nombre_es: item.nombre }, zonaCodigo);
  return (
    <article className="tarjeta recomendada">
      <div className="recomendada-foto">
        <img src={imagen} alt="" loading="lazy" />
        <span className="puesto">#{item.posicion}</span>
      </div>
      <div className="recomendada-cuerpo">
        <div className="fila entre" style={{ alignItems: "start", flexWrap: "nowrap" }}>
          <h3>{item.nombre}</h3>
          <span className="puntaje" title="Puntaje"><b>{item.puntaje.toFixed(2)}</b><small>puntaje</small></span>
        </div>
        <div className="fila">
          <Insignia tono={NIVEL[item.zona.nivel] ?? "neutro"}>
            {item.zona.nombre ?? item.zona.id}
            {item.zona.ocupacion != null && ` · ${Math.round(item.zona.ocupacion * 100)}%`}
          </Insignia>
          {item.motivo === "alternativa_descongestion" && <Insignia tono="alerta">{t("alternativa")}</Insignia>}
        </div>
        <p className="tenue">{item.explicacion}</p>
        <details>
          <summary>{t("porQue")}</summary>
          <div className="pila" style={{ marginTop: ".7rem" }}>
            {item.desglose.map((a) => (
              <div key={a.criterio}>
                <div className="fila entre" style={{ fontSize: ".88rem" }}><span>{a.etiqueta}</span><strong>+{a.aporte.toFixed(2)}</strong></div>
                <div className="barra" style={{ marginTop: ".3rem" }}><span style={{ width: `${Math.round(a.valor * 100)}%` }} /></div>
                <small className="tenue">peso {a.peso} × valor {a.valor.toFixed(2)}</small>
              </div>
            ))}
            {item.alternativa_de && (
              <small className="tenue">Reemplaza a «{item.alternativa_de.nombre}», en una zona saturada.</small>
            )}
          </div>
        </details>
        <Link className="boton-secundario" to={`/ofertas/${item.oferta_id}`} style={{ marginTop: "auto" }}>{t("verDetalle")}</Link>
      </div>
    </article>
  );
}

function TarjetaOferta({ o, zona, aforo }: { o: OfertaEnriquecida; zona?: Zona; aforo?: Popular }) {
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const categoria = o.atributos.categorias?.[0];
  const nivel = aforo?.zona.nivel;
  return (
    <Link to={`/ofertas/${o.id}`} className="tarjeta oferta">
      <div className="oferta-imagen">
        <img src={o.fotos[0]} alt={en ? o.nombre_en : o.nombre_es} loading="lazy" />
        <div className="etiquetas">
          {categoria ? <span>{en ? CATEGORIA_EN[categoria] ?? categoria : categoria}</span> : <span />}
          <span className="estrella">★ {o.total_calificaciones ? o.calificacion_promedio.toFixed(1) : (en ? "New" : "Nuevo")}</span>
        </div>
        {nivel && NIVEL_TEXTO[nivel] && (
          <span className="aforo"><Insignia tono={NIVEL[nivel]}>{NIVEL_TEXTO[nivel][en ? 1 : 0]}</Insignia></span>
        )}
      </div>
      <div className="oferta-cuerpo">
        <div className="fila entre">
          {zona && <span className="lugar"><Icono n="lugar" />{en ? zona.nombre_en : zona.nombre_es}</span>}
          <span className="verificado"><Icono n="escudo" tam={14} />{en ? "Verified" : "Verificado"}</span>
        </div>
        <h3>{en ? o.nombre_en : o.nombre_es}</h3>
        <p className="tenue">{en ? o.descripcion_en : o.descripcion_es}</p>
        <div className="oferta-pie">
          <div>
            <div className="tarifa-etq">{en ? "From" : "Desde"}</div>
            <div className="tarifa">{o.desde != null ? pesos(o.desde, o.moneda) : "—"}</div>
            <small className="tenue">{t("porPersona")}{o.atributos.duracion_horas ? ` · ${o.atributos.duracion_horas} h` : ""}</small>
          </div>
          <span className="flecha" aria-hidden="true"><Icono n="flecha" /></span>
        </div>
      </div>
    </Link>
  );
}

export default function Inicio() {
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const [intereses, setIntereses] = useState<string[]>(["naturaleza"]);
  const [categoria, setCategoria] = useState("");
  const [zonaFiltro, setZonaFiltro] = useState("");
  const [texto, setTexto] = useState("");
  const [busqueda, setBusqueda] = useState("");

  const zonas = useCarga(() => api<Zona[]>("/api/v1/catalogo/zonas"));
  const aforos = useCarga(() => api<Popular[]>("/api/v1/ia/populares", { query: { limite: 20 } }).catch(() => [] as Popular[])); // 20 = máximo que acepta IA
  const recomendacion = useCarga(
    () => api<Recomendacion>("/api/v1/ia/recomendaciones", { query: { intereses: intereses.join(","), limite: 6, idioma } }),
    [intereses.join(","), idioma],
  );
  // El listado no trae tarifa ni imágenes: se completan con el detalle de cada oferta.
  const catalogo = useCarga(async () => {
    const r = await api<{ items: Oferta[]; total: number }>("/api/v1/catalogo/ofertas", { query: { categoria, limit: 50, idioma } });
    return Promise.all(r.items.map(async (o): Promise<OfertaEnriquecida> => {
      try {
        const d = await api<DetalleOferta & { imagenes?: { clave_objeto: string }[] }>(`/api/v1/catalogo/ofertas/${o.id}`);
        const precios = d.tarifas.map((x) => Number(x.precio_por_persona));
        return { ...o, desde: precios.length ? Math.min(...precios) : null, moneda: d.tarifas[0]?.moneda ?? "COP",
                 fotos: fotosDeOferta(o, d.zona?.codigo, d.imagenes) };
      } catch {
        return { ...o, desde: null, moneda: "COP", fotos: fotosDeOferta(o) };
      }
    }));
  }, [categoria, idioma]);

  const zonaPorId = (id: string) => zonas.datos?.find((z) => z.id === id);
  const aforoDe = (id: string) => aforos.datos?.find((a) => a.oferta_id === id);
  const alternar = (i: string) => setIntereses((act) => (act.includes(i) ? act.filter((x) => x !== i) : [...act, i]));
  const reservasTotales = (aforos.datos ?? []).reduce((s, a) => s + a.reservas_confirmadas, 0);

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return (catalogo.datos ?? []).filter((o) =>
      (!zonaFiltro || o.zona_id === zonaFiltro) &&
      (!q || [o.nombre_es, o.nombre_en, o.descripcion_es, o.descripcion_en].join(" ").toLowerCase().includes(q)));
  }, [catalogo.datos, busqueda, zonaFiltro]);

  const destinos = useMemo(() => {
    const lista = (zonas.datos ?? []).filter((z) => FOTO_ZONA[z.codigo]);
    return lista.sort((a, b) => ORDEN_ZONAS.indexOf(a.codigo) - ORDEN_ZONAS.indexOf(b.codigo));
  }, [zonas.datos]);
  const experienciasEn = (zonaId: string) => (catalogo.datos ?? []).filter((o) => o.zona_id === zonaId).length;
  const irAlCatalogo = () => document.getElementById("catalogo")?.scrollIntoView({ behavior: "smooth" });
  const zonaActiva = zonaFiltro ? zonaPorId(zonaFiltro) : undefined;

  return (
    <>
      <section className="heroe a-sangre">
        <img className="heroe-foto" src={foto("heroe")} alt={en ? "Coves of Tayrona National Park" : "Ensenadas del Parque Nacional Natural Tayrona"} />
        <div className="contenedor heroe-contenido">
          <span className="pildora">{en ? "Santa Marta · Colombian Caribbean" : "Santa Marta · Caribe colombiano"}</span>
          <h1>{en ? <>Where the Sierra Nevada <em>meets the sea</em></> : <>Donde la Sierra Nevada <em>se encuentra con el mar</em></>}</h1>
          <p className="heroe-texto">{t("subtitulo")}</p>
          <form className="buscador" onSubmit={(e) => { e.preventDefault(); setBusqueda(texto); irAlCatalogo(); }}>
            <label>{en ? "What are you looking for?" : "¿Qué quieres vivir?"}
              <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={en ? "Hike, diving, cooking…" : "Caminata, buceo, cocina…"} />
            </label>
            <label>{en ? "Destination" : "Destino"}
              <select value={zonaFiltro} onChange={(e) => setZonaFiltro(e.target.value)}>
                <option value="">{en ? "All of Santa Marta" : "Todo Santa Marta"}</option>
                {destinos.map((z) => <option key={z.id} value={z.id}>{en ? z.nombre_en : z.nombre_es}</option>)}
              </select>
            </label>
            <button className="boton-grande boton-sol">{en ? "Search" : "Buscar"}</button>
          </form>
          <div className="cifras">
            <div><b>{catalogo.datos?.length ?? "—"}</b>{en ? "verified experiences" : "experiencias verificadas"}</div>
            <div><b>{zonas.datos?.length ?? "—"}</b>{en ? "destinations" : "destinos"}</div>
            <div><b>{reservasTotales}</b>{en ? "confirmed bookings" : "reservas confirmadas"}</div>
          </div>
        </div>
        <Link to="/creditos" className="credito-foto">Foto: Felipe Restrepo Acosta · CC BY-SA 4.0</Link>
      </section>

      <section id="destinos" className="seccion">
        <div className="encabezado-seccion">
          <div>
            <span className="sobretitulo">{en ? "Destinations" : "Destinos"}</span>
            <h2>{en ? "From the snowy peaks to the reef" : "De los picos nevados al arrecife"}</h2>
            <p className="tenue">{en
              ? "Santa Marta fits the jungle, the mountains and the Caribbean in one trip. Pick an area to see what you can do there."
              : "En Santa Marta caben la selva, la montaña y el Caribe en un solo viaje. Elige un destino y mira qué puedes vivir allí."}</p>
          </div>
        </div>
        <div className="destinos">
          {destinos.map((z) => (
            <button key={z.id} className="destino" aria-pressed={zonaFiltro === z.id}
              onClick={() => { setZonaFiltro(zonaFiltro === z.id ? "" : z.id); irAlCatalogo(); }}>
              <img src={foto(FOTO_ZONA[z.codigo])} alt="" loading="lazy" />
              <span className="destino-texto">
                <strong>{en ? z.nombre_en : z.nombre_es}</strong>
                <span>{LEMA_ZONA[z.codigo]?.[en ? 1 : 0]}</span>
                <small>{experienciasEn(z.id)} {en ? "experiences" : "experiencias"}</small>
              </span>
            </button>
          ))}
        </div>
      </section>

      <section id="para-ti" className="ia a-sangre seccion">
        <img className="ia-fondo" src={foto("atardecer")} alt="" loading="lazy" />
        <div className="contenedor">
          <div className="encabezado-seccion">
            <div>
              <span className="sobretitulo">{en ? "Explainable AI" : "IA explicable"}</span>
              <h2>{en ? "Recommended for you" : "Recomendado para ti"}</h2>
              <p>{en
                ? "Tell us what you like. Every suggestion shows its score and why it appears, and crowded areas get a quieter alternative."
                : "Cuéntanos qué te gusta. Cada sugerencia muestra su puntaje y por qué aparece, y si una zona está saturada te proponemos una alternativa más tranquila."}</p>
            </div>
          </div>
          <div className="chips" style={{ marginBottom: "1.6rem" }} role="group" aria-label={t("intereses")}>
            {INTERESES.map((i) => (
              <button key={i} className="chip" aria-pressed={intereses.includes(i)} onClick={() => alternar(i)}>
                {en ? CATEGORIA_EN[i] : i}
              </button>
            ))}
          </div>
          <Estado carga={recomendacion}>
            {(r) => r.items.length === 0
              ? <Aviso>{t("vacio")}</Aviso>
              : <div className="rejilla">{r.items.map((it) => (
                  <TarjetaRecomendada key={it.oferta_id} item={it} zonaCodigo={zonas.datos?.find((z) => z.id === it.zona.id)?.codigo} />
                ))}</div>}
          </Estado>
        </div>
      </section>

      <section id="catalogo" className="seccion">
        <div className="encabezado-seccion">
          <div>
            <span className="sobretitulo">{en ? "Authentic experiences" : "Turismo vivencial auténtico"}</span>
            <h2>{zonaActiva ? (en ? `Experiences in ${zonaActiva.nombre_en}` : `Experiencias en ${zonaActiva.nombre_es}`)
              : (en ? "All experiences" : "Todas las experiencias")}</h2>
            <p className="tenue">{en
              ? "Every experience is published by an operator verified with the National Tourism Registry, with real availability."
              : "Cada experiencia la publica un prestador verificado con el Registro Nacional de Turismo, con cupos reales."}</p>
          </div>
          <div className="fila">
            {zonaActiva && <button className="boton-texto" onClick={() => setZonaFiltro("")}>✕ {en ? zonaActiva.nombre_en : zonaActiva.nombre_es}</button>}
            {busqueda && <button className="boton-texto" onClick={() => { setBusqueda(""); setTexto(""); }}>✕ «{busqueda}»</button>}
          </div>
        </div>
        <div className="chips" style={{ marginBottom: "1.6rem" }}>
          <button className="chip" aria-pressed={categoria === ""} onClick={() => setCategoria("")}>{en ? "All" : "Todas"}</button>
          {INTERESES.map((i) => (
            <button key={i} className="chip" aria-pressed={categoria === i} onClick={() => setCategoria(i)}>
              {en ? CATEGORIA_EN[i] : i}
            </button>
          ))}
        </div>
        <Estado carga={catalogo}>
          {() => visibles.length === 0 ? <Aviso>{t("vacio")}</Aviso> : (
            <div className="rejilla">
              {visibles.map((o) => <TarjetaOferta key={o.id} o={o} zona={zonaPorId(o.zona_id)} aforo={aforoDe(o.id)} />)}
            </div>
          )}
        </Estado>
      </section>

      <section className="seccion pilares">
        <img src={foto("sierra")} alt="" loading="lazy" />
        <div>
          <span className="sobretitulo">{en ? "Responsible tourism" : "Turismo responsable"}</span>
          <h2>{en ? "Travel that takes care of the Sierra and the sea" : "Viajar cuidando la Sierra y el mar"}</h2>
        </div>
        <div className="pilares-lista">
          <div className="pilar">
            <Icono n="escudo" />
            <strong>{en ? "Verified operators" : "Prestadores verificados"}</strong>
            <p>{en ? "Only operators approved with their National Tourism Registry can publish." : "Solo publican prestadores aprobados con su Registro Nacional de Turismo."}</p>
          </div>
          <div className="pilar">
            <Icono n="calendario" />
            <strong>{en ? "Real availability" : "Cupos reales"}</strong>
            <p>{en ? "Every spot is reserved on payment, so there is no overbooking." : "Cada cupo se aparta al pagar: no hay sobreventa ni dobles cobros."}</p>
          </div>
          <div className="pilar">
            <Icono n="hoja" />
            <strong>{en ? "Load capacity" : "Capacidad de carga"}</strong>
            <p>{en ? "Each area has a daily visitor limit; near it, we suggest quieter places." : "Cada zona tiene un límite diario de visitantes; cerca del límite, sugerimos lugares más tranquilos."}</p>
          </div>
        </div>
      </section>
    </>
  );
}
