#!/usr/bin/env python3
"""Exporta el OpenAPI público de Reservas al directorio único de contratos."""

import argparse
import json
from pathlib import Path
import sys

SERVICIO = Path(__file__).resolve().parents[1]
RAIZ_REPO = SERVICIO.parents[1]
sys.path.insert(0, str(SERVICIO / "src"))

from reservas.main import app  # noqa: E402

DESTINO = RAIZ_REPO / "contratos" / "reservas-openapi.json"


def contenido_openapi() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="comprueba que el contrato guardado coincide con la API actual",
    )
    args = parser.parse_args()
    esperado = contenido_openapi()
    if args.check:
        if not DESTINO.exists() or DESTINO.read_text(encoding="utf-8") != esperado:
            print(f"{DESTINO} no coincide con la API actual; ejecuta el script sin --check.")
            return 1
        print(f"OpenAPI actualizado: {DESTINO.relative_to(RAIZ_REPO)}")
        return 0
    DESTINO.write_text(esperado, encoding="utf-8")
    print(f"OpenAPI exportado: {DESTINO.relative_to(RAIZ_REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
