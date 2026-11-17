import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, INTERESES, pesos, type DetalleOferta, type ItemRecomendado, type Oferta, type Recomendacion, type Zona } from "../api";
import { Paisaje, Portada } from "../ilustraciones";
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

interface Popular { oferta_id: string; zona: { nivel: string; ocupacion: number | null }; reservas_confirmadas: number }
interface OfertaEnriquecida extends Oferta { desde: number | null; moneda: string }

function TarjetaRecomendada({ item }: { item: ItemRecomendado }) {
  const { t } = useIdioma();
  return (
    <article className="tarjeta pila">
      <div className="fila entre">
        <h3 style={{ margin: 0 }}>{item.nombre}</h3>
        <span className="puntaje" title="Puntaje">{item.puntaje.toFixed(2)}</span>
      </div>
      <div className="fila">
        <Insignia tono={NIVEL[item.zona.nivel] ?? "neutro"}>
          {item.zona.nombre ?? item.zona.id}
          {item.zona.ocupacion != null && ` · ${Math.round(item.zona.ocupacion * 100)}%`}
        </Insignia>
        {item.motivo === "alternativa_descongestion" && <Insignia tono="alerta">{t("alternativa")}</Insignia>}
      </div>
      <p className="tenue" style={{ margin: 0 }}>{item.explicacion}</p>
      <details>
        <summary>{t("porQue")}</summary>
        <div className="pila" style={{ marginTop: ".6rem" }}>
          {item.desglose.map((a) => (
            <div key={a.criterio}>
              <div className="fila entre"><span>{a.etiqueta}</span><strong>+{a.aporte.toFixed(2)}</strong></div>
              <div className="barra"><span style={{ width: `${Math.round(a.valor * 100)}%` }} /></div>
              <small className="tenue">peso {a.peso} × valor {a.valor.toFixed(2)}</small>
            </div>
          ))}
          {item.alternativa_de && (
            <small className="tenue">Reemplaza a «{item.alternativa_de.nombre}», en una zona saturada.</small>
          )}
        </div>
      </details>
      <Link className="boton-secundario" to={`/ofertas/${item.oferta_id}`}>{t("verDetalle")}</Link>
    </article>
  );
}

function TarjetaOferta({ o, zona, aforo }: { o: OfertaEnriquecida; zona?: Zona; aforo?: Popular }) {
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const categoria = o.atributos.categorias?.[0];
  const nivel = aforo?.zona.nivel;
  return (
    <Link to={`/ofertas/${o.id}`} className="tarjeta oferta" style={{ textDecoration: "none", color: "inherit" }}>
      <div className="oferta-imagen">
        <Portada categoria={categoria} alto={190} />
        <div className="etiquetas">
          {categoria && <span>{en ? CATEGORIA_EN[categoria] ?? categoria : categoria}</span>}
          <span className="estrella">★ {o.total_calificaciones ? o.calificacion_promedio.toFixed(1) : (en ? "New" : "Nuevo")}</span>
        </div>
        {nivel && NIVEL_TEXTO[nivel] && (
          <span className="aforo"><Insignia tono={NIVEL[nivel]}>{NIVEL_TEXTO[nivel][en ? 1 : 0]}</Insignia></span>
        )}
      </div>
      <div className="oferta-cuerpo">
        <span className="verificado">
          ✓ {en ? "Verified operator" : "Prestador verificado"}{zona && <span className="tenue"> · {en ? zona.nombre_en : zona.nombre_es}</span>}
        </span>
        <h3>{en ? o.nombre_en : o.nombre_es}</h3>
        <p className="tenue" style={{ margin: 0 }}>{en ? o.descripcion_en : o.descripcion_es}</p>
        <div className="oferta-pie">
          <div>
            <div className="tarifa-etq">{en ? "From" : "Desde"}</div>
            <div className="tarifa">{o.desde != null ? pesos(o.desde, o.moneda) : "—"}</div>
            <small className="tenue">{t("porPersona")}</small>
          </div>
          <span className="boton">{t("verDetalle")}</span>
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
  const [texto, setTexto] = useState("");
  const [busqueda, setBusqueda] = useState("");

  const zonas = useCarga(() => api<Zona[]>("/api/v1/catalogo/zonas"));
  const aforos = useCarga(() => api<Popular[]>("/api/v1/ia/populares", { query: { limite: 20 } }).catch(() => [] as Popular[])); // 20 = máximo que acepta IA
  const recomendacion = useCarga(
    () => api<Recomendacion>("/api/v1/ia/recomendaciones", { query: { intereses: intereses.join(","), limite: 6, idioma } }),
    [intereses.join(","), idioma],
  );
  // El catálogo no trae la tarifa en el listado: se completa con el detalle de cada oferta.
  const catalogo = useCarga(async () => {
    const r = await api<{ items: Oferta[]; total: number }>("/api/v1/catalogo/ofertas", { query: { categoria, limit: 50, idioma } });
    return Promise.all(r.items.map(async (o): Promise<OfertaEnriquecida> => {
      try {
        const d = await api<DetalleOferta>(`/api/v1/catalogo/ofertas/${o.id}`);
        const precios = d.tarifas.map((x) => Number(x.precio_por_persona));
        return { ...o, desde: precios.length ? Math.min(...precios) : null, moneda: d.tarifas[0]?.moneda ?? "COP" };
      } catch {
        return { ...o, desde: null, moneda: "COP" };
      }
    }));
  }, [categoria, idioma]);

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return (catalogo.datos ?? []).filter((o) =>
      !q || [o.nombre_es, o.nombre_en, o.descripcion_es, o.descripcion_en].join(" ").toLowerCase().includes(q));
  }, [catalogo.datos, busqueda]);

  const zonaPorId = (id: string) => zonas.datos?.find((z) => z.id === id);
  const aforoDe = (id: string) => aforos.datos?.find((a) => a.oferta_id === id);
  const alternar = (i: string) => setIntereses((act) => (act.includes(i) ? act.filter((x) => x !== i) : [...act, i]));
  const reservasTotales = (aforos.datos ?? []).reduce((s, a) => s + a.reservas_confirmadas, 0);

  return (
    <>
      <section className="heroe">
        <Paisaje />
        <div className="heroe-contenido">
          <span className="pildora">● {en ? "Sustainable tourism · Santa Marta" : "Turismo sostenible · Santa Marta"}</span>
          <h1>{en ? "Where the Sierra Nevada meets the Caribbean" : "Donde la Sierra Nevada se encuentra con el Caribe"}</h1>
          <p>{t("subtitulo")}</p>
          <form className="buscador" onSubmit={(e) => { e.preventDefault(); setBusqueda(texto);
            document.getElementById("catalogo")?.scrollIntoView({ behavior: "smooth" }); }}>
            <label>{en ? "What are you looking for?" : "¿Qué buscas?"}
              <input value={texto} onChange={(e) => setTexto(e.target.value)}
                placeholder={en ? "Hike, diving, cooking…" : "Caminata, buceo, cocina…"} />
            </label>
            <button className="boton-grande">{en ? "Discover" : "Descubrir"}</button>
          </form>
          <div className="cifras">
            <div><b>{catalogo.datos?.length ?? "—"}</b>{en ? "experiences" : "experiencias"}</div>
            <div><b>{zonas.datos?.length ?? "—"}</b>{en ? "areas" : "zonas"}</div>
            <div><b>{reservasTotales}</b>{en ? "confirmed bookings" : "reservas confirmadas"}</div>
          </div>
        </div>
      </section>

      <section className="ia">
        <span className="sobretitulo">{en ? "Explainable AI" : "IA explicable"}</span>
        <h2>{t("paraTi")}</h2>
        <p style={{ opacity: .85, marginTop: 0 }}>{t("intereses")}</p>
        <div className="chips" style={{ marginBottom: "1.2rem" }}>
          {INTERESES.map((i) => (
            <button key={i} className="chip" aria-pressed={intereses.includes(i)} onClick={() => alternar(i)}>
              {en ? CATEGORIA_EN[i] : i}
            </button>
          ))}
        </div>
        <Estado carga={recomendacion}>
          {(r) => r.items.length === 0
            ? <Aviso>{t("vacio")}</Aviso>
            : <div className="rejilla">{r.items.map((it) => <TarjetaRecomendada key={it.oferta_id} item={it} />)}</div>}
        </Estado>
      </section>

      <section id="catalogo">
        <div className="encabezado-seccion">
          <div>
            <span className="sobretitulo">{en ? "Authentic experiences" : "Turismo vivencial auténtico"}</span>
            <h2>{en ? "Experience explorer" : "Explorador de experiencias"}</h2>
            <p className="tenue" style={{ margin: ".4rem 0 0", maxWidth: 560 }}>
              {en ? "Every service is published by an operator verified with the National Tourism Registry."
                : "Cada servicio lo publica un prestador verificado con el Registro Nacional de Turismo."}
            </p>
          </div>
          {busqueda && <button className="boton-texto" onClick={() => { setBusqueda(""); setTexto(""); }}>✕ «{busqueda}»</button>}
        </div>
        <div className="chips" style={{ marginBottom: "1.4rem" }}>
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
    </>
  );
}
