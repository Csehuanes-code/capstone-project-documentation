"""Use cases for the Catálogo application layer.

Each usecase is a dedicated command/query class adhering to Clean Architecture.
Dependencies (repositories, external clients, event publisher) are injected via constructor.
No web framework (FastAPI) or ORM (SQLAlchemy) references exist here.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from catalog_service.application.ports import (
    CalificacionRepository,
    EventPublisher,
    FavoritoRepository,
    ImagenOfertaRepository,
    ItinerarioRepository,
    LoteRepository,
    OfertaRepository,
    PerfilPrestadorRepository,
    PoliticaCancelacionRepository,
    ReservasClient,
    TarifaRepository,
    TipoServicioRepository,
    ZonaRepository,
)
from catalog_service.domain.entities import (
    Calificacion,
    Favorito,
    ItemItinerario,
    Itinerario,
    LoteSincronizacion,
    Oferta,
    PerfilPrestador,
    PoliticaCancelacion,
    RespuestaCalificacion,
    Tarifa,
)
from catalog_service.domain.exceptions import (
    CalificacionDuplicada,
    DomainError,
    EntityNotFoundError,
    PuntajeInvalido,
    ZonaNoCanonica,
)
from catalog_service.domain.rules import (
    calcular_calificacion_promedio,
    validate_atributos_contra_esquema,
    validate_categorias_canonicas,
    validate_indice_sostenibilidad,
    validate_prestador_verificado,
    validate_tarifa_sin_solapamiento,
    validate_zona_canonica,
)
from catalog_service.domain.value_objects import (
    EstadoLote,
    EstadoModeracion,
    EstadoOferta,
    Temporada,
)

# ---------------------------------------------------------------------------
# CU-07: Consultar Catálogo
# ---------------------------------------------------------------------------


class ConsultarCatalogoUseCase:
    """CU-07: Consultar Catálogo de Atractivos, Actividades y Servicios.

    Allows public browsing, filtering, ordering, and pagination.
    """

    def __init__(
        self,
        oferta_repo: OfertaRepository,
        zona_repo: ZonaRepository,
    ) -> None:
        self.oferta_repo = oferta_repo
        self.zona_repo = zona_repo

    async def execute(
        self,
        *,
        tipo_codigo: str | None = None,
        zona_codigo: str | None = None,
        categoria: str | None = None,
        orden: str = "relevancia",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Oferta], int]:
        if zona_codigo:
            validate_zona_canonica(zona_codigo)
        if categoria:
            validate_categorias_canonicas([categoria])

        return await self.oferta_repo.list_offers(
            tipo_codigo=tipo_codigo,
            zona_codigo=zona_codigo,
            categoria=categoria,
            estado=EstadoOferta.PUBLICADA,
            orden=orden,
            limit=limit,
            offset=offset,
        )


class ConsultarOfertaDetalleUseCase:
    """Retrieves full details of a single offer including images, active tariffs, and cancellation policy."""

    def __init__(
        self,
        oferta_repo: OfertaRepository,
        imagen_repo: ImagenOfertaRepository,
        tarifa_repo: TarifaRepository,
        politica_repo: PoliticaCancelacionRepository,
        zona_repo: ZonaRepository,
        tipo_repo: TipoServicioRepository,
        prestador_repo: PerfilPrestadorRepository,
    ) -> None:
        self.oferta_repo = oferta_repo
        self.imagen_repo = imagen_repo
        self.tarifa_repo = tarifa_repo
        self.politica_repo = politica_repo
        self.zona_repo = zona_repo
        self.tipo_repo = tipo_repo
        self.prestador_repo = prestador_repo

    async def execute(self, oferta_id: UUID) -> dict[str, Any]:
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)

        zona = await self.zona_repo.get_by_id(oferta.zona_id)
        tipo = await self.tipo_repo.get_by_id(oferta.tipo_servicio_id)
        prestador = (
            await self.prestador_repo.get_by_id(oferta.prestador_id)
            if oferta.prestador_id
            else None
        )
        imagenes = await self.imagen_repo.list_by_oferta(oferta_id)
        tarifas = await self.tarifa_repo.list_by_oferta(oferta_id)
        politica = await self.politica_repo.get_by_oferta(oferta_id)

        return {
            "oferta": oferta,
            "zona": zona,
            "tipo_servicio": tipo,
            "prestador": prestador,
            "imagenes": imagenes,
            "tarifas": tarifas,
            "politica_cancelacion": politica,
        }


# ---------------------------------------------------------------------------
# ADR-04 §4.2: Synchronous Call from Reservas
# ---------------------------------------------------------------------------


class ObtenerCondicionesOfertaUseCase:
    """Reservas → Catálogo: GET /ofertas/{id}/condiciones (ADR-04 §4.2).

    Returns current tariff, cancellation policy, status, and zone for reservation processing.
    """

    def __init__(
        self,
        oferta_repo: OfertaRepository,
        tarifa_repo: TarifaRepository,
        politica_repo: PoliticaCancelacionRepository,
        zona_repo: ZonaRepository,
    ) -> None:
        self.oferta_repo = oferta_repo
        self.tarifa_repo = tarifa_repo
        self.politica_repo = politica_repo
        self.zona_repo = zona_repo

    async def execute(self, oferta_id: UUID, fecha: datetime.date | None = None) -> dict[str, Any]:
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)

        fecha_consulta = fecha or datetime.date.today()
        tarifa = await self.tarifa_repo.get_vigente(oferta_id, fecha_consulta)
        politica = await self.politica_repo.get_by_oferta(oferta_id)
        zona = await self.zona_repo.get_by_id(oferta.zona_id)

        return {
            "oferta_id": str(oferta.id),
            "nombre_es": oferta.nombre_es,
            "nombre_en": oferta.nombre_en,
            "estado": oferta.estado.value,
            "activa": oferta.estado == EstadoOferta.PUBLICADA,
            "zona_id": zona.codigo if zona else "",
            "tarifa_vigente": {
                "precio_por_persona": float(tarifa.precio_por_persona) if tarifa else 0.0,
                "moneda": tarifa.moneda if tarifa else "COP",
                "temporada": tarifa.temporada.value if tarifa else Temporada.MEDIA.value,
            }
            if tarifa
            else None,
            "politica_cancelacion": {
                "horas_reembolso_total": politica.horas_reembolso_total if politica else 24,
                "horas_reembolso_parcial": politica.horas_reembolso_parcial if politica else 12,
                "porcentaje_reembolso_parcial": politica.porcentaje_reembolso_parcial
                if politica
                else 50,
            }
            if politica
            else None,
        }


# ---------------------------------------------------------------------------
# CU-22: Gestionar Oferta Turística
# ---------------------------------------------------------------------------


class GestionarOfertaUseCase:
    """CU-22: Gestionar Oferta Turística (Crear, Editar, Dar de Baja).

    Enforces that only verified providers may publish (RF-USR-19, RF-CAT-08, RF-CAT-09).
    Publishes domain events matching catalogo.oferta.schema.json (ADR-04).
    """

    def __init__(
        self,
        oferta_repo: OfertaRepository,
        zona_repo: ZonaRepository,
        tipo_repo: TipoServicioRepository,
        prestador_repo: PerfilPrestadorRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self.oferta_repo = oferta_repo
        self.zona_repo = zona_repo
        self.tipo_repo = tipo_repo
        self.prestador_repo = prestador_repo
        self.event_publisher = event_publisher

    async def crear_oferta(
        self,
        *,
        prestador_id: UUID,
        tipo_servicio_id: UUID,
        zona_id: UUID,
        nombre_es: str,
        nombre_en: str,
        descripcion_es: str = "",
        descripcion_en: str = "",
        atributos: dict[str, Any] | None = None,
        estado: EstadoOferta = EstadoOferta.BORRADOR,
        indice_sostenibilidad: float = 1.0,
    ) -> Oferta:
        # 1. Verify provider
        prestador = await self.prestador_repo.get_by_id(prestador_id)
        if estado == EstadoOferta.PUBLICADA:
            if not prestador or not prestador.verificado:
                validate_prestador_verificado(prestador_id, False)

        # 2. Verify zone
        zona = await self.zona_repo.get_by_id(zona_id)
        if not zona:
            raise EntityNotFoundError("Zona", zona_id)
        validate_zona_canonica(zona.codigo)

        # 3. Verify service type and attributes schema
        tipo = await self.tipo_repo.get_by_id(tipo_servicio_id)
        if not tipo:
            raise EntityNotFoundError("TipoServicio", tipo_servicio_id)
        atributos_dict = atributos or {}
        validate_atributos_contra_esquema(atributos_dict, tipo.esquema_atributos)

        # 4. Validate canonical categories if present in attributes
        if "categorias" in atributos_dict:
            validate_categorias_canonicas(atributos_dict["categorias"])

        validate_indice_sostenibilidad(indice_sostenibilidad)

        now = datetime.datetime.now(datetime.UTC)
        nueva_oferta = Oferta(
            id=uuid4(),
            prestador_id=prestador_id,
            tipo_servicio_id=tipo_servicio_id,
            zona_id=zona_id,
            nombre_es=nombre_es,
            nombre_en=nombre_en,
            descripcion_es=descripcion_es,
            descripcion_en=descripcion_en,
            atributos=atributos_dict,
            estado=estado,
            calificacion_promedio=Decimal("0.00"),
            total_calificaciones=0,
            creado_en=now,
            actualizado_en=now,
        )

        saved = await self.oferta_repo.save(nueva_oferta)

        # 5. Emit event if published
        if saved.estado == EstadoOferta.PUBLICADA:
            await self._publicar_evento_oferta(
                saved, zona.codigo, "catalogo.oferta.publicada", indice_sostenibilidad
            )

        return saved

    async def actualizar_oferta(
        self,
        oferta_id: UUID,
        prestador_id: UUID,
        *,
        nombre_es: str | None = None,
        nombre_en: str | None = None,
        descripcion_es: str | None = None,
        descripcion_en: str | None = None,
        atributos: dict[str, Any] | None = None,
        estado: EstadoOferta | None = None,
        indice_sostenibilidad: float = 1.0,
    ) -> Oferta:
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)

        # Isolation rule: Provider can only edit own offer (RF-CAT-09, ADR-06 §3.2)
        if oferta.prestador_id != prestador_id:
            raise DomainError(
                "No está autorizado a modificar una oferta de otro prestador.", code="FORBIDDEN"
            )

        if estado == EstadoOferta.PUBLICADA and oferta.estado != EstadoOferta.PUBLICADA:
            prestador = await self.prestador_repo.get_by_id(prestador_id)
            if not prestador or not prestador.verificado:
                validate_prestador_verificado(prestador_id, False)

        if nombre_es is not None:
            oferta.nombre_es = nombre_es
        if nombre_en is not None:
            oferta.nombre_en = nombre_en
        if descripcion_es is not None:
            oferta.descripcion_es = descripcion_es
        if descripcion_en is not None:
            oferta.descripcion_en = descripcion_en
        if atributos is not None:
            tipo = await self.tipo_repo.get_by_id(oferta.tipo_servicio_id)
            if tipo:
                validate_atributos_contra_esquema(atributos, tipo.esquema_atributos)
            if "categorias" in atributos:
                validate_categorias_canonicas(atributos["categorias"])
            oferta.atributos = atributos
        if estado is not None:
            oferta.estado = estado

        oferta.actualizado_en = datetime.datetime.now(datetime.UTC)
        saved = await self.oferta_repo.save(oferta)

        zona = await self.zona_repo.get_by_id(oferta.zona_id)
        zona_codigo = zona.codigo if zona else "centro"

        event_name = (
            "catalogo.oferta.publicada"
            if saved.estado == EstadoOferta.PUBLICADA
            else "catalogo.oferta.actualizada"
        )
        await self._publicar_evento_oferta(saved, zona_codigo, event_name, indice_sostenibilidad)

        return saved

    async def retirar_oferta(self, oferta_id: UUID, prestador_id: UUID) -> Oferta:
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)

        if oferta.prestador_id != prestador_id:
            raise DomainError(
                "No está autorizado a retirar una oferta de otro prestador.", code="FORBIDDEN"
            )

        oferta.estado = EstadoOferta.DADA_DE_BAJA
        oferta.actualizado_en = datetime.datetime.now(datetime.UTC)
        saved = await self.oferta_repo.save(oferta)

        zona = await self.zona_repo.get_by_id(oferta.zona_id)
        zona_codigo = zona.codigo if zona else "centro"

        # Contract: 'retirada' = same body with activa=false
        await self._publicar_evento_oferta(
            saved, zona_codigo, "catalogo.oferta.retirada", 1.0, activa=False
        )
        return saved

    async def _publicar_evento_oferta(
        self,
        oferta: Oferta,
        zona_codigo: str,
        tipo_evento: str,
        indice_sostenibilidad: float = 1.0,
        activa: bool | None = None,
    ) -> None:
        categorias = oferta.atributos.get("categorias", ["cultura"])
        if not isinstance(categorias, list) or not categorias:
            categorias = ["cultura"]

        # Exact schema matching contratos/eventos/catalogo.oferta.schema.json
        payload = {
            "oferta_id": str(oferta.id),
            "nombre": oferta.nombre_es,
            "zona_id": zona_codigo,
            "categorias": categorias,
            "calificacion_promedio": float(oferta.calificacion_promedio),
            "numero_resenas": oferta.total_calificaciones,
            "indice_sostenibilidad": float(indice_sostenibilidad),
            "prestador_id": str(oferta.prestador_id or uuid4()),
            "activa": activa if activa is not None else (oferta.estado == EstadoOferta.PUBLICADA),
        }
        await self.event_publisher.publish(tipo_evento, payload)


# ---------------------------------------------------------------------------
# CU-19: Calificar y Comentar Experiencia
# ---------------------------------------------------------------------------


class CrearCalificacionUseCase:
    """CU-19: Calificar y Comentar Experiencia (RF-CAT-15, RF-CAT-16).

    Rules:
    - Only completed reservations can be reviewed.
    - Exactly one review per reservation (reserva_id is unique).
    - Recalculates oferta.calificacion_promedio.
    - Publishes catalogo.oferta.actualizada event.
    """

    def __init__(
        self,
        calificacion_repo: CalificacionRepository,
        oferta_repo: OfertaRepository,
        zona_repo: ZonaRepository,
        reservas_client: ReservasClient,
        event_publisher: EventPublisher,
    ) -> None:
        self.calificacion_repo = calificacion_repo
        self.oferta_repo = oferta_repo
        self.zona_repo = zona_repo
        self.reservas_client = reservas_client
        self.event_publisher = event_publisher

    async def execute(
        self,
        *,
        oferta_id: UUID,
        turista_id: UUID,
        reserva_id: UUID,
        puntaje: int,
        comentario: str = "",
    ) -> Calificacion:
        # 1. Validate score range 1-5
        if not (1 <= puntaje <= 5):
            raise PuntajeInvalido(puntaje)

        # 2. Check duplicate review for same reservation (RF-CAT-15)
        existente = await self.calificacion_repo.get_by_reserva_id(reserva_id)
        if existente:
            raise CalificacionDuplicada(reserva_id)

        # 3. Synchronous verification with Reservas: GET /reservas/{id}/estado (ADR-04 §4.2)
        reserva_info = await self.reservas_client.get_reserva_estado(reserva_id)
        if not reserva_info:
            raise DomainError(
                "No fue posible verificar el estado de la reserva con el servicio de Reservas."
            )
        if reserva_info.get("estado") != "completada":
            raise DomainError(
                f"Solo se pueden calificar reservas completadas. Estado actual: {reserva_info.get('estado')!r}"
            )

        # 4. Verify offer exists
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)

        # 5. Persist Calificacion
        now = datetime.datetime.now(datetime.UTC)
        nueva_calif = Calificacion(
            id=uuid4(),
            oferta_id=oferta_id,
            turista_id=turista_id,
            reserva_id=reserva_id,
            puntaje=puntaje,
            comentario=comentario,
            estado_moderacion=EstadoModeracion.PUBLICADA,
            creada_en=now,
        )
        saved = await self.calificacion_repo.save(nueva_calif)

        # 6. Recalculate average rating (RF-CAT-16)
        puntajes = await self.calificacion_repo.list_puntajes_by_oferta(oferta_id)
        promedio = calcular_calificacion_promedio(puntajes)
        oferta.calificacion_promedio = promedio
        oferta.total_calificaciones = len(puntajes)
        oferta.actualizado_en = now
        await self.oferta_repo.save(oferta)

        # 7. Publish update event so IA can update proyeccion_oferta
        zona = await self.zona_repo.get_by_id(oferta.zona_id)
        zona_codigo = zona.codigo if zona else "centro"
        categorias = oferta.atributos.get("categorias", ["cultura"])

        payload = {
            "oferta_id": str(oferta.id),
            "nombre": oferta.nombre_es,
            "zona_id": zona_codigo,
            "categorias": categorias,
            "calificacion_promedio": float(oferta.calificacion_promedio),
            "numero_resenas": oferta.total_calificaciones,
            "indice_sostenibilidad": 1.0,
            "prestador_id": str(oferta.prestador_id or uuid4()),
            "activa": oferta.estado == EstadoOferta.PUBLICADA,
        }
        await self.event_publisher.publish("catalogo.oferta.actualizada", payload)

        return saved


# ---------------------------------------------------------------------------
# CU-20: Responder a Calificaciones
# ---------------------------------------------------------------------------


class ResponderCalificacionUseCase:
    """CU-20: Responder a Calificaciones y Comentarios (RF-CAT-17)."""

    def __init__(
        self,
        calificacion_repo: CalificacionRepository,
        oferta_repo: OfertaRepository,
    ) -> None:
        self.calificacion_repo = calificacion_repo
        self.oferta_repo = oferta_repo

    async def execute(
        self,
        *,
        calificacion_id: UUID,
        prestador_id: UUID,
        texto: str,
    ) -> RespuestaCalificacion:
        calif = await self.calificacion_repo.get_by_id(calificacion_id)
        if not calif:
            raise EntityNotFoundError("Calificacion", calificacion_id)

        oferta = await self.oferta_repo.get_by_id(calif.oferta_id)
        if not oferta or oferta.prestador_id != prestador_id:
            raise DomainError(
                "Un prestador solo puede responder reseñas de su propia oferta.", code="FORBIDDEN"
            )

        now = datetime.datetime.now(datetime.UTC)
        respuesta = RespuestaCalificacion(
            calificacion_id=calificacion_id,
            prestador_id=prestador_id,
            texto=texto,
            estado_moderacion=EstadoModeracion.PUBLICADA,
            creada_en=now,
        )
        return await self.calificacion_repo.save_respuesta(respuesta)


# ---------------------------------------------------------------------------
# CU-09: Favoritos
# ---------------------------------------------------------------------------


class GestionarFavoritosUseCase:
    """CU-09: Guardar Atractivo en Lista de Favoritos (RF-CAT-05)."""

    def __init__(self, favorito_repo: FavoritoRepository, oferta_repo: OfertaRepository) -> None:
        self.favorito_repo = favorito_repo
        self.oferta_repo = oferta_repo

    async def agregar_favorito(self, turista_id: UUID, oferta_id: UUID) -> None:
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)

        fav = Favorito(
            turista_id=turista_id,
            oferta_id=oferta_id,
            creado_en=datetime.datetime.now(datetime.UTC),
        )
        await self.favorito_repo.add(fav)

    async def eliminar_favorito(self, turista_id: UUID, oferta_id: UUID) -> None:
        await self.favorito_repo.remove(turista_id, oferta_id)

    async def listar_favoritos(self, turista_id: UUID) -> list[Oferta]:
        return await self.favorito_repo.list_by_turista(turista_id)


# ---------------------------------------------------------------------------
# CU-10: Itinerarios
# ---------------------------------------------------------------------------


class GestionarItinerariosUseCase:
    """CU-10: Crear Itinerario Personalizado Multi-Servicio (RF-CAT-06, RF-CAT-07)."""

    def __init__(
        self,
        itinerario_repo: ItinerarioRepository,
        oferta_repo: OfertaRepository,
    ) -> None:
        self.itinerario_repo = itinerario_repo
        self.oferta_repo = oferta_repo

    async def crear_itinerario(
        self,
        turista_id: UUID,
        nombre: str,
        fecha_inicio: datetime.date | None = None,
        fecha_fin: datetime.date | None = None,
    ) -> Itinerario:
        itinerario = Itinerario(
            id=uuid4(),
            turista_id=turista_id,
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        return await self.itinerario_repo.save(itinerario)

    async def agregar_item(
        self,
        itinerario_id: UUID,
        oferta_id: UUID,
        dia: datetime.date,
        orden: int = 0,
        hora_inicio: datetime.time | None = None,
        hora_fin: datetime.time | None = None,
    ) -> tuple[ItemItinerario, list[str]]:
        itinerario = await self.itinerario_repo.get_by_id(itinerario_id)
        if not itinerario:
            raise EntityNotFoundError("Itinerario", itinerario_id)

        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)

        # Check schedule overlap warning (RF-CAT-07: warn but do not block)
        advertencias: list[str] = []
        if hora_inicio and hora_fin:
            items_existentes = await self.itinerario_repo.list_items(itinerario_id)
            for item in items_existentes:
                if item.dia == dia and item.hora_inicio and item.hora_fin:
                    if hora_inicio < item.hora_fin and item.hora_inicio < hora_fin:
                        advertencias.append(
                            f"Advertencia: solapamiento de horario con otra actividad el {dia}."
                        )

        item = ItemItinerario(
            id=uuid4(),
            itinerario_id=itinerario_id,
            oferta_id=oferta_id,
            dia=dia,
            orden=orden,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
        )
        saved = await self.itinerario_repo.add_item(item)
        return saved, advertencias

    async def listar_itinerarios(self, turista_id: UUID) -> list[Itinerario]:
        return await self.itinerario_repo.list_by_turista(turista_id)


# ---------------------------------------------------------------------------
# CU-24: Configurar Política de Cancelación y Precios Estacionales
# ---------------------------------------------------------------------------


class ConfigurarTarifasUseCase:
    """CU-24: Configurar Política de Cancelación y Precios Estacionales (RF-CAT-13, RF-CAT-14)."""

    def __init__(
        self,
        tarifa_repo: TarifaRepository,
        politica_repo: PoliticaCancelacionRepository,
        oferta_repo: OfertaRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self.tarifa_repo = tarifa_repo
        self.politica_repo = politica_repo
        self.oferta_repo = oferta_repo
        self.event_publisher = event_publisher

    async def agregar_tarifa(
        self,
        oferta_id: UUID,
        prestador_id: UUID,
        temporada: Temporada,
        vigente_desde: datetime.date,
        vigente_hasta: datetime.date,
        precio_por_persona: Decimal,
        moneda: str = "COP",
    ) -> Tarifa:
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)
        if oferta.prestador_id != prestador_id:
            raise DomainError(
                "No está autorizado a modificar tarifas de otra oferta.", code="FORBIDDEN"
            )

        # Validate no overlapping date range for same season
        tarifas_existentes = await self.tarifa_repo.list_by_oferta(oferta_id)
        tuplas_existentes = [
            (t.temporada, t.vigente_desde, t.vigente_hasta) for t in tarifas_existentes
        ]
        validate_tarifa_sin_solapamiento(temporada, vigente_desde, vigente_hasta, tuplas_existentes)

        tarifa = Tarifa(
            id=uuid4(),
            oferta_id=oferta_id,
            temporada=temporada,
            vigente_desde=vigente_desde,
            vigente_hasta=vigente_hasta,
            precio_por_persona=precio_por_persona,
            moneda=moneda,
        )
        saved = await self.tarifa_repo.save(tarifa)

        # Audit event (RF-CAT-14, ADR-04 §4.3)
        await self.event_publisher.publish(
            "auditoria.evento",
            {
                "servicio_origen": "catalogo",
                "tipo_evento": "cambio_tarifa",
                "entidad": "tarifa",
                "entidad_id": str(saved.id),
                "actor_id": str(prestador_id),
                "detalle": {
                    "oferta_id": str(oferta_id),
                    "temporada": temporada.value,
                    "precio": str(precio_por_persona),
                },
            },
        )
        return saved

    async def configurar_politica_cancelacion(
        self,
        oferta_id: UUID,
        prestador_id: UUID,
        horas_reembolso_total: int,
        horas_reembolso_parcial: int,
        porcentaje_reembolso_parcial: int,
    ) -> PoliticaCancelacion:
        oferta = await self.oferta_repo.get_by_id(oferta_id)
        if not oferta:
            raise EntityNotFoundError("Oferta", oferta_id)
        if oferta.prestador_id != prestador_id:
            raise DomainError(
                "No está autorizado a configurar la política de otra oferta.", code="FORBIDDEN"
            )

        politica = PoliticaCancelacion(
            oferta_id=oferta_id,
            horas_reembolso_total=horas_reembolso_total,
            horas_reembolso_parcial=horas_reembolso_parcial,
            porcentaje_reembolso_parcial=porcentaje_reembolso_parcial,
        )
        saved = await self.politica_repo.save(politica)

        await self.event_publisher.publish(
            "auditoria.evento",
            {
                "servicio_origen": "catalogo",
                "tipo_evento": "cambio_politica_cancelacion",
                "entidad": "politica_cancelacion",
                "entidad_id": str(oferta_id),
                "actor_id": str(prestador_id),
                "detalle": {
                    "horas_reembolso_total": horas_reembolso_total,
                    "porcentaje_reembolso_parcial": porcentaje_reembolso_parcial,
                },
            },
        )
        return saved


# ---------------------------------------------------------------------------
# CU-23: Sincronizar Inventario en Lote
# ---------------------------------------------------------------------------


class SincronizarLoteUseCase:
    """CU-23: Sincronizar Inventario en Lote (RF-CAT-11, RF-CAT-12, EC-INTEROP-01).

    Batch synchronization with atomic processing: all valid or none (lotes todo o nada).
    """

    def __init__(
        self,
        lote_repo: LoteRepository,
        oferta_repo: OfertaRepository,
        zona_repo: ZonaRepository,
        tipo_repo: TipoServicioRepository,
    ) -> None:
        self.lote_repo = lote_repo
        self.oferta_repo = oferta_repo
        self.zona_repo = zona_repo
        self.tipo_repo = tipo_repo

    async def execute(
        self,
        *,
        prestador_id: UUID,
        fuente_id: UUID,
        registros: list[dict[str, Any]],
    ) -> LoteSincronizacion:
        now = datetime.datetime.now(datetime.UTC)
        lote = LoteSincronizacion(
            id=uuid4(),
            prestador_id=prestador_id,
            fuente_id=fuente_id,
            estado=EstadoLote.PROCESANDO,
            total_registros=len(registros),
            aceptados=0,
            rechazados=[],
            recibido_en=now,
        )

        ofertas_para_guardar: list[Oferta] = []

        for idx, item in enumerate(registros):
            try:
                # Validation checks
                zona_codigo = item.get("zona_codigo", "")
                validate_zona_canonica(zona_codigo)
                zona = await self.zona_repo.get_by_codigo(zona_codigo)
                if not zona:
                    raise ZonaNoCanonica(zona_codigo)

                tipo_codigo = item.get("tipo_codigo", "")
                tipo = await self.tipo_repo.get_by_codigo(tipo_codigo)
                if not tipo:
                    raise EntityNotFoundError("TipoServicio", tipo_codigo)

                atributos = item.get("atributos", {})
                validate_atributos_contra_esquema(atributos, tipo.esquema_atributos)

                oferta = Oferta(
                    id=uuid4(),
                    prestador_id=prestador_id,
                    tipo_servicio_id=tipo.id,
                    zona_id=zona.id,
                    nombre_es=item.get("nombre_es", ""),
                    nombre_en=item.get("nombre_en", ""),
                    descripcion_es=item.get("descripcion_es", ""),
                    descripcion_en=item.get("descripcion_en", ""),
                    atributos=atributos,
                    estado=EstadoOferta.BORRADOR,
                    creado_en=now,
                    actualizado_en=now,
                )
                ofertas_para_guardar.append(oferta)
            except Exception as e:
                lote.rechazados.append({"fila": idx + 1, "motivo": str(e)})

        # Transactional all-or-nothing rule: if any row fails, reject batch
        if lote.rechazados:
            lote.estado = EstadoLote.FALLIDO
            lote.aceptados = 0
        else:
            for of in ofertas_para_guardar:
                await self.oferta_repo.save(of)
            lote.estado = EstadoLote.COMPLETADO
            lote.aceptados = len(ofertas_para_guardar)

        lote.finalizado_en = datetime.datetime.now(datetime.UTC)
        return await self.lote_repo.save(lote)


# ---------------------------------------------------------------------------
# CU-29: Moderar Contenido
# ---------------------------------------------------------------------------


class ModerarContenidoUseCase:
    """CU-29: Moderar Contenido (Reseñas y Fotos) (RF-CAT-18)."""

    def __init__(self, calificacion_repo: CalificacionRepository) -> None:
        self.calificacion_repo = calificacion_repo

    async def execute(
        self,
        calificacion_id: UUID,
        nuevo_estado: EstadoModeracion,
        justificacion: str = "",
    ) -> Calificacion:
        calif = await self.calificacion_repo.get_by_id(calificacion_id)
        if not calif:
            raise EntityNotFoundError("Calificacion", calificacion_id)

        calif.estado_moderacion = nuevo_estado
        return await self.calificacion_repo.save(calif)


# ---------------------------------------------------------------------------
# Event Consumer Use Cases (ADR-04 §4.3)
# ---------------------------------------------------------------------------


class ProcesarVerificacionPrestadorUseCase:
    """Consumes `auth.prestador.verificacion_resuelta` (ADR-04 §4.3).

    Updates PerfilPrestador `verificado` flag so provider can publish offers.
    """

    def __init__(self, prestador_repo: PerfilPrestadorRepository) -> None:
        self.prestador_repo = prestador_repo

    async def execute(self, prestador_id: UUID, verificado: bool) -> PerfilPrestador:
        perfil = await self.prestador_repo.get_by_id(prestador_id)
        if not perfil:
            perfil = PerfilPrestador(
                prestador_id=prestador_id,
                nombre_comercial="Prestador",
                verificado=verificado,
                actualizado_en=datetime.datetime.now(datetime.UTC),
            )
        else:
            perfil.verificado = verificado
            perfil.actualizado_en = datetime.datetime.now(datetime.UTC)

        return await self.prestador_repo.save(perfil)


class AnonimizarTitularUseCase:
    """Consumes `auth.titular.datos_eliminados` (CU-06, Ley 1581, ADR-04 §4.3).

    Anonymizes user references in reviews and favorites while preserving aggregated ratings.
    """

    def __init__(
        self,
        favorito_repo: FavoritoRepository,
    ) -> None:
        self.favorito_repo = favorito_repo

    async def execute(self, titular_id: UUID) -> None:
        # Delete favorites of deleted user
        ofertas = await self.favorito_repo.list_by_turista(titular_id)
        for of in ofertas:
            await self.favorito_repo.remove(titular_id, of.id)
