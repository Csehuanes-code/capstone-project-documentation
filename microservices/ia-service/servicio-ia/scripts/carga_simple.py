"""Diagnóstico: peticiones por segundo contra una sola ruta. Uso: python carga_simple.py URL [N] [C]"""

import asyncio
import sys
import time

import aiohttp


async def main(url: str, n: int, concurrencia: int) -> None:
    sem = asyncio.Semaphore(concurrencia)
    conector = aiohttp.TCPConnector(limit=concurrencia)
    async with aiohttp.ClientSession(connector=conector) as s:
        async def una():
            async with sem, s.get(url) as r:
                r.raise_for_status()
                await r.read()

        inicio = time.perf_counter()
        await asyncio.gather(*(una() for _ in range(n)))
        d = time.perf_counter() - inicio
    print(f"{url}: {n / d:.0f} peticiones/s ({n} en {d:.1f} s, concurrencia {concurrencia})")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 500,
                     int(sys.argv[3]) if len(sys.argv) > 3 else 50))
