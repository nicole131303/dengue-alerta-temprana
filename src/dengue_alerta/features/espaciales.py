"""Variables de contagio espacial: ¿qué está pasando en los distritos vecinos?

El dengue no respeta límites administrativos: la gente se infecta donde
trabaja o estudia y el mosquito se mueve. Un aumento en los vecinos suele
anticipar el aumento propio por una o dos semanas.
"""

from __future__ import annotations

import pandas as pd


def agregar(panel: pd.DataFrame, adyacencia: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    p = panel.copy()
    base = p[["ubigeo", "fecha", "casos", "brote_rt"]].rename(columns={"ubigeo": "vecino"})

    # Cruce (distrito, vecino) x semana y agregación sobre los vecinos
    cruzado = adyacencia.merge(base, on="vecino", how="inner")
    vec = (
        cruzado.groupby(["ubigeo", "fecha"])
        .agg(
            vec_casos=("casos", "sum"),
            vec_en_brote=("brote_rt", "mean"),
            n_vecinos=("vecino", "nunique"),
        )
        .reset_index()
    )
    p = p.merge(vec, on=["ubigeo", "fecha"], how="left")
    p[["vec_casos", "vec_en_brote"]] = p[["vec_casos", "vec_en_brote"]].fillna(0.0)
    p["n_vecinos"] = p["n_vecinos"].fillna(0)

    p = p.sort_values(["ubigeo", "fecha"])
    g = p.groupby("ubigeo", sort=False)["vec_casos"]
    p["vec_casos_lag1"] = g.shift(1)
    p["vec_casos_4s"] = g.transform(lambda s: s.rolling(4, min_periods=4).sum())
    p["vec_tendencia"] = p["vec_casos_4s"] - p.groupby("ubigeo", sort=False)["vec_casos_4s"].shift(
        4
    )

    nuevas = ["vec_casos", "vec_casos_lag1", "vec_casos_4s", "vec_tendencia", "vec_en_brote"]
    return p.reset_index(drop=True), nuevas
