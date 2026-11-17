"""Pruebas de contrato: memoria y SQLAlchemy deben comportarse igual ante el mismo uso."""

import os
from dataclasses import replace
from uuid import uuid4

import pytest

from ia.aplicacion.casos_uso import ConsultarRecomendacion, GenerarRecomendaciones
from ia.dominio.repositorios import (
    RepositorioCriterios,
    RepositorioOfertas,
    RepositorioRecomendaciones,
    RepositorioZonas,
)
from ia.infraestructura import semilla
from ia.infraestructura.memoria import (
    CriteriosEnMemoria,
    EventosProcesadosEnMemoria,
    OfertasEnMemoria,
    RecomendacionesEnMemoria,
    UnidadDeTrabajoEnMemoria,
    ZonasEnMemoria,
)
from ia.infraestructura.sql.conexion import (
    crear_esquema,
    crear_motor,
    crear_sesiones,
    sembrar_si_vacia,
)
from ia.infraestructura.sql.tablas import Base
from ia.infraestructura.sql.repositorios import (
    CriteriosSql,
    EventosProcesadosSql,
    OfertasSql,
    RecomendacionesSql,
    UnidadDeTrabajoSql,
    ZonasSql,
)

from .conftest import AHORA, oferta, zona


class RelojFijo:
    def ahora(self):
        return AHORA


def _memoria():
    r = dict(
        ofertas=OfertasEnMemoria(semilla.OFERTAS),
        zonas=ZonasEnMemoria(semilla.ZONAS),
        criterios=CriteriosEnMemoria(semilla.CRITERIOS_V1),
        recomendaciones=RecomendacionesEnMemoria(),
        eventos=EventosProcesadosEnMemoria(),
    )
    r["unidad"] = lambda: UnidadDeTrabajoEnMemoria(r["ofertas"], r["zonas"], r["eventos"])
    return r


URL_POSTGRES = os.getenv("IA_TEST_DATABASE_URL")


def _sql(url: str = "sqlite+pysqlite:///:memory:"):
    motor = crear_motor(url)
    if url == URL_POSTGRES:
        Base.metadata.drop_all(motor)
    crear_esquema(motor)
    sesiones = crear_sesiones(motor)
    assert sembrar_si_vacia(sesiones, semilla.CRITERIOS_V1, semilla.ZONAS, semilla.OFERTAS)
    assert not sembrar_si_vacia(sesiones, semilla.CRITERIOS_V1, semilla.ZONAS, semilla.OFERTAS)
    return dict(
        ofertas=OfertasSql(sesiones),
        zonas=ZonasSql(sesiones),
        criterios=CriteriosSql(sesiones),
        recomendaciones=RecomendacionesSql(sesiones),
        eventos=EventosProcesadosSql(sesiones),
        unidad=lambda: UnidadDeTrabajoSql(sesiones),
    )


def _postgres():
    return _sql(URL_POSTGRES)


FABRICAS = [_memoria, _sql] + ([_postgres] if URL_POSTGRES else [])


@pytest.fixture(params=FABRICAS, ids=[f.__name__.strip("_") for f in FABRICAS])
def repos(request):
    return request.param()


@pytest.mark.skipif(not URL_POSTGRES, reason="requiere IA_TEST_DATABASE_URL (PostgreSQL)")
def test_postgres_impide_modificar_pesos_ya_guardados():
    """El trigger hace inmutable configuracion_criterios, aunque alguien escriba SQL a mano."""
    _postgres()  # esquema limpio con pesos v1
    motor = crear_motor(URL_POSTGRES)
    with pytest.raises(Exception, match="inmutable"):
        with motor.begin() as c:
            c.exec_driver_sql("UPDATE configuracion_criterios SET max_por_zona = 9")


def test_implementan_las_interfaces_abstractas(repos):
    assert isinstance(repos["ofertas"], RepositorioOfertas)
    assert isinstance(repos["zonas"], RepositorioZonas)
    assert isinstance(repos["criterios"], RepositorioCriterios)
    assert isinstance(repos["recomendaciones"], RepositorioRecomendaciones)


def test_no_se_puede_instanciar_una_interfaz():
    with pytest.raises(TypeError):
        RepositorioOfertas()  # type: ignore[abstract]


def test_ofertas(repos):
    r = repos["ofertas"]
    assert {o.oferta_id for o in r.listar_activas()} == {o.oferta_id for o in semilla.OFERTAS}
    assert r.obtener("minca-cascadas") == next(
        o for o in semilla.OFERTAS if o.oferta_id == "minca-cascadas"
    )
    assert r.obtener("no-existe") is None

    r.guardar(replace(r.obtener("museo-oro"), activa=False))
    assert "museo-oro" not in {o.oferta_id for o in r.listar_activas()}

    nueva = oferta("nueva", "z9", {"playa", "aventura"})
    r.guardar(nueva)
    assert r.obtener("nueva") == nueva


def test_zonas(repos):
    r = repos["zonas"]
    assert r.listar()["tayrona"].ocupacion == 0.92
    r.guardar(zona("tayrona", 0.4, "Tayrona"))
    assert r.obtener("tayrona").ocupacion == 0.4
    assert r.obtener("tayrona").actualizado_en == AHORA


def test_criterios_versionados(repos):
    r = repos["criterios"]
    assert r.vigente() == semilla.CRITERIOS_V1
    with pytest.raises(ValueError):
        r.agregar_version(semilla.CRITERIOS_V1)
    v2 = replace(semilla.CRITERIOS_V1, version=2, max_por_zona=3)
    r.agregar_version(v2)
    assert r.vigente() == v2
    assert r.obtener(1) == semilla.CRITERIOS_V1
    assert r.obtener(7) is None


def test_recomendacion_ida_y_vuelta(repos):
    generar = GenerarRecomendaciones(
        repos["ofertas"], repos["zonas"], repos["criterios"], repos["recomendaciones"], RelojFijo()
    )
    emitida = generar.ejecutar(["naturaleza", "cultura", "playa"], limite=7, turista_id="t-1")
    leida = ConsultarRecomendacion(repos["recomendaciones"]).ejecutar(emitida.id)
    assert leida == emitida
    assert repos["recomendaciones"].obtener(uuid4()) is None


def test_eventos_procesados(repos):
    r = repos["eventos"]
    assert r.registrar_si_nuevo("ev-1") is True
    assert r.registrar_si_nuevo("ev-1") is False
    assert r.registrar_si_nuevo("ev-2") is True


def test_memoria_y_sql_recomiendan_lo_mismo():
    resultados = []
    for fabrica in (_memoria, _sql):
        r = fabrica()
        generar = GenerarRecomendaciones(
            r["ofertas"], r["zonas"], r["criterios"], r["recomendaciones"], RelojFijo(),
            generar_id=lambda: uuid4(),
        )
        rec = generar.ejecutar(["naturaleza", "cultura"])
        resultados.append([(i.oferta_id, i.puntaje, i.motivo) for i in rec.items])
    assert resultados[0] == resultados[1]


# --- Unidad de trabajo: el evento y su efecto se guardan juntos o ninguno ------------------

from ia.aplicacion.eventos import ProcesarReservaConfirmada, ReservaConfirmada  # noqa: E402


class _OfertasQueFallan:
    """Envuelve el repositorio real; guardar() falla como si se cortara la conexión."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)

    def guardar(self, oferta):
        raise RuntimeError("corte simulado a mitad de la transacción")


def _con_corte(fabrica):
    def nueva():
        uow = fabrica()
        iniciar = uow._iniciar

        def iniciar_con_corte():
            iniciar()
            uow.ofertas = _OfertasQueFallan(uow.ofertas)

        uow._iniciar = iniciar_con_corte
        return uow

    return nueva


def test_evento_repetido_cuenta_una_sola_vez(repos):
    manejador = ProcesarReservaConfirmada(repos["unidad"])
    antes = repos["ofertas"].obtener("minca-cascadas").reservas_confirmadas
    assert manejador.ejecutar(ReservaConfirmada("ev-uow-1", "minca-cascadas")) is True
    assert manejador.ejecutar(ReservaConfirmada("ev-uow-1", "minca-cascadas")) is False
    assert repos["ofertas"].obtener("minca-cascadas").reservas_confirmadas == antes + 1


def test_un_corte_a_mitad_no_deja_el_evento_marcado(repos):
    """Sin unidad de trabajo, el evento quedaría 'procesado' sin haber sumado la reserva."""
    antes = repos["ofertas"].obtener("minca-cascadas").reservas_confirmadas

    with pytest.raises(RuntimeError, match="corte simulado"):
        ProcesarReservaConfirmada(_con_corte(repos["unidad"])).ejecutar(
            ReservaConfirmada("ev-uow-2", "minca-cascadas")
        )
    assert repos["ofertas"].obtener("minca-cascadas").reservas_confirmadas == antes

    # Al reintentar (RabbitMQ reenvía el mensaje) el evento se aplica normalmente.
    assert ProcesarReservaConfirmada(repos["unidad"]).ejecutar(
        ReservaConfirmada("ev-uow-2", "minca-cascadas")
    ) is True
    assert repos["ofertas"].obtener("minca-cascadas").reservas_confirmadas == antes + 1
