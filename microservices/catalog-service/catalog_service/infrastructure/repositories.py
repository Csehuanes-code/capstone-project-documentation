"""SQLAlchemy async repository implementations for catalogo_db."""

from __future__ import annotations

import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog_service.application.ports import (
    CalificacionRepository,
    FavoritoRepository,
    ImagenOfertaRepository,
    ItinerarioRepository,
    LoteRepository,
    OfertaRepository,
    PerfilPrestadorRepository,
    PoliticaCancelacionRepository,
    TarifaRepository,
    TipoServicioRepository,
    ZonaRepository,
)
from catalog_service.domain.entities import (
    Calificacion,
    Favorito,
    ImagenOferta,
    ItemItinerario,
    Itinerario,
    LoteSincronizacion,
    Oferta,
    PerfilPrestador,
    PoliticaCancelacion,
    RespuestaCalificacion,
    Tarifa,
    TipoServicio,
    Zona,
)
from catalog_service.domain.value_objects import (
    CategoriaPrestador,
    EstadoLote,
    EstadoModeracion,
    EstadoOferta,
    Temporada,
)
from catalog_service.infrastructure.models import (
    CalificacionModel,
    FavoritoModel,
    ImagenOfertaModel,
    ItemItinerarioModel,
    ItinerarioModel,
    LoteSincronizacionModel,
    OfertaModel,
    PerfilPrestadorModel,
    PoliticaCancelacionModel,
    RespuestaCalificacionModel,
    TarifaModel,
    TipoServicioModel,
    ZonaModel,
)


class SqlAlchemyZonaRepository(ZonaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: ZonaModel) -> Zona:
        return Zona(
            id=m.id,
            codigo=m.codigo,
            nombre_es=m.nombre_es,
            nombre_en=m.nombre_en,
            ecosistema_sensible=m.ecosistema_sensible,
            latitud=m.latitud,
            longitud=m.longitud,
        )

    async def get_by_id(self, zona_id: UUID) -> Zona | None:
        m = await self.session.get(ZonaModel, zona_id)
        return self._to_entity(m) if m else None

    async def get_by_codigo(self, codigo: str) -> Zona | None:
        stmt = select(ZonaModel).where(ZonaModel.codigo == codigo)
        res = await self.session.execute(stmt)
        m = res.scalar_one_or_none()
        return self._to_entity(m) if m else None

    async def list_all(self) -> list[Zona]:
        stmt = select(ZonaModel).order_by(ZonaModel.codigo)
        res = await self.session.execute(stmt)
        return [self._to_entity(m) for m in res.scalars().all()]

    async def save(self, zona: Zona) -> Zona:
        m = await self.session.get(ZonaModel, zona.id)
        if not m:
            m = ZonaModel(
                id=zona.id,
                codigo=zona.codigo,
                nombre_es=zona.nombre_es,
                nombre_en=zona.nombre_en,
                ecosistema_sensible=zona.ecosistema_sensible,
                latitud=zona.latitud,
                longitud=zona.longitud,
            )
            self.session.add(m)
        else:
            m.codigo = zona.codigo
            m.nombre_es = zona.nombre_es
            m.nombre_en = zona.nombre_en
            m.ecosistema_sensible = zona.ecosistema_sensible
            m.latitud = zona.latitud
            m.longitud = zona.longitud
        return zona


class SqlAlchemyTipoServicioRepository(TipoServicioRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: TipoServicioModel) -> TipoServicio:
        return TipoServicio(
            id=m.id,
            codigo=m.codigo,
            nombre_es=m.nombre_es,
            nombre_en=m.nombre_en,
            reservable=m.reservable,
            esquema_atributos=m.esquema_atributos,
        )

    async def get_by_id(self, tipo_id: UUID) -> TipoServicio | None:
        m = await self.session.get(TipoServicioModel, tipo_id)
        return self._to_entity(m) if m else None

    async def get_by_codigo(self, codigo: str) -> TipoServicio | None:
        stmt = select(TipoServicioModel).where(TipoServicioModel.codigo == codigo)
        res = await self.session.execute(stmt)
        m = res.scalar_one_or_none()
        return self._to_entity(m) if m else None

    async def list_all(self) -> list[TipoServicio]:
        stmt = select(TipoServicioModel).order_by(TipoServicioModel.codigo)
        res = await self.session.execute(stmt)
        return [self._to_entity(m) for m in res.scalars().all()]

    async def save(self, tipo: TipoServicio) -> TipoServicio:
        m = await self.session.get(TipoServicioModel, tipo.id)
        if not m:
            m = TipoServicioModel(
                id=tipo.id,
                codigo=tipo.codigo,
                nombre_es=tipo.nombre_es,
                nombre_en=tipo.nombre_en,
                reservable=tipo.reservable,
                esquema_atributos=tipo.esquema_atributos,
            )
            self.session.add(m)
        else:
            m.codigo = tipo.codigo
            m.nombre_es = tipo.nombre_es
            m.nombre_en = tipo.nombre_en
            m.reservable = tipo.reservable
            m.esquema_atributos = tipo.esquema_atributos
        return tipo


class SqlAlchemyPerfilPrestadorRepository(PerfilPrestadorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: PerfilPrestadorModel) -> PerfilPrestador:
        return PerfilPrestador(
            prestador_id=m.prestador_id,
            nombre_comercial=m.nombre_comercial,
            numero_rnt=m.numero_rnt,
            verificado=m.verificado,
            categoria=CategoriaPrestador(m.categoria),
            actualizado_en=m.actualizado_en,
        )

    async def get_by_id(self, prestador_id: UUID) -> PerfilPrestador | None:
        m = await self.session.get(PerfilPrestadorModel, prestador_id)
        return self._to_entity(m) if m else None

    async def save(self, perfil: PerfilPrestador) -> PerfilPrestador:
        m = await self.session.get(PerfilPrestadorModel, perfil.prestador_id)
        if not m:
            m = PerfilPrestadorModel(
                prestador_id=perfil.prestador_id,
                nombre_comercial=perfil.nombre_comercial,
                numero_rnt=perfil.numero_rnt,
                verificado=perfil.verificado,
                categoria=perfil.categoria.value,
                actualizado_en=perfil.actualizado_en,
            )
            self.session.add(m)
        else:
            m.nombre_comercial = perfil.nombre_comercial
            m.numero_rnt = perfil.numero_rnt
            m.verificado = perfil.verificado
            m.categoria = perfil.categoria.value
            m.actualizado_en = perfil.actualizado_en
        return perfil


class SqlAlchemyOfertaRepository(OfertaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: OfertaModel) -> Oferta:
        return Oferta(
            id=m.id,
            prestador_id=m.prestador_id,
            tipo_servicio_id=m.tipo_servicio_id,
            zona_id=m.zona_id,
            nombre_es=m.nombre_es,
            nombre_en=m.nombre_en,
            descripcion_es=m.descripcion_es,
            descripcion_en=m.descripcion_en,
            atributos=m.atributos or {},
            estado=EstadoOferta(m.estado),
            fuente_id=m.fuente_id,
            actualizado_fuente_en=m.actualizado_fuente_en,
            calificacion_promedio=m.calificacion_promedio,
            total_calificaciones=m.total_calificaciones,
            creado_en=m.creado_en,
            actualizado_en=m.actualizado_en,
        )

    async def get_by_id(self, oferta_id: UUID) -> Oferta | None:
        m = await self.session.get(OfertaModel, oferta_id)
        return self._to_entity(m) if m else None

    async def list_offers(
        self,
        *,
        tipo_codigo: str | None = None,
        zona_codigo: str | None = None,
        categoria: str | None = None,
        estado: EstadoOferta | None = EstadoOferta.PUBLICADA,
        prestador_id: UUID | None = None,
        orden: str = "relevancia",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Oferta], int]:
        stmt = select(OfertaModel)
        count_stmt = select(func.count(OfertaModel.id))

        if estado is not None:
            stmt = stmt.where(OfertaModel.estado == estado.value)
            count_stmt = count_stmt.where(OfertaModel.estado == estado.value)

        if prestador_id is not None:
            stmt = stmt.where(OfertaModel.prestador_id == prestador_id)
            count_stmt = count_stmt.where(OfertaModel.prestador_id == prestador_id)

        if zona_codigo:
            stmt = stmt.join(OfertaModel.zona).where(ZonaModel.codigo == zona_codigo)
            count_stmt = count_stmt.join(OfertaModel.zona).where(ZonaModel.codigo == zona_codigo)

        if tipo_codigo:
            stmt = stmt.join(OfertaModel.tipo_servicio).where(
                TipoServicioModel.codigo == tipo_codigo
            )
            count_stmt = count_stmt.join(OfertaModel.tipo_servicio).where(
                TipoServicioModel.codigo == tipo_codigo
            )

        if orden in ("popularidad", "calificacion"):
            stmt = stmt.order_by(
                OfertaModel.calificacion_promedio.desc(),
                OfertaModel.total_calificaciones.desc(),
            )
        else:
            stmt = stmt.order_by(OfertaModel.creado_en.desc())

        # Count total
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        # Paginate
        stmt = stmt.offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        models = res.scalars().all()

        offers = [self._to_entity(m) for m in models]

        if categoria:
            offers = [o for o in offers if categoria in o.atributos.get("categorias", [])]

        return offers, total

    async def save(self, oferta: Oferta) -> Oferta:
        m = await self.session.get(OfertaModel, oferta.id)
        if not m:
            m = OfertaModel(
                id=oferta.id,
                prestador_id=oferta.prestador_id,
                tipo_servicio_id=oferta.tipo_servicio_id,
                zona_id=oferta.zona_id,
                nombre_es=oferta.nombre_es,
                nombre_en=oferta.nombre_en,
                descripcion_es=oferta.descripcion_es,
                descripcion_en=oferta.descripcion_en,
                atributos=oferta.atributos,
                estado=oferta.estado.value,
                fuente_id=oferta.fuente_id,
                actualizado_fuente_en=oferta.actualizado_fuente_en,
                calificacion_promedio=oferta.calificacion_promedio,
                total_calificaciones=oferta.total_calificaciones,
                creado_en=oferta.creado_en or datetime.datetime.now(datetime.UTC),
                actualizado_en=oferta.actualizado_en or datetime.datetime.now(datetime.UTC),
            )
            self.session.add(m)
        else:
            m.nombre_es = oferta.nombre_es
            m.nombre_en = oferta.nombre_en
            m.descripcion_es = oferta.descripcion_es
            m.descripcion_en = oferta.descripcion_en
            m.atributos = oferta.atributos
            m.estado = oferta.estado.value
            m.calificacion_promedio = oferta.calificacion_promedio
            m.total_calificaciones = oferta.total_calificaciones
            m.actualizado_en = oferta.actualizado_en or datetime.datetime.now(datetime.UTC)
        return oferta

    async def update_estado(self, oferta_id: UUID, estado: EstadoOferta) -> None:
        m = await self.session.get(OfertaModel, oferta_id)
        if m:
            m.estado = estado.value
            m.actualizado_en = datetime.datetime.now(datetime.UTC)


class SqlAlchemyTarifaRepository(TarifaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: TarifaModel) -> Tarifa:
        return Tarifa(
            id=m.id,
            oferta_id=m.oferta_id,
            temporada=Temporada(m.temporada),
            vigente_desde=m.vigente_desde,
            vigente_hasta=m.vigente_hasta,
            precio_por_persona=m.precio_por_persona,
            moneda=m.moneda,
        )

    async def list_by_oferta(self, oferta_id: UUID) -> list[Tarifa]:
        stmt = (
            select(TarifaModel)
            .where(TarifaModel.oferta_id == oferta_id)
            .order_by(TarifaModel.vigente_desde)
        )
        res = await self.session.execute(stmt)
        return [self._to_entity(m) for m in res.scalars().all()]

    async def get_vigente(self, oferta_id: UUID, fecha: datetime.date) -> Tarifa | None:
        stmt = select(TarifaModel).where(
            TarifaModel.oferta_id == oferta_id,
            TarifaModel.vigente_desde <= fecha,
            TarifaModel.vigente_hasta >= fecha,
        )
        res = await self.session.execute(stmt)
        m = res.scalar_one_or_none()
        return self._to_entity(m) if m else None

    async def save(self, tarifa: Tarifa) -> Tarifa:
        m = await self.session.get(TarifaModel, tarifa.id)
        if not m:
            m = TarifaModel(
                id=tarifa.id,
                oferta_id=tarifa.oferta_id,
                temporada=tarifa.temporada.value,
                vigente_desde=tarifa.vigente_desde,
                vigente_hasta=tarifa.vigente_hasta,
                precio_por_persona=tarifa.precio_por_persona,
                moneda=tarifa.moneda,
            )
            self.session.add(m)
        else:
            m.temporada = tarifa.temporada.value
            m.vigente_desde = tarifa.vigente_desde
            m.vigente_hasta = tarifa.vigente_hasta
            m.precio_por_persona = tarifa.precio_por_persona
            m.moneda = tarifa.moneda
        return tarifa


class SqlAlchemyPoliticaCancelacionRepository(PoliticaCancelacionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: PoliticaCancelacionModel) -> PoliticaCancelacion:
        return PoliticaCancelacion(
            oferta_id=m.oferta_id,
            horas_reembolso_total=m.horas_reembolso_total,
            horas_reembolso_parcial=m.horas_reembolso_parcial,
            porcentaje_reembolso_parcial=m.porcentaje_reembolso_parcial,
        )

    async def get_by_oferta(self, oferta_id: UUID) -> PoliticaCancelacion | None:
        m = await self.session.get(PoliticaCancelacionModel, oferta_id)
        return self._to_entity(m) if m else None

    async def save(self, politica: PoliticaCancelacion) -> PoliticaCancelacion:
        m = await self.session.get(PoliticaCancelacionModel, politica.oferta_id)
        if not m:
            m = PoliticaCancelacionModel(
                oferta_id=politica.oferta_id,
                horas_reembolso_total=politica.horas_reembolso_total,
                horas_reembolso_parcial=politica.horas_reembolso_parcial,
                porcentaje_reembolso_parcial=politica.porcentaje_reembolso_parcial,
            )
            self.session.add(m)
        else:
            m.horas_reembolso_total = politica.horas_reembolso_total
            m.horas_reembolso_parcial = politica.horas_reembolso_parcial
            m.porcentaje_reembolso_parcial = politica.porcentaje_reembolso_parcial
        return politica


class SqlAlchemyImagenOfertaRepository(ImagenOfertaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: ImagenOfertaModel) -> ImagenOferta:
        return ImagenOferta(
            id=m.id,
            oferta_id=m.oferta_id,
            clave_objeto=m.clave_objeto,
            orden=m.orden,
            texto_alternativo_es=m.texto_alternativo_es,
            texto_alternativo_en=m.texto_alternativo_en,
        )

    async def list_by_oferta(self, oferta_id: UUID) -> list[ImagenOferta]:
        stmt = (
            select(ImagenOfertaModel)
            .where(ImagenOfertaModel.oferta_id == oferta_id)
            .order_by(ImagenOfertaModel.orden)
        )
        res = await self.session.execute(stmt)
        return [self._to_entity(m) for m in res.scalars().all()]

    async def save(self, imagen: ImagenOferta) -> ImagenOferta:
        m = await self.session.get(ImagenOfertaModel, imagen.id)
        if not m:
            m = ImagenOfertaModel(
                id=imagen.id,
                oferta_id=imagen.oferta_id,
                clave_objeto=imagen.clave_objeto,
                orden=imagen.orden,
                texto_alternativo_es=imagen.texto_alternativo_es,
                texto_alternativo_en=imagen.texto_alternativo_en,
            )
            self.session.add(m)
        else:
            m.clave_objeto = imagen.clave_objeto
            m.orden = imagen.orden
            m.texto_alternativo_es = imagen.texto_alternativo_es
            m.texto_alternativo_en = imagen.texto_alternativo_en
        return imagen


class SqlAlchemyCalificacionRepository(CalificacionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: CalificacionModel) -> Calificacion:
        return Calificacion(
            id=m.id,
            oferta_id=m.oferta_id,
            turista_id=m.turista_id,
            reserva_id=m.reserva_id,
            puntaje=m.puntaje,
            comentario=m.comentario,
            estado_moderacion=EstadoModeracion(m.estado_moderacion),
            creada_en=m.creada_en,
        )

    async def get_by_id(self, calificacion_id: UUID) -> Calificacion | None:
        m = await self.session.get(CalificacionModel, calificacion_id)
        return self._to_entity(m) if m else None

    async def get_by_reserva_id(self, reserva_id: UUID) -> Calificacion | None:
        stmt = select(CalificacionModel).where(CalificacionModel.reserva_id == reserva_id)
        res = await self.session.execute(stmt)
        m = res.scalar_one_or_none()
        return self._to_entity(m) if m else None

    async def list_by_oferta(
        self, oferta_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Calificacion], int]:
        count_stmt = select(func.count(CalificacionModel.id)).where(
            CalificacionModel.oferta_id == oferta_id,
            CalificacionModel.estado_moderacion == EstadoModeracion.PUBLICADA.value,
        )
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(CalificacionModel)
            .where(
                CalificacionModel.oferta_id == oferta_id,
                CalificacionModel.estado_moderacion == EstadoModeracion.PUBLICADA.value,
            )
            .order_by(CalificacionModel.creada_en.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [self._to_entity(m) for m in res.scalars().all()], total

    async def list_puntajes_by_oferta(self, oferta_id: UUID) -> list[int]:
        stmt = select(CalificacionModel.puntaje).where(
            CalificacionModel.oferta_id == oferta_id,
            CalificacionModel.estado_moderacion == EstadoModeracion.PUBLICADA.value,
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save(self, calificacion: Calificacion) -> Calificacion:
        m = await self.session.get(CalificacionModel, calificacion.id)
        if not m:
            m = CalificacionModel(
                id=calificacion.id,
                oferta_id=calificacion.oferta_id,
                turista_id=calificacion.turista_id,
                reserva_id=calificacion.reserva_id,
                puntaje=calificacion.puntaje,
                comentario=calificacion.comentario,
                estado_moderacion=calificacion.estado_moderacion.value,
                creada_en=calificacion.creada_en or datetime.datetime.now(datetime.UTC),
            )
            self.session.add(m)
        else:
            m.puntaje = calificacion.puntaje
            m.comentario = calificacion.comentario
            m.estado_moderacion = calificacion.estado_moderacion.value
        return calificacion

    async def save_respuesta(self, respuesta: RespuestaCalificacion) -> RespuestaCalificacion:
        m = await self.session.get(RespuestaCalificacionModel, respuesta.calificacion_id)
        if not m:
            m = RespuestaCalificacionModel(
                calificacion_id=respuesta.calificacion_id,
                prestador_id=respuesta.prestador_id,
                texto=respuesta.texto,
                estado_moderacion=respuesta.estado_moderacion.value,
                creada_en=respuesta.creada_en or datetime.datetime.now(datetime.UTC),
            )
            self.session.add(m)
        else:
            m.texto = respuesta.texto
            m.estado_moderacion = respuesta.estado_moderacion.value
        return respuesta

    async def get_respuesta(self, calificacion_id: UUID) -> RespuestaCalificacion | None:
        m = await self.session.get(RespuestaCalificacionModel, calificacion_id)
        if not m:
            return None
        return RespuestaCalificacion(
            calificacion_id=m.calificacion_id,
            prestador_id=m.prestador_id,
            texto=m.texto,
            estado_moderacion=EstadoModeracion(m.estado_moderacion),
            creada_en=m.creada_en,
        )


class SqlAlchemyFavoritoRepository(FavoritoRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, turista_id: UUID, oferta_id: UUID) -> Favorito | None:
        stmt = select(FavoritoModel).where(
            FavoritoModel.turista_id == turista_id,
            FavoritoModel.oferta_id == oferta_id,
        )
        res = await self.session.execute(stmt)
        m = res.scalar_one_or_none()
        if not m:
            return None
        return Favorito(turista_id=m.turista_id, oferta_id=m.oferta_id, creado_en=m.creado_en)

    async def list_by_turista(self, turista_id: UUID) -> list[Oferta]:
        stmt = (
            select(OfertaModel)
            .join(FavoritoModel, FavoritoModel.oferta_id == OfertaModel.id)
            .where(FavoritoModel.turista_id == turista_id)
        )
        res = await self.session.execute(stmt)
        models = res.scalars().all()
        repo = SqlAlchemyOfertaRepository(self.session)
        return [repo._to_entity(m) for m in models]

    async def add(self, favorito: Favorito) -> None:
        existing = await self.get(favorito.turista_id, favorito.oferta_id)
        if not existing:
            m = FavoritoModel(
                turista_id=favorito.turista_id,
                oferta_id=favorito.oferta_id,
                creado_en=favorito.creado_en or datetime.datetime.now(datetime.UTC),
            )
            self.session.add(m)

    async def remove(self, turista_id: UUID, oferta_id: UUID) -> None:
        stmt = delete(FavoritoModel).where(
            FavoritoModel.turista_id == turista_id,
            FavoritoModel.oferta_id == oferta_id,
        )
        await self.session.execute(stmt)


class SqlAlchemyItinerarioRepository(ItinerarioRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: ItinerarioModel) -> Itinerario:
        return Itinerario(
            id=m.id,
            turista_id=m.turista_id,
            nombre=m.nombre,
            fecha_inicio=m.fecha_inicio,
            fecha_fin=m.fecha_fin,
        )

    async def get_by_id(self, itinerario_id: UUID) -> Itinerario | None:
        m = await self.session.get(ItinerarioModel, itinerario_id)
        return self._to_entity(m) if m else None

    async def list_by_turista(self, turista_id: UUID) -> list[Itinerario]:
        stmt = select(ItinerarioModel).where(ItinerarioModel.turista_id == turista_id)
        res = await self.session.execute(stmt)
        return [self._to_entity(m) for m in res.scalars().all()]

    async def save(self, itinerario: Itinerario) -> Itinerario:
        m = await self.session.get(ItinerarioModel, itinerario.id)
        if not m:
            m = ItinerarioModel(
                id=itinerario.id,
                turista_id=itinerario.turista_id,
                nombre=itinerario.nombre,
                fecha_inicio=itinerario.fecha_inicio,
                fecha_fin=itinerario.fecha_fin,
            )
            self.session.add(m)
        else:
            m.nombre = itinerario.nombre
            m.fecha_inicio = itinerario.fecha_inicio
            m.fecha_fin = itinerario.fecha_fin
        return itinerario

    async def add_item(self, item: ItemItinerario) -> ItemItinerario:
        m = ItemItinerarioModel(
            id=item.id,
            itinerario_id=item.itinerario_id,
            oferta_id=item.oferta_id,
            dia=item.dia,
            orden=item.orden,
            hora_inicio=item.hora_inicio,
            hora_fin=item.hora_fin,
        )
        self.session.add(m)
        return item

    async def list_items(self, itinerario_id: UUID) -> list[ItemItinerario]:
        stmt = (
            select(ItemItinerarioModel)
            .where(ItemItinerarioModel.itinerario_id == itinerario_id)
            .order_by(ItemItinerarioModel.dia, ItemItinerarioModel.orden)
        )
        res = await self.session.execute(stmt)
        return [
            ItemItinerario(
                id=m.id,
                itinerario_id=m.itinerario_id,
                oferta_id=m.oferta_id,
                dia=m.dia,
                orden=m.orden,
                hora_inicio=m.hora_inicio,
                hora_fin=m.hora_fin,
            )
            for m in res.scalars().all()
        ]


class SqlAlchemyLoteRepository(LoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, m: LoteSincronizacionModel) -> LoteSincronizacion:
        return LoteSincronizacion(
            id=m.id,
            prestador_id=m.prestador_id,
            fuente_id=m.fuente_id,
            estado=EstadoLote(m.estado),
            total_registros=m.total_registros,
            aceptados=m.aceptados,
            rechazados=m.rechazados or [],
            recibido_en=m.recibido_en,
            finalizado_en=m.finalizado_en,
        )

    async def get_by_id(self, lote_id: UUID) -> LoteSincronizacion | None:
        m = await self.session.get(LoteSincronizacionModel, lote_id)
        return self._to_entity(m) if m else None

    async def save(self, lote: LoteSincronizacion) -> LoteSincronizacion:
        m = await self.session.get(LoteSincronizacionModel, lote.id)
        if not m:
            m = LoteSincronizacionModel(
                id=lote.id,
                prestador_id=lote.prestador_id,
                fuente_id=lote.fuente_id,
                estado=lote.estado.value,
                total_registros=lote.total_registros,
                aceptados=lote.aceptados,
                rechazados=lote.rechazados,
                recibido_en=lote.recibido_en or datetime.datetime.now(datetime.UTC),
                finalizado_en=lote.finalizado_en,
            )
            self.session.add(m)
        else:
            m.estado = lote.estado.value
            m.aceptados = lote.aceptados
            m.rechazados = lote.rechazados
            m.finalizado_en = lote.finalizado_en
        return lote
