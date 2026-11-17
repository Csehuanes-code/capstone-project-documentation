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
        theme_color: "#0b2531",
        background_color: "#f3f6f5",
        display: "standalone",
        start_url: "/",
        icons: [{ src: "/icono.svg", sizes: "any", type: "image/svg+xml", purpose: "any maskable" }],
      },
      workbox: {
        // La API nunca se cachea: reservas y cupos deben ser siempre los reales.
        // /correo es el buzón de la demo (Mailpit) detrás del gateway: no lo atiende la PWA.
        navigateFallbackDenylist: [/^\/api\//, /^\/\.well-known\//, /^\/correo/],
        runtimeCaching: [
          { urlPattern: ({ url }) => url.pathname.startsWith("/api/"), handler: "NetworkOnly" },
          // Fotos de destinos: se guardan al verlas por primera vez (la app sigue luciendo bien sin conexión).
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/fotos/"),
            handler: "CacheFirst",
            options: { cacheName: "fotos", expiration: { maxEntries: 40 } },
          },
        ],
      },
    }),
  ],
  server: { port: 5173, proxy: { "/api": "http://localhost:8080" } },
});
