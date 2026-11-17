"""Prueba de carga del servicio IA (evidencia para EC-DESM-01 / EC-ESC-01).

Simula N turistas simultáneos; cada uno hace varias peticiones seguidas con intereses al azar
(como en W1/W3): genera su recomendación y luego abre "¿Por qué veo esto?".

Uso:
    python scripts/prueba_carga.py --usuarios 500 --peticiones 4
    python scripts/prueba_carga.py --url http://127.0.0.1:8000 --usuarios 100 --salida docs/evidencias

Meta del documento de diseño: p95 < 800 ms con 500 usuarios simultáneos, sin errores.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

INTERESES = ["naturaleza", "cultura", "gastronomia", "historia", "playa", "aventura"]
META_P95_MS = 800


async def turista(cliente: aiohttp.ClientSession, url: str, peticiones: int, tiempos: list,
                  errores: list, pausa: float = 0):
    if pausa:
        await asyncio.sleep(random.uniform(0, pausa))  # los turistas no llegan todos a la vez
    for _ in range(peticiones):
        intereses = ",".join(random.sample(INTERESES, k=random.randint(1, 3)))
        inicio = time.perf_counter()
        try:
            async with cliente.get(
                f"{url}/api/v1/ia/recomendaciones", params={"intereses": intereses, "limite": 5}
            ) as r:
                cuerpo = await r.json() if r.status == 200 else None
            tiempos.append(("recomendaciones", (time.perf_counter() - inicio) * 1000))
            if cuerpo is None:
                errores.append(f"recomendaciones {r.status}")
                continue

            inicio = time.perf_counter()
            async with cliente.get(f"{url}/api/v1/ia/recomendaciones/{cuerpo['id']}") as r:
                await r.read()
            tiempos.append(("por_que_veo_esto", (time.perf_counter() - inicio) * 1000))
            if r.status != 200:
                errores.append(f"por_que_veo_esto {r.status}")
            if pausa:
                await asyncio.sleep(random.uniform(0.5 * pausa, 1.5 * pausa))  # lee y decide
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            errores.append(type(e).__name__)


def percentil(datos: list[float], p: float) -> float:
    datos = sorted(datos)
    k = (len(datos) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(datos) - 1)
    return datos[f] + (datos[c] - datos[f]) * (k - f)


def resumen(nombre: str, ms: list[float]) -> dict:
    return {
        "endpoint": nombre,
        "peticiones": len(ms),
        "p50_ms": round(percentil(ms, 50), 1),
        "p95_ms": round(percentil(ms, 95), 1),
        "p99_ms": round(percentil(ms, 99), 1),
        "max_ms": round(max(ms), 1),
        "promedio_ms": round(statistics.mean(ms), 1),
    }


async def main(args) -> int:
    tiempos: list[tuple[str, float]] = []
    errores: list[str] = []
    conector = aiohttp.TCPConnector(limit=args.usuarios)
    tiempo_max = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=conector, timeout=tiempo_max) as cliente:
        async with cliente.get(f"{args.url}/health/ready") as r:
            r.raise_for_status()
        inicio = time.perf_counter()
        await asyncio.gather(
            *(turista(cliente, args.url, args.peticiones, tiempos, errores, args.pausa)
              for _ in range(args.usuarios))
        )
        duracion = time.perf_counter() - inicio

    todos = [ms for _, ms in tiempos]
    por_endpoint = [
        resumen(n, [ms for e, ms in tiempos if e == n])
        for n in ("recomendaciones", "por_que_veo_esto")
        if any(e == n for e, _ in tiempos)
    ]
    total = len(tiempos) + len([e for e in errores if " " not in e])
    resultado = {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url": args.url,
        "usuarios_simultaneos": args.usuarios,
        "pausa_media_s": args.pausa,
        "peticiones_por_usuario": args.peticiones * 2,
        "peticiones_totales": total,
        "duracion_s": round(duracion, 1),
        "peticiones_por_segundo": round(total / duracion, 1),
        "errores": len(errores),
        "tasa_error_pct": round(100 * len(errores) / max(total, 1), 2),
        "general": resumen("todas", todos) if todos else None,
        "por_endpoint": por_endpoint,
        "meta_p95_ms": META_P95_MS,
    }
    resultado["cumple_meta"] = bool(
        todos and resultado["general"]["p95_ms"] < META_P95_MS and not errores
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    if errores:
        print("Errores (primeros 10):", errores[:10])
    if args.salida:
        carpeta = Path(args.salida)
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / f"carga-{args.usuarios}u-pausa{args.pausa:g}s.json"
        archivo.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Guardado en {archivo}")
    return 0 if resultado["cumple_meta"] else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--usuarios", type=int, default=500)
    p.add_argument("--peticiones", type=int, default=2, help="recomendaciones por usuario")
    p.add_argument("--pausa", type=float, default=0,
                   help="segundos medios entre clics de un turista (0 = prueba extrema)")
    p.add_argument("--salida", default=None, help="carpeta donde guardar el resultado JSON")
    raise SystemExit(asyncio.run(main(p.parse_args())))
