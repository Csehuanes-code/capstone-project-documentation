"""Motor, sesiones y carga inicial de ia_db."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ia.dominio.modelos import ConfiguracionCriterios, EstadoZona, ProyeccionOferta

from .repositorios import CriteriosSql, OfertasSql, ZonasSql
from .tablas import Base, ConfiguracionCriteriosTabla, ProyeccionOfertaTabla


def crear_motor(url: str) -> Engine:
    """Ej.: postgresql+psycopg://usuario:clave@host:5432/ia_db"""
    if url.startswith("sqlite") and ":memory:" in url:
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    if url.startswith("postgresql"):
        # Falla rápido si la base no responde, para que /health/ready no se cuelgue.
        return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    return create_engine(url, pool_pre_ping=True)


def crear_sesiones(motor: Engine) -> sessionmaker[Session]:
    return sessionmaker(motor, expire_on_commit=False)


def crear_esquema(motor: Engine) -> None:
    """Solo para desarrollo y pruebas. En producción el esquema se gestiona con migraciones."""
    Base.metadata.create_all(motor)


def sembrar_si_vacia(
    sesiones: sessionmaker[Session],
    criterios: ConfiguracionCriterios,
    zonas: list[EstadoZona],
    ofertas: list[ProyeccionOferta],
) -> bool:
    """Carga datos de prueba si no hay ofertas. Devuelve True si sembró.

    Los pesos v1 los inserta la migración inicial; aquí solo se agregan si faltan
    (caso de una base creada con crear_esquema, sin Alembic).
    """
    with sesiones() as s:
        if s.scalar(select(ProyeccionOfertaTabla.oferta_id).limit(1)) is not None:
            return False
        sin_criterios = s.scalar(select(ConfiguracionCriteriosTabla.version).limit(1)) is None
    if sin_criterios:
        CriteriosSql(sesiones).agregar_version(criterios)
    for z in zonas:
        ZonasSql(sesiones).guardar(z)
    for o in ofertas:
        OfertasSql(sesiones).guardar(o)
    return True
