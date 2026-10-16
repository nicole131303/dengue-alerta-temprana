"""Datos compartidos por las pruebas (fixtures).

Se generan datos sintéticos pequeños UNA vez por sesión de pruebas
(``scope="session"``) para que toda la batería corra en segundos.
"""

from __future__ import annotations

import pytest

from dengue_alerta.datos import clima, estructurales, minsa, sintetico
from dengue_alerta.panel.construir import construir_panel
from dengue_alerta.panel.etiquetas import etiquetar_panel

REGLA = {"min_casos": 5, "min_semanas": 3, "gap_cierre": 2}
HORIZONTES = [2, 4]


@pytest.fixture(scope="session")
def datos_sinteticos():
    return sintetico.generar(n_filas=3, n_columnas=4, anio_inicio=2016, anio_fin=2023, semilla=11)


@pytest.fixture(scope="session")
def casos_limpios(datos_sinteticos):
    return minsa.limpiar(datos_sinteticos.casos, ["C", "P"])


@pytest.fixture(scope="session")
def panel(casos_limpios):
    return etiquetar_panel(construir_panel(casos_limpios), REGLA, HORIZONTES)


@pytest.fixture(scope="session")
def clima_semanal(datos_sinteticos, tmp_path_factory):
    ruta = tmp_path_factory.mktemp("clima") / "clima.csv"
    datos_sinteticos.clima_diario.to_csv(ruta, index=False)
    return clima.a_semana_epidemiologica(clima.leer_clima_diario(ruta))


@pytest.fixture(scope="session")
def datos_estructurales(datos_sinteticos, tmp_path_factory):
    ruta = tmp_path_factory.mktemp("est") / "est.csv"
    datos_sinteticos.estructurales.to_csv(ruta, index=False)
    return estructurales.leer_estructurales(ruta)
