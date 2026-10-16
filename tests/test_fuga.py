"""Pruebas anti-fuga: ninguna variable de la semana t puede usar información de t+1 en adelante.

Si alguien agrega una variable que mira el futuro, estas pruebas fallan en
GitHub Actions y el Pull Request no se puede fusionar.
"""

import numpy as np
import pandas as pd

from conftest import HORIZONTES, REGLA
from dengue_alerta.datos.enso import indices_por_semana
from dengue_alerta.features import climaticas
from dengue_alerta.modelado.auditoria import prueba_perturbacion


def test_perturbar_el_futuro_no_cambia_variables_del_pasado(panel, datos_sinteticos):
    reporte = prueba_perturbacion(
        panel, "2020-06-30", REGLA, HORIZONTES, adyacencia=datos_sinteticos.adyacencia
    )
    assert reporte["variables_que_cambiaron"] == []
    assert reporte["variables_revisadas"] > 15


def test_la_etiqueta_retrospectiva_si_mira_el_futuro():
    # Control positivo: demuestra que la prueba es capaz de detectar dependencia del futuro
    base = pd.DataFrame(
        {
            "ubigeo": "240101",
            "fecha": pd.date_range("2020-01-05", periods=10, freq="7D"),
            "anio_epi": 2020,
            "semana_epi": range(1, 11),
            "casos": [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
        }
    )
    reporte = prueba_perturbacion(base, "2020-02-02", REGLA, HORIZONTES)
    assert reporte["variables_que_cambiaron"] == []
    assert reporte["semanas_con_etiqueta_cambiada"] > 0


def test_clima_usa_solo_rezagos(panel, clima_semanal):
    p, cols = climaticas.agregar(panel, clima_semanal, None, [2, 4], 2)
    assert all("lag" in c for c in cols)
    assert "precip_mm" not in p.columns  # el clima de la semana t no entra al modelo
    uno = p[p["ubigeo"] == p["ubigeo"].iloc[0]].reset_index(drop=True)
    original = clima_semanal[clima_semanal["ubigeo"] == uno["ubigeo"].iloc[0]].set_index("fecha")
    t = 30
    fecha_lag = uno.loc[t, "fecha"] - pd.Timedelta(weeks=2)
    assert np.isclose(uno.loc[t, "precip_mm_lag2"], original.loc[fecha_lag, "precip_mm"])


def test_enso_respeta_rezago_de_publicacion():
    indices = pd.DataFrame({"anio": [2023] * 12, "mes": range(1, 13), "icen": range(12)})
    semanas = pd.Series(pd.to_datetime(["2023-05-07"]))  # mayo
    salida = indices_por_semana(semanas, indices, rezago_meses=2)
    assert salida["enso_icen"].iloc[0] == 2  # usa marzo (índice 2), no mayo
