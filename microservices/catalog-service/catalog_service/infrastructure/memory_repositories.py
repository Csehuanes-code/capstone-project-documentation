"""In-memory implementations of all repository ports for testing and standalone dev mode."""

from __future__ import annotations

import datetime
from uuid import UUID

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
from catalog_service.domain.value_objects import EstadoOferta


class InMemoryZonaRepository(ZonaRepository):
    def __init__(self, initial: list[Zona] | None = None) -> None:
        self.zonas: dict[UUID, Zona] = {z.id: z for z in initial or []}

    async def get_by_id(self, zona_id: UUID) -> Zona | None:
        return self.zonas.get(zona_id)

    async def get_by_codigo(self, codigo: str) -> Zona | None:
        for z in self.zonas.values():
            if z.codigo == codigo:
                return z
        return None

    async def list_all(self) -> list[Zona]:
        return list(self.zonas.values())

    async def save(self, zona: Zona) -> Zona:
        self.zonas[zona.id] = zona
        return zona


class InMemoryTipoServicioRepository(TipoServicioRepository):
    def __init__(self, initial: list[TipoServicio] | None = None) -> None:
        self.tipos: dict[UUID, TipoServicio] = {t.id: t for t in initial or []}

    async def get_by_id(self, tipo_id: UUID) -> TipoServicio | None:
        return self.tipos.get(tipo_id)

    async def get_by_codigo(self, codigo: str) -> TipoServicio | None:
        for t in self.tipos.values():
            if t.codigo == codigo:
                return t
        return None

    async def list_all(self) -> list[TipoServicio]:
        return list(self.tipos.values())

    async def save(self, tipo: TipoServicio) -> TipoServicio:
        self.tipos[tipo.id] = tipo
        return tipo


class InMemoryPerfilPrestadorRepository(PerfilPrestadorRepository):
    def __init__(self, initial: list[PerfilPrestador] | None = None) -> None:
        self.perfiles: dict[UUID, PerfilPrestador] = {p.prestador_id: p for p in initial or []}

    async def get_by_id(self, prestador_id: UUID) -> PerfilPrestador | None:
        return self.perfiles.get(prestador_id)

    async def save(self, perfil: PerfilPrestador) -> PerfilPrestador:
        self.perfiles[perfil.prestador_id] = perfil
        return perfil


class InMemoryOfertaRepository(OfertaRepository):
    def __init__(
        self,
        initial: list[Oferta] | None = None,
        zona_repo: ZonaRepository | None = None,
        tipo_repo: TipoServicioRepository | None = None,
    ) -> None:
        self.ofertas: dict[UUID, Oferta] = {o.id: o for o in initial or []}
        self.zona_repo = zona_repo
        self.tipo_repo = tipo_repo

    async def get_by_id(self, oferta_id: UUID) -> Oferta | None:
        return self.ofertas.get(oferta_id)

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
        results = list(self.ofertas.values())

        if estado is not None:
            results = [o for o in results if o.estado == estado]

        if prestador_id is not None:
            results = [o for o in results if o.prestador_id == prestador_id]

        if zona_codigo and self.zona_repo:
            zona = await self.zona_repo.get_by_codigo(zona_codigo)
            if zona:
                results = [o for o in results if o.zona_id == zona.id]
            else:
                return [], 0

        if tipo_codigo and self.tipo_repo:
            tipo = await self.tipo_repo.get_by_codigo(tipo_codigo)
            if tipo:
                results = [o for o in results if o.tipo_servicio_id == tipo.id]
            else:
                return [], 0

        if categoria:
            results = [o for o in results if categoria in o.atributos.get("categorias", [])]

        # Ordering
        if orden == "popularidad" or orden == "calificacion":
            results.sort(
                key=lambda o: (o.calificacion_promedio, o.total_calificaciones),
                reverse=True,
            )

        total = len(results)
        paginated = results[offset : offset + limit]
        return paginated, total

    async def save(self, oferta: Oferta) -> Oferta:
        self.ofertas[oferta.id] = oferta
        return oferta

    async def update_estado(self, oferta_id: UUID, estado: EstadoOferta) -> None:
        if oferta_id in self.ofertas:
            self.ofertas[oferta_id].estado = estado


class InMemoryTarifaRepository(TarifaRepository):
    def __init__(self, initial: list[Tarifa] | None = None) -> None:
        self.tarifas: dict[UUID, Tarifa] = {t.id: t for t in initial or []}

    async def list_by_oferta(self, oferta_id: UUID) -> list[Tarifa]:
        return [t for t in self.tarifas.values() if t.oferta_id == oferta_id]

    async def get_vigente(self, oferta_id: UUID, fecha: datetime.date) -> Tarifa | None:
        matches = [
            t
            for t in self.tarifas.values()
            if t.oferta_id == oferta_id and t.vigente_desde <= fecha <= t.vigente_hasta
        ]
        return matches[0] if matches else None

    async def save(self, tarifa: Tarifa) -> Tarifa:
        self.tarifas[tarifa.id] = tarifa
        return tarifa


class InMemoryPoliticaCancelacionRepository(PoliticaCancelacionRepository):
    def __init__(self, initial: list[PoliticaCancelacion] | None = None) -> None:
        self.politicas: dict[UUID, PoliticaCancelacion] = {p.oferta_id: p for p in initial or []}

    async def get_by_oferta(self, oferta_id: UUID) -> PoliticaCancelacion | None:
        return self.politicas.get(oferta_id)

    async def save(self, politica: PoliticaCancelacion) -> PoliticaCancelacion:
        self.politicas[politica.oferta_id] = politica
        return politica


class InMemoryImagenOfertaRepository(ImagenOfertaRepository):
    def __init__(self, initial: list[ImagenOferta] | None = None) -> None:
        self.imagenes: dict[UUID, ImagenOferta] = {img.id: img for img in initial or []}

    async def list_by_oferta(self, oferta_id: UUID) -> list[ImagenOferta]:
        items = [img for img in self.imagenes.values() if img.oferta_id == oferta_id]
        items.sort(key=lambda img: img.orden)
        return items

    async def save(self, imagen: ImagenOferta) -> ImagenOferta:
        self.imagenes[imagen.id] = imagen
        return imagen


class InMemoryCalificacionRepository(CalificacionRepository):
    def __init__(self) -> None:
        self.calificaciones: dict[UUID, Calificacion] = {}
        self.respuestas: dict[UUID, RespuestaCalificacion] = {}

    async def get_by_id(self, calificacion_id: UUID) -> Calificacion | None:
        return self.calificaciones.get(calificacion_id)

    async def get_by_reserva_id(self, reserva_id: UUID) -> Calificacion | None:
        for c in self.calificaciones.values():
            if c.reserva_id == reserva_id:
                return c
        return None

    async def list_by_oferta(
        self, oferta_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Calificacion], int]:
        matches = [c for c in self.calificaciones.values() if c.oferta_id == oferta_id]
        return matches[offset : offset + limit], len(matches)

    async def list_puntajes_by_oferta(self, oferta_id: UUID) -> list[int]:
        return [c.puntaje for c in self.calificaciones.values() if c.oferta_id == oferta_id]

    async def save(self, calificacion: Calificacion) -> Calificacion:
        self.calificaciones[calificacion.id] = calificacion
        return calificacion

    async def save_respuesta(self, respuesta: RespuestaCalificacion) -> RespuestaCalificacion:
        self.respuestas[respuesta.calificacion_id] = respuesta
        return respuesta

    async def get_respuesta(self, calificacion_id: UUID) -> RespuestaCalificacion | None:
        return self.respuestas.get(calificacion_id)


class InMemoryFavoritoRepository(FavoritoRepository):
    def __init__(self, oferta_repo: OfertaRepository | None = None) -> None:
        self.favoritos: list[Favorito] = []
        self.oferta_repo = oferta_repo

    async def get(self, turista_id: UUID, oferta_id: UUID) -> Favorito | None:
        for f in self.favoritos:
            if f.turista_id == turista_id and f.oferta_id == oferta_id:
                return f
        return None

    async def list_by_turista(self, turista_id: UUID) -> list[Oferta]:
        oferta_ids = [f.oferta_id for f in self.favoritos if f.turista_id == turista_id]
        if not self.oferta_repo:
            return []
        res = []
        for oid in oferta_ids:
            of = await self.oferta_repo.get_by_id(oid)
            if of:
                res.append(of)
        return res

    async def add(self, favorito: Favorito) -> None:
        existing = await self.get(favorito.turista_id, favorito.oferta_id)
        if not existing:
            self.favoritos.append(favorito)

    async def remove(self, turista_id: UUID, oferta_id: UUID) -> None:
        self.favoritos = [
            f
            for f in self.favoritos
            if not (f.turista_id == turista_id and f.oferta_id == oferta_id)
        ]


class InMemoryItinerarioRepository(ItinerarioRepository):
    def __init__(self) -> None:
        self.itinerarios: dict[UUID, Itinerario] = {}
        self.items: list[ItemItinerario] = []

    async def get_by_id(self, itinerario_id: UUID) -> Itinerario | None:
        return self.itinerarios.get(itinerario_id)

    async def list_by_turista(self, turista_id: UUID) -> list[Itinerario]:
        return [it for it in self.itinerarios.values() if it.turista_id == turista_id]

    async def save(self, itinerario: Itinerario) -> Itinerario:
        self.itinerarios[itinerario.id] = itinerario
        return itinerario

    async def add_item(self, item: ItemItinerario) -> ItemItinerario:
        self.items.append(item)
        return item

    async def list_items(self, itinerario_id: UUID) -> list[ItemItinerario]:
        matched = [i for i in self.items if i.itinerario_id == itinerario_id]
        matched.sort(key=lambda i: (i.dia, i.orden))
        return matched


class InMemoryLoteRepository(LoteRepository):
    def __init__(self) -> None:
        self.lotes: dict[UUID, LoteSincronizacion] = {}

    async def get_by_id(self, lote_id: UUID) -> LoteSincronizacion | None:
        return self.lotes.get(lote_id)

    async def save(self, lote: LoteSincronizacion) -> LoteSincronizacion:
        self.lotes[lote.id] = lote
        return lote
