"""Métricas de evaluación de la alerta temprana.

* PR-AUC (métrica principal): con clases desbalanceadas, la ROC-AUC se ve
  optimista; la curva precisión-sensibilidad castiga las falsas alarmas.
* Precisión, sensibilidad y F1 con un umbral elegido en VALIDACIÓN
  (nunca en prueba).
* Precisión@k: de los k distritos con mayor riesgo cada semana, ¿cuántos
  tuvieron brote? Es la métrica que importa a quien decide dónde fumigar.
* Brier: calidad de la probabilidad (0 = perfecta).

Todo se reporta en el total y en el subgrupo ``sin_brote_hoy``: ahí está
el verdadero valor de una alerta TEMPRANA (anticipar brotes nuevos).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def umbral_optimo_f1(y: np.ndarray, p: np.ndarray) -> float:
    """Umbral que maximiza F1 (se calcula en validación y se fija para prueba)."""
    if len(np.unique(y)) < 2:
        return 0.5
    precision, sensibilidad, umbrales = precision_recall_curve(y, p)
    f1 = 2 * precision * sensibilidad / np.clip(precision + sensibilidad, 1e-12, None)
    return float(umbrales[np.argmax(f1[:-1])])


def precision_en_k(df: pd.DataFrame, y_col: str, p_col: str, k: int) -> float:
    """Promedio semanal de la precisión entre los k distritos con mayor riesgo."""

    def una_semana(g: pd.DataFrame) -> float:
        return float(g.nlargest(min(k, len(g)), p_col)[y_col].mean())

    valores = [una_semana(g) for _, g in df.groupby("fecha") if g[y_col].sum() > 0]
    return float(np.mean(valores)) if valores else float("nan")


def calcular(y: np.ndarray, p: np.ndarray, umbral: float) -> dict[str, float]:
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    pred = (p >= umbral).astype(int)
    dos_clases = len(np.unique(y)) == 2
    return {
        "n": int(len(y)),
        "positivos": int(y.sum()),
        "pr_auc": float(average_precision_score(y, p)) if dos_clases else float("nan"),
        "roc_auc": float(roc_auc_score(y, p)) if dos_clases else float("nan"),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "sensibilidad": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "brier": float(brier_score_loss(y, np.clip(p, 0, 1))),
        "umbral": float(umbral),
    }


def evaluar_estratificado(
    df: pd.DataFrame, y_col: str, p_col: str, umbral: float, k: int
) -> list[dict]:
    """Métricas para el total y para los distritos que hoy NO están en brote."""
    filas = []
    for subgrupo, parte in (("total", df), ("sin_brote_hoy", df[df["sin_brote_hoy"] == 1])):
        m = calcular(parte[y_col].to_numpy(), parte[p_col].to_numpy(), umbral)
        m["precision_at_k"] = precision_en_k(parte, y_col, p_col, k)
        m["subgrupo"] = subgrupo
        filas.append(m)
    return filas
