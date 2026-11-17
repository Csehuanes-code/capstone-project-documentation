from ia.dominio.modelos import Motivo
from ia.dominio.puntaje import calcular_puntaje
from ia.dominio.ranking import ordenar_por_popularidad, seleccionar

from .conftest import oferta, zona


def _puntajes(ofertas, zonas, config, intereses=("naturaleza",)):
    zs = {z.zona_id: z for z in zonas}
    return [calcular_puntaje(o, zs.get(o.zona_id), frozenset(intereses), config) for o in ofertas]


def test_oferta_en_zona_saturada_se_reemplaza_por_alternativa(config):
    """EC-SOST-01 / boceto W3: Pueblito saturado → se sugiere una alternativa tranquila."""
    # Pueblito puntúa más alto aun con su zona saturada (0,81 frente a 0,78)...
    ofertas = [
        oferta("pueblito", "tayrona", {"naturaleza", "cultura"}, nota=5.0, resenas=500, sost=1.0),
        oferta("naranjos", "naranjos", {"naturaleza"}, nota=3.0, resenas=5, sost=0.0),
    ]
    zonas = [zona("tayrona", 0.95, "Tayrona"), zona("naranjos", 0.30)]
    puntajes = _puntajes(ofertas, zonas, config, ("naturaleza", "cultura"))
    assert puntajes[0].total > puntajes[1].total

    # ...pero se recomienda la alternativa en su lugar.
    items = seleccionar(puntajes, config, 5)

    assert [i.oferta_id for i in items] == ["naranjos"]
    assert items[0].motivo is Motivo.ALTERNATIVA_DESCONGESTION
    assert items[0].alternativa_de_id == "pueblito"
    assert items[0].alternativa_de_zona == "Tayrona"


def test_sin_alternativa_se_mantiene_la_original(config):
    ofertas = [oferta("pueblito", "tayrona", {"naturaleza"})]
    items = seleccionar(_puntajes(ofertas, [zona("tayrona", 0.95)], config), config, 5)
    assert [i.oferta_id for i in items] == ["pueblito"]
    assert items[0].motivo is Motivo.PERSONALIZADA


def test_la_alternativa_debe_compartir_categoria(config):
    ofertas = [
        oferta("pueblito", "tayrona", {"naturaleza"}, nota=5.0, resenas=500),
        oferta("museo", "centro", {"cultura"}, nota=3.0, resenas=5),
    ]
    zonas = [zona("tayrona", 0.95), zona("centro", 0.2)]
    items = seleccionar(_puntajes(ofertas, zonas, config), config, 1)
    assert items[0].oferta_id == "pueblito"


def test_diversidad_maximo_por_zona(config):
    ofertas = [oferta(f"o{i}", "misma-zona", nota=4.9 - i * 0.1) for i in range(4)]
    ofertas.append(oferta("otra", "otra-zona", nota=3.0))
    zonas = [zona("misma-zona", 0.2), zona("otra-zona", 0.2)]
    items = seleccionar(_puntajes(ofertas, zonas, config), config, 5)
    assert sum(i.zona_id == "misma-zona" for i in items) == config.max_por_zona
    assert "otra" in [i.oferta_id for i in items]


def test_respeta_el_limite_y_numera_posiciones(config):
    ofertas = [oferta(f"o{i}", f"z{i}") for i in range(10)]
    items = seleccionar(_puntajes(ofertas, [], config), config, 3)
    assert [i.posicion for i in items] == [1, 2, 3]


def test_es_determinista_ante_empates(config):
    ofertas = [oferta(f"o{i}", f"z{i}") for i in range(5)]
    a = seleccionar(_puntajes(ofertas, [], config), config, 5)
    b = seleccionar(_puntajes(list(reversed(ofertas)), [], config), config, 5)
    assert [i.oferta_id for i in a] == [i.oferta_id for i in b] == [f"o{i}" for i in range(5)]


def test_popularidad():
    ofertas = [oferta("a", reservas=5), oferta("b", reservas=50), oferta("c", reservas=20)]
    assert [o.oferta_id for o in ordenar_por_popularidad(ofertas, 2)] == ["b", "c"]
