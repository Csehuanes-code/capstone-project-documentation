import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ProveedorIdioma } from "./idioma";
import { ProveedorSesion } from "./sesion";
import { aplicarTemaGuardado } from "./extras";
import "./estilos.css";
import "./estilos-v2.css";
import "./estilos-v3.css";
import "./estilos-v4.css";

aplicarTemaGuardado();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ProveedorIdioma>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </ProveedorIdioma>
    </BrowserRouter>
  </React.StrictMode>,
);

// Pantalla de bienvenida: se desvanece cuando la app ya pintó (mínimo ~0,65 s desde que abrió la página).
const splash = document.getElementById("splash");
if (splash) {
  setTimeout(() => {
    splash.classList.add("fuera");
    setTimeout(() => splash.remove(), 700);
  }, Math.max(0, 650 - performance.now()));
}
