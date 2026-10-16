"""Variables estructurales: explican por qué unos distritos son más vulnerables que otros."""

from __future__ import annotations

import pandas as pd

COLUMNAS_CANDIDATAS = [
    "log_densidad",
    "altitud_m",
    "pct_sin_agua_red",
    "pct_sin_desague",
    "pct_hacinamiento",
]


def agregar(panel: pd.DataFrame, estructurales: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    columnas = [c for c in COLUMNAS_CANDIDATAS if c in estructurales.columns]
    p = panel.merge(estructurales[["ubigeo", *columnas]], on="ubigeo", how="left")
    return p, columnas
