"""Variables predictoras y ensamblado del dataset."""

import numpy as np
import pandas as pd

from dengue_alerta.features import epidemiologicas, espaciales
from dengue_alerta.features.dataset import construir_dataset
from dengue_alerta.features.epidemiologicas import semanas_desde_ultimo

CFG = {"lags_casos": 8, "lags_clima": [2, 4], "rezago_publicacion_enso_meses": 2}


def test_rezagos_no_cruzan_distritos(panel):
    p, _ = epidemiologicas.agregar(panel)
    primeras = p.groupby("ubigeo").head(1)
    assert primeras["casos_lag1"].isna().all()  # la primera semana no tiene pasado


def test_acumulado_4_semanas(panel):
    p, _ = epidemiologicas.agregar(panel)
    u = p[p["ubigeo"] == p["ubigeo"].iloc[0]].reset_index(drop=True)
    assert u.loc[20, "casos_4s"] == u.loc[17:20, "casos"].sum()


def test_semanas_desde_ultimo_brote():
    assert semanas_desde_ultimo(np.array([0, 1, 0, 0, 1, 0])).tolist() == [999, 0, 1, 2, 0, 1]


def test_vecinos_suman_casos_de_los_adyacentes():
    fechas = pd.date_range("2020-01-05", periods=3, freq="7D")
    panel = pd.DataFrame(
        {
            "ubigeo": np.repeat(["000001", "000002", "000003"], 3),
            "fecha": np.tile(fechas, 3),
            "casos": [1, 2, 3, 10, 20, 30, 100, 200, 300],
            "brote_rt": 0,
        }
    )
    ady = pd.DataFrame({"ubigeo": ["000001", "000001"], "vecino": ["000002", "000003"]})
    p, _ = espaciales.agregar(panel, ady)
    d1 = p[p["ubigeo"] == "000001"]["vec_casos"].tolist()
    assert d1 == [110, 220, 330]
    assert p[p["ubigeo"] == "000002"]["vec_casos"].eq(0).all()  # sin vecinos declarados


def test_dataset_registra_grupos_y_filtra_altitud(
    panel, datos_sinteticos, clima_semanal, datos_estructurales
):
    d, grupos = construir_dataset(
        panel,
        CFG,
        2500,
        adyacencia=datos_sinteticos.adyacencia,
        clima_semanal=clima_semanal,
        enso=datos_sinteticos.enso,
        datos_estructurales=datos_estructurales,
    )
    assert set(grupos) == {"epidemiologicas", "espaciales", "climaticas", "estructurales"}
    for cols in grupos.values():
        assert set(cols) <= set(d.columns)
    altos = datos_estructurales.loc[datos_estructurales["altitud_m"] >= 2500, "ubigeo"]
    assert not d["ubigeo"].isin(altos).any()
    assert not d.duplicated(["ubigeo", "fecha"]).any()
