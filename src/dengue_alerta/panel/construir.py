"""Agregación de casos individuales a una grilla completa distrito x semana."""

from __future__ import annotations

import pandas as pd

from dengue_alerta.panel.calendario import anio_y_semana, semana_a_fecha


def construir_panel(casos: pd.DataFrame) -> pd.DataFrame:
    """Cuenta casos por (ubigeo, semana) y rellena con 0 las semanas sin registros.

    El paso de "rellenar con ceros" es crítico: el MINSA solo publica filas
    cuando hay un caso. Si no se completan las semanas vacías, un ``shift(1)``
    saltaría a la última semana con casos (que puede ser de hace meses) y
    todas las variables de rezago quedarían mal calculadas.
    """
    conteo = casos.groupby(["ubigeo", "anio", "semana"]).size().rename("casos").reset_index()

    pares = conteo[["anio", "semana"]].drop_duplicates().copy()
    pares["fecha"] = [
        semana_a_fecha(a, s) for a, s in zip(pares["anio"], pares["semana"], strict=True)
    ]
    conteo = conteo.merge(pares, on=["anio", "semana"]).dropna(subset=["fecha"])

    semanas = pd.date_range(conteo["fecha"].min(), conteo["fecha"].max(), freq="7D")
    distritos = sorted(conteo["ubigeo"].unique())
    grilla = pd.MultiIndex.from_product([distritos, semanas], names=["ubigeo", "fecha"])

    panel = (
        conteo.groupby(["ubigeo", "fecha"])["casos"]
        .sum()
        .reindex(grilla, fill_value=0)
        .reset_index()
    )
    panel["ubigeo"] = panel["ubigeo"].astype(str)
    panel["casos"] = panel["casos"].astype("int64")
    panel["anio_epi"], panel["semana_epi"] = anio_y_semana(panel["fecha"])
    return panel.sort_values(["ubigeo", "fecha"]).reset_index(drop=True)
