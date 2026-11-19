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
import Arquitectura from "./pages/Arquitectura";
import { BotonTema, useRecordatorios } from "./extras";
import { Toasts } from "./ui";
import Intro, { yaVioIntro } from "./intro";

/** Tarjetas que se inclinan siguiendo el puntero ([data-tilt]) y brillo que lo sigue ([data-brillo]). */
function useEfectosPuntero() {
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || !window.matchMedia?.("(hover: hover)").matches) return;
    let activa: HTMLElement | null = null;
    const soltar = () => {
      if (activa) { activa.style.removeProperty("--rx"); activa.style.removeProperty("--ry"); activa.classList.remove("inclinada"); activa = null; }
    };
    const mover = (e: PointerEvent) => {
      const objetivo = e.target as Element | null;
      const brillo = objetivo?.closest?.("[data-brillo]") as HTMLElement | null;
      if (brillo) {
        const r = brillo.getBoundingClientRect();
        brillo.style.setProperty("--mx", `${e.clientX - r.left}px`);
        brillo.style.setProperty("--my", `${e.clientY - r.top}px`);
      }
      const tarjeta = objetivo?.closest?.("[data-tilt]") as HTMLElement | null;
      if (tarjeta !== activa) soltar();
      if (!tarjeta) return;
      activa = tarjeta;
      const r = tarjeta.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      tarjeta.classList.add("inclinada");
      tarjeta.style.setProperty("--rx", `${(0.5 - y) * 8}deg`);
      tarjeta.style.setProperty("--ry", `${(x - 0.5) * 10}deg`);
      tarjeta.style.setProperty("--gx", `${x * 100}%`);
      tarjeta.style.setProperty("--gy", `${y * 100}%`);
    };
    document.addEventListener("pointermove", mover, { passive: true });
    document.addEventListener("pointerleave", soltar);
    return () => { document.removeEventListener("pointermove", mover); document.removeEventListener("pointerleave", soltar); };
  }, []);
}

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
  useEfectosPuntero();
  // Intro de bienvenida: la primera vez que se entra a la portada (o al pedirla desde el pie de página).
  const [intro, setIntro] = useState(() => pathname === "/" && !yaVioIntro()
    && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  // Recordatorios del navegador (si el turista los activó): tours de hoy y de mañana.
  const [recordar, setRecordar] = useState(0);
  useEffect(() => { const f = () => setRecordar((n) => n + 1); window.addEventListener("sierramar:recordatorios", f); return () => window.removeEventListener("sierramar:recordatorios", f); }, []);
  useRecordatorios(usuario?.rol === "turista", en, recordar);

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
            <NavLink to="/arquitectura" className="menu-vivo"><span className="en-vivo" aria-hidden="true" />{en ? "Live" : "En vivo"}</NavLink>
          </nav>
          <div className="acciones">
            <div className="segmento" role="group" aria-label="Idioma / Language">
              <button aria-pressed={!en} onClick={() => en && cambiar()}>ES</button>
              <button aria-pressed={en} onClick={() => !en && cambiar()}>EN</button>
            </div>
            <BotonTema en={en} />
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
        <div key={pathname} className="pagina">
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/ofertas/:id" element={<DetalleOferta />} />
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/confirmar" element={<Confirmar />} />
          <Route path="/creditos" element={<Creditos />} />
          <Route path="/arquitectura" element={<Arquitectura />} />
          <Route path="/reservas/:id" element={<Protegida><ComprobantePagina /></Protegida>} />
          <Route path="/mis-reservas" element={<Protegida rol="turista"><MisReservas /></Protegida>} />
          <Route path="/prestador" element={<Protegida rol="prestador"><Prestador /></Protegida>} />
          <Route path="/admin" element={<Protegida rol="administrador"><Admin /></Protegida>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </div>
      </main>

      {intro && <Intro alTerminar={() => setIntro(false)} />}
      <Toasts />
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
              <li><Link to="/arquitectura">{en ? "Live architecture" : "Arquitectura en vivo"}</Link></li>
            </ul>
          </div>
        </div>
        <div className="contenedor pie-final">
          <span>© 2026 SierraMar · Santa Marta, Colombia</span>
          <span className="fila" style={{ gap: "1rem" }}>
            <button type="button" className="boton-texto" onClick={() => { window.scrollTo(0, 0); setIntro(true); }}>{en ? "Watch welcome" : "Ver bienvenida"}</button>
            <Link to="/creditos">{en ? "Photo credits" : "Créditos fotográficos"}</Link>
          </span>
        </div>
      </footer>
    </>
  );
}
