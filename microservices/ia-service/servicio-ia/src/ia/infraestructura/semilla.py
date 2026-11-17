"""Datos de prueba inventados, tomados de los bocetos W1 y W3 del documento de diseño.

Mientras Catálogo y Analítica no publiquen eventos, estas proyecciones hacen sus veces.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ia.dominio.modelos import ConfiguracionCriterios, Criterio, EstadoZona, ProyeccionOferta

_MEDIDO = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)

CRITERIOS_V1 = ConfiguracionCriterios(
    version=1,
    pesos={
        Criterio.AFINIDAD: 0.45,
        Criterio.CALIDAD: 0.25,
        Criterio.DESCONGESTION: 0.20,
        Criterio.SOSTENIBILIDAD: 0.10,
    },
    creada_en=_MEDIDO,
)

ZONAS = [
    EstadoZona("minca", "Minca", 0.30, _MEDIDO),
    EstadoZona("tayrona", "Tayrona", 0.92, _MEDIDO),
    EstadoZona("centro", "Centro Histórico", 0.35, _MEDIDO),
    EstadoZona("los-naranjos", "Los Naranjos", 0.25, _MEDIDO),
    EstadoZona("taganga", "Taganga", 0.55, _MEDIDO),
]


def _oferta(oid, nombre, zona, cats, nota, resenas, sost, prestador, reservas):
    return ProyeccionOferta(
        oferta_id=oid,
        nombre=nombre,
        zona_id=zona,
        categorias=frozenset(cats),
        calificacion_promedio=nota,
        numero_resenas=resenas,
        indice_sostenibilidad=sost,
        prestador_id=prestador,
        reservas_confirmadas=reservas,
    )


OFERTAS = [
    _oferta("minca-cascadas", "Tour cascadas de Minca", "minca",
            {"naturaleza", "aventura"}, 4.7, 32, 1.0, "prest-guias-sierra-viva", 40),
    _oferta("pueblito-caminata", "Caminata Pueblito", "tayrona",
            {"naturaleza", "cultura"}, 4.8, 210, 0.8, "prest-tayrona-tours", 180),
    _oferta("cocina-caribena", "Taller de cocina caribeña", "centro",
            {"cultura", "gastronomia"}, 4.5, 12, 0.7, "prest-sabor-caribe", 25),
    _oferta("museo-oro", "Museo del Oro", "centro",
            {"cultura", "historia"}, 4.6, 150, 0.9, "prest-banrep", 90),
    _oferta("playa-cristal", "Playa Cristal", "tayrona",
            {"playa", "naturaleza"}, 4.4, 300, 0.6, "prest-tayrona-tours", 220),
    _oferta("sendero-naranjos", "Sendero Los Naranjos", "los-naranjos",
            {"naturaleza", "cultura"}, 4.5, 40, 0.9, "prest-guias-sierra-viva", 15),
    _oferta("taganga-buceo", "Bautizo de buceo en Taganga", "taganga",
            {"playa", "aventura"}, 4.6, 80, 0.7, "prest-taganga-dive", 60),
]
