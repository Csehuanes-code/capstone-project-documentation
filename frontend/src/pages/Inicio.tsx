import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CREDITOS, type ClaveFoto } from "../fotos";
import { irConFoto } from "../transicion";
import { api, INTERESES, pesos, type DetalleOferta, type ItemRecomendado, type Oferta, type Recomendacion, type Zona } from "../api";
import { FOTO_ZONA, LEMA_ZONA, foto, fotosDeOferta } from "../fotos";
import { Icono } from "../ilustraciones";
import MapaZonas, { type EstadoZona } from "../MapaZonas";
import { useIdioma } from "../idioma";
import { Aviso, Contador, Estado, Insignia, useCarga } from "../ui";

// Portada: cada foto con la palabra que completa el título.
const PORTADAS: { foto: ClaveFoto; es: string; en: string; lugar: [string, string] }[] = [
  { foto: "heroe", es: "con el mar", en: "meets the sea", lugar: ["Ensenadas del Tayrona", "Tayrona coves"] },
  { foto: "minca-cascada", es: "con la selva", en: "meets the jungle", lugar: ["Cascadas de Minca", "Minca waterfalls"] },
  { foto: "catedral", es: "con la historia", en: "meets history", lugar: ["Catedral de Santa Marta", "Santa Marta Cathedral"] },
  { foto: "atardecer", es: "con el atardecer", en: "meets the sunset", lugar: ["Bahía de Santa Marta", "Santa Marta bay"] },
];

const PASOS: { icono: "brujula" | "calendario" | "ondas" | "hoja"; es: [string, string]; en: [string, string] }[] = [
  { icono: "brujula", es: ["Elige", "Experiencias de prestadores verificados con su RNT."], en: ["Choose", "Experiences from operators verified with their RNT."] },
  { icono: "calendario", es: ["Reserva", "Cupos reales, pago seguro y comprobante al instante."], en: ["Book", "Real availability, secure payment and an instant receipt."] },
  { icono: "ondas", es: ["Vive", "Presenta tu código QR y disfruta Santa Marta."], en: ["Enjoy", "Show your QR code and enjoy Santa Marta."] },
  { icono: "hoja", es: ["Cuida", "Tu visita respeta la capacidad de carga de cada zona."], en: ["Care", "Your visit respects each area's load capacity."] },
];

// Ejemplos ilustrativos de la demo (no son reseñas reales de usuarios).
const TESTIMONIOS = [
  { nombre: "Laura · Medellín", experiencia: "Tour cascadas de Minca", foto: "minca-cascada" as ClaveFoto,
    es: "Reservé en dos minutos desde el celular y el comprobante me llegó al correo. La IA me llevó a Minca en vez de Tayrona y fue lo mejor del viaje.",
    en: "I booked in two minutes from my phone and got the receipt by email. The AI suggested Minca instead of Tayrona, and it was the best part of the trip." },
  { nombre: "Tom · Ámsterdam", experiencia: "Bautismo de buceo en Taganga", foto: "buceo" as ClaveFoto,
    es: "Todo en inglés, el precio claro desde el principio y un prestador verificado. Me dio confianza para reservar algo que no conocía.",
    en: "Everything in English, a clear price from the start and a verified operator. It gave me confidence to book something new." },
  { nombre: "Don Efraín · prestador en Taganga", experiencia: "Panel del prestador", foto: "taganga" as ClaveFoto,
    es: "Publiqué mi tour con un formulario sencillo y veo mis reservas en un solo lugar. Ya no compito solo contra los operadores grandes.",
    en: "I published my tour with a simple form and see my bookings in one place. I no longer compete alone against the big operators." },
];

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

// Un color por criterio de la IA: afinidad, calidad, descongestión, sostenibilidad.
const COLOR_CRITERIO = ["#0b8f8a", "#5fd3c6", "#f5a245", "#ff7a59"];
const NOMBRE_CRITERIO: Record<string, [string, string]> = {
  afinidad: ["Afinidad", "Affinity"], calidad: ["Calidad", "Quality"],
  descongestion: ["Descongestión", "Low crowds"], sostenibilidad: ["Sostenibilidad", "Sustainability"],
};
const GRAVEDAD: Record<string, number> = { desconocida: 0, tranquila: 1, moderada: 2, muy_concurrida: 3 };

interface Popular { oferta_id: string; zona: { nivel: string; ocupacion: number | null }; reservas_confirmadas: number }
interface OfertaEnriquecida extends Oferta { desde: number | null; moneda: string; fotos: string[] }

function TarjetaRecomendada({ item, zonaCodigo }: { item: ItemRecomendado; zonaCodigo?: string }) {
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const [imagen] = fotosDeOferta({ nombre_es: item.nombre }, zonaCodigo);
  return (
    <article className="tarjeta recomendada" data-tilt="">
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
        <div className="desglose-barra" role="img"
          aria-label={item.desglose.map((a) => `${a.etiqueta} +${a.aporte.toFixed(2)}`).join(", ")}>
          {item.desglose.map((a, i) => (
            <span key={a.criterio} title={`${a.etiqueta}: +${a.aporte.toFixed(2)}`}
              style={{ width: `${Math.max(0, a.aporte) * 100}%`, background: COLOR_CRITERIO[i % COLOR_CRITERIO.length], animationDelay: `${i * 120}ms` }} />
          ))}
        </div>
        <div className="desglose-leyenda">
          {item.desglose.map((a, i) => (
            <span key={a.criterio}><i style={{ background: COLOR_CRITERIO[i % COLOR_CRITERIO.length] }} />{NOMBRE_CRITERIO[a.criterio]?.[en ? 1 : 0] ?? a.etiqueta.split(" ")[0]} <b>+{a.aporte.toFixed(2)}</b></span>
          ))}
        </div>
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
  const navegar = useNavigate();
  const imagen = useRef<HTMLImageElement>(null);
  const ruta = `/ofertas/${o.id}`;
  return (
    <Link to={ruta} className="tarjeta oferta" data-tilt=""
      onClick={(e) => {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        irConFoto(navegar, ruta, imagen.current, { foto: o.fotos[0], nombre: en ? o.nombre_en : o.nombre_es });
      }}>
      <div className="oferta-imagen">
        <img ref={imagen} src={o.fotos[0]} alt={en ? o.nombre_en : o.nombre_es} loading="lazy" />
        {o.desde != null && <span className="precio-flotante">{pesos(o.desde, o.moneda)}</span>}
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
  const textoExperiencias = (n: number) => en ? `${n} ${n === 1 ? "experience" : "experiences"}` : `${n} ${n === 1 ? "experiencia" : "experiencias"}`;
  // Estado de cada zona para el mapa: la ocupación más alta entre sus ofertas (IA la recibe de Analítica).
  const estadosZona = useMemo(() => {
    const r: Record<string, EstadoZona> = {};
    for (const o of catalogo.datos ?? []) {
      const a = aforos.datos?.find((p) => p.oferta_id === o.id);
      if (!a) continue;
      const previo = r[o.zona_id];
      const nivel = a.zona.nivel ?? "desconocida";
      if (!previo || (GRAVEDAD[nivel] ?? 0) > (GRAVEDAD[previo.nivel] ?? 0)
        || ((a.zona.ocupacion ?? -1) > (previo.ocupacion ?? -1) && nivel === previo.nivel)) {
        r[o.zona_id] = { nivel, ocupacion: a.zona.ocupacion };
      }
    }
    return r;
  }, [catalogo.datos, aforos.datos]);
  const irAlCatalogo = () => document.getElementById("catalogo")?.scrollIntoView({ behavior: "smooth" });
  const zonaActiva = zonaFiltro ? zonaPorId(zonaFiltro) : undefined;

  // Portada rotativa: cambia de foto y de palabra cada 6 s (quieta si el usuario pide menos movimiento).
  const [portada, setPortada] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => setPortada((p) => (p + 1) % PORTADAS.length), 6000);
    return () => clearInterval(t);
  }, []);
  const actual = PORTADAS[portada];
  const credito = CREDITOS[actual.foto];

  // Destacadas: las más reservadas primero (popularidad que IA recibe de Reservas).
  const destacadas = useMemo(() => [...(catalogo.datos ?? [])]
    .sort((a, b) => (aforoDe(b.id)?.reservas_confirmadas ?? 0) - (aforoDe(a.id)?.reservas_confirmadas ?? 0)),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [catalogo.datos, aforos.datos]);
  const carrusel = useRef<HTMLDivElement>(null);
  const deslizar = (dir: number) => carrusel.current?.scrollBy({ left: dir * Math.min(carrusel.current.clientWidth * 0.8, 720), behavior: "smooth" });
  const navegar = useNavigate();

  return (
    <>
      <section className="heroe a-sangre">
        {PORTADAS.map((p, i) => (
          <img key={p.foto} className={`heroe-foto${i === portada ? " activa" : ""}`} src={foto(p.foto)} alt={i === portada ? p.lugar[en ? 1 : 0] : ""}
            aria-hidden={i !== portada} />
        ))}
        <div className="heroe-orbes" aria-hidden="true"><span /><span /><span /></div>
        <div className="contenedor heroe-contenido">
          <span className="pildora">{en ? "Santa Marta · Colombian Caribbean" : "Santa Marta · Caribe colombiano"}</span>
          <h1>{en ? "Where the Sierra Nevada " : "Donde la Sierra Nevada se encuentra "}<em key={portada} className="palabra">{en ? actual.en : actual.es}</em></h1>
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
            <div><b><Contador valor={catalogo.datos?.length} /></b>{en ? "verified experiences" : "experiencias verificadas"}</div>
            <div><b><Contador valor={zonas.datos?.length} /></b>{en ? "destinations" : "destinos"}</div>
            <div><b><Contador valor={aforos.datos ? reservasTotales : null} /></b>{en ? "confirmed bookings" : "reservas confirmadas"}</div>
          </div>
          <div className="puntos-portada" role="group" aria-label={en ? "Cover photos" : "Fotos de portada"}>
            {PORTADAS.map((p, i) => (
              <button key={p.foto} type="button" aria-pressed={i === portada} aria-label={p.lugar[en ? 1 : 0]} onClick={() => setPortada(i)} />
            ))}
          </div>
        </div>
        <Link to="/creditos" className="credito-foto">{actual.lugar[en ? 1 : 0]} · Foto: {credito.autor} · {credito.licencia}</Link>
        <svg className="olas" viewBox="0 0 1440 120" preserveAspectRatio="none" aria-hidden="true">
          <path className="ola ola-1" d="M0 70 C240 30 480 110 720 70 C960 30 1200 110 1440 70 C1680 30 1920 110 2160 70 L2160 120 L0 120 Z" />
          <path className="ola ola-2" d="M0 85 C240 55 480 115 720 85 C960 55 1200 115 1440 85 C1680 55 1920 115 2160 85 L2160 120 L0 120 Z" />
          <path className="ola ola-3" d="M0 98 C240 80 480 116 720 98 C960 80 1200 116 1440 98 C1680 80 1920 116 2160 98 L2160 120 L0 120 Z" />
        </svg>
      </section>

      <section className="seccion destacadas">
        <div className="encabezado-seccion">
          <div>
            <span className="sobretitulo">{en ? "Most booked" : "Lo más reservado"}</span>
            <h2>{en ? "Featured experiences" : "Experiencias destacadas"}</h2>
          </div>
          <div className="fila">
            <button type="button" className="flecha-carrusel" aria-label={en ? "Previous" : "Anterior"} onClick={() => deslizar(-1)}>←</button>
            <button type="button" className="flecha-carrusel" aria-label={en ? "Next" : "Siguiente"} onClick={() => deslizar(1)}>→</button>
          </div>
        </div>
        <div className="carrusel" ref={carrusel}>
          {destacadas.map((o, i) => (
            <Link key={o.id} to={`/ofertas/${o.id}`} className="destacada" data-tilt=""
              onClick={(e) => {
                if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                e.preventDefault();
                const img = e.currentTarget.querySelector("img");
                irConFoto(navegar, `/ofertas/${o.id}`, img, { foto: o.fotos[0], nombre: en ? o.nombre_en : o.nombre_es });
              }}>
              <img src={o.fotos[0]} alt="" loading={i < 3 ? "eager" : "lazy"} />
              <span className="destacada-puesto">{String(i + 1).padStart(2, "0")}</span>
              <span className="destacada-texto">
                <small>{zonaPorId(o.zona_id)?.[en ? "nombre_en" : "nombre_es"]}</small>
                <strong>{en ? o.nombre_en : o.nombre_es}</strong>
                <span>{o.desde != null ? `${en ? "From" : "Desde"} ${pesos(o.desde, o.moneda)}` : ""}{(aforoDe(o.id)?.reservas_confirmadas ?? 0) > 0 ? ` · ${aforoDe(o.id)!.reservas_confirmadas} ${aforoDe(o.id)!.reservas_confirmadas === 1 ? (en ? "booking" : "reserva") : (en ? "bookings" : "reservas")}` : ""}</span>
              </span>
            </Link>
          ))}
        </div>
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
          {destinos.map((z) => {
            const n = experienciasEn(z.id);
            const pronto = catalogo.datos != null && n === 0;
            return (
              <button key={z.id} className={`destino aparece${pronto ? " proximamente" : ""}`} aria-pressed={zonaFiltro === z.id}
                onClick={() => { if (pronto) return; setZonaFiltro(zonaFiltro === z.id ? "" : z.id); irAlCatalogo(); }}>
                <img src={foto(FOTO_ZONA[z.codigo])} alt="" loading="lazy" />
                <span className="destino-texto">
                  <strong>{en ? z.nombre_en : z.nombre_es}</strong>
                  <span>{LEMA_ZONA[z.codigo]?.[en ? 1 : 0]}</span>
                  {pronto
                    ? <small className="pronto">{en ? "Coming soon" : "Próximamente"}</small>
                    : <small>{textoExperiencias(n)}</small>}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="seccion aparece" data-brillo="">
        <MapaZonas zonas={destinos} estados={estadosZona} elegida={zonaFiltro}
          onElegir={(id) => { if (experienciasEn(id) === 0) return; setZonaFiltro(id); irAlCatalogo(); }} />
      </section>

      <section className="seccion como-funciona">
        <div className="encabezado-seccion" style={{ justifyContent: "center", textAlign: "center" }}>
          <div>
            <span className="sobretitulo">{en ? "How it works" : "Cómo funciona"}</span>
            <h2>{en ? "From idea to trip, in four steps" : "De la idea al viaje, en cuatro pasos"}</h2>
          </div>
        </div>
        <ol className="pasos">
          <li className="pasos-linea" aria-hidden="true"><span /></li>
          {PASOS.map((p, i) => (
            <li key={p.icono} className="paso aparece" style={{ animationDelay: `${i * 80}ms` }}>
              <span className="paso-icono"><Icono n={p.icono} tam={30} /></span>
              <small>{String(i + 1).padStart(2, "0")}</small>
              <strong>{p[en ? "en" : "es"][0]}</strong>
              <p className="tenue">{p[en ? "en" : "es"][1]}</p>
            </li>
          ))}
        </ol>
      </section>

      <section id="para-ti" className="ia a-sangre seccion" data-brillo="">
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
              {visibles.map((o) => <div key={o.id} className="aparece" style={{ display: "grid" }}><TarjetaOferta o={o} zona={zonaPorId(o.zona_id)} aforo={aforoDe(o.id)} /></div>)}
            </div>
          )}
        </Estado>
      </section>

      <section className="seccion testimonios">
        <div className="encabezado-seccion">
          <div>
            <span className="sobretitulo">{en ? "Voices from the destination" : "Voces del destino"}</span>
            <h2>{en ? "What a trip with SierraMar feels like" : "Así se siente viajar con SierraMar"}</h2>
            <p className="tenue">{en ? "Illustrative examples for this demo." : "Ejemplos ilustrativos de esta demo."}</p>
          </div>
        </div>
        <div className="rejilla">
          {TESTIMONIOS.map((t) => (
            <figure key={t.nombre} className="testimonio aparece" data-tilt="">
              <span className="comillas" aria-hidden="true">“</span>
              <blockquote>{en ? t.en : t.es}</blockquote>
              <figcaption>
                <img src={foto(t.foto)} alt="" loading="lazy" />
                <span><b>{t.nombre}</b><small>{t.experiencia} · ★★★★★</small></span>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="seccion pilares aparece">
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
