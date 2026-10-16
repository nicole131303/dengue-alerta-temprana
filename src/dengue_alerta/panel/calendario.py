"""Calendario epidemiológico (semanas CDC/MMWR, las que usa el MINSA).

La semana epidemiológica va de domingo a sábado; la semana 1 es la que
contiene el primer sábado de enero. Por eso algunos años tienen 53 semanas
y la semana 1 puede empezar a fines de diciembre del año anterior.
Convertimos (año, semana) a la fecha del domingo de inicio para poder
ordenar, desplazar y cruzar con el clima sin ambigüedades.
"""

from __future__ import annotations

import pandas as pd
from epiweeks import Week


def semana_a_fecha(anio: int, semana: int) -> pd.Timestamp:
    """(año, semana epidemiológica) -> domingo de inicio. NaT si la semana no existe."""
    try:
        return pd.Timestamp(Week(int(anio), int(semana)).startdate())
    except ValueError:  # p. ej. semana 53 en un año que solo tiene 52
        return pd.NaT


def inicio_de_semana(fechas: pd.Series) -> pd.Series:
    """Fecha diaria -> domingo de inicio de su semana epidemiológica (vectorizado)."""
    fechas = pd.to_datetime(fechas).dt.normalize()
    dias_desde_domingo = (fechas.dt.dayofweek + 1) % 7  # lunes=0 ... domingo=6
    return fechas - pd.to_timedelta(dias_desde_domingo, unit="D")


def anio_y_semana(fechas: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Domingo de inicio -> (año epidemiológico, número de semana).

    Se calcula una vez por fecha única y se mapea: con ~700 distritos el
    panel tiene más de medio millón de filas pero solo ~730 semanas distintas.
    """
    unicas = pd.Series(pd.to_datetime(fechas).unique())
    semanas = {f: Week.fromdate(f.date()) for f in unicas}
    anio = fechas.map(lambda f: semanas[f].year).astype("int64")
    sem = fechas.map(lambda f: semanas[f].week).astype("int64")
    return anio, sem
