"""Mantiene la demo "viva" (se puede correr a diario; es idempotente).

1. Franjas: cada oferta tiene horarios para las próximas semanas (el calendario del detalle se ve lleno).
2. Ocupación de HOY: reserva lo justo para que el mapa muestre colores reales
   (Tayrona saturada, Minca moderada). Analítica solo cuenta reservas cuyo servicio es hoy,
   así que sin esto todas las zonas aparecen "tranquilas".

Solo usa la librería estándar para poder correr en el servidor sin instalar nada:
    URL_GATEWAY=https://mi-dominio python3 scripts/demo/ambientar.py
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

GW = os.environ.get("URL_GATEWAY", "http://localhost:8080").rstrip("/")
DIAS = int(os.environ.get("AMBIENTAR_DIAS", "40"))
PRESTADOR = ("prestador@turismo.co", os.environ.get("PRESTADOR_PASSWORD", "Prestador-Demo-2026"))
TURISTA = ("turista@turismo.co", os.environ.get("TURISTA_PASSWORD", "Turista-Demo-2026"))
# Umbral diario configurado por sembrar.py y ocupación que queremos mostrar hoy.
OBJETIVO = {"tayrona": (12, 0.92), "minca": (60, 0.65)}
COLOMBIA = timezone(timedelta(hours=-5))
CUPO_HOY = 120  # franja de las 23:30 de hoy, usada solo para mover la ocupación


def llamar(metodo: str, ruta: str, cuerpo: object = None, token: str | None = None,
           cabeceras: dict[str, str] | None = None) -> tuple[int, object]:
    h = {"Content-Type": "application/json", **(cabeceras or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(GW + ruta, data=datos, headers=h, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]


def entrar(email: str, clave: str) -> str:
    estado, r = llamar("POST", "/api/v1/auth/sesiones", {"email": email, "password": clave})
    if estado != 200 or not isinstance(r, dict):
        raise SystemExit(f"No se pudo iniciar sesión como {email}: {estado} {r}")
    return str(r["access_token"])


def asegurar_tarifa(oferta: dict[str, str], token: str) -> None:
    """Las reservas exigen una tarifa vigente; si la oferta no tiene, el prestador publica una."""
    _, detalle = llamar("GET", f"/api/v1/catalogo/ofertas/{oferta['id']}")
    if isinstance(detalle, dict) and detalle.get("tarifas"):
        return
    desde = datetime.now(COLOMBIA).date()
    estado, _ = llamar("POST", f"/api/v1/catalogo/ofertas/{oferta['id']}/tarifas", {
        "temporada": "media", "vigente_desde": desde.isoformat(),
        "vigente_hasta": (desde + timedelta(days=365)).isoformat(), "precio_por_persona": 110000, "moneda": "COP"}, token)
    print(f"Tarifa para {oferta['nombre_es']}: {estado}")


def main() -> None:
    hoy = datetime.now(COLOMBIA).date()
    prestador = entrar(*PRESTADOR)
    turista = entrar(*TURISTA)
    _, zonas = llamar("GET", "/api/v1/catalogo/zonas")
    codigo = {z["id"]: z["codigo"] for z in zonas}  # type: ignore[union-attr]
    _, catalogo = llamar("GET", "/api/v1/catalogo/ofertas?limit=50")
    ofertas = catalogo["items"]  # type: ignore[index]

    # 1. Franjas para las próximas semanas (algunos días con pocos cupos para que se note en el calendario).
    creadas = 0
    for i, o in enumerate(ofertas):
        _, existentes = llamar("GET", f"/api/v1/ofertas/{o['id']}/disponibilidad")
        ya = {(f["fecha"], f["hora_inicio"][:5]) for f in existentes} if isinstance(existentes, list) else set()
        for d in range(1, DIAS + 1):
            if (d + i) % 5 == 4:  # días de descanso del prestador
                continue
            fecha = (hoy + timedelta(days=d)).isoformat()
            for hora, cupo in (("08:00", 12), ("14:00", 2 if (d + i) % 4 == 0 else 8)):
                if (fecha, hora) in ya:
                    continue
                estado, _ = llamar("POST", "/api/v1/prestador/franjas", {
                    "oferta_id": o["id"], "fecha": fecha, "hora_inicio": hora, "cupo_total": cupo}, prestador)
                creadas += estado == 201
    print(f"Franjas nuevas: {creadas}")

    # 2. Ocupación de hoy por zona (la mide Analítica y la publica a IA).
    _, populares = llamar("GET", "/api/v1/ia/populares?limite=20")
    zona_de_oferta = {o["id"]: codigo.get(o["zona_id"]) for o in ofertas}
    ocupacion_actual: dict[str, float] = {}
    for p in populares if isinstance(populares, list) else []:
        z = zona_de_oferta.get(p.get("oferta_id", ""))
        if z and p["zona"].get("ocupacion") is not None:
            ocupacion_actual[z] = max(ocupacion_actual.get(z, 0.0), float(p["zona"]["ocupacion"]))

    for zona, (umbral, meta) in OBJETIVO.items():
        oferta = next((o for o in ofertas if codigo.get(o["zona_id"]) == zona), None)
        if oferta is None:
            continue
        asegurar_tarifa(oferta, prestador)
        llamar("POST", "/api/v1/prestador/franjas", {
            "oferta_id": oferta["id"], "fecha": hoy.isoformat(), "hora_inicio": "23:30", "cupo_total": CUPO_HOY}, prestador)
        _, de_hoy = llamar("GET", f"/api/v1/ofertas/{oferta['id']}/disponibilidad?fecha={hoy.isoformat()}")
        franja = next((f for f in de_hoy if f["hora_inicio"].startswith("23:30")), None) if isinstance(de_hoy, list) else None
        if franja is None:
            print(f"{zona}: no hay franja de hoy disponible")
            continue
        # Lo ya reservado en la franja de la demo: así es idempotente aunque IA aún no reciba la ocupación.
        libres = franja["cupo_disponible"]
        faltan = math.ceil(umbral * meta) - max(CUPO_HOY - libres, round(ocupacion_actual.get(zona, 0.0) * umbral))
        reservadas = 0
        while faltan > 0 and libres > 0:
            personas = min(faltan, 20, libres)
            estado, r = llamar("POST", "/api/v1/reservas", {
                "franja_id": franja["id"], "personas": personas, "correo_turista": TURISTA[0], "idioma": "es",
                "datos_pago": {"numero_tarjeta": "4111111111111111"}, "acompanantes": []},
                turista, {"Idempotency-Key": str(uuid.uuid4())})
            if estado != 201:
                print(f"{zona}: {oferta['nombre_es']} rechazó la reserva ({estado}): {r}")
                break
            reservadas += personas
            faltan -= personas
            libres -= personas
        print(f"{zona}: +{reservadas} visitantes hoy (umbral {umbral}, meta {meta:.0%})")


if __name__ == "__main__":
    main()
