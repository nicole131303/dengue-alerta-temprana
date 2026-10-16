"""Clima distrital: CHIRPS (precipitación) y ERA5-Land (temperatura y punto de rocío).

Los valores diarios por distrito se extraen en Google Earth Engine con
``scripts/gee/clima_distrital.js`` (promedio espacial dentro del polígono
de cada distrito) y se exportan como CSV con columnas:

    ubigeo, fecha, precip_mm, temp_c, rocio_c

Aquí se calcula la humedad relativa y se agrega a semana epidemiológica.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dengue_alerta.io import normalizar_ubigeo
from dengue_alerta.panel.calendario import inicio_de_semana


def humedad_relativa(temp_c: pd.Series, rocio_c: pd.Series) -> pd.Series:
    """Humedad relativa (%) con la aproximación de Magnus a partir de T y punto de rocío."""
    a, b = 17.625, 243.04
    hr = 100 * np.exp(a * rocio_c / (b + rocio_c)) / np.exp(a * temp_c / (b + temp_c))
    return hr.clip(0, 100)


def leer_clima_diario(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype={"ubigeo": str}, parse_dates=["fecha"])
    df["ubigeo"] = normalizar_ubigeo(df["ubigeo"])
    if "hum_rel" not in df.columns:
        df["hum_rel"] = humedad_relativa(df["temp_c"], df["rocio_c"])
    return df


def a_semana_epidemiologica(diario: pd.DataFrame) -> pd.DataFrame:
    """Diario -> semanal: lluvia acumulada; temperatura y humedad promedio."""
    d = diario.copy()
    d["fecha"] = inicio_de_semana(d["fecha"])
    semanal = (
        d.groupby(["ubigeo", "fecha"])
        .agg(
            precip_mm=("precip_mm", "sum"),
            temp_c=("temp_c", "mean"),
            hum_rel=("hum_rel", "mean"),
            dias=("precip_mm", "size"),
        )
        .reset_index()
    )
    # Una semana incompleta (bordes del rango descargado) subestima la lluvia acumulada
    semanal = semanal[semanal["dias"] == 7].drop(columns="dias")
    semanal["ubigeo"] = semanal["ubigeo"].astype(str)
    return semanal.reset_index(drop=True)
