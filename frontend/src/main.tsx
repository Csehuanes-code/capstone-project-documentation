import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ProveedorIdioma } from "./idioma";
import { ProveedorSesion } from "./sesion";
import "./estilos.css";
import "./estilos-v2.css";

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
