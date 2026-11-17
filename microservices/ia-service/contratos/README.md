# Contratos del servicio IA (propuesta)

| Archivo | Para quién | Qué es |
|---|---|---|
| `ia-openapi.json` | PWA, Gateway (Carlos) | API REST que expone IA. Abrir en https://editor.swagger.io |
| `vocabulario.json` | **Todos** | Ids compartidos de intereses/categorías y zonas |
| `eventos/sobre-evento.schema.json` | **Todos** (Santiago: plantilla común) | Formato común de todo mensaje en RabbitMQ |
| `eventos/catalogo.oferta.schema.json` | Luis publica | Estado completo de una oferta |
| `eventos/analitica.zona.ocupacion_actualizada.schema.json` | Carlos publica | Ocupación de una zona |
| `eventos/reservas.reserva.confirmada.schema.json` | Santiago publica | Reserva confirmada (sin datos del turista) |

Todo es propuesta: si un campo no les sirve, se cambia aquí antes de programarlo.
Según el documento de diseño (§5.1), estos archivos deben terminar en el paquete común
`contratos.openapi` / `contratos.eventos` del repositorio del grupo.

Ejemplo de mensaje completo en RabbitMQ:

```json
{
  "evento_id": "5b1e6a0e-3f0b-4c1e-9a55-1c0f3a1d2e77",
  "tipo": "analitica.zona.ocupacion_actualizada",
  "version": 1,
  "ocurrido_en": "2026-11-14T08:00:05Z",
  "correlation_id": null,
  "datos": { "zona_id": "tayrona", "nombre": "Tayrona", "ocupacion": 0.92, "medido_en": "2026-11-14T08:00:00Z" }
}
```
