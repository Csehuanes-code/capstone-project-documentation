// Transición de vista: la foto de la tarjeta "viaja" y se convierte en la portada del detalle
// (View Transitions API). Si el navegador no la soporta o el usuario pide menos movimiento, navega normal.
import { flushSync } from "react-dom";
import type { NavigateFunction } from "react-router-dom";

type DocumentoConTransicion = Document & { startViewTransition?: (cb: () => void) => { finished: Promise<void> } };

export const NOMBRE_FOTO = "foto-oferta";

export function irConFoto(navegar: NavigateFunction, ruta: string, img: HTMLImageElement | null, estado?: unknown) {
  const doc = document as DocumentoConTransicion;
  const menosMovimiento = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  if (!doc.startViewTransition || menosMovimiento) {
    navegar(ruta, { state: estado });
    return;
  }
  if (img) img.style.viewTransitionName = NOMBRE_FOTO;
  document.documentElement.classList.add("en-transicion");
  const t = doc.startViewTransition(() => {
    if (img) img.style.viewTransitionName = "";
    flushSync(() => navegar(ruta, { state: estado }));
    window.scrollTo(0, 0);
  });
  t.finished.finally(() => document.documentElement.classList.remove("en-transicion"));
}
