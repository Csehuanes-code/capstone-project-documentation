import { CREDITOS, foto, type ClaveFoto } from "../fotos";
import { useIdioma } from "../idioma";

/** Atribución de las fotos (las licencias CC BY y CC BY-SA la exigen). */
export default function Creditos() {
  const { idioma } = useIdioma();
  const en = idioma === "en";
  const lista = Object.entries(CREDITOS) as [ClaveFoto, (typeof CREDITOS)[ClaveFoto]][];
  return (
    <div className="apilado">
      <div>
        <span className="sobretitulo">{en ? "Photo credits" : "Créditos fotográficos"}</span>
        <h1 style={{ marginTop: ".6rem" }}>{en ? "The photographers behind SierraMar" : "Quién tomó estas fotos"}</h1>
        <p className="tenue" style={{ maxWidth: "62ch", margin: 0 }}>{en
          ? "All photos come from Wikimedia Commons under free licenses. They were resized and converted to WebP; no other changes were made."
          : "Todas las fotos vienen de Wikimedia Commons con licencias libres. Se redimensionaron y se convirtieron a WebP, sin otros cambios."}</p>
      </div>
      <div className="creditos">
        {lista.map(([clave, c]) => (
          <figure key={clave}>
            <img src={foto(clave)} alt={c.archivo} loading="lazy" />
            <figcaption>
              <strong>{c.autor || (en ? "Unknown author" : "Autor desconocido")}</strong>
              <span className="tenue">
                {c.url_licencia ? <a href={c.url_licencia} target="_blank" rel="noreferrer">{c.licencia}</a> : c.licencia}
                {" · "}<a href={c.pagina} target="_blank" rel="noreferrer">Wikimedia Commons</a>
              </span>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}
