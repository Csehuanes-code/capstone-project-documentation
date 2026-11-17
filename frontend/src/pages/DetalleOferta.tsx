import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, pesos, type Comprobante, type DetalleOferta, type Franja } from "../api";
import { useIdioma } from "../idioma";
import { useSesion } from "../sesion";
import { Aviso, Estado, Insignia, useCarga } from "../ui";

export default function DetalleOfertaPagina() {
  const { id = "" } = useParams();
  const { t, idioma } = useIdioma();
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

  const detalle = useCarga(() => api<DetalleOferta>(`/api/v1/catalogo/ofertas/${id}`), [id]);
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
      else setError({ texto: idioma === "en" ? r.mensaje_en : r.mensaje_es });
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
        return (
          <div className="columnas">
            <section className="pila">
              <Link to="/" className="tenue">← {t("explorar")}</Link>
              <h1>{idioma === "en" ? o.nombre_en : o.nombre_es}</h1>
              <div className="fila">
                {d.zona && <Insignia>{idioma === "en" ? d.zona.nombre_en : d.zona.nombre_es}</Insignia>}
                {(o.atributos.categorias ?? []).map((c) => <Insignia key={c}>{c}</Insignia>)}
                {o.atributos.duracion_horas && <Insignia>{o.atributos.duracion_horas} h</Insignia>}
                <span>★ {o.calificacion_promedio.toFixed(1)} ({o.total_calificaciones})</span>
              </div>
              <p>{idioma === "en" ? o.descripcion_en : o.descripcion_es}</p>
              {d.politica_cancelacion && (
                <div className="tarjeta">
                  <strong>{t("politica")}</strong>
                  <p className="tenue" style={{ marginBottom: 0 }}>
                    100 % ≥ {d.politica_cancelacion.horas_reembolso_total} h · {d.politica_cancelacion.porcentaje_reembolso_parcial} %
                    ≥ {d.politica_cancelacion.horas_reembolso_parcial} h · 0 % después
                  </p>
                </div>
              )}

              <h2>{t("disponibilidad")}</h2>
              <div className="fila">
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
                        <p className="tenue">Fechas cercanas con cupo:</p>
                        {cercanas.datos!.map((f) => (
                          <button key={f.id} className="boton-secundario" onClick={() => setFecha(f.fecha)}>
                            {f.fecha} · {f.hora_inicio} · {f.cupo_disponible} {t("cupos")}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="pila">
                    {lista.map((f) => (
                      <div key={f.id} className="franja" role="button" tabIndex={0} aria-pressed={franja?.id === f.id}
                        onClick={() => setFranja(f)} onKeyDown={(e) => e.key === "Enter" && setFranja(f)}>
                        <span><strong>{f.fecha}</strong> · {f.hora_inicio}</span>
                        <Insignia tono={f.cupo_disponible <= 2 ? "alerta" : "ok"}>{f.cupo_disponible} {t("cupos")}</Insignia>
                      </div>
                    ))}
                  </div>
                )}
              </Estado>
            </section>

            <aside className="tarjeta pila" style={{ alignSelf: "start", position: "sticky", top: 80 }}>
              {tarifa && (
                <div>
                  <span className="precio">{pesos(tarifa.precio_por_persona, tarifa.moneda)}</span>
                  <span className="tenue"> {t("porPersona")}</span>
                </div>
              )}
              {!usuario ? (
                <Aviso><Link to="/entrar">{t("entrar")}</Link> para reservar.</Aviso>
              ) : usuario.rol !== "turista" ? (
                <Aviso>Solo las cuentas de turista pueden reservar.</Aviso>
              ) : !franja ? (
                <p className="tenue">Elige un horario de la lista.</p>
              ) : (
                <form className="formulario" onSubmit={reservar}>
                  <strong>{franja.fecha} · {franja.hora_inicio} · {personas} {t("personas").toLowerCase()}</strong>
                  {tarifa && <div>{t("total")}: <strong>{pesos(tarifa.precio_por_persona * personas)}</strong></div>}
                  <label>{t("correo")}<input type="email" required value={correo} onChange={(e) => setCorreo(e.target.value)} /></label>
                  {personas > 1 && (
                    <label>{t("acompanantes")}<input value={acompanantes} onChange={(e) => setAcompanantes(e.target.value)} /></label>
                  )}
                  <label>{t("tarjeta")}
                    <input value={tarjeta} onChange={(e) => setTarjeta(e.target.value)} inputMode="numeric" />
                  </label>
                  <small className="tenue">Pruebas: …0002 rechazada · …9999 tiempo agotado · …0019 sin reembolso</small>
                  <button disabled={enviando}>{enviando ? t("cargando") : t("pagar")}</button>
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
            </aside>
          </div>
        );
      }}
    </Estado>
  );
}
