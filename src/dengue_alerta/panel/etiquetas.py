"""Definición operacional de brote y variable objetivo.

Hay DOS versiones de la misma regla, y entender la diferencia es la clave
de todo el proyecto:

* ``etiquetar_brotes`` (retrospectiva): mira la serie completa. Si un
  episodio llega a cumplir la regla, marca como brote TODAS sus semanas,
  incluso las primeras, cuando todavía no se sabía. Es la "verdad" que el
  modelo debe aprender a anticipar -> solo se usa como OBJETIVO.

* ``brote_en_tiempo_real`` (causal): recorre la serie semana a semana y
  solo enciende el estado cuando la regla ya se cumplió con datos pasados.
  Es lo que un epidemiólogo sabría hoy -> puede usarse como PREDICTOR.

Regla (Dostal et al., 2022): >= ``min_casos`` casos acumulados en
>= ``min_semanas`` semanas consecutivas con casos. El episodio termina
cuando hay ``gap_cierre`` semanas seguidas sin casos.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def tiene_disparador(segmento: Sequence[int], min_casos: int = 5, min_semanas: int = 3) -> bool:
    """¿El tramo contiene una racha de semanas consecutivas con casos que cumpla la regla?"""
    largo, suma = 0, 0
    for v in segmento:
        if v > 0:
            largo += 1
            suma += v
            if largo >= min_semanas and suma >= min_casos:
                return True
        else:
            largo, suma = 0, 0
    return False


def etiquetar_brotes(
    casos: Sequence[int], min_casos: int = 5, min_semanas: int = 3, gap_cierre: int = 2
) -> np.ndarray:
    """Etiqueta retrospectiva: 1 en todas las semanas de un episodio que llegó a ser brote."""
    c = np.asarray(casos)
    n = len(c)
    y = np.zeros(n, dtype=np.int64)
    i = 0
    while i < n:
        if c[i] == 0:
            i += 1
            continue
        # Delimitar el episodio: termina tras `gap_cierre` ceros seguidos
        inicio = fin = i
        ceros = 0
        j = i + 1
        while j < n:
            if c[j] > 0:
                fin, ceros = j, 0
            else:
                ceros += 1
                if ceros >= gap_cierre:
                    break
            j += 1
        if tiene_disparador(c[inicio : fin + 1], min_casos, min_semanas):
            y[inicio : fin + 1] = 1
        i = fin + 1
    return y


def brote_en_tiempo_real(
    casos: Sequence[int], min_casos: int = 5, min_semanas: int = 3, gap_cierre: int = 2
) -> np.ndarray:
    """Estado causal: en la semana t solo usa casos[0..t]."""
    c = np.asarray(casos)
    estado = np.zeros(len(c), dtype=np.int64)
    activo, largo, suma, ceros = False, 0, 0, 0
    for t, v in enumerate(c):
        if v > 0:
            largo, suma, ceros = largo + 1, suma + v, 0
        else:
            largo, suma, ceros = 0, 0, ceros + 1
        if not activo and largo >= min_semanas and suma >= min_casos:
            activo = True
        if activo and ceros >= gap_cierre:
            activo = False
        estado[t] = int(activo)
    return estado


def _por_distrito(df: pd.DataFrame, columna: str, funcion, **kwargs) -> pd.Series:
    """Aplica una función de serie a cada distrito conservando el índice original."""
    return df.groupby("ubigeo", sort=False)[columna].transform(
        lambda s: pd.Series(funcion(s.to_numpy(), **kwargs), index=s.index)
    )


def etiquetar_panel(panel: pd.DataFrame, regla: dict, horizontes: Sequence[int]) -> pd.DataFrame:
    """Agrega al panel: ``brote``, ``brote_rt``, ``sin_brote_hoy`` y ``y_h{h}``.

    ``y_h{h}`` = ¿el distrito estará en brote dentro de h semanas?
    Se obtiene desplazando la etiqueta retrospectiva h semanas hacia atrás.
    Las últimas h semanas de cada distrito quedan sin objetivo (NaN) porque
    su futuro aún no se conoce: esas filas no se usan para entrenar.
    """
    p = panel.sort_values(["ubigeo", "fecha"]).copy()
    p["brote"] = _por_distrito(p, "casos", etiquetar_brotes, **regla).astype("int64")
    p["brote_rt"] = _por_distrito(p, "casos", brote_en_tiempo_real, **regla).astype("int64")
    p["sin_brote_hoy"] = (p["brote_rt"] == 0).astype("int64")
    for h in horizontes:
        p[f"y_h{h}"] = p.groupby("ubigeo", sort=False)["brote"].shift(-h)
    return p.reset_index(drop=True)


def retraso_de_deteccion(brote: np.ndarray, brote_rt: np.ndarray) -> list[int]:
    """Semanas entre el inicio real de cada brote y el momento en que la regla lo detecta.

    Es la ventana que el modelo de alerta temprana busca adelantar.
    """
    retrasos = []
    n = len(brote)
    t = 0
    while t < n:
        if brote[t] == 1 and (t == 0 or brote[t - 1] == 0):
            inicio = t
            while t < n and brote[t] == 1:
                if brote_rt[t] == 1:
                    retrasos.append(t - inicio)
                    break
                t += 1
            while t < n and brote[t] == 1:
                t += 1
        else:
            t += 1
    return retrasos
