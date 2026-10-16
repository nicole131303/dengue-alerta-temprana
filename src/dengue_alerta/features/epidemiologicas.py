"""Variables de la propia historia de casos del distrito."""

from __future__ import annotations

import numpy as np
import pandas as pd


def semanas_desde_ultimo(estado: np.ndarray, tope: int = 999) -> np.ndarray:
    """Semanas transcurridas desde la última semana en estado de brote (``tope`` si nunca)."""
    salida = np.full(len(estado), tope, dtype=np.int64)
    ultimo = None
    for t, e in enumerate(estado):
        if e == 1:
            ultimo = t
        if ultimo is not None:
            salida[t] = min(t - ultimo, tope)
    return salida


def agregar(panel: pd.DataFrame, n_lags: int = 8) -> tuple[pd.DataFrame, list[str]]:
    p = panel.sort_values(["ubigeo", "fecha"]).copy()
    g = p.groupby("ubigeo", sort=False)["casos"]
    nuevas: list[str] = []

    # Rezagos: casos de t, t-1, ..., t-(n_lags-1)
    for k in range(n_lags):
        p[f"casos_lag{k}"] = g.shift(k)
        nuevas.append(f"casos_lag{k}")

    # Acumulados recientes (ventanas que TERMINAN en t)
    for v in (4, 12, 52):
        p[f"casos_{v}s"] = g.transform(lambda s, v=v: s.rolling(v, min_periods=v).sum())
        nuevas.append(f"casos_{v}s")

    # Pendiente de los últimos 4 puntos (regresión lineal con x = -1.5, -0.5, 0.5, 1.5)
    p["tendencia_4s"] = (
        3 * p["casos_lag0"] + p["casos_lag1"] - p["casos_lag2"] - 3 * p["casos_lag3"]
    ) / 10
    # Aceleración: ¿las últimas 4 semanas superan a las 4 anteriores?
    previas_4s = p.groupby("ubigeo", sort=False)["casos_4s"].shift(4)  # semanas t-7 .. t-4
    p["razon_4s"] = (p["casos_4s"] + 1) / (previas_4s + 1)
    nuevas += ["tendencia_4s", "razon_4s"]

    # Estado causal y memoria del último brote (inmunidad de rebaño de corto plazo)
    p["sem_desde_brote"] = p.groupby("ubigeo", sort=False)["brote_rt"].transform(
        lambda s: pd.Series(semanas_desde_ultimo(s.to_numpy()), index=s.index)
    )
    nuevas += ["brote_rt", "sem_desde_brote"]

    # Estacionalidad como círculo: la semana 52 queda "cerca" de la semana 1
    angulo = 2 * np.pi * p["semana_epi"] / 52.18
    p["sem_sin"], p["sem_cos"] = np.sin(angulo), np.cos(angulo)
    nuevas += ["sem_sin", "sem_cos"]
    return p.reset_index(drop=True), nuevas
