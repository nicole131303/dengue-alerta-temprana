"""Variables climáticas con rezago y del fenómeno El Niño.

¿Por qué con rezago? Entre la lluvia y el aumento de casos pasa el ciclo
del mosquito (huevo -> adulto ~ 7 a 10 días), la incubación extrínseca del
virus en el mosquito (~ 8 a 12 días) y la intrínseca en la persona
(~ 4 a 7 días). Por eso se usan rezagos de 2 a 8 semanas.
"""

from __future__ import annotations

import pandas as pd

from dengue_alerta.datos.enso import indices_por_semana


def agregar(
    panel: pd.DataFrame,
    clima_semanal: pd.DataFrame,
    enso: pd.DataFrame | None,
    lags: list[int],
    rezago_enso_meses: int,
) -> tuple[pd.DataFrame, list[str]]:
    p = panel.merge(clima_semanal, on=["ubigeo", "fecha"], how="left")
    p = p.sort_values(["ubigeo", "fecha"])
    nuevas: list[str] = []

    for var in ("precip_mm", "temp_c", "hum_rel"):
        g = p.groupby("ubigeo", sort=False)[var]
        for k in lags:
            p[f"{var}_lag{k}"] = g.shift(k)
            nuevas.append(f"{var}_lag{k}")

    # Lluvia acumulada de 4 semanas que terminó hace 2 semanas (criaderos formados)
    g = p.groupby("ubigeo", sort=False)["precip_mm"]
    p["precip_4s_lag2"] = g.transform(lambda s: s.shift(2).rolling(4, min_periods=4).sum())
    # Anomalía: lluvia frente al promedio histórico del distrito (calculado de forma expansiva)
    p["precip_anom_lag2"] = p["precip_4s_lag2"] - g.transform(
        lambda s: s.shift(2).rolling(4).sum().expanding(min_periods=52).mean()
    )
    nuevas += ["precip_4s_lag2", "precip_anom_lag2"]

    # El clima "contemporáneo" (semana t) no se usa como predictor: se quita
    p = p.drop(columns=["precip_mm", "temp_c", "hum_rel"])

    if enso is not None:
        semanal = indices_por_semana(p["fecha"], enso, rezago_enso_meses)
        p = p.merge(semanal, on="fecha", how="left")
        nuevas += [c for c in semanal.columns if c != "fecha"]

    return p.reset_index(drop=True), nuevas
