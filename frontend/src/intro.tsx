// Intro de bienvenida (estilo video corto, ~7 s): se muestra la primera vez que alguien entra a la portada.
// Es animación CSS sobre las fotos reales de la demo: carga al instante y funciona sin conexión.
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { foto, type ClaveFoto } from "./fotos";
import { Isotipo } from "./ilustraciones";
import { useIdioma } from "./idioma";

const DURACION = 7200; // ms hasta que se abre el telón
const FOTOS: ClaveFoto[] = ["heroe", "minca-cascada", "atardecer"];

export function yaVioIntro() {
  try { return localStorage.getItem("intro-vista") === "1"; } catch { return true; }
}

export default function Intro({ alTerminar }: { alTerminar: () => void }) {
  const { idioma } = useIdioma();
  const en = idioma === "en";
  const [saliendo, setSaliendo] = useState(false);

  const cerrar = () => {
    if (saliendo) return;
    setSaliendo(true);
    try { localStorage.setItem("intro-vista", "1"); } catch { /* modo privado */ }
    setTimeout(alTerminar, 750);
  };

  useEffect(() => {
    const t = setTimeout(cerrar, DURACION);
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape" || e.key === "Enter" || e.key === " ") cerrar(); };
    window.addEventListener("keydown", tecla);
    const previo = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { clearTimeout(t); window.removeEventListener("keydown", tecla); document.body.style.overflow = previo; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const lema = en ? "From the Caribbean to the Sierra Nevada" : "Del Caribe a la Sierra Nevada";
  return createPortal(
    <div className={`intro${saliendo ? " intro-sale" : ""}`} role="dialog" aria-modal="true" aria-label={en ? "Welcome to SierraMar" : "Bienvenida a SierraMar"}>
      {FOTOS.map((f, i) => <img key={f} src={foto(f)} alt="" className={`intro-foto intro-foto-${i + 1}`} />)}
      <div className="intro-velo" aria-hidden="true" />

      <div className="intro-escena intro-escena-1">
        <span className="intro-pequeno">{en ? "Welcome to" : "Bienvenido a"}</span>
        <span className="intro-lugar">Santa Marta</span>
      </div>

      <div className="intro-escena intro-escena-2">
        <span className="intro-logo"><Isotipo tam={88} /></span>
        <span className="intro-marca" aria-label="SierraMar">
          {"SierraMar".split("").map((l, i) => (
            <span key={i} className={i >= 6 ? "mar" : undefined} style={{ animationDelay: `${2.75 + i * 0.07}s` }}>{l}</span>
          ))}
        </span>
      </div>

      <div className="intro-escena intro-escena-3">
        <span className="intro-lema">{lema}</span>
        <span className="intro-sub">{en ? "travel while caring for the destination" : "viaja cuidando el destino"}</span>
      </div>

      <button type="button" className="intro-saltar" onClick={cerrar}>{en ? "Skip intro" : "Saltar intro"} →</button>
      <i className="intro-progreso" aria-hidden="true" />
    </div>,
    document.body,
  );
}
