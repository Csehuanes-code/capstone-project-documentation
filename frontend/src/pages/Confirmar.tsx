import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useIdioma } from "../idioma";
import { Aviso } from "../ui";

/** Destino del enlace del correo de confirmación (Auth → RabbitMQ → Reservas → correo). */
export default function Confirmar() {
  const { t } = useIdioma();
  const [params] = useSearchParams();
  const [estado, setEstado] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const enviado = useRef(false);

  useEffect(() => {
    if (enviado.current) return; // el enlace es de un solo uso: no reenviar en StrictMode
    enviado.current = true;
    api("/api/v1/auth/confirmaciones", { method: "POST", body: { token: params.get("token") ?? "" } })
      .then(() => setEstado({ tipo: "ok", texto: t("cuentaConfirmada") }))
      .catch((e: Error) => setEstado({ tipo: "error", texto: e.message }));
  }, [params, t]);

  return (
    <div style={{ maxWidth: 460, margin: "0 auto" }} className="pila">
      <h1>{t("registro")}</h1>
      {estado ? <Aviso tipo={estado.tipo}>{estado.texto}</Aviso> : <p className="tenue">{t("cargando")}</p>}
      {estado?.tipo === "ok" && <Link className="boton" to="/entrar">{t("entrar")}</Link>}
    </div>
  );
}
