from dataclasses import replace
from datetime import timedelta

import pytest

from ia.aplicacion.casos_uso import (
    ConsultarCriterios,
    ConsultarRecomendacion,
    GenerarRecomendaciones,
    ListarPopulares,
)
from ia.aplicacion.dto import recomendacion_dto
from ia.aplicacion.errores import RecomendacionNoEncontrada, SolicitudInvalida
from ia.aplicacion.puertos import Reloj
from ia.aplicacion.eventos import (
    OcupacionZonaActualizada,
    OfertaActualizada,
    ProcesarOcupacionZona,
    ProcesarOfertaActualizada,
    ProcesarReservaConfirmada,
    ReservaConfirmada,
)
from ia.dominio.modelos import Criterio
from ia.infraestructura import semilla
from ia.infraestructura.memoria import (
    UnidadDeTrabajoEnMemoria,
    CriteriosEnMemoria,
    EventosProcesadosEnMemoria,
    OfertasEnMemoria,
    RecomendacionesEnMemoria,
    ZonasEnMemoria,
)

from .conftest import AHORA


class RelojFijo(Reloj):
    def ahora(self):
        return AHORA


@pytest.fixture
def repos():
    return {
        "ofertas": OfertasEnMemoria(semilla.OFERTAS),
        "zonas": ZonasEnMemoria(semilla.ZONAS),
        "criterios": CriteriosEnMemoria(semilla.CRITERIOS_V1),
        "recomendaciones": RecomendacionesEnMemoria(),
        "eventos": EventosProcesadosEnMemoria(),
    }


@pytest.fixture
def generar(repos):
    return GenerarRecomendaciones(
        repos["ofertas"], repos["zonas"], repos["criterios"], repos["recomendaciones"], RelojFijo()
    )


def test_genera_guarda_y_se_puede_consultar(generar, repos):
    rec = generar.ejecutar(["naturaleza", "cultura"], limite=5)
    assert 1 <= len(rec.items) <= 5
    assert rec.version_pesos == 1
    assert ConsultarRecomendacion(repos["recomendaciones"]).ejecutar(rec.id) == rec


def test_recomendacion_inexistente(repos):
    from uuid import uuid4

    with pytest.raises(RecomendacionNoEncontrada):
        ConsultarRecomendacion(repos["recomendaciones"]).ejecutar(uuid4())


def test_limite_invalido(generar):
    with pytest.raises(SolicitudInvalida):
        generar.ejecutar([], limite=0)


def test_ninguna_recomendacion_de_la_semilla_sale_de_zona_saturada_sin_aviso(generar):
    """Con la semilla, Tayrona está al 92 %: lo que aparezca de allí debe ser excepción explícita."""
    rec = generar.ejecutar(["naturaleza", "cultura", "playa"], limite=7)
    for item in rec.items:
        if item.zona_id == "tayrona":
            assert "muy concurrida" in recomendacion_dto(rec).items[item.posicion - 1].explicacion


@pytest.mark.parametrize("idioma", ["es", "en"])
def test_todas_las_recomendaciones_tienen_explicacion(generar, idioma):
    """EC-IA-01: explicación en el 100 % de las recomendaciones, en ES y EN."""
    for intereses in ([], ["naturaleza"], ["cultura", "gastronomia"], ["playa"]):
        dto = recomendacion_dto(generar.ejecutar(intereses, limite=7), idioma)
        assert dto.items
        assert all(i.explicacion.strip() for i in dto.items)
        assert all(len(i.desglose) == 4 for i in dto.items)


def test_una_version_nueva_de_pesos_no_altera_lo_ya_emitido(generar, repos):
    antes = generar.ejecutar(["naturaleza"])
    v2 = replace(
        semilla.CRITERIOS_V1,
        version=2,
        pesos={
            Criterio.AFINIDAD: 0.30,
            Criterio.CALIDAD: 0.20,
            Criterio.DESCONGESTION: 0.40,
            Criterio.SOSTENIBILIDAD: 0.10,
        },
    )
    repos["criterios"].agregar_version(v2)

    despues = generar.ejecutar(["naturaleza"])
    guardada = ConsultarRecomendacion(repos["recomendaciones"]).ejecutar(antes.id)

    assert guardada.version_pesos == 1 and guardada == antes
    assert despues.version_pesos == 2
    assert ConsultarCriterios(repos["criterios"]).ejecutar(1) == semilla.CRITERIOS_V1


def test_no_se_puede_sobrescribir_una_version(repos):
    with pytest.raises(ValueError):
        repos["criterios"].agregar_version(semilla.CRITERIOS_V1)


def test_populares(repos):
    populares = ListarPopulares(repos["ofertas"], repos["zonas"], repos["criterios"]).ejecutar(3)
    assert [p.oferta.oferta_id for p in populares] == [
        "playa-cristal",
        "pueblito-caminata",
        "museo-oro",
    ]


# --- Eventos (ADR-04): consumidores idempotentes -------------------------------------------


def _unidad(repos):
    return lambda: UnidadDeTrabajoEnMemoria(repos["ofertas"], repos["zonas"], repos["eventos"])



def test_reserva_confirmada_repetida_cuenta_una_vez(repos):
    manejador = ProcesarReservaConfirmada(_unidad(repos))
    antes = repos["ofertas"].obtener("minca-cascadas").reservas_confirmadas

    assert manejador.ejecutar(ReservaConfirmada("ev-1", "minca-cascadas")) is True
    assert manejador.ejecutar(ReservaConfirmada("ev-1", "minca-cascadas")) is False

    assert repos["ofertas"].obtener("minca-cascadas").reservas_confirmadas == antes + 1


def test_oferta_actualizada_conserva_popularidad_y_puede_retirarse(repos):
    manejador = ProcesarOfertaActualizada(_unidad(repos))
    previa = repos["ofertas"].obtener("museo-oro")
    manejador.ejecutar(
        OfertaActualizada(
            evento_id="ev-2",
            oferta_id="museo-oro",
            nombre="Museo del Oro Tairona",
            zona_id="centro",
            categorias=("cultura", "historia"),
            calificacion_promedio=4.7,
            numero_resenas=151,
            indice_sostenibilidad=0.9,
            prestador_id="prest-banrep",
            activa=False,
        )
    )
    nueva = repos["ofertas"].obtener("museo-oro")
    assert nueva.nombre == "Museo del Oro Tairona"
    assert nueva.reservas_confirmadas == previa.reservas_confirmadas
    assert "museo-oro" not in {o.oferta_id for o in repos["ofertas"].listar_activas()}


def test_alerta_de_capacidad_cambia_la_recomendacion(generar, repos):
    """EC-SOST-01: al saturarse Minca, deja de recomendarse como primera opción tranquila."""
    manejador = ProcesarOcupacionZona(_unidad(repos))
    manejador.ejecutar(
        OcupacionZonaActualizada("ev-3", "minca", "Minca", 0.97, AHORA + timedelta(minutes=5))
    )
    rec = generar.ejecutar(["naturaleza", "aventura"], limite=7)
    for item in rec.items:
        if item.oferta_id == "minca-cascadas":
            assert item.nivel.value == "muy_concurrida"


def test_medicion_vieja_no_pisa_la_nueva(repos):
    manejador = ProcesarOcupacionZona(_unidad(repos))
    manejador.ejecutar(OcupacionZonaActualizada("ev-4", "minca", "Minca", 0.9, AHORA))
    manejador.ejecutar(
        OcupacionZonaActualizada("ev-5", "minca", "Minca", 0.1, AHORA - timedelta(hours=1))
    )
    assert repos["zonas"].obtener("minca").ocupacion == 0.9
