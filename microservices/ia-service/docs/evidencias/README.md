# Evidencias del servicio IA — Recomendación

Qué promete el Documento de Diseño Arquitectónico y qué lo demuestra en este servicio.
Estado al 16/11/2026: **121 pruebas pasan**, incluidas las ejecutadas contra PostgreSQL 16 real.

Cómo reproducir todo:

```powershell
docker compose up -d --build
$env:IA_TEST_DATABASE_URL = "postgresql+psycopg://ia:ia_local_dev@127.0.0.1:5433/ia_test"
.\.venv\Scripts\python.exe -m pytest -q
```

## Escenarios de calidad

| Escenario / restricción | Qué promete el documento | Evidencia | Resultado |
|---|---|---|---|
| **EC-IA-01** (RC-ET01) | Explicación en el 100 % de las recomendaciones | `test_aplicacion.py::test_todas_las_recomendaciones_tienen_explicacion` (ES y EN, 4 perfiles de intereses) | ✅ |
| **EC-IA-01** | Lo que ve el turista es el mismo cálculo que se hizo | `test_api.py::test_por_que_veo_esto` (la recomendación guardada devuelve el mismo desglose) y `test_puntaje.py::test_el_total_es_la_suma_del_desglose` | ✅ |
| **EC-IA-02** (RC-ET02) | El prestador no influye en el puntaje | `test_puntaje.py::test_el_prestador_no_influye_en_el_puntaje` | ✅ |
| **ADR-07** | Fórmula 0,45 / 0,25 / 0,20 / 0,10 del boceto W3 | `test_puntaje.py::test_reproduce_el_ejemplo_del_boceto_w3` (Tour Minca = 0,92) | ✅ |
| **ADR-07** | Calificación bayesiana | `test_puntaje.py::test_calidad_bayesiana_desconfia_de_pocas_resenas` | ✅ |
| **ADR-07** | Pesos versionados e inmutables | `test_aplicacion.py::test_una_version_nueva_de_pesos_no_altera_lo_ya_emitido`; en PostgreSQL un trigger lo impone: `test_repositorios.py::test_postgres_impide_modificar_pesos_ya_guardados` | ✅ |
| **EC-SOST-01** (RC-A01) | Zona saturada (≥ 80 %) → alternativa menos concurrida | `test_ranking.py::test_oferta_en_zona_saturada_se_reemplaza_por_alternativa`, `test_aplicacion.py::test_alerta_de_capacidad_cambia_la_recomendacion` | ✅ |
| **ADR-07** | Reglas de diversidad | `test_ranking.py::test_diversidad_maximo_por_zona` | ✅ |
| **EC-MANT-01** (RC-ARQ04) | El CI falla si una capa viola la regla de dependencia | `.importlinter` + `test_import_linter.py` y `test_arquitectura.py`. Probado metiendo una violación a propósito: la prueba falló | ✅ |
| **EC-MULTI-01** (RC-S02) | Textos en español e inglés | `test_api.py::test_recomendaciones_en_ingles` | ✅ |
| **ADR-04** | Consumidores de eventos idempotentes | `test_repositorios.py::test_evento_repetido_cuenta_una_sola_vez` (memoria, SQLite y PostgreSQL) | ✅ |
| **ADR-04** | El evento y su efecto se guardan juntos (outbox / evento_procesado) | `test_repositorios.py::test_un_corte_a_mitad_no_deja_el_evento_marcado` (simula un corte: nada queda a medias y el reintento funciona) | ✅ |
| **ADR-03** | Base lógica propia `ia_db`, JSONB, migraciones | `test_migraciones.py` (la migración produce exactamente el esquema del código y se revierte) | ✅ |
| **EC-DISP** (RC-T04) | El balanceador detecta si el servicio no puede atender | `test_api.py::test_ready_responde_503_si_la_base_no_responde` | ✅ |
| **ADR-02** | Si IA falla, la reserva no se afecta | Por diseño: IA no está en el camino síncrono de la reserva y solo consume eventos | ✅ (diseño) |

## Carga (EC-DESM / EC-ESC)

Medido con `scripts/prueba_carga.py` desde dentro de la red de Docker, contra **una instancia**
limitada a **2 CPU** (igual que una VM de ADR-08), con PostgreSQL 16, en Docker Desktop sobre un portátil.
Datos completos en los JSON de esta carpeta.

| Prueba | Usuarios | Pausa entre clics | Peticiones | Errores | Peticiones/s | p95 |
|---|---|---|---|---|---|---|
| Realista | 500 | 5 s de media | 3.000 | **0** | 92 | 2,1 s |
| Extrema | 500 | ninguna, todos a la vez | 2.000 | **0** | 139 | 5,8 s |

**Lectura honesta:**
- **Cero errores** en ambas: bajo carga el servicio se pone lento, pero no falla.
- **Con una sola instancia no se cumple** la meta de p95 < 800 ms. El límite es la CPU: con 2 CPU, una instancia atiende unas 140 recomendaciones por segundo.
- La meta EC-DESM-01 del documento se fijó para el **Catálogo**. IA no está en el camino crítico, y si se cae la PWA muestra recomendaciones por popularidad.
- Producción tiene **2 VMs**, lo que duplica la capacidad, pero **no se ha medido** con dos réplicas.

Optimizaciones ya aplicadas, cada una medida: caché de lectura de 5 s, INSERT directo en vez del ORM e
ítems en una sola sentencia. Una recomendación pasó de 55 ms a 14 ms y de ~11 ms a ~5 ms de CPU.

Si se exige cumplir la meta en IA, las opciones son: medir con 2 réplicas detrás del balanceador,
servir la sección "Recomendado para ti" de W1 con caché por combinación de intereses, o pasar a un
acceso asíncrono a la base de datos.
