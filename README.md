# Plataforma de Turismo de Santa Marta — Grupo 4

Cinco microservicios (Auth, Catálogo, Reservas, IA, Analítica), una PWA y un gateway.

## Levantar todo (demo)

```sh
sh scripts/generar_claves.sh      # una vez: claves ES256 de Auth en ./secretos
docker compose up -d --build
docker compose run --rm demo      # datos de demostración (usuarios, ofertas, franjas, umbrales)
```

| Qué | URL |
|---|---|
| Aplicación (PWA + API por el gateway) | http://localhost:8080 |
| Correos (Mailpit) | http://localhost:8025 |
| RabbitMQ (guest/guest) | http://localhost:15680 |
| Panel del gateway | http://localhost:8090 |

Cuentas de demostración: `turista@turismo.co / Turista-Demo-2026`,
`prestador@turismo.co / Prestador-Demo-2026`, `admin@turismo.co / Admin-Demo-2026`.

## Cómo se conectan

- **Gateway (Traefik):** única entrada; enruta por prefijo (`despliegue/gateway/dinamico.yml`).
- **JWT ES256:** Auth firma; los demás validan con la clave pública.
- **RabbitMQ (exchange `turismo`, outbox en cada servicio):**
  - Auth → `auth.notificacion.solicitada` → Reservas envía el correo de confirmación.
  - Auth → `auth.prestador.verificacion_resuelta` → Catálogo habilita al prestador.
  - Catálogo → `catalogo.oferta.*` → IA y Reservas.
  - Reservas → `reservas.reserva.confirmada` → IA (popularidad) y Analítica (indicadores).
  - Analítica → `analitica.zona.ocupacion_actualizada` → IA (descongestión).
- **REST síncrono:** Reservas → Catálogo (condiciones); Catálogo → Reservas (estado para calificar).

Contratos compartidos en `contratos/`.
