"""Índices del fenómeno El Niño: ICEN (IGP / ENFEN) y, opcionalmente, ONI (NOAA).

Formato esperado del CSV: ``anio, mes, icen[, oni]`` (un valor por mes).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def leer_indices(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta)
    df[["anio", "mes"]] = df[["anio", "mes"]].astype("int64")
    return df.sort_values(["anio", "mes"]).reset_index(drop=True)


def indices_por_semana(fechas: pd.Series, indices: pd.DataFrame, rezago_meses: int) -> pd.DataFrame:
    """Asigna a cada semana el último índice que YA ESTABA PUBLICADO en esa fecha.

    El ICEN es una media móvil de 3 meses centrada: el valor del mes m
    necesita datos de m+1 y se publica alrededor de m+2. Si a la semana de
    marzo le pegáramos el ICEN de marzo, el modelo usaría un dato que en
    marzo nadie tenía -> fuga de información. Por eso se usa el mes
    ``fecha - rezago_meses``.
    """
    semanas = pd.DataFrame({"fecha": pd.Series(fechas).drop_duplicates().sort_values()})
    referencia = semanas["fecha"].dt.to_period("M") - rezago_meses
    semanas["anio"] = referencia.dt.year.astype("int64")
    semanas["mes"] = referencia.dt.month.astype("int64")
    columnas = [c for c in indices.columns if c not in ("anio", "mes")]
    salida = semanas.merge(indices, on=["anio", "mes"], how="left").drop(columns=["anio", "mes"])
    return salida.rename(columns={c: f"enso_{c}" for c in columnas})
