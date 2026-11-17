import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { foto } from "../fotos";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso } from "../ui";

// Cuentas públicas de la demo. La del administrador no va aquí: su clave cambia en cada despliegue.
const DEMO = [
  { rol: ["Turista", "Tourist"], email: "turista@turismo.co", clave: "Turista-Demo-2026" },
  { rol: ["Prestador", "Operator"], email: "prestador@turismo.co", clave: "Prestador-Demo-2026" },
];

export default function Entrar() {
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const { entrar } = useSesion();
  const navegar = useNavigate();
  const [email, setEmail] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try {
      const u = await entrar(email, clave);
      navegar(u.rol === "prestador" ? "/prestador" : u.rol === "administrador" ? "/admin" : "/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="acceso">
      <div className="acceso-foto">
        <img src={foto("atardecer")} alt={en ? "Sunset over Santa Marta bay" : "Atardecer en la bahía de Santa Marta"} />
        <blockquote>
          {en ? "The sunset over El Morro is waiting for you." : "El atardecer sobre El Morro te está esperando."}
          <cite>{en ? "Santa Marta bay" : "Bahía de Santa Marta"}</cite>
        </blockquote>
      </div>
      <div className="acceso-formulario">
        <div>
          <span className="sobretitulo">{en ? "Welcome back" : "Bienvenido de nuevo"}</span>
          <h1 style={{ marginTop: ".6rem" }}>{t("entrar")}</h1>
        </div>
        <form className="formulario" onSubmit={enviar}>
          <label>{t("correo")}<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="tu@correo.co" /></label>
          <label>{t("clave")}<input type="password" autoComplete="current-password" required value={clave} onChange={(e) => setClave(e.target.value)} /></label>
          {error && <Aviso tipo="error">{error}</Aviso>}
          <button className="boton-grande" disabled={enviando}>{enviando ? t("cargando") : t("entrar")}</button>
          <p className="tenue" style={{ margin: 0 }}>{en ? "New here?" : "¿Primera vez?"} <Link to="/registro">{t("registro")}</Link></p>
        </form>
        <div className="demo-cuentas">
          <span className="tarifa-etq">{en ? "Demo accounts" : "Cuentas de demostración"}</span>
          {DEMO.map((d) => (
            <button key={d.email} type="button" onClick={() => { setEmail(d.email); setClave(d.clave); }}>
              <strong>{d.rol[en ? 1 : 0]}</strong><span>{d.email}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
