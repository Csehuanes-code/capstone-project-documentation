"""EC-MANT-01 con import-linter: ejecuta los contratos de .importlinter como parte de pytest."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def test_contratos_de_import_linter():
    ejecutable = shutil.which("lint-imports", path=str(Path(sys.executable).parent))
    if ejecutable is None:
        pytest.skip("import-linter no está instalado")
    entorno = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    resultado = subprocess.run(
        [ejecutable, "--config", str(RAIZ / ".importlinter")],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
