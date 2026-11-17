import { useState } from "react";
import { Link } from "react-router-dom";
import { api, INTERESES, type ItemRecomendado, type Oferta, type Recomendacion, type Zona } from "../api";
import { useIdioma } from "../idioma";
import { Aviso, Estado, Insignia, useCarga } from "../ui";

const NIVEL: Record<string, "ok" | "alerta" | "peligro" | "neutro"> = {
  tranquila: "ok", moderada: "alerta", muy_concurrida: "peligro", desconocida: "neutro",
};

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

export default function Inicio() {
  const { t, idioma } = useIdioma();
  const [intereses, setIntereses] = useState<string[]>(["naturaleza"]);
  const [zona, setZona] = useState("");
  const [categoria, setCategoria] = useState("");

  const zonas = useCarga(() => api<Zona[]>("/api/v1/catalogo/zonas"));
  const recomendacion = useCarga(
    () => api<Recomendacion>("/api/v1/ia/recomendaciones", { query: { intereses: intereses.join(","), limite: 6, idioma } }),
    [intereses.join(","), idioma],
  );
  const catalogo = useCarga(
    () => api<{ items: Oferta[]; total: number }>("/api/v1/catalogo/ofertas", {
      query: { zona_codigo: zona, categoria, limit: 50, idioma },
    }),
    [zona, categoria, idioma],
  );
  const nombreZona = (id: string) => {
    const z = zonas.datos?.find((x) => x.id === id);
    return z ? (idioma === "en" ? z.nombre_en : z.nombre_es) : "";
  };
  const alternar = (i: string) =>
    setIntereses((act) => (act.includes(i) ? act.filter((x) => x !== i) : [...act, i]));

  return (
    <>
      <section className="heroe">
        <h1>{t("lema")}</h1>
        <p>{t("subtitulo")}</p>
      </section>

      <section>
        <h2>{t("paraTi")}</h2>
        <p className="tenue">{t("intereses")}</p>
        <div className="chips" style={{ marginBottom: "1rem" }}>
          {INTERESES.map((i) => (
            <button key={i} className="chip" aria-pressed={intereses.includes(i)} onClick={() => alternar(i)}>{i}</button>
          ))}
        </div>
        <Estado carga={recomendacion}>
          {(r) => r.items.length === 0
            ? <Aviso>{t("vacio")}</Aviso>
            : <div className="rejilla">{r.items.map((it) => <TarjetaRecomendada key={it.oferta_id} item={it} />)}</div>}
        </Estado>
      </section>

      <section>
        <h2>{t("catalogo")}</h2>
        <div className="fila" style={{ marginBottom: "1rem" }}>
          <select value={zona} onChange={(e) => setZona(e.target.value)} aria-label={t("zona")}>
            <option value="">{t("todasZonas")}</option>
            {zonas.datos?.map((z) => <option key={z.id} value={z.codigo}>{idioma === "en" ? z.nombre_en : z.nombre_es}</option>)}
          </select>
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)} aria-label="Categoría">
            <option value="">{t("todasCategorias")}</option>
            {INTERESES.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>
        <Estado carga={catalogo}>
          {(c) => c.items.length === 0 ? <Aviso>{t("vacio")}</Aviso> : (
            <div className="rejilla">
              {c.items.map((o) => (
                <article key={o.id} className="tarjeta pila">
                  <h3 style={{ margin: 0 }}>{idioma === "en" ? o.nombre_en : o.nombre_es}</h3>
                  <div className="fila">
                    <Insignia>{nombreZona(o.zona_id)}</Insignia>
                    {(o.atributos.categorias ?? []).map((cat) => <Insignia key={cat}>{cat}</Insignia>)}
                  </div>
                  <p className="tenue" style={{ margin: 0 }}>{idioma === "en" ? o.descripcion_en : o.descripcion_es}</p>
                  <div className="fila entre">
                    <span>★ {o.calificacion_promedio.toFixed(1)} <small className="tenue">({o.total_calificaciones})</small></span>
                    <Link className="boton-secundario" to={`/ofertas/${o.id}`}>{t("verDetalle")}</Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </Estado>
      </section>
    </>
  );
}
