import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useIdioma } from "../idioma";
import { Aviso } from "../ui";

// Buzón de la demo: Mailpit en local (puerto 8025) o detrás del gateway en la nube (/correo/).
const BUZON = location.hostname === "localhost" ? "http://localhost:8025" : "/correo/";

export default function Registro() {
  const { t } = useIdioma();
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
    <div style={{ maxWidth: 460, margin: "0 auto" }} className="pila">
      <h1>{t("registro")}</h1>
      <form className="tarjeta formulario" onSubmit={enviar}>
        <label>{t("correo")}<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>{t("clave")}<input type="password" required minLength={8} value={clave} onChange={(e) => setClave(e.target.value)} /></label>
        <label>{t("rol")}
          <select value={rol} onChange={(e) => setRol(e.target.value as "turista" | "prestador")}>
            <option value="turista">{t("turista")}</option>
            <option value="prestador">{t("prestador")}</option>
          </select>
        </label>
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
        <button disabled={!consentimiento}>{t("registro")}</button>
        <Link to="/entrar">{t("entrar")}</Link>
      </form>
    </div>
  );
}
