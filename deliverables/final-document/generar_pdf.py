"""Genera documento-final.pdf a partir de documento-final.md.

Requisitos: Docker (para mermaid-cli), Microsoft Edge o Google Chrome, y `pip install markdown`.
Uso, desde esta carpeta:  python generar_pdf.py

1. Extrae cada bloque ```mermaid a diagramas/NN.mmd y lo dibuja como PNG con mermaid-cli.
2. Convierte el Markdown a HTML con portada y estilos de impresión.
3. Imprime el HTML a PDF con el navegador en modo headless.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import markdown

AQUI = Path(__file__).resolve().parent
DIAGRAMAS = AQUI / "diagramas"
NAVEGADORES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
]
MERMAID = "minlag/mermaid-cli:11.4.2"


def dibujar_diagramas(texto: str) -> str:
    DIAGRAMAS.mkdir(exist_ok=True)
    configuracion = DIAGRAMAS / "config.json"
    configuracion.write_text('{"theme":"neutral","themeVariables":{"fontFamily":"Inter, Arial, sans-serif","fontSize":"15px"},'
                             '"flowchart":{"htmlLabels":true,"curve":"basis"},"er":{"layoutDirection":"TB"}}', encoding="utf-8")
    bloques = re.findall(r"```mermaid\n(.*?)```", texto, flags=re.S)
    for i, codigo in enumerate(bloques, 1):
        (DIAGRAMAS / f"{i:02d}.mmd").write_text(codigo, encoding="utf-8")
        subprocess.run(["docker", "run", "--rm", "-v", f"{DIAGRAMAS}:/data", MERMAID,
                        "-i", f"/data/{i:02d}.mmd", "-o", f"/data/{i:02d}.png", "-c", "/data/config.json",
                        "-s", "2", "-w", "1400", "-b", "white"], check=True, capture_output=True,
                       env={**os.environ, "MSYS_NO_PATHCONV": "1"})
        print("diagrama", i)
    contador = iter(range(1, len(bloques) + 1))
    return re.sub(r"```mermaid\n.*?```", lambda _: f'<img class="diagrama" src="diagramas/{next(contador):02d}.png" alt="Diagrama">',
                  texto, flags=re.S)


ESTILOS = """
@page { size: A4; margin: 18mm 16mm 20mm; }
* { box-sizing: border-box; }
body { font-family: Inter, "Segoe UI", Arial, sans-serif; font-size: 10.2pt; line-height: 1.5; color: #14262e; margin: 0; }
h1, h2, h3 { font-family: "Space Grotesk", "Segoe UI", Arial, sans-serif; color: #0b2531; line-height: 1.2; }
h1 { font-size: 21pt; margin: 0 0 6pt; }
h2 { font-size: 16pt; margin: 22pt 0 8pt; padding-bottom: 4pt; border-bottom: 2px solid #0e7c7b; break-after: avoid; }
h2:not(:first-of-type) { break-before: page; }
h3 { font-size: 12.5pt; margin: 16pt 0 6pt; break-after: avoid; color: #0e7c7b; }
p, li { orphans: 3; widows: 3; }
a { color: #0e7c7b; text-decoration: none; }
code { font-family: Consolas, "JetBrains Mono", monospace; font-size: 8.8pt; background: #eef3f2; padding: 0 3px; border-radius: 3px; }
table { width: 100%; border-collapse: collapse; margin: 8pt 0 10pt; font-size: 8.9pt; break-inside: auto; }
tr { break-inside: avoid; }
th, td { border: 1px solid #d6e0de; padding: 4pt 6pt; text-align: left; vertical-align: top; }
th { background: #0b2531; color: #fff; font-weight: 600; }
tr:nth-child(even) td { background: #f5f8f7; }
blockquote { margin: 10pt 0; padding: 8pt 12pt; border-left: 4px solid #f2a541; background: #fdf5e8; font-size: 10.5pt; }
blockquote p { margin: 0; }
img { max-width: 100%; }
img.diagrama { display: block; margin: 8pt auto 2pt; max-height: 235mm; break-inside: avoid; }
p > img { display: block; margin: 8pt auto 2pt; border: 1px solid #d6e0de; border-radius: 6px; break-inside: avoid; max-height: 200mm; }
td img { border: 1px solid #d6e0de; border-radius: 6px; max-height: 150mm; }
td:has(img) { background: #fff !important; border: 0; text-align: center; }
p > em:only-child, td > em { display: block; text-align: center; color: #586c73; font-size: 8.8pt; margin-bottom: 10pt; }
hr { display: none; }
.portada { height: 255mm; display: flex; flex-direction: column; justify-content: space-between; break-after: page; }
.portada .franja { background: #0b2531; color: #fff; padding: 26mm 14mm 16mm; border-radius: 6mm; }
.portada .franja small { color: #f2a541; letter-spacing: .2em; font-weight: 700; font-size: 9pt; }
.portada .franja h1 { color: #fff; font-size: 30pt; margin: 6mm 0 3mm; }
.portada .franja p { color: #cfe3e0; font-size: 13pt; margin: 0; }
.portada img.foto { width: 100%; height: 78mm; object-fit: cover; border-radius: 6mm; margin-top: 6mm; }
.portada .datos { font-size: 10.5pt; line-height: 1.7; }
.portada .datos b { color: #0b2531; }
.portada .logo { height: 22mm; }
"""


def portada() -> str:
    return """
<section class="portada">
  <div>
    <div class="franja">
      <small>DOCUMENTO FINAL DE ARQUITECTURA</small>
      <h1>SierraMar</h1>
      <p>Plataforma Digital para la Gestión Integrada y Sostenible del Turismo en Santa Marta</p>
    </div>
    <img class="foto" src="../../frontend/public/fotos/heroe.webp" alt="Parque Nacional Natural Tayrona">
  </div>
  <div class="datos">
    <img class="logo" src="../../docs/poster/logo-unimagdalena.png" alt="Universidad del Magdalena"><br>
    <b>Universidad del Magdalena</b> · Facultad de Ingeniería · Programa de Ingeniería de Sistemas<br>
    <b>Asignatura:</b> Arquitectura de Software, 2026-II · <b>Grupo 4</b><br>
    <b>Integrantes:</b> Carlos Sehuanes · Luis Rincón · David Hasbum · Santiago Criollo · Julián Tobias<br>
    <b>Demo:</b> https://20-226-88-58.sslip.io · <b>Repositorio:</b> github.com/Csehuanes-code/capstone-project-documentation<br>
    Santa Marta, noviembre de 2026
  </div>
</section>"""


def main() -> None:
    texto = (AQUI / "documento-final.md").read_text(encoding="utf-8")
    texto = re.sub(r"\A# .*?\n---\n", "", texto, count=1, flags=re.S)  # la portada reemplaza el encabezado
    texto = dibujar_diagramas(texto)
    cuerpo = markdown.markdown(texto, extensions=["tables", "sane_lists"])
    html = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Documento Final — SierraMar</title>'
            f'<style>{ESTILOS}</style></head><body>{portada()}{cuerpo}</body></html>')
    destino_html = AQUI / "documento-final.html"
    destino_html.write_text(html, encoding="utf-8")
    navegador = next((n for n in NAVEGADORES if Path(n).exists()), None) or shutil.which("chromium")
    subprocess.run([navegador, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={AQUI / 'documento-final.pdf'}", destino_html.as_uri()], check=True, capture_output=True)
    destino_html.unlink()
    print("PDF:", AQUI / "documento-final.pdf")


if __name__ == "__main__":
    main()
