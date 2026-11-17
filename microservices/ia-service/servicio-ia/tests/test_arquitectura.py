"""EC-MANT-01: el CI falla si una capa viola la regla de dependencia de Clean Architecture."""

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1] / "src" / "ia"

# capa -> paquetes internos que puede importar (además de sí misma)
PERMITIDOS = {
    "dominio": set(),
    "aplicacion": {"dominio"},
    "api": {"aplicacion"},
    "infraestructura": {"aplicacion", "dominio"},
}
# frameworks que no pueden aparecer en las capas internas
PROHIBIDOS_EXTERNOS = {
    "dominio": {"fastapi", "pydantic", "sqlalchemy", "psycopg", "pika", "aio_pika", "starlette"},
    "aplicacion": {"fastapi", "pydantic", "sqlalchemy", "psycopg", "pika", "aio_pika", "starlette"},
}


def _imports(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    capa = archivo.relative_to(RAIZ).parts[0]
    modulos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:  # import relativo: se resuelve dentro de la misma capa o subiendo
                partes = ["ia", capa] if nodo.level == 1 else ["ia"]
                modulos.add(".".join(partes + ([nodo.module] if nodo.module else [])))
            elif nodo.module:
                modulos.add(nodo.module)
    return modulos


def _archivos():
    for capa in PERMITIDOS:
        for archivo in sorted((RAIZ / capa).rglob("*.py")):
            yield pytest.param(capa, archivo, id=f"{capa}/{archivo.name}")


@pytest.mark.parametrize(("capa", "archivo"), list(_archivos()))
def test_regla_de_dependencia(capa, archivo):
    for modulo in _imports(archivo):
        partes = modulo.split(".")
        if partes[0] == "ia" and len(partes) > 1:
            destino = partes[1]
            assert destino == capa or destino in PERMITIDOS[capa], (
                f"{capa} no puede depender de {destino} ({archivo.name} importa {modulo})"
            )
        assert partes[0] not in PROHIBIDOS_EXTERNOS.get(capa, set()), (
            f"{capa} no puede usar el framework {partes[0]} ({archivo.name})"
        )
