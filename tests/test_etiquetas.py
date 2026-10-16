"""La regla de brote es el corazón del proyecto: se prueba con casos hechos a mano."""

import numpy as np
import pytest

from dengue_alerta.panel.etiquetas import (
    brote_en_tiempo_real,
    etiquetar_brotes,
    retraso_de_deteccion,
    tiene_disparador,
)

# Ejemplo de la exposición: semanas 0..19
EJEMPLO = [0, 1, 0, 2, 3, 1, 4, 0, 1, 0, 0, 0, 2, 0, 0, 1, 1, 1, 0, 0]


def test_ejemplo_a_mano_etiqueta_retrospectiva():
    esperado = np.zeros(20, dtype=int)
    esperado[1:9] = 1  # todo el episodio 1..8 es brote (aunque al inicio no se sabía)
    np.testing.assert_array_equal(etiquetar_brotes(EJEMPLO), esperado)


def test_ejemplo_a_mano_estado_en_tiempo_real():
    esperado = np.zeros(20, dtype=int)
    esperado[5:10] = 1  # se enciende en la semana 5 y se apaga tras 2 ceros (semana 10)
    np.testing.assert_array_equal(brote_en_tiempo_real(EJEMPLO), esperado)


def test_retraso_de_deteccion_del_ejemplo():
    assert retraso_de_deteccion(etiquetar_brotes(EJEMPLO), brote_en_tiempo_real(EJEMPLO)) == [4]


@pytest.mark.parametrize(
    "serie, esperado",
    [
        ([1, 1, 1], False),  # 3 semanas pero solo 3 casos
        ([2, 2, 1], True),  # 3 semanas y 5 casos
        ([5, 0, 5, 0, 5], False),  # muchos casos pero nunca 3 semanas seguidas
        ([0, 0, 0], False),
        ([10, 10], False),  # solo 2 semanas
    ],
)
def test_disparador(serie, esperado):
    assert tiene_disparador(serie) is esperado


def test_un_cero_aislado_no_corta_el_episodio():
    # Un solo cero no cierra el episodio: la semana 0 (antes del disparador) también es brote
    assert etiquetar_brotes([3, 0, 3, 3, 3, 0, 0]).tolist() == [1, 1, 1, 1, 1, 0, 0]


def test_el_disparador_exige_semanas_consecutivas():
    # [3,0,3,3]: es un solo episodio pero la racha más larga con casos es de 2 semanas
    assert etiquetar_brotes([3, 0, 3, 3, 0, 0]).sum() == 0


def test_dos_ceros_cierran_el_episodio():
    y = etiquetar_brotes([2, 2, 2, 0, 0, 1])
    assert y.tolist() == [1, 1, 1, 0, 0, 0]


def test_estado_en_tiempo_real_nunca_se_adelanta_a_la_etiqueta():
    rng = np.random.default_rng(0)
    for _ in range(200):
        serie = rng.poisson(rng.uniform(0.1, 3), size=60)
        y, rt = etiquetar_brotes(serie), brote_en_tiempo_real(serie)
        # Toda semana CON CASOS que en tiempo real se declara brote, retrospectivamente también
        # lo es. (La primera semana en cero tras el brote puede seguir "encendida" en tiempo
        # real, porque todavía no se sabe que el episodio terminó: hacen falta 2 ceros.)
        assert np.all(y[(rt == 1) & (serie > 0)] == 1)


def test_parametros_de_la_regla_son_configurables():
    serie = [1, 1, 1, 0, 0]
    assert etiquetar_brotes(serie, min_casos=3).sum() == 3
    assert etiquetar_brotes(serie, min_casos=5).sum() == 0
