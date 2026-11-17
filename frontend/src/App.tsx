import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import type { Rol } from "./api";
import { Icono, Isotipo } from "./ilustraciones";
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
import Creditos from "./pages/Creditos";

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

/** En la portada la cabecera va transparente sobre la foto hasta que el usuario baja. */
function useSobreFoto(activo: boolean) {
  const [arriba, setArriba] = useState(true);
  useEffect(() => {
    if (!activo) return;
    const revisar = () => setArriba(window.scrollY < 80);
    revisar();
    window.addEventListener("scroll", revisar, { passive: true });
    return () => window.removeEventListener("scroll", revisar);
  }, [activo]);
  return activo && arriba;
}

export default function App() {
  const { usuario, salir } = useSesion();
  const { t, idioma, cambiar } = useIdioma();
  const navegar = useNavigate();
  const { pathname } = useLocation();
  const instalar = useInstalacion();
  const enInicio = pathname === "/";
  const sobreFoto = useSobreFoto(enInicio);
  const en = idioma === "en";
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);

  const panel = usuario?.rol === "turista" ? { to: "/mis-reservas", texto: t("misReservas"), icono: "ticket" as const }
    : usuario?.rol === "prestador" ? { to: "/prestador", texto: t("panel"), icono: "panel" as const }
    : usuario?.rol === "administrador" ? { to: "/admin", texto: t("admin"), icono: "panel" as const } : null;

  return (
    <>
      <header className={`cabecera${sobreFoto ? " sobre-foto" : ""}`}>
        <div className="contenedor cabecera-fila">
          <Link to="/" className="marca" aria-label="SierraMar, inicio">
            <Isotipo tam={40} />
            <span>
              <span className="marca-nombre">Sierra<span>Mar</span></span>
              <span className="marca-lema">{en ? "Sustainable tourism · Santa Marta" : "Turismo sostenible · Santa Marta"}</span>
            </span>
          </Link>
          <nav className="menu" aria-label="Principal">
            <NavLink to="/" end>{t("explorar")}</NavLink>
            <a href="/#destinos">{en ? "Destinations" : "Destinos"}</a>
            <a href="/#para-ti">{t("paraTi")}</a>
            {panel && <NavLink to={panel.to}>{panel.texto}</NavLink>}
          </nav>
          <div className="acciones">
            <div className="segmento" role="group" aria-label="Idioma / Language">
              <button aria-pressed={!en} onClick={() => en && cambiar()}>ES</button>
              <button aria-pressed={en} onClick={() => !en && cambiar()}>EN</button>
            </div>
            {instalar && <button className="boton-texto" onClick={instalar} title={en ? "Install app" : "Instalar app"}>⤓</button>}
            {usuario ? (
              <>
                <span className="usuario" title={usuario.email}>
                  <span className="avatar">{(usuario.email || usuario.rol).charAt(0).toUpperCase()}</span>
                  <span className="correo-usuario">{usuario.email || usuario.rol}</span>
                </span>
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

      <main className={`contenedor principal${enInicio ? " inicio" : ""}`}>
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/ofertas/:id" element={<DetalleOferta />} />
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/confirmar" element={<Confirmar />} />
          <Route path="/creditos" element={<Creditos />} />
          <Route path="/reservas/:id" element={<Protegida><ComprobantePagina /></Protegida>} />
          <Route path="/mis-reservas" element={<Protegida rol="turista"><MisReservas /></Protegida>} />
          <Route path="/prestador" element={<Protegida rol="prestador"><Prestador /></Protegida>} />
          <Route path="/admin" element={<Protegida rol="administrador"><Admin /></Protegida>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <nav className="barra-movil" aria-label={en ? "Quick navigation" : "Navegación rápida"}>
        <NavLink to="/" end><Icono n="brujula" />{t("explorar")}</NavLink>
        {panel
          ? <NavLink to={panel.to}><Icono n={panel.icono} />{panel.texto}</NavLink>
          : <NavLink to="/entrar"><Icono n="persona" />{t("entrar")}</NavLink>}
      </nav>

      <footer className="pie">
        <div className="contenedor pie-columnas">
          <div>
            <Link to="/" className="marca"><Isotipo tam={36} /><span className="marca-nombre">Sierra<span>Mar</span></span></Link>
            <p>{en
              ? "Digital platform for integrated and sustainable tourism management in Santa Marta. Verified operators, real availability and load capacity per area."
              : "Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta. Prestadores verificados, cupos reales y capacidad de carga por zona."}</p>
          </div>
          <div>
            <h4>{en ? "Explore" : "Explora"}</h4>
            <ul>
              <li><a href="/#destinos">{en ? "Destinations" : "Destinos"}</a></li>
              <li><a href="/#para-ti">{en ? "Recommended for you" : "Recomendado para ti"}</a></li>
              <li><a href="/#catalogo">{en ? "All experiences" : "Todas las experiencias"}</a></li>
            </ul>
          </div>
          <div>
            <h4>{en ? "Operators" : "Prestadores"}</h4>
            <ul>
              <li><Link to="/registro">{en ? "Publish your experience" : "Publica tu experiencia"}</Link></li>
              <li><Link to="/entrar">{t("entrar")}</Link></li>
            </ul>
          </div>
          <div>
            <h4>{en ? "Project" : "Proyecto"}</h4>
            <ul>
              <li>Universidad del Magdalena</li>
              <li>{en ? "Systems Engineering" : "Ingeniería de Sistemas"}</li>
              <li>{en ? "Software Architecture 2026-II · Group 4" : "Arquitectura de Software 2026-II · Grupo 4"}</li>
            </ul>
          </div>
        </div>
        <div className="contenedor pie-final">
          <span>© 2026 SierraMar · Santa Marta, Colombia</span>
          <Link to="/creditos">{en ? "Photo credits" : "Créditos fotográficos"}</Link>
        </div>
      </footer>
    </>
  );
}
