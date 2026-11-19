"""Genera laboratorio.pdf desde laboratorio.md y los diagramas PlantUML.

Requisitos: Docker (imagen plantuml/plantuml), Microsoft Edge o Google Chrome y `pip install markdown`.
Uso, desde esta carpeta:  python generar_pdf.py
"""
import os
import shutil
import subprocess
from pathlib import Path

import markdown

AQUI = Path(__file__).resolve().parent
NAVEGADORES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
               r"C:\Program Files\Google\Chrome\Application\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium"]

ESTILOS = """
@page { size: Letter; margin: 20mm 18mm 20mm; }
body { font-family: Inter, "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1f2a30; margin: 0; }
h1, h2, h3 { font-family: "Source Serif 4", Georgia, serif; font-weight: 500; color: #14212a; line-height: 1.2; }
h1 { font-size: 26pt; margin: 0 0 10pt; }
h2 { font-size: 18pt; margin: 22pt 0 8pt; break-after: avoid; }
h3 { font-size: 13.5pt; margin: 16pt 0 6pt; break-after: avoid; }
a { color: #0e7c7b; text-decoration: none; }
code { font-family: Consolas, "JetBrains Mono", monospace; font-size: 8.8pt; background: #f1f1ee; padding: 0 3px; border-radius: 3px; }
pre { background: #f5f5f2; border-radius: 6px; padding: 10pt 12pt; font-size: 7.9pt; line-height: 1.4; white-space: pre-wrap; }
pre code { background: none; padding: 0; font-size: inherit; }
table { width: 100%; border-collapse: collapse; margin: 8pt 0 12pt; font-size: 9pt; }
tr { break-inside: avoid; }
th, td { border: 1px solid #e2e2dc; padding: 5pt 7pt; text-align: left; vertical-align: top; }
th { background: #f3f3ef; font-weight: 500; color: #4a565c; }
blockquote { margin: 10pt 0; padding: 4pt 0 4pt 12pt; border-left: 3px solid #cfcfc8; color: #2a353b; }
img { display: block; max-width: 100%; max-height: 225mm; margin: 10pt auto 2pt; break-inside: avoid; }
p > em:only-child { display: block; font-size: 10.5pt; margin-bottom: 10pt; }
"""


def main() -> None:
    subprocess.run(["docker", "run", "--rm", "-v", f"{AQUI / 'diagramas'}:/data", "-w", "/data",
                    "plantuml/plantuml:1.2024.7", "-tpng", "-Sdpi=170", "f*.puml"],
                   check=True, capture_output=True, env={**os.environ, "MSYS_NO_PATHCONV": "1"})
    cuerpo = markdown.markdown((AQUI / "laboratorio.md").read_text(encoding="utf-8"),
                               extensions=["tables", "fenced_code", "sane_lists"])
    html = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Laboratorio: Documentación de Arquitecturas de Software</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:wght@400;500&display=swap">'
            f'<style>{ESTILOS}</style></head><body>{cuerpo}</body></html>')
    destino = AQUI / "laboratorio.html"
    destino.write_text(html, encoding="utf-8")
    navegador = next((n for n in NAVEGADORES if Path(n).exists()), None) or shutil.which("chromium")
    subprocess.run([navegador, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    "--virtual-time-budget=8000", f"--print-to-pdf={AQUI / 'laboratorio.pdf'}", destino.as_uri()],
                   check=True, capture_output=True)
    destino.unlink()
    print("PDF:", AQUI / "laboratorio.pdf")


if __name__ == "__main__":
    main()
