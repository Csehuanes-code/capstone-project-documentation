"""Controladores REST de Reservas. Todo bajo /api/v1 (el Gateway enruta por prefijo).

Público:     GET  /ofertas/{id}/disponibilidad[/cercanas]
Turista:     POST /reservas · GET /reservas/mias · POST /reservas/{id}/cancelar
             POST /reservas/{id}/disputas · POST /franjas/{id}/lista-espera
             GET  /lista-espera/mias · DELETE /lista-espera/{id}
Dueño/prest./admin: GET /reservas/{id}
Prestador:   GET  /prestador/reservas · POST /prestador/franjas
Admin:       GET  /admin/disputas · POST /admin/disputas/{id}/resolver
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request, Response, status
from fastapi.responses import JSONResponse

from comun.seguridad import Identidad, requiere_rol
from reservas.api.esquemas import (
    AbrirDisputaRequest,
    ComprobanteReservaResponse,
    CrearFranjaRequest,
    CrearReservaRequest,
    CupoInsuficienteResponse,
    DisputaResponse,
    EntradaListaEsperaResponse,
    ErrorResponse,
    FranjaDisponibilidadResponse,
    PoliticaCancelacionDTO,
    ResolverDisputaRequest,
    UnirseListaEsperaRequest,
)
from reservas.aplicacion.casos_uso import (
    AbrirDisputaUseCase,
    CancelarReservaUseCase,
    ConsultarComprobanteUseCase,
    ConsultarDisponibilidadUseCase,
    CrearFranjaPrestadorUseCase,
    IniciarReservaUseCase,
    ListarDisputasUseCase,
    ListarMiListaEsperaUseCase,
    ListarReservasPrestadorUseCase,
    ListarReservasTuristaUseCase,
    ResolverDisputaUseCase,
    RetirarseListaEsperaUseCase,
    SugerirFechasCercanasUseCase,
    UnirseListaEsperaUseCase,
)
from reservas.aplicacion.dto import (
    FiltroReservas,
    ResultadoDisputa,
    ResultadoIniciarReserva,
    ResultadoListaEspera,
    SolicitudCrearFranja,
    SolicitudIniciarReserva,
)
from reservas.dominio.entidades import FranjaDisponibilidad
from reservas.dominio.excepciones import (
    AccesoDenegadoDominioError,
    ClaveIdempotenciaDuplicadaError,
    CupoInsuficienteError,
    DisputaInvalidaError,
    ErrorDominio,
    ListaEsperaInvalidaError,
    OfertaNoDisponibleError,
    RecursoNoEncontradoError,
    ReembolsoFallidoError,
    ReservaNoCancelableError,
    ServicioCatalogoNoDisponibleError,
    TransicionEstadoInvalidaError,
)

# Error de dominio → código HTTP. Cualquier otra excepción responde 500 sin detalles internos.
CODIGOS_ERROR: list[tuple[type[ErrorDominio], int]] = [
    (AccesoDenegadoDominioError, status.HTTP_403_FORBIDDEN),
    (RecursoNoEncontradoError, status.HTTP_404_NOT_FOUND),
    (CupoInsuficienteError, status.HTTP_409_CONFLICT),
    (OfertaNoDisponibleError, status.HTTP_409_CONFLICT),
    (TransicionEstadoInvalidaError, status.HTTP_409_CONFLICT),
    (ReservaNoCancelableError, status.HTTP_409_CONFLICT),
    (ListaEsperaInvalidaError, status.HTTP_409_CONFLICT),
    (ClaveIdempotenciaDuplicadaError, status.HTTP_409_CONFLICT),
    (DisputaInvalidaError, 422),
    (ReembolsoFallidoError, status.HTTP_502_BAD_GATEWAY),
    (ServicioCatalogoNoDisponibleError, status.HTTP_503_SERVICE_UNAVAILABLE),
]


def registrar_manejadores_error(app: FastAPI) -> None:
    @app.exception_handler(ErrorDominio)
    async def _error_dominio(_request: Request, exc: ErrorDominio) -> JSONResponse:
        codigo = next((c for tipo, c in CODIGOS_ERROR if isinstance(exc, tipo)), status.HTTP_400_BAD_REQUEST)
        cuerpo: dict[str, object] = {"detail": str(exc)}
        if isinstance(exc, CupoInsuficienteError):
            cuerpo |= {"disponibles": exc.disponibles, "lista_espera_disponible": True}
        return JSONResponse(status_code=codigo, content=cuerpo)


@dataclass(frozen=True)
class CasosDeUsoReservas:
    disponibilidad: ConsultarDisponibilidadUseCase
    fechas_cercanas: SugerirFechasCercanasUseCase
    iniciar_reserva: IniciarReservaUseCase
    comprobante: ConsultarComprobanteUseCase
    mis_reservas: ListarReservasTuristaUseCase
    reservas_prestador: ListarReservasPrestadorUseCase
    crear_franja: CrearFranjaPrestadorUseCase
    cancelar: CancelarReservaUseCase
    unirse_lista: UnirseListaEsperaUseCase
    retirarse_lista: RetirarseListaEsperaUseCase
    mi_lista: ListarMiListaEsperaUseCase
    abrir_disputa: AbrirDisputaUseCase
    listar_disputas: ListarDisputasUseCase
    resolver_disputa: ResolverDisputaUseCase


def _comprobante(res: ResultadoIniciarReserva) -> ComprobanteReservaResponse:
    return ComprobanteReservaResponse(
        reserva_id=res.reserva_id,
        codigo=res.codigo,
        estado=res.estado,  # type: ignore[arg-type]
        oferta_id=res.oferta_id,
        nombre_oferta=res.nombre_oferta,
        zona_id=res.zona_id,
        prestador_id=res.prestador_id,
        prestador_nombre=res.prestador_nombre,
        prestador_contacto=res.prestador_contacto,
        punto_encuentro=res.punto_encuentro,
        fecha_servicio=res.fecha_servicio,
        hora_servicio=res.hora_servicio,
        personas=res.personas,
        acompanantes=res.acompanantes,
        precio_unitario=res.precio_unitario,
        total=res.total,
        moneda=res.moneda,
        politica_cancelacion=PoliticaCancelacionDTO(**res.politica_cancelacion),
        pago_aprobado=res.pago_aprobado,
        referencia_pago=res.referencia_pago,
        monto_reembolso=res.monto_reembolso,
        mensaje_es=res.mensaje_es,
        mensaje_en=res.mensaje_en,
    )


def _franja(f: FranjaDisponibilidad) -> FranjaDisponibilidadResponse:
    return FranjaDisponibilidadResponse(
        id=f.id, oferta_id=f.oferta_id, zona_id=f.zona_id, prestador_id=f.prestador_id,
        fecha=f.fecha, hora_inicio=f.hora_inicio.strftime("%H:%M"),
        cupo_total=f.cupo_total, cupo_disponible=f.cupo_disponible,
    )


def _entrada(r: ResultadoListaEspera) -> EntradaListaEsperaResponse:
    return EntradaListaEsperaResponse(**r.__dict__)


def _disputa(r: ResultadoDisputa) -> DisputaResponse:
    return DisputaResponse(**r.__dict__)


ERRORES_COMUNES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Falta el token o no es válido"},
    403: {"model": ErrorResponse, "description": "Rol sin permiso o recurso de otro usuario"},
}


def crear_router_reservas(
    *, obtener_identidad: Callable[..., Identidad], casos: CasosDeUsoReservas
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    turista = requiere_rol(obtener_identidad, "turista")
    prestador = requiere_rol(obtener_identidad, "prestador")
    administrador = requiere_rol(obtener_identidad, "administrador")

    # --- CU-08: disponibilidad (público) ---------------------------------------------------

    @router.get(
        "/ofertas/{oferta_id}/disponibilidad",
        response_model=list[FranjaDisponibilidadResponse],
        tags=["Disponibilidad"],
        summary="Franjas con cupo para una fecha y número de personas (CU-08, W2)",
    )
    def consultar_disponibilidad(
        oferta_id: str,
        fecha: date | None = Query(default=None, description="AAAA-MM-DD"),
        personas: int = Query(default=1, ge=1, le=20),
    ) -> list[FranjaDisponibilidadResponse]:
        return [_franja(f) for f in casos.disponibilidad.ejecutar(oferta_id, fecha, personas)]

    @router.get(
        "/ofertas/{oferta_id}/disponibilidad/cercanas",
        response_model=list[FranjaDisponibilidadResponse],
        tags=["Disponibilidad"],
        summary="Fechas cercanas con cupo cuando la pedida está agotada (RF-RES-02)",
    )
    def fechas_cercanas(
        oferta_id: str,
        fecha: date = Query(..., description="Fecha deseada (AAAA-MM-DD)"),
        personas: int = Query(default=1, ge=1, le=20),
    ) -> list[FranjaDisponibilidadResponse]:
        return [_franja(f) for f in casos.fechas_cercanas.ejecutar(oferta_id, fecha, personas)]

    # --- CU-11 / CU-12 / CU-16: reservar ---------------------------------------------------

    @router.post(
        "/reservas",
        response_model=ComprobanteReservaResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Reservas"],
        summary="Reservar y pagar (CU-11 flujo crítico, CU-12 grupo, CU-16 pago; W4)",
        responses={
            201: {"description": "Reserva confirmada y pago aprobado"},
            402: {"model": ComprobanteReservaResponse,
                  "description": "Pago rechazado o tiempo agotado: sin cobro y cupo devuelto"},
            404: {"model": ErrorResponse, "description": "La franja no existe"},
            409: {"model": CupoInsuficienteResponse,
                  "description": "Sin cupo suficiente (informa el máximo), oferta inactiva o lista de espera vencida"},
            503: {"model": ErrorResponse, "description": "Catálogo no disponible (no se bloqueó cupo)"},
            **ERRORES_COMUNES,
        },
    )
    def iniciar_reserva(
        body: CrearReservaRequest,
        response: Response,
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=4, max_length=120,
                                      description="Repetir la misma clave devuelve la misma respuesta"),
        identidad: Identidad = Depends(turista),
    ) -> ComprobanteReservaResponse:
        resultado = casos.iniciar_reserva.ejecutar(
            SolicitudIniciarReserva(
                clave_idempotencia=idempotency_key,
                franja_id=body.franja_id,
                personas=body.personas,
                turista_id=identidad.sub,
                correo_turista=str(body.correo_turista),
                idioma=body.idioma,
                metodo_pago=body.metodo_pago,
                datos_pago=body.datos_pago,
                acompanantes=body.acompanantes,
                entrada_lista_espera_id=body.entrada_lista_espera_id,
            )
        )
        if not resultado.pago_aprobado:
            response.status_code = status.HTTP_402_PAYMENT_REQUIRED
        return _comprobante(resultado)

    # --- W6 / CU-15 / RF-RES-15 ---------------------------------------------------------------

    @router.get(
        "/reservas/mias",
        response_model=list[ComprobanteReservaResponse],
        tags=["Reservas"],
        summary="Historial del turista, filtrable por estado, fechas y prestador (W6, RF-RES-15)",
        responses=ERRORES_COMUNES,
    )
    def listar_mis_reservas(
        estado: str | None = Query(default=None, description="pendiente_pago, confirmada, cancelada…"),
        desde: date | None = Query(default=None),
        hasta: date | None = Query(default=None),
        prestador_id: str | None = Query(default=None),
        identidad: Identidad = Depends(turista),
    ) -> list[ComprobanteReservaResponse]:
        filtro = FiltroReservas(estado=estado, desde=desde, hasta=hasta, prestador_id=prestador_id)
        return [_comprobante(r) for r in casos.mis_reservas.ejecutar(identidad.sub, filtro)]

    @router.get(
        "/reservas/{reserva_id}",
        response_model=ComprobanteReservaResponse,
        tags=["Reservas"],
        summary="Comprobante: solo el turista dueño, el prestador de la oferta o un admin (CU-18, W5)",
        responses={404: {"model": ErrorResponse}, **ERRORES_COMUNES},
    )
    def consultar_comprobante(
        reserva_id: str, identidad: Identidad = Depends(obtener_identidad)
    ) -> ComprobanteReservaResponse:
        return _comprobante(casos.comprobante.ejecutar(reserva_id, identidad.sub, identidad.rol))

    # --- CU-14: cancelar ---------------------------------------------------------------------

    @router.post(
        "/reservas/{reserva_id}/cancelar",
        response_model=ComprobanteReservaResponse,
        tags=["Reservas"],
        summary="Cancelar aplicando la política del prestador y reembolsar si corresponde (CU-14)",
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, **ERRORES_COMUNES},
    )
    def cancelar_reserva(
        reserva_id: str, identidad: Identidad = Depends(turista)
    ) -> ComprobanteReservaResponse:
        return _comprobante(casos.cancelar.ejecutar(reserva_id, identidad.sub))

    # --- CU-17: disputas ---------------------------------------------------------------------

    @router.post(
        "/reservas/{reserva_id}/disputas",
        response_model=DisputaResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Disputas"],
        summary="Reportar un cobro incorrecto (CU-17)",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, **ERRORES_COMUNES},
    )
    def abrir_disputa(
        reserva_id: str, body: AbrirDisputaRequest, identidad: Identidad = Depends(turista)
    ) -> DisputaResponse:
        return _disputa(casos.abrir_disputa.ejecutar(
            reserva_id=reserva_id, turista_id=identidad.sub, motivo=body.motivo
        ))

    @router.get(
        "/admin/disputas",
        response_model=list[DisputaResponse],
        tags=["Disputas"],
        summary="Disputas para revisión del administrador (CU-17)",
        responses=ERRORES_COMUNES,
    )
    def listar_disputas(
        estado: str | None = Query(default=None, pattern="^(en_revision|aprobada|rechazada)$"),
        _admin: Identidad = Depends(administrador),
    ) -> list[DisputaResponse]:
        return [_disputa(d) for d in casos.listar_disputas.ejecutar(estado)]

    @router.post(
        "/admin/disputas/{disputa_id}/resolver",
        response_model=DisputaResponse,
        tags=["Disputas"],
        summary="Aprobar (con reembolso) o rechazar una disputa, con justificación (CU-17)",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse},
                   502: {"model": ErrorResponse, "description": "La pasarela rechazó el reembolso"},
                   **ERRORES_COMUNES},
    )
    def resolver_disputa(
        disputa_id: str, body: ResolverDisputaRequest, admin: Identidad = Depends(administrador)
    ) -> DisputaResponse:
        return _disputa(casos.resolver_disputa.ejecutar(
            disputa_id=disputa_id,
            administrador_id=admin.sub,
            aprobada=body.decision == "aprobada",
            justificacion=body.justificacion,
            monto_reembolso=body.monto_reembolso,
        ))

    # --- CU-13: lista de espera -------------------------------------------------------------

    @router.post(
        "/franjas/{franja_id}/lista-espera",
        response_model=EntradaListaEsperaResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Lista de espera"],
        summary="Unirse a la lista de espera de una franja agotada (CU-13)",
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, **ERRORES_COMUNES},
    )
    def unirse_lista_espera(
        franja_id: str, body: UnirseListaEsperaRequest, identidad: Identidad = Depends(turista)
    ) -> EntradaListaEsperaResponse:
        return _entrada(casos.unirse_lista.ejecutar(
            franja_id=franja_id, turista_id=identidad.sub, correo_turista=str(body.correo_turista),
            idioma=body.idioma, personas=body.personas,
        ))

    @router.get(
        "/lista-espera/mias",
        response_model=list[EntradaListaEsperaResponse],
        tags=["Lista de espera"],
        summary="Mis entradas de lista de espera (posición u oferta vigente)",
        responses=ERRORES_COMUNES,
    )
    def mi_lista_espera(identidad: Identidad = Depends(turista)) -> list[EntradaListaEsperaResponse]:
        return [_entrada(e) for e in casos.mi_lista.ejecutar(identidad.sub)]

    @router.delete(
        "/lista-espera/{entrada_id}",
        response_model=EntradaListaEsperaResponse,
        tags=["Lista de espera"],
        summary="Salir de la lista o declinar el cupo ofrecido (pasa al siguiente)",
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, **ERRORES_COMUNES},
    )
    def retirarse_lista_espera(
        entrada_id: str, identidad: Identidad = Depends(turista)
    ) -> EntradaListaEsperaResponse:
        return _entrada(casos.retirarse_lista.ejecutar(entrada_id, identidad.sub))

    # --- Prestador: W7 + RC-N03, franjas ------------------------------------------------------

    @router.get(
        "/prestador/reservas",
        response_model=list[ComprobanteReservaResponse],
        tags=["Prestador"],
        summary="Reservas de mis ofertas; 403 si se piden las de otro prestador (W7, RC-N03)",
        responses=ERRORES_COMUNES,
    )
    def listar_reservas_prestador(
        prestador_id: str | None = Query(default=None, description="Si es otro distinto al del token → 403"),
        estado: str | None = Query(default=None),
        desde: date | None = Query(default=None),
        hasta: date | None = Query(default=None),
        identidad: Identidad = Depends(prestador),
    ) -> list[ComprobanteReservaResponse]:
        filtro = FiltroReservas(estado=estado, desde=desde, hasta=hasta)
        return [_comprobante(r) for r in casos.reservas_prestador.ejecutar(identidad.sub, prestador_id, filtro)]

    @router.post(
        "/prestador/franjas",
        response_model=FranjaDisponibilidadResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Prestador"],
        summary="Publicar una franja de disponibilidad para una oferta propia",
        responses={409: {"model": ErrorResponse}, **ERRORES_COMUNES},
    )
    def crear_franja(
        body: CrearFranjaRequest, identidad: Identidad = Depends(prestador)
    ) -> FranjaDisponibilidadResponse:
        return _franja(casos.crear_franja.ejecutar(
            SolicitudCrearFranja(
                prestador_id=identidad.sub, oferta_id=body.oferta_id, fecha=body.fecha,
                hora_inicio=body.hora_inicio, cupo_total=body.cupo_total,
            )
        ))

    return router
