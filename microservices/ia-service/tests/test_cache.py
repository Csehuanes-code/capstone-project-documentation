from dataclasses import replace

from ia.infraestructura import semilla
from ia.infraestructura.cache import CriteriosConCache, OfertasConCache, ZonasConCache
from ia.infraestructura.memoria import CriteriosEnMemoria, OfertasEnMemoria, ZonasEnMemoria

from .conftest import zona


class RelojManual:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Contador(OfertasEnMemoria):
    def __init__(self, *a):
        super().__init__(*a)
        self.lecturas = 0

    def listar_activas(self):
        self.lecturas += 1
        return super().listar_activas()


def test_lee_una_vez_y_vence_a_los_ttl_segundos():
    reloj, base = RelojManual(), Contador(semilla.OFERTAS)
    cache = OfertasConCache(base, ttl=5, reloj=reloj)
    for _ in range(10):
        cache.listar_activas()
    assert base.lecturas == 1
    reloj.t = 5.1
    cache.listar_activas()
    assert base.lecturas == 2


def test_un_cambio_que_ve_otro_proceso_aparece_al_vencer():
    reloj, base = RelojManual(), OfertasEnMemoria(semilla.OFERTAS)
    cache = OfertasConCache(base, ttl=5, reloj=reloj)
    cache.listar_activas()
    base.guardar(replace(base.obtener("museo-oro"), activa=False))  # p. ej. un evento
    assert "museo-oro" in {o.oferta_id for o in cache.listar_activas()}
    reloj.t = 6
    assert "museo-oro" not in {o.oferta_id for o in cache.listar_activas()}


def test_escribir_por_el_decorador_invalida_al_instante():
    base = ZonasEnMemoria(semilla.ZONAS)
    cache = ZonasConCache(base, ttl=60, reloj=RelojManual())
    assert cache.listar()["tayrona"].ocupacion == 0.92
    cache.guardar(zona("tayrona", 0.1, "Tayrona"))
    assert cache.listar()["tayrona"].ocupacion == 0.1


def test_una_version_nueva_de_pesos_invalida_la_vigente():
    cache = CriteriosConCache(CriteriosEnMemoria(semilla.CRITERIOS_V1), ttl=60, reloj=RelojManual())
    assert cache.vigente().version == 1
    cache.agregar_version(replace(semilla.CRITERIOS_V1, version=2))
    assert cache.vigente().version == 2
    assert cache.obtener(1) == semilla.CRITERIOS_V1
    assert cache.obtener(9) is None


def test_devuelve_copias_para_que_nadie_altere_la_cache():
    cache = OfertasConCache(OfertasEnMemoria(semilla.OFERTAS), ttl=60, reloj=RelojManual())
    cache.listar_activas().clear()
    assert len(cache.listar_activas()) == len(semilla.OFERTAS)
