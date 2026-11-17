import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso } from "../ui";

const DEMO = [
  { rol: "Turista", email: "turista@turismo.co", clave: "Turista-Demo-2026" },
  { rol: "Prestador", email: "prestador@turismo.co", clave: "Prestador-Demo-2026" },
  { rol: "Administrador", email: "admin@turismo.co", clave: "Admin-Demo-2026" },
];

export default function Entrar() {
  const { t } = useIdioma();
  const { entrar } = useSesion();
  const navegar = useNavigate();
  const [email, setEmail] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const u = await entrar(email, clave);
      navegar(u.rol === "prestador" ? "/prestador" : u.rol === "administrador" ? "/admin" : "/");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: "0 auto" }} className="pila">
      <h1>{t("entrar")}</h1>
      <form className="tarjeta formulario" onSubmit={enviar}>
        <label>{t("correo")}<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>{t("clave")}<input type="password" autoComplete="current-password" required value={clave} onChange={(e) => setClave(e.target.value)} /></label>
        {error && <Aviso tipo="error">{error}</Aviso>}
        <button>{t("entrar")}</button>
        <Link to="/registro">{t("registro")}</Link>
      </form>
      <div className="tarjeta pila">
        <strong>Cuentas de demostración</strong>
        {DEMO.map((d) => (
          <button key={d.email} className="boton-secundario" onClick={() => { setEmail(d.email); setClave(d.clave); }}>
            {d.rol}: {d.email}
          </button>
        ))}
      </div>
    </div>
  );
}
