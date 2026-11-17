"""Datos de demostración, cargados por la API pública (gateway) como lo haría un usuario real.

Recorre la integración completa entre los 5 microservicios:
  1. Auth: el administrador inicial inicia sesión; se registran un prestador y un turista.
  2. Auth → RabbitMQ → Reservas → Mailpit: llega el correo de confirmación; se confirma la cuenta.
  3. El prestador pide verificación y el administrador la aprueba.
     Auth → RabbitMQ → Catálogo: el prestador queda verificado y puede publicar.
  4. Catálogo: el prestador publica ofertas con tarifa y política de cancelación.
     Catálogo → RabbitMQ → IA y Reservas: ambos reciben las ofertas.
  5. Reservas: el prestador publica franjas de disponibilidad.
  6. Analítica: el administrador configura la capacidad de carga por zona.

Es idempotente: se puede volver a ejecutar sin duplicar datos.
Uso:  docker compose run --rm demo
"""

from __future__ import annotations

import os
import re
import sys
import time
from datetime import date, timedelta
from typing import Any

import httpx

GW = os.environ.get("URL_GATEWAY", "http://localhost:8080").rstrip("/")
MAILPIT = os.environ.get("URL_MAILPIT", "http://localhost:8025").rstrip("/")
ADMIN = (os.environ.get("ADMIN_EMAIL", "admin@turismo.co"), os.environ.get("ADMIN_PASSWORD", "Admin-Demo-2026"))
PRESTADOR = ("prestador@turismo.co", "Prestador-Demo-2026")
TURISTA = ("turista@turismo.co", "Turista-Demo-2026")

OFERTAS = [
    {"nombre_es": "Tour cascadas de Minca", "nombre_en": "Minca waterfalls tour", "zona": "minca",
     "categorias": ["naturaleza", "aventura"], "precio": 120000, "sost": 0.9, "duracion": 6,
     "descripcion_es": "Caminata guiada a las cascadas de Marinka y Pozo Azul, con almuerzo campesino.",
     "descripcion_en": "Guided hike to Marinka and Pozo Azul waterfalls, with a farm lunch."},
    {"nombre_es": "Caminata a Pueblito Chairama", "nombre_en": "Pueblito Chairama hike", "zona": "tayrona",
     "categorias": ["naturaleza", "historia"], "precio": 95000, "sost": 0.8, "duracion": 5,
     "descripcion_es": "Sendero ancestral tayrona dentro del Parque Nacional.",
     "descripcion_en": "Ancestral Tayrona trail inside the National Park."},
    {"nombre_es": "Excursión sostenible a Playa Cristal", "nombre_en": "Sustainable Playa Cristal trip",
     "zona": "tayrona", "categorias": ["playa", "naturaleza"], "precio": 135000, "sost": 0.7, "duracion": 7,
     "descripcion_es": "Lancha y snorkel en una de las playas más claras del Caribe.",
     "descripcion_en": "Boat ride and snorkeling at one of the clearest Caribbean beaches."},
    {"nombre_es": "Taller de cocina caribeña", "nombre_en": "Caribbean cooking workshop", "zona": "centro",
     "categorias": ["gastronomia", "cultura"], "precio": 80000, "sost": 0.85, "duracion": 3,
     "descripcion_es": "Cocina pescado frito, patacón y arroz con coco con una cocinera samaria.",
     "descripcion_en": "Cook fried fish, patacón and coconut rice with a local cook."},
    {"nombre_es": "Recorrido histórico Centro y Museo del Oro", "nombre_en": "Historic center and Gold Museum",
     "zona": "centro", "categorias": ["historia", "cultura"], "precio": 45000, "sost": 1.0, "duracion": 3,
     "descripcion_es": "La ciudad más antigua de Colombia, a pie, con guía bilingüe.",
     "descripcion_en": "Colombia's oldest city on foot, with a bilingual guide."},
    {"nombre_es": "Bautismo de buceo en Taganga", "nombre_en": "Discover scuba in Taganga", "zona": "taganga",
     "categorias": ["aventura", "playa"], "precio": 180000, "sost": 0.6, "duracion": 4,
     "descripcion_es": "Primera inmersión con instructor certificado.",
     "descripcion_en": "First dive with a certified instructor."},
    {"nombre_es": "Sendero Los Naranjos", "nombre_en": "Los Naranjos trail", "zona": "los-naranjos",
     "categorias": ["naturaleza"], "precio": 75000, "sost": 0.95, "duracion": 4,
     "descripcion_es": "Bosque seco tropical y desembocadura del río Piedras.",
     "descripcion_en": "Tropical dry forest and the Piedras river mouth."},
]
# Capacidad de carga por zona (visitantes/día). Tayrona baja para que la demo muestre alertas.
UMBRALES = {"tayrona": 12, "minca": 60, "centro": 200, "taganga": 80, "los-naranjos": 40, "rodadero": 300}


def paso(texto: str) -> None:
    print(f"\n==> {texto}", flush=True)


def esperar(descripcion: str, intento: Any, segundos: float = 60) -> Any:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        resultado = intento()
        if resultado:
            return resultado
        time.sleep(1)
    sys.exit(f"ERROR: se agotó la espera: {descripcion}")


def login(c: httpx.Client, email: str, clave: str) -> dict[str, str]:
    r = c.post(f"{GW}/api/v1/auth/sesiones", json={"email": email, "password": clave})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def token_de_confirmacion(c: httpx.Client, email: str) -> str | None:
    r = c.get(f"{MAILPIT}/api/v1/search", params={"query": f"to:{email}"})
    for m in r.json().get("messages", []):
        cuerpo = c.get(f"{MAILPIT}/api/v1/message/{m['ID']}").json().get("Text", "")
        if hallado := re.search(r"/confirmar\?token=([\w-]+)", cuerpo):
            return hallado.group(1)
    return None


def asegurar_usuario(c: httpx.Client, email: str, clave: str, rol: str) -> dict[str, str]:
    r = c.post(f"{GW}/api/v1/auth/usuarios", json={
        "email": email, "password": clave, "role": rol, "consent_accepted": True, "policy_version": "2026-01"})
    if r.status_code == 201:
        print(f"   registrado {email}; esperando el correo de confirmación (Auth → RabbitMQ → Reservas → Mailpit)")
        token = esperar("correo de confirmación", lambda: token_de_confirmacion(c, email))
        c.post(f"{GW}/api/v1/auth/confirmaciones", json={"token": token}).raise_for_status()
        print("   cuenta confirmada desde el enlace del correo")
    elif r.status_code != 409:
        r.raise_for_status()
    return login(c, email, clave)


def main() -> None:
    with httpx.Client(timeout=15) as c:
        paso("Esperando a que el gateway y los servicios respondan")
        esperar("gateway", lambda: c.get(f"{GW}/api/v1/catalogo/zonas").status_code == 200, 120)

        paso("Auth: administrador, prestador y turista")
        admin = login(c, *ADMIN)
        prestador = asegurar_usuario(c, *PRESTADOR, "prestador")
        asegurar_usuario(c, *TURISTA, "turista")

        paso("Verificación del prestador (CU-26 y CU-28)")
        r = c.post(f"{GW}/api/v1/auth/prestadores/verificaciones", headers=prestador, json={
            "business_name": "Guías Sierra Viva", "nit": "900123456-7", "rnt": "RNT-45821"})
        print(f"   solicitud enviada: HTTP {r.status_code}")
        for s in c.get(f"{GW}/api/v1/auth/admin/verificaciones", headers=admin, params={"estado": "enviada"}).json():
            c.post(f"{GW}/api/v1/auth/admin/verificaciones/{s['id']}/decision", headers=admin, json={
                "decision": "aprobar", "justification": "RNT vigente y documentos completos."}).raise_for_status()
            print(f"   aprobada {s['business_name']} (Auth → RabbitMQ → Catálogo)")

        paso("Catálogo: ofertas con tarifa y política")
        zonas = {z["codigo"]: z["id"] for z in c.get(f"{GW}/api/v1/catalogo/zonas").json()}
        tipos = {t["codigo"]: t["id"] for t in c.get(f"{GW}/api/v1/catalogo/tipos-servicio").json()}
        existentes = {o["nombre_es"]: o for o in
                      c.get(f"{GW}/api/v1/catalogo/ofertas", params={"limit": 100}).json()["items"]}
        hoy = date.today()
        ofertas: list[dict[str, Any]] = []
        for o in OFERTAS:
            if o["nombre_es"] in existentes:
                ofertas.append(existentes[o["nombre_es"]])
                continue
            cuerpo = {
                "tipo_servicio_id": tipos["tour"], "zona_id": zonas[o["zona"]],
                "nombre_es": o["nombre_es"], "nombre_en": o["nombre_en"],
                "descripcion_es": o["descripcion_es"], "descripcion_en": o["descripcion_en"],
                "atributos": {"duracion_horas": o["duracion"], "nivel_dificultad": "media",
                              "categorias": o["categorias"]},
                "estado": "publicada", "indice_sostenibilidad": o["sost"],
            }

            def publicar(cuerpo: dict[str, Any] = cuerpo) -> dict[str, Any] | None:
                r = c.post(f"{GW}/api/v1/catalogo/ofertas", headers=prestador, json=cuerpo)
                return r.json() if r.status_code == 201 else None  # 403 hasta que llegue la verificación

            creada = esperar(f"publicar {o['nombre_es']}", publicar)
            oid = creada["id"]
            c.post(f"{GW}/api/v1/catalogo/ofertas/{oid}/tarifas", headers=prestador, json={
                "temporada": "media", "vigente_desde": hoy.isoformat(),
                "vigente_hasta": (hoy + timedelta(days=365)).isoformat(),
                "precio_por_persona": o["precio"], "moneda": "COP"}).raise_for_status()
            c.put(f"{GW}/api/v1/catalogo/ofertas/{oid}/politica-cancelacion", headers=prestador, json={
                "horas_reembolso_total": 48, "horas_reembolso_parcial": 24,
                "porcentaje_reembolso_parcial": 50}).raise_for_status()
            print(f"   publicada {o['nombre_es']} ({o['zona']})")
            ofertas.append(creada)

        paso("Reservas: franjas de disponibilidad (cuando llega cada oferta por evento)")
        for oferta in ofertas:
            ya = c.get(f"{GW}/api/v1/ofertas/{oferta['id']}/disponibilidad").json()
            if ya:
                continue
            for dias in (2, 5, 9):
                for hora, cupo in (("08:00", 10), ("14:00", 3)):
                    def crear(dias: int = dias, hora: str = hora, cupo: int = cupo) -> bool:
                        r = c.post(f"{GW}/api/v1/prestador/franjas", headers=prestador, json={
                            "oferta_id": oferta["id"], "fecha": (hoy + timedelta(days=dias)).isoformat(),
                            "hora_inicio": hora, "cupo_total": cupo})
                        return r.status_code == 201  # 409 hasta que llegue catalogo.oferta.publicada
                    esperar(f"franja de {oferta['nombre_es']}", crear)
            print(f"   6 franjas para {oferta['nombre_es']}")

        paso("Analítica: capacidad de carga por zona (CU-31)")
        for zona, maximo in UMBRALES.items():
            c.put(f"{GW}/api/v1/analitica/umbrales", headers=admin, json={
                "zona_id": zona, "visitantes_maximos": maximo, "confirmar_advertencia": True}).raise_for_status()
        print(f"   {len(UMBRALES)} umbrales configurados")

        paso("IA: recomendaciones con las ofertas reales")
        rec = esperar("ofertas en IA", lambda: c.get(f"{GW}/api/v1/ia/recomendaciones",
                       params={"intereses": "naturaleza,aventura"}).json().get("items"))
        for item in rec[:3]:
            print(f"   {item.get('nombre')}: puntaje {item.get('puntaje')}")

        print("\nListo. Usuarios de demostración:")
        for email, clave in (ADMIN, PRESTADOR, TURISTA):
            print(f"   {email} / {clave}")


if __name__ == "__main__":
    main()
