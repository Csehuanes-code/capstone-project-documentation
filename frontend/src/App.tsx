import { Link, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import type { Rol } from "./api";
import { Isotipo } from "./ilustraciones";
import { useIdioma } from "./idioma";
import { useSesion } from "./sesion";
import Inicio from "./pages/Inicio";
import DetalleOferta from "./pages/DetalleOferta";
import ComprobantePagina from "./pages/Comprobante";
import MisReservas from "./pages/MisReservas";
import Entrar from "./pages/Entrar";
import Registro from "./pages/Registro";
import Confirmar from "./pages/Confirmar";
import Prestador from "./pages/Prestador";
import Admin from "./pages/Admin";

function Protegida({ rol, children }: { rol?: Rol; children: ReactNode }) {
  const { usuario } = useSesion();
  if (!usuario) return <Navigate to="/entrar" replace />;
  if (rol && usuario.rol !== rol) return <Navigate to="/" replace />;
  return <>{children}</>;
}

interface EventoInstalacion extends Event { prompt: () => Promise<void> }

/** Botón "Instalar app": aparece cuando el navegador permite instalar la PWA. */
function useInstalacion() {
  const [evento, setEvento] = useState<EventoInstalacion | null>(null);
  useEffect(() => {
    const guardar = (e: Event) => { e.preventDefault(); setEvento(e as EventoInstalacion); };
    window.addEventListener("beforeinstallprompt", guardar);
    return () => window.removeEventListener("beforeinstallprompt", guardar);
  }, []);
  return evento ? () => { evento.prompt(); setEvento(null); } : null;
}

export default function App() {
  const { usuario, salir } = useSesion();
  const { t, idioma, cambiar } = useIdioma();
  const navegar = useNavigate();
  const instalar = useInstalacion();
  const en = idioma === "en";
  return (
    <>
      <div className="aviso-superior">
        <div className="contenedor">
          <span><b>{en ? "SUSTAINABLE TOURISM" : "TURISMO SOSTENIBLE"}</b> · {en
            ? "Verified operators · real availability · no overbooking"
            : "Prestadores verificados · cupos reales · sin sobreventa"}</span>
          <span>{en ? "Santa Marta, Colombia" : "Santa Marta, Colombia"}</span>
        </div>
      </div>
      <header className="cabecera">
        <div className="contenedor cabecera-fila">
          <Link to="/" className="marca" aria-label="SierraMar, inicio">
            <Isotipo tam={42} />
            <span>
              <span className="marca-nombre">Sierra<span>Mar</span></span>
              <span className="marca-lema">{en ? "Sustainable tourism" : "Turismo sostenible"}</span>
            </span>
          </Link>
          <nav className="menu" aria-label="Principal">
            <NavLink to="/" end>{t("explorar")}</NavLink>
            {usuario?.rol === "turista" && <NavLink to="/mis-reservas">{t("misReservas")}</NavLink>}
            {usuario?.rol === "prestador" && <NavLink to="/prestador">{t("panel")}</NavLink>}
            {usuario?.rol === "administrador" && <NavLink to="/admin">{t("admin")}</NavLink>}
          </nav>
          <div className="acciones">
            <div className="segmento" role="group" aria-label="Idioma / Language">
              <button aria-pressed={!en} onClick={() => en && cambiar()}>ES</button>
              <button aria-pressed={en} onClick={() => !en && cambiar()}>EN</button>
            </div>
            {instalar && <button className="boton-secundario" onClick={instalar}>⤓ {en ? "Install app" : "Instalar app"}</button>}
            {usuario ? (
              <>
                <span className="usuario" title={usuario.email}>{usuario.email || usuario.rol}</span>
                <button className="boton-texto" onClick={() => { salir(); navegar("/"); }}>{t("salir")}</button>
              </>
            ) : (
              <>
                <Link className="boton-texto" to="/entrar">{t("entrar")}</Link>
                <Link className="boton" to="/registro">{t("registro")}</Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="contenedor principal">
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/ofertas/:id" element={<DetalleOferta />} />
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/confirmar" element={<Confirmar />} />
          <Route path="/reservas/:id" element={<Protegida><ComprobantePagina /></Protegida>} />
          <Route path="/mis-reservas" element={<Protegida rol="turista"><MisReservas /></Protegida>} />
          <Route path="/prestador" element={<Protegida rol="prestador"><Prestador /></Protegida>} />
          <Route path="/admin" element={<Protegida rol="administrador"><Admin /></Protegida>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="pie">
        <div className="contenedor">
          <div>
            <b>SierraMar</b>
            <p style={{ margin: ".4rem 0 0", maxWidth: 420 }}>
              {en
                ? "Digital platform for integrated and sustainable tourism management in Santa Marta."
                : "Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta."}
            </p>
          </div>
          <div>
            Universidad del Magdalena · Ingeniería de Sistemas<br />
            Arquitectura de Software 2026-II · Grupo 4
          </div>
        </div>
      </footer>
    </>
  );
}
