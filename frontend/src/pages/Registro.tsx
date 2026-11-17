import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { foto } from "../fotos";
import { useIdioma } from "../idioma";
import { Aviso } from "../ui";

// Buzón de la demo: Mailpit en local (puerto 8025) o detrás del gateway en la nube (/correo/).
const BUZON = location.hostname === "localhost" ? "http://localhost:8025" : "/correo/";

export default function Registro() {
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const [email, setEmail] = useState("");
  const [clave, setClave] = useState("");
  const [rol, setRol] = useState<"turista" | "prestador">("turista");
  const [consentimiento, setConsentimiento] = useState(false);
  const [estado, setEstado] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEstado(null);
    try {
      await api("/api/v1/auth/usuarios", {
        method: "POST",
        body: { email, password: clave, role: rol, consent_accepted: consentimiento, policy_version: "2026-01" },
      });
      setEstado({ tipo: "ok", texto: t("revisaCorreo") });
    } catch (err) {
      setEstado({ tipo: "error", texto: (err as Error).message });
    }
  }

  return (
    <div className="acceso">
      <div className="acceso-foto">
        <img src={foto(rol === "prestador" ? "pueblito" : "sierra")} alt="" />
        <blockquote>
          {rol === "prestador"
            ? (en ? "Share your territory with travellers who respect it." : "Comparte tu territorio con viajeros que lo respetan.")
            : (en ? "From the snowy peaks to the Caribbean, in one trip." : "De los picos nevados al Caribe, en un solo viaje.")}
          <cite>{rol === "prestador" ? "Pueblito Chairama, Tayrona" : "Sierra Nevada de Santa Marta"}</cite>
        </blockquote>
      </div>
      <div className="acceso-formulario">
        <div>
          <span className="sobretitulo">{en ? "Join SierraMar" : "Únete a SierraMar"}</span>
          <h1 style={{ marginTop: ".6rem" }}>{t("registro")}</h1>
        </div>
        <form className="formulario" onSubmit={enviar}>
          <div className="chips" role="group" aria-label={t("rol")}>
            <button type="button" className="chip" aria-pressed={rol === "turista"} onClick={() => setRol("turista")}>{t("turista")}</button>
            <button type="button" className="chip" aria-pressed={rol === "prestador"} onClick={() => setRol("prestador")}>{t("prestador")}</button>
          </div>
          <label>{t("correo")}<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="tu@correo.co" /></label>
          <label>{t("clave")}<input type="password" required minLength={8} value={clave} onChange={(e) => setClave(e.target.value)} placeholder={en ? "At least 8 characters" : "Mínimo 8 caracteres"} /></label>
          <label className="casilla">
            <input type="checkbox" checked={consentimiento} onChange={(e) => setConsentimiento(e.target.checked)} />
            {t("consentimiento")}
          </label>
          {estado && (
            <Aviso tipo={estado.tipo}>
              {estado.texto}
              {estado.tipo === "ok" && <> <a href={BUZON} target="_blank" rel="noreferrer">{BUZON}</a></>}
            </Aviso>
          )}
          <button className="boton-grande" disabled={!consentimiento}>{t("registro")}</button>
          <p className="tenue" style={{ margin: 0 }}>{en ? "Already have an account?" : "¿Ya tienes cuenta?"} <Link to="/entrar">{t("entrar")}</Link></p>
        </form>
      </div>
    </div>
  );
}
