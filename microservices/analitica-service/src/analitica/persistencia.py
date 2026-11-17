"""Adaptadores SQLAlchemy/PostgreSQL para hechos, umbrales, alertas y outbox."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    and_,
    create_engine,
    func,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from analitica.configuracion import config
from analitica.dominio import ZONAS_NOMBRE, ReservaConfirmada, UmbralZona, hoy_colombia

metadata = MetaData()
reservas = Table(
    "reserva_hecho", metadata,
    Column("evento_id", String(36), primary_key=True), Column("reserva_id", String(100), nullable=False, unique=True),
    Column("oferta_id", String(100), nullable=False), Column("zona_id", String(40), nullable=False, index=True),
    Column("personas", Integer, nullable=False), Column("fecha_servicio", Date, nullable=False, index=True),
    Column("total", Numeric(14, 2), nullable=False), Column("creado_en", DateTime(timezone=True), nullable=False),
)
eventos_procesados = Table(
    "evento_procesado", metadata, Column("evento_id", String(36), primary_key=True),
    Column("tipo", String(100), nullable=False), Column("procesado_en", DateTime(timezone=True), nullable=False),
)
umbrales = Table(
    "umbral_zona", metadata, Column("zona_id", String(40), primary_key=True),
    Column("visitantes_maximos", Integer, nullable=False), Column("periodo_dias", Integer, nullable=False, default=1),
    Column("actualizado_en", DateTime(timezone=True), nullable=False),
)
alertas = Table(
    "alerta_capacidad", metadata, Column("id", String(36), primary_key=True),
    Column("zona_id", String(40), nullable=False, index=True), Column("ocupacion", Numeric(10, 4), nullable=False),
    Column("visitantes", Integer, nullable=False), Column("umbral", Integer, nullable=False),
    Column("creada_en", DateTime(timezone=True), nullable=False), Column("resuelta_en", DateTime(timezone=True)),
)
outbox = Table(
    "outbox_evento", metadata, Column("evento_id", String(36), primary_key=True),
    Column("tipo", String(100), nullable=False), Column("datos", JSON, nullable=False),
    Column("ocurrido_en", DateTime(timezone=True), nullable=False), Column("publicado_en", DateTime(timezone=True)),
    Column("intentos", Integer, nullable=False, default=0), Column("disponible_en", DateTime(timezone=True), nullable=False),
)
_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(config.database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _factory
    if _factory is None:
        _factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _factory


class RepositorioSql:
    def __init__(self, factory: sessionmaker[Session] | None = None) -> None:
        self._factory = factory or get_session_factory()

    def guardar_umbral(self, umbral: UmbralZona) -> None:
        with self._factory.begin() as session:
            values = {"zona_id": umbral.zona_id, "visitantes_maximos": umbral.visitantes_maximos,
                      "periodo_dias": umbral.periodo_dias, "actualizado_en": datetime.now(UTC)}
            stmt = insert(umbrales).values(**values).on_conflict_do_update(
                index_elements=[umbrales.c.zona_id], set_={k: v for k, v in values.items() if k != "zona_id"}
            )
            session.execute(stmt)
            self._actualizar_ocupacion(session, umbral.zona_id)

    def obtener_umbrales(self) -> list[UmbralZona]:
        with self._factory() as session:
            rows = session.execute(select(umbrales).order_by(umbrales.c.zona_id)).mappings()
            return [UmbralZona(r["zona_id"], r["visitantes_maximos"], r["periodo_dias"]) for r in rows]

    def obtener_umbral(self, zona_id: str) -> UmbralZona | None:
        with self._factory() as session:
            row = session.execute(select(umbrales).where(umbrales.c.zona_id == zona_id)).mappings().first()
            return UmbralZona(row["zona_id"], row["visitantes_maximos"], row["periodo_dias"]) if row else None

    def visitantes_historicos_promedio(self, zona_id: str, dias: int = 30) -> float:
        with self._factory() as session:
            rows = session.execute(
                select(reservas.c.fecha_servicio, func.sum(reservas.c.personas).label("personas"))
                .where(and_(reservas.c.zona_id == zona_id,
                            reservas.c.fecha_servicio >= hoy_colombia() - timedelta(days=dias),
                            reservas.c.fecha_servicio < hoy_colombia()))
                .group_by(reservas.c.fecha_servicio)
            ).all()
            return float(sum(r.personas for r in rows) / dias) if rows else 0.0

    def indicadores(self, desde: date, hasta: date, zona_id: str | None = None) -> list[dict[str, object]]:
        query = select(
            reservas.c.zona_id, func.count().label("reservas"), func.sum(reservas.c.personas).label("visitantes"),
            func.sum(reservas.c.total).label("ingresos_cop"),
        ).where(reservas.c.fecha_servicio.between(desde, hasta))
        if zona_id:
            query = query.where(reservas.c.zona_id == zona_id)
        query = query.group_by(reservas.c.zona_id).order_by(reservas.c.zona_id)
        with self._factory() as session:
            rows = session.execute(query).mappings().all()
            total = sum(int(r["visitantes"] or 0) for r in rows)
            threshold_rows = {r.zona_id: r for r in session.execute(select(umbrales)).all()}
            result: list[dict[str, object]] = []
            for row in rows:
                count = int(row["visitantes"] or 0)
                threshold = threshold_rows.get(row["zona_id"])
                ratio = count / threshold.visitantes_maximos if threshold else None
                result.append({
                    "zona_id": row["zona_id"], "desde": desde.isoformat(), "hasta": hasta.isoformat(),
                    "reservas_confirmadas": int(row["reservas"] or 0), "visitantes_reservados": count,
                    "ingresos_cop": str(row["ingresos_cop"] or Decimal(0)),
                    "concentracion": count / total if total else 0.0,
                    "umbral_visitantes": threshold.visitantes_maximos if threshold else None,
                    "ocupacion_estimada": ratio, "cerca_del_umbral": bool(ratio is not None and ratio >= config.alert_ratio),
                })
            return result

    def alertas_activas(self) -> list[dict[str, object]]:
        with self._factory() as session:
            rows = session.execute(select(alertas).where(alertas.c.resuelta_en.is_(None)).order_by(alertas.c.creada_en)).mappings()
            return [dict(r) for r in rows]

    def procesar_reserva(self, reserva: ReservaConfirmada) -> bool:
        try:
            with self._factory.begin() as session:
                session.execute(insert(eventos_procesados).values(
                    evento_id=reserva.evento_id, tipo="reservas.reserva.confirmada", procesado_en=datetime.now(UTC)
                ))
                session.execute(insert(reservas).values(
                    evento_id=reserva.evento_id, reserva_id=reserva.reserva_id, oferta_id=reserva.oferta_id,
                    zona_id=reserva.zona_id, personas=reserva.personas, fecha_servicio=reserva.fecha_servicio,
                    total=reserva.total, creado_en=datetime.now(UTC),
                ))
                # Toda reserva recalcula y publica la ocupación de su zona (si tiene umbral).
                self._actualizar_ocupacion(session, reserva.zona_id)
            return True
        except IntegrityError:
            return False

    def _actualizar_ocupacion(self, session: Session, zona_id: str) -> None:
        threshold = session.execute(select(umbrales).where(umbrales.c.zona_id == zona_id)).mappings().first()
        if not threshold:
            return
        end = hoy_colombia()
        start = end - timedelta(days=int(threshold["periodo_dias"]) - 1)
        people = int(session.scalar(select(func.coalesce(func.sum(reservas.c.personas), 0)).where(
            and_(reservas.c.zona_id == zona_id, reservas.c.fecha_servicio.between(start, end))
        )) or 0)
        ratio = people / int(threshold["visitantes_maximos"])
        now = datetime.now(UTC)
        active = session.execute(select(alertas).where(
            and_(alertas.c.zona_id == zona_id, alertas.c.resuelta_en.is_(None))
        )).first()
        if ratio >= config.alert_ratio and active is None:
            session.execute(insert(alertas).values(
                id=str(uuid.uuid4()), zona_id=zona_id, ocupacion=ratio, visitantes=people,
                umbral=threshold["visitantes_maximos"], creada_en=now,
            ))
        elif ratio < config.alert_ratio and active is not None:
            session.execute(update(alertas).where(alertas.c.id == active.id).values(resuelta_en=now))
        payload = {"zona_id": zona_id, "nombre": ZONAS_NOMBRE[zona_id],
                   "ocupacion": ratio, "medido_en": now.isoformat().replace("+00:00", "Z")}
        event_id = str(uuid.uuid4())
        session.execute(insert(outbox).values(
            evento_id=event_id, tipo="analitica.zona.ocupacion_actualizada", datos=payload,
            ocurrido_en=now, disponible_en=now, intentos=0,
        ))

    def recalcular_ocupaciones(self) -> int:
        """Recalcula y publica la ocupación de todas las zonas con umbral (tarea periódica)."""
        with self._factory.begin() as session:
            zonas: list[str] = list(session.scalars(select(umbrales.c.zona_id)))
            for zona_id in zonas:
                self._actualizar_ocupacion(session, zona_id)
        return len(zonas)

    def publicar_pendientes(self, publish: Any, lote: int = 50) -> int:
        """Publica con confirmación; duplicados tras un crash conservan evento_id y son idempotentes."""
        count = 0
        with self._factory.begin() as session:
            rows = session.execute(select(outbox).where(
                and_(outbox.c.publicado_en.is_(None), outbox.c.disponible_en <= datetime.now(UTC))
            ).order_by(outbox.c.ocurrido_en).limit(lote).with_for_update(skip_locked=True)).mappings().all()
            for row in rows:
                envelope = {"evento_id": row["evento_id"], "tipo": row["tipo"], "version": 1,
                            "ocurrido_en": row["ocurrido_en"].isoformat(), "correlation_id": None,
                            "datos": row["datos"]}
                try:
                    publish(row["tipo"], json.dumps(envelope, ensure_ascii=False).encode("utf-8"), row["evento_id"])
                except Exception:  # noqa: BLE001 - el publicador puede fallar por red o confirmación
                    attempts = row["intentos"] + 1
                    session.execute(update(outbox).where(outbox.c.evento_id == row["evento_id"]).values(
                        intentos=attempts, disponible_en=datetime.now(UTC) + timedelta(seconds=min(2 ** attempts, 300))
                    ))
                else:
                    session.execute(update(outbox).where(outbox.c.evento_id == row["evento_id"]).values(publicado_en=datetime.now(UTC)))
                    count += 1
        return count
