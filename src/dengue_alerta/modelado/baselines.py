"""Líneas base: reglas simples que cualquier modelo debe superar para justificarse.

* Persistencia: "si hoy hay brote, en h semanas también". Es muy fuerte en
  el total (los brotes duran varias semanas) pero por construcción NO puede
  anticipar ningún brote nuevo -> por eso se evalúa en el subgrupo
  ``sin_brote_hoy``, donde su sensibilidad es 0.
* Estacional ingenua: "lo que pasó la misma semana del año pasado".
"""

from __future__ import annotations

import pandas as pd


def persistencia(df: pd.DataFrame) -> pd.Series:
    return df["brote_rt"].astype(float)


def estacional_ingenua(df: pd.DataFrame, h: int, panel_completo: pd.DataFrame) -> pd.Series:
    """Estado causal del distrito en la semana objetivo (t+h) pero un año antes.

    Usa ``brote_rt`` de t+h-52, que ya se conocía en t porque h < 52.
    """
    ref = panel_completo[["ubigeo", "fecha", "brote_rt"]].copy()
    ref["fecha"] = ref["fecha"] + pd.Timedelta(weeks=52 - h)
    unido = df[["ubigeo", "fecha"]].merge(ref, on=["ubigeo", "fecha"], how="left")
    return pd.Series(unido["brote_rt"].fillna(0).astype(float).to_numpy(), index=df.index)


LINEAS_BASE = {"persistencia", "estacional"}
