import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// En desarrollo (npm run dev) todas las llamadas /api van al gateway del docker-compose.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icono.svg"],
      manifest: {
        name: "SierraMar · Turismo sostenible en Santa Marta",
        short_name: "SierraMar",
        description: "Reserva experiencias de turismo sostenible en Santa Marta",
        lang: "es",
        theme_color: "#0b6e6e",
        background_color: "#f6f3ee",
        display: "standalone",
        start_url: "/",
        icons: [{ src: "/icono.svg", sizes: "any", type: "image/svg+xml", purpose: "any maskable" }],
      },
      workbox: {
        // La API nunca se cachea: reservas y cupos deben ser siempre los reales.
        // /correo es el buzón de la demo (Mailpit) detrás del gateway: no lo atiende la PWA.
        navigateFallbackDenylist: [/^\/api\//, /^\/\.well-known\//, /^\/correo/],
        runtimeCaching: [{ urlPattern: /^\/api\//, handler: "NetworkOnly" }],
      },
    }),
  ],
  server: { port: 5173, proxy: { "/api": "http://localhost:8080" } },
});
