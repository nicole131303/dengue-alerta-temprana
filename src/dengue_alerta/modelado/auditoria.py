"""Auditoría de fuga de información (prueba de perturbación del futuro).

Idea (Kapoor y Narayanan, 2023): si una variable de la semana t cambia
cuando altero los casos POSTERIORES a t, entonces esa variable está usando
el futuro y el desempeño del modelo es una ilusión.

Procedimiento:
    1. Se construyen etiquetas y variables con los datos originales.
    2. Se alteran al azar todos los casos posteriores a una fecha de corte.
    3. Se reconstruye todo.
    4. Para fechas <= corte: las VARIABLES deben ser idénticas (0 cambios);
       la ETIQUETA retrospectiva sí puede cambiar (es lo esperado, mira el futuro).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from dengue_alerta.features import epidemiologicas, espaciales
from dengue_alerta.panel.etiquetas import etiquetar_panel


def _construir(panel: pd.DataFrame, regla: dict, horizontes, adyacencia, n_lags):
    p = etiquetar_panel(
        panel[["ubigeo", "fecha", "anio_epi", "semana_epi", "casos"]], regla, horizontes
    )
    p, cols = epidemiologicas.agregar(p, n_lags)
    if adyacencia is not None:
        p, extra = espaciales.agregar(p, adyacencia)
        cols = cols + extra
    return p.sort_values(["ubigeo", "fecha"]).reset_index(drop=True), cols


def prueba_perturbacion(
    panel: pd.DataFrame,
    corte: str,
    regla: dict,
    horizontes,
    adyacencia=None,
    n_lags: int = 8,
    semilla: int = 0,
) -> dict:
    corte = pd.Timestamp(corte)
    original, cols = _construir(panel, regla, horizontes, adyacencia, n_lags)

    alterado = panel.copy()
    futuro = alterado["fecha"] > corte
    rng = np.random.default_rng(semilla)
    actuales = alterado.loc[futuro, "casos"].to_numpy()
    alterado.loc[futuro, "casos"] = actuales + 1 + rng.poisson(2 * actuales + 2)  # siempre cambia
    perturbado, _ = _construir(alterado, regla, horizontes, adyacencia, n_lags)

    pasado = original["fecha"] <= corte
    a = original.loc[pasado, cols]
    b = perturbado.loc[pasado, cols]
    distintas = [c for c in cols if not a[c].fillna(-1).equals(b[c].fillna(-1))]
    etiquetas = int((original.loc[pasado, "brote"] != perturbado.loc[pasado, "brote"]).sum())
    return {
        "corte": str(corte.date()),
        "variables_revisadas": len(cols),
        "variables_que_cambiaron": distintas,  # DEBE estar vacía
        "semanas_con_etiqueta_cambiada": etiquetas,  # puede ser > 0 (mira el futuro)
    }
