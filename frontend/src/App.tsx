import { Link, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import type { Rol } from "./api";
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

export default function App() {
  const { usuario, salir } = useSesion();
  const { t, idioma, cambiar } = useIdioma();
  const navegar = useNavigate();
  return (
    <>
      <header className="cabecera">
        <div className="contenedor cabecera-fila">
          <Link to="/" className="marca">
            <img src="/icono.svg" alt="" width={32} height={32} />
            <span>Turismo Santa Marta</span>
          </Link>
          <nav className="menu">
            <NavLink to="/" end>{t("explorar")}</NavLink>
            {usuario?.rol === "turista" && <NavLink to="/mis-reservas">{t("misReservas")}</NavLink>}
            {usuario?.rol === "prestador" && <NavLink to="/prestador">{t("panel")}</NavLink>}
            {usuario?.rol === "administrador" && <NavLink to="/admin">{t("admin")}</NavLink>}
          </nav>
          <div className="acciones">
            <button className="boton-texto" onClick={cambiar} aria-label="Idioma / Language">
              {idioma === "es" ? "EN" : "ES"}
            </button>
            {usuario ? (
              <>
                <span className="usuario" title={usuario.email}>{usuario.email || usuario.rol}</span>
                <button className="boton-secundario" onClick={() => { salir(); navegar("/"); }}>{t("salir")}</button>
              </>
            ) : (
              <Link className="boton" to="/entrar">{t("entrar")}</Link>
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
      <footer className="pie contenedor">
        Grupo 4 · Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta
      </footer>
    </>
  );
}
