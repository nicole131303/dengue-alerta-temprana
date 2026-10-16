"""Variables estructurales por distrito (cambian poco en el tiempo).

Fuentes: Censo 2017 del INEI (REDATAM) para población y servicios básicos
de la vivienda, y SRTM para la altitud media. Formato esperado del CSV:

    ubigeo, poblacion, superficie_km2, altitud_m,
    pct_sin_agua_red, pct_sin_desague, pct_hacinamiento
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dengue_alerta.io import normalizar_ubigeo


def leer_estructurales(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype={"ubigeo": str})
    df["ubigeo"] = normalizar_ubigeo(df["ubigeo"])
    for col in df.columns.drop("ubigeo"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    if {"poblacion", "superficie_km2"} <= set(df.columns):
        df["log_densidad"] = np.log1p(df["poblacion"] / df["superficie_km2"])
    return df


def distritos_bajo_altitud(estructurales: pd.DataFrame, altitud_max: float) -> set[str]:
    """Distritos de la zona de riesgo entomológico (por debajo de ``altitud_max`` m s. n. m.)."""
    return set(estructurales.loc[estructurales["altitud_m"] < altitud_max, "ubigeo"])
