import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, pesos, type Comprobante, type DetalleOferta, type Franja } from "../api";
import { fotosDeOferta } from "../fotos";
import { Icono } from "../ilustraciones";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, Estado, Insignia, useCarga } from "../ui";

type DetalleConImagenes = DetalleOferta & { imagenes?: { clave_objeto: string }[] };

export default function DetalleOfertaPagina() {
  const { id = "" } = useParams();
  const { t, idioma } = useIdioma();
  const en = idioma === "en";
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [fecha, setFecha] = useState("");
  const [personas, setPersonas] = useState(1);
  const [franja, setFranja] = useState<Franja | null>(null);
  const [correo, setCorreo] = useState(usuario?.email ?? "");
  const [tarjeta, setTarjeta] = useState("4111111111111111");
  const [acompanantes, setAcompanantes] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<{ texto: string; disponibles?: number } | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  // La misma clave en reintentos: si la red falla y el turista vuelve a pulsar, NO se cobra dos veces.
  const claveIdempotencia = useMemo(() => crypto.randomUUID(), [franja?.id, personas]);

  const detalle = useCarga(() => api<DetalleConImagenes>(`/api/v1/catalogo/ofertas/${id}`), [id]);
  const franjas = useCarga(
    () => api<Franja[]>(`/api/v1/ofertas/${id}/disponibilidad`, { query: { fecha, personas } }),
    [id, fecha, personas],
  );
  const cercanas = useCarga(
    () => (fecha && franjas.datos?.length === 0
      ? api<Franja[]>(`/api/v1/ofertas/${id}/disponibilidad/cercanas`, { query: { fecha, personas } })
      : Promise.resolve([] as Franja[])),
    [id, fecha, personas, franjas.datos?.length],
  );

  async function reservar(e: FormEvent) {
    e.preventDefault();
    if (!franja) return;
    setEnviando(true); setError(null); setAviso(null);
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
      if (r.pago_aprobado) navegar(`/reservas/${r.reserva_id}`);
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
      setAviso(`Quedaste en la lista de espera (posición ${r.posicion ?? "-"}). Te avisaremos por correo.`);
    } catch (err) {
      setError({ texto: (err as Error).message });
    }
  }

  return (
    <Estado carga={detalle}>
      {(d) => {
        const o = d.oferta;
        const tarifa = d.tarifas[0];
        const fotos = fotosDeOferta(o, d.zona?.codigo, d.imagenes).slice(0, 3);
        const nombre = en ? o.nombre_en : o.nombre_es;
        const p = d.politica_cancelacion;
        return (
          <div className="apilado">
            <div className="migas">
              <Link to="/">{t("explorar")}</Link><span>/</span>
              {d.zona && <><span>{en ? d.zona.nombre_en : d.zona.nombre_es}</span><span>/</span></>}
              <span style={{ color: "var(--texto)" }}>{nombre}</span>
            </div>

            <div className="encabezado-seccion" style={{ margin: 0 }}>
              <div>
                <h1 style={{ margin: 0 }}>{nombre}</h1>
                <div className="fila" style={{ marginTop: ".7rem" }}>
                  {d.zona && <span className="lugar"><Icono n="lugar" />{en ? d.zona.nombre_en : d.zona.nombre_es}, Santa Marta</span>}
                  <span className="tenue">·</span>
                  <span>★ <strong>{o.total_calificaciones ? o.calificacion_promedio.toFixed(1) : (en ? "New" : "Nuevo")}</strong>
                    {o.total_calificaciones > 0 && <span className="tenue"> ({o.total_calificaciones})</span>}</span>
                  <span className="tenue">·</span>
                  <span className="verificado"><Icono n="escudo" tam={14} />{en ? "Verified operator" : "Prestador verificado"}</span>
                </div>
              </div>
            </div>

            <div className={`galeria${fotos.length === 1 ? " una" : fotos.length === 2 ? " dos" : ""}`}>
              {fotos.map((src, i) => <img key={src} src={src} alt={i === 0 ? nombre : ""} />)}
            </div>

            <div className="columnas">
              <section className="apilado">
                <div className="datos-clave">
                  {o.atributos.duracion_horas && <div className="dato"><span>{en ? "Duration" : "Duración"}</span><strong>{o.atributos.duracion_horas} h</strong></div>}
                  {(o.atributos.categorias ?? []).slice(0, 2).map((c) => <div key={c} className="dato"><span>{en ? "Type" : "Tipo"}</span><strong>{c.charAt(0).toUpperCase() + c.slice(1)}</strong></div>)}
                  {d.zona && <div className="dato"><span>{t("zona")}</span><strong>{en ? d.zona.nombre_en : d.zona.nombre_es}</strong></div>}
                </div>

                <div>
                  <h2 style={{ fontSize: "1.5rem" }}>{en ? "About this experience" : "Sobre esta experiencia"}</h2>
                  <p style={{ fontSize: "1.05rem", margin: 0 }}>{en ? o.descripcion_en : o.descripcion_es}</p>
                </div>

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

                <div>
                  <h2 style={{ fontSize: "1.5rem" }}>{t("disponibilidad")}</h2>
                  <div className="campos" style={{ marginBottom: "1rem" }}>
                    <label>{t("fecha")}<input type="date" value={fecha} onChange={(e) => { setFecha(e.target.value); setFranja(null); }} /></label>
                    <label>{t("personas")}
                      <input type="number" min={1} max={20} value={personas}
                        onChange={(e) => { setPersonas(Math.max(1, Number(e.target.value))); setFranja(null); }} />
                    </label>
                  </div>
                  <Estado carga={franjas}>
                    {(lista) => lista.length === 0 ? (
                      <div className="pila">
                        <Aviso>{t("sinCupos")}</Aviso>
                        {(cercanas.datos?.length ?? 0) > 0 && (
                          <div className="pila">
                            <p className="tenue" style={{ margin: 0 }}>{en ? "Nearby dates with spots:" : "Fechas cercanas con cupo:"}</p>
                            <div className="franjas">
                              {cercanas.datos!.map((f) => (
                                <button key={f.id} className="boton-secundario" onClick={() => setFecha(f.fecha)}>
                                  {f.fecha} · {f.hora_inicio} · {f.cupo_disponible} {t("cupos")}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="franjas">
                        {lista.map((f) => (
                          <div key={f.id} className="franja" role="button" tabIndex={0} aria-pressed={franja?.id === f.id}
                            onClick={() => setFranja(f)} onKeyDown={(e) => e.key === "Enter" && setFranja(f)}>
                            <span><strong>{f.hora_inicio.slice(0, 5)}</strong><br /><small className="tenue">{f.fecha}</small></span>
                            <Insignia tono={f.cupo_disponible <= 2 ? "alerta" : "ok"}>{f.cupo_disponible} {t("cupos")}</Insignia>
                          </div>
                        ))}
                      </div>
                    )}
                  </Estado>
                </div>
              </section>

              <aside className="tarjeta reserva-caja pila">
                {tarifa && (
                  <div>
                    <div className="tarifa-etq">{en ? "From" : "Desde"}</div>
                    <span className="precio">{pesos(tarifa.precio_por_persona, tarifa.moneda)}</span>
                    <span className="tenue"> {t("porPersona")}</span>
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
                      <strong>{franja.fecha} · {franja.hora_inicio.slice(0, 5)} · {personas} {t("personas").toLowerCase()}</strong>
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
                {aviso && <Aviso tipo="ok">{aviso}</Aviso>}
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
