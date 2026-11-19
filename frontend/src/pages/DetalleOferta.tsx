import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, pesos, type Comprobante, type DetalleOferta, type Franja } from "../api";
import { fotosDeOferta } from "../fotos";
import { Icono } from "../ilustraciones";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { NOMBRE_FOTO } from "../transicion";
import { Aviso, avisar, Estado, Insignia, useCarga } from "../ui";

type DetalleConImagenes = DetalleOferta & { imagenes?: { clave_objeto: string }[] };

const ESTILO_FOTO = { viewTransitionName: NOMBRE_FOTO } as CSSProperties;

function isoLocal(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Portada a sangre con parallax suave: la foto baja más lento que la página. */
function PortadaDetalle({ foto, children }: { foto?: string; children: ReactNode }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    let cuadro = 0;
    const mover = () => {
      cancelAnimationFrame(cuadro);
      cuadro = requestAnimationFrame(() => ref.current?.style.setProperty("--desplazar", String(Math.min(window.scrollY, 700) * 0.35)));
    };
    window.addEventListener("scroll", mover, { passive: true });
    return () => { cancelAnimationFrame(cuadro); window.removeEventListener("scroll", mover); };
  }, []);
  return (
    <section ref={ref} className="detalle-heroe a-sangre">
      {foto && <img src={foto} alt="" style={ESTILO_FOTO} />}
      <div className="detalle-heroe-texto">{children}</div>
    </section>
  );
}

/** Calendario del mes: resalta los días con cupo y muestra cuántos quedan. */
function Calendario({ dias, elegida, onElegir, en }: {
  dias: Map<string, number>; elegida: string; onElegir: (fecha: string) => void; en: boolean;
}) {
  const claves = [...dias.keys()].sort();
  const hoy = isoLocal(new Date());
  const [mes, setMes] = useState(() => (elegida || claves[0] || hoy).slice(0, 7));
  const [a, m] = mes.split("-").map(Number);
  const primero = new Date(a, m - 1, 1);
  const hueco = (primero.getDay() + 6) % 7;
  const total = new Date(a, m, 0).getDate();
  const minimo = (claves[0] ?? hoy).slice(0, 7);
  const maximo = (claves[claves.length - 1] ?? hoy).slice(0, 7);
  const mover = (d: number) => { const n = new Date(a, m - 1 + d, 1); setMes(isoLocal(n).slice(0, 7)); };
  const semana = en ? ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"] : ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
  return (
    <div className="calendario">
      <div className="calendario-cabecera">
        <button type="button" onClick={() => mover(-1)} disabled={mes <= minimo} aria-label={en ? "Previous month" : "Mes anterior"}>‹</button>
        <strong>{(() => { const t = primero.toLocaleDateString(en ? "en-US" : "es-CO", { month: "long", year: "numeric" }).replace(" de ", " "); return t.charAt(0).toUpperCase() + t.slice(1); })()}</strong>
        <button type="button" onClick={() => mover(1)} disabled={mes >= maximo} aria-label={en ? "Next month" : "Mes siguiente"}>›</button>
      </div>
      <div className="calendario-dias">
        {semana.map((d) => <span key={d}>{d}</span>)}
        {Array.from({ length: hueco }, (_, i) => <i key={`h${i}`} />)}
        {Array.from({ length: total }, (_, i) => {
          const fecha = `${mes}-${String(i + 1).padStart(2, "0")}`;
          const cupo = dias.get(fecha);
          const clase = ["dia", cupo ? "con-cupo" : "", cupo && cupo <= 3 ? "pocos" : "", fecha === elegida ? "elegido" : "", fecha === hoy ? "hoy" : ""].filter(Boolean).join(" ");
          return (
            <button key={fecha} type="button" className={clase} disabled={!cupo} aria-pressed={fecha === elegida}
              aria-label={`${fecha}: ${cupo ? `${cupo} ${en ? "spots" : "cupos"}` : en ? "no spots" : "sin cupos"}`}
              onClick={() => onElegir(fecha)}>
              {i + 1}
              {cupo ? <small>{cupo}</small> : null}
            </button>
          );
        })}
      </div>
      <div className="calendario-pie">
        <span><i />{en ? "Spots available (number left)" : "Con cupo (número disponible)"}</span>
        <span><i className="pocos-i" />{en ? "Almost full" : "Últimos cupos"}</span>
      </div>
    </div>
  );
}

export default function DetalleOfertaPagina() {
  const { id = "" } = useParams();
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const previa = (useLocation().state ?? null) as { foto?: string; nombre?: string } | null;
  const [fecha, setFecha] = useState("");
  const [personas, setPersonas] = useState(1);
  const [franja, setFranja] = useState<Franja | null>(null);
  const [correo, setCorreo] = useState(usuario?.email ?? "");
  const [tarjeta, setTarjeta] = useState("4111111111111111");
  const [acompanantes, setAcompanantes] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<{ texto: string; disponibles?: number } | null>(null);
  // La misma clave en reintentos: si la red falla y el turista vuelve a pulsar, NO se cobra dos veces.
  const claveIdempotencia = useMemo(() => crypto.randomUUID(), [franja?.id, personas]);

  const detalle = useCarga(() => api<DetalleConImagenes>(`/api/v1/catalogo/ofertas/${id}`), [id]);
  // Todas las franjas con cupo para ese número de personas: alimentan el calendario y los horarios del día.
  const franjas = useCarga(
    () => api<Franja[]>(`/api/v1/ofertas/${id}/disponibilidad`, { query: { personas } }),
    [id, personas],
  );
  const cupoPorDia = useMemo(() => {
    const m = new Map<string, number>();
    for (const f of franjas.datos ?? []) m.set(f.fecha, (m.get(f.fecha) ?? 0) + f.cupo_disponible);
    return m;
  }, [franjas.datos]);
  const delDia = (franjas.datos ?? []).filter((f) => f.fecha === fecha);
  const cercanas = useCarga(
    () => (fecha && franjas.datos && delDia.length === 0
      ? api<Franja[]>(`/api/v1/ofertas/${id}/disponibilidad/cercanas`, { query: { fecha, personas } })
      : Promise.resolve([] as Franja[])),
    [id, fecha, personas, franjas.datos, delDia.length],
  );

  async function reservar(e: FormEvent) {
    e.preventDefault();
    if (!franja) return;
    setEnviando(true); setError(null);
    try {
      const r = await api<Comprobante>("/api/v1/reservas", {
        method: "POST",
        headers: { "Idempotency-Key": claveIdempotencia },
        body: {
          franja_id: franja.id, personas, correo_turista: correo, idioma,
          datos_pago: { numero_tarjeta: tarjeta },
          acompanantes: acompanantes.split(",").map((s) => s.trim()).filter(Boolean),
        },
      });
      if (r.pago_aprobado) navegar(`/reservas/${r.reserva_id}`, { state: { nueva: true } });
      else setError({ texto: en ? r.mensaje_en : r.mensaje_es });
      franjas.recargar();
    } catch (err) {
      const ae = err as ApiError;
      const disponibles = (ae.body as { disponibles?: number } | null)?.disponibles;
      setError({ texto: ae.message, disponibles });
    } finally {
      setEnviando(false);
    }
  }

  async function listaEspera() {
    if (!franja) return;
    try {
      const r = await api<{ posicion: number | null }>(`/api/v1/franjas/${franja.id}/lista-espera`, {
        method: "POST", body: { personas, correo_turista: correo, idioma },
      });
      setError(null);
      avisar(en
        ? `You're on the waiting list (position ${r.posicion ?? "-"}). We'll email you.`
        : `Quedaste en la lista de espera (posición ${r.posicion ?? "-"}). Te avisaremos por correo.`);
    } catch (err) {
      avisar((err as Error).message, "error");
    }
  }

  function cambiarPersonas(n: number) {
    setPersonas(Math.min(20, Math.max(1, n)));
    setFranja(null);
  }

  // Mientras carga, la portada ya muestra la foto que "viajó" desde la tarjeta (transición de vista).
  if (!detalle.datos && !detalle.error && previa?.foto) {
    return (
      <div className="apilado">
        <PortadaDetalle foto={previa.foto}>
          <h1>{previa.nombre}</h1>
        </PortadaDetalle>
        <Estado carga={detalle}>{() => null}</Estado>
      </div>
    );
  }

  return (
    <Estado carga={detalle}>
      {(d) => {
        const o = d.oferta;
        const tarifa = d.tarifas[0];
        const fotos = fotosDeOferta(o, d.zona?.codigo, d.imagenes).slice(0, 4);
        const portada = previa?.foto ?? fotos[0];
        const resto = fotos.filter((f) => f !== portada).slice(0, 3);
        const nombre = en ? o.nombre_en : o.nombre_es;
        const zona = d.zona ? (en ? d.zona.nombre_en : d.zona.nombre_es) : null;
        const p = d.politica_cancelacion;
        return (
          <div className="apilado">
            <PortadaDetalle foto={portada}>
              <div className="migas">
                <Link to="/">{t("explorar")}</Link><span>/</span>
                {zona && <><span>{zona}</span><span>/</span></>}
                <span>{nombre}</span>
              </div>
              <h1>{nombre}</h1>
              <div className="fila">
                {zona && <span className="chip-vidrio"><Icono n="lugar" />{zona}, Santa Marta</span>}
                <span className="chip-vidrio">★ <strong>{o.total_calificaciones ? o.calificacion_promedio.toFixed(1) : (en ? "New" : "Nuevo")}</strong>
                  {o.total_calificaciones > 0 && <span style={{ opacity: .75 }}> ({o.total_calificaciones})</span>}</span>
                {o.atributos.duracion_horas && <span className="chip-vidrio"><Icono n="reloj" />{o.atributos.duracion_horas} h</span>}
                <span className="chip-vidrio"><Icono n="escudo" />{en ? "Verified operator" : "Prestador verificado"}</span>
              </div>
            </PortadaDetalle>

            <div className="columnas">
              <section className="apilado">
                <div className="datos-clave">
                  {o.atributos.duracion_horas && <div className="dato"><span>{en ? "Duration" : "Duración"}</span><strong>{o.atributos.duracion_horas} h</strong></div>}
                  {(o.atributos.categorias ?? []).slice(0, 2).map((c) => <div key={c} className="dato"><span>{en ? "Type" : "Tipo"}</span><strong>{c.charAt(0).toUpperCase() + c.slice(1)}</strong></div>)}
                  {zona && <div className="dato"><span>{t("zona")}</span><strong>{zona}</strong></div>}
                </div>

                <div>
                  <h2 style={{ fontSize: "1.5rem" }}>{en ? "About this experience" : "Sobre esta experiencia"}</h2>
                  <p style={{ fontSize: "1.05rem", margin: 0 }}>{en ? o.descripcion_en : o.descripcion_es}</p>
                </div>

                <div className="pila">
                  <div className="fila entre" style={{ flexWrap: "wrap", gap: "1rem" }}>
                    <h2 style={{ fontSize: "1.5rem", margin: 0 }}>{t("disponibilidad")}</h2>
                    <div className="fila" style={{ gap: ".7rem" }}>
                      <span className="tenue"><Icono n="personas" tam={18} /> {t("personas")}</span>
                      <div className="contador-personas">
                        <button type="button" onClick={() => cambiarPersonas(personas - 1)} disabled={personas <= 1} aria-label={en ? "One less" : "Una menos"}>−</button>
                        <output aria-live="polite"><span key={personas}>{personas}</span></output>
                        <button type="button" onClick={() => cambiarPersonas(personas + 1)} disabled={personas >= 20} aria-label={en ? "One more" : "Una más"}>+</button>
                      </div>
                    </div>
                  </div>
                  <Estado carga={franjas}>
                    {(todas) => todas.length === 0 ? (
                      <Aviso>{en ? "No upcoming dates with spots for that group size." : "No hay fechas próximas con cupo para ese número de personas."}</Aviso>
                    ) : (
                      <div className="pila">
                        <Calendario dias={cupoPorDia} elegida={fecha} en={en} onElegir={(f) => { setFecha(f); setFranja(null); }} />
                        {!fecha ? (
                          <p className="tenue" style={{ margin: 0 }}><Icono n="calendario" tam={16} /> {en ? "Pick a highlighted day to see its time slots." : "Elige un día resaltado para ver sus horarios."}</p>
                        ) : delDia.length === 0 ? (
                          <div className="pila">
                            <Aviso>{t("sinCupos")}</Aviso>
                            {(cercanas.datos?.length ?? 0) > 0 && (
                              <div className="pila">
                                <p className="tenue" style={{ margin: 0 }}>{en ? "Nearby dates with spots:" : "Fechas cercanas con cupo:"}</p>
                                <div className="franjas">
                                  {cercanas.datos!.map((f) => (
                                    <button key={f.id} className="boton-secundario" onClick={() => setFecha(f.fecha)}>
                                      {f.fecha} · {f.hora_inicio.slice(0, 5)} · {f.cupo_disponible} {t("cupos")}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="franjas">
                            {delDia.map((f) => (
                              <div key={f.id} className="franja" role="button" tabIndex={0} aria-pressed={franja?.id === f.id}
                                onClick={() => setFranja(f)} onKeyDown={(e) => e.key === "Enter" && setFranja(f)}>
                                <span><strong>{f.hora_inicio.slice(0, 5)}</strong><br /><small className="tenue">{f.fecha}</small></span>
                                <Insignia tono={f.cupo_disponible <= 2 ? "alerta" : "ok"}>{f.cupo_disponible} {t("cupos")}</Insignia>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </Estado>
                </div>

                {resto.length > 0 && (
                  <div className="galeria-mini">
                    {resto.map((src) => <img key={src} src={src} alt="" loading="lazy" />)}
                  </div>
                )}

                {p && (
                  <div>
                    <h2 style={{ fontSize: "1.5rem" }}>{t("politica")}</h2>
                    <div className="politica">
                      <div><b>100 %</b><span>{en ? `refund ${p.horas_reembolso_total} h or more before` : `de reembolso con ${p.horas_reembolso_total} h o más de anticipación`}</span></div>
                      <div><b>{p.porcentaje_reembolso_parcial} %</b><span>{en ? `refund ${p.horas_reembolso_parcial} h or more before` : `de reembolso con ${p.horas_reembolso_parcial} h o más`}</span></div>
                      <div><b>0 %</b><span>{en ? "after that" : "después de ese plazo"}</span></div>
                    </div>
                  </div>
                )}
              </section>

              <aside className="tarjeta reserva-caja vidrio pila">
                {tarifa && (
                  <div>
                    <div className="tarifa-etq">{en ? "From" : "Desde"}</div>
                    <span className="precio">{pesos(tarifa.precio_por_persona, tarifa.moneda)}</span>
                    <span className="tenue"> {t("porPersona")}</span>
                  </div>
                )}
                {tarifa && (
                  <div className="fila entre">
                    <span className="tenue">{personas} × {pesos(tarifa.precio_por_persona, tarifa.moneda)}</span>
                    <strong key={personas} className="total-animado">{pesos(tarifa.precio_por_persona * personas, tarifa.moneda)}</strong>
                  </div>
                )}
                {!usuario ? (
                  <div className="pila">
                    <p className="tenue" style={{ margin: 0 }}>{en ? "Sign in with a tourist account to book." : "Inicia sesión con una cuenta de turista para reservar."}</p>
                    <Link className="boton boton-bloque" to="/entrar">{t("entrar")}</Link>
                  </div>
                ) : usuario.rol !== "turista" ? (
                  <Aviso>{en ? "Only tourist accounts can book." : "Solo las cuentas de turista pueden reservar."}</Aviso>
                ) : !franja ? (
                  <p className="tenue" style={{ margin: 0 }}><Icono n="calendario" tam={16} /> {en ? "Pick a date and a time slot." : "Elige una fecha y un horario disponible."}</p>
                ) : (
                  <form className="formulario" onSubmit={reservar}>
                    <div className="dato">
                      <span>{en ? "Your booking" : "Tu reserva"}</span>
                      <strong>{franja.fecha} · {franja.hora_inicio.slice(0, 5)} · {personas} {personas === 1 ? (en ? "guest" : "persona") : t("personas").toLowerCase()}</strong>
                    </div>
                    {tarifa && <div className="fila entre"><span>{t("total")}</span><span className="precio" style={{ fontSize: "1.5rem" }}>{pesos(tarifa.precio_por_persona * personas)}</span></div>}
                    <label>{t("correo")}<input type="email" required value={correo} onChange={(e) => setCorreo(e.target.value)} /></label>
                    {personas > 1 && (
                      <label>{t("acompanantes")}<input value={acompanantes} onChange={(e) => setAcompanantes(e.target.value)} /></label>
                    )}
                    <label>{t("tarjeta")}
                      <input value={tarjeta} onChange={(e) => setTarjeta(e.target.value)} inputMode="numeric" />
                    </label>
                    <small className="tenue">{en ? "Test cards" : "Pruebas"}: …0002 {en ? "declined" : "rechazada"} · …9999 {en ? "timeout" : "tiempo agotado"} · …0019 {en ? "no refund" : "sin reembolso"}</small>
                    <button className="boton-grande boton-sol" disabled={enviando}>{enviando ? t("cargando") : t("pagar")}</button>
                  </form>
                )}
                {error && (
                  <Aviso tipo="error">
                    {error.texto}
                    {error.disponibles !== undefined && (
                      <div style={{ marginTop: ".5rem" }}>
                        <button className="boton-secundario" onClick={listaEspera}>{t("listaEspera")}</button>
                      </div>
                    )}
                  </Aviso>
                )}
                <div className="fila tenue" style={{ fontSize: ".82rem", gap: ".4rem" }}>
                  <Icono n="escudo" tam={16} />{en ? "Secure payment · no overbooking" : "Pago seguro · sin sobreventa"}
                </div>
              </aside>
            </div>
          </div>
        );
      }}
    </Estado>
  );
}
