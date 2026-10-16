"""Fábrica de modelos: un nombre del YAML -> un estimador listo para ``fit``.

Patrón *factory*: el resto del código nunca hace ``import lightgbm``
directamente; pide ``crear_modelo("lightgbm", ...)``. Así agregar un modelo
nuevo es agregar una función aquí y su nombre en el YAML, sin tocar el
entrenamiento, la evaluación ni el tablero.

Desbalance de clases: los brotes son ~10-15 % de las semanas. Sin
corrección, el modelo aprende a decir "no hay brote" siempre. Se usa
ponderación de clases (``class_weight`` / ``scale_pos_weight``).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def _logistica(params: dict, semilla: int, peso_pos: float):
    return Pipeline(
        [
            ("imputar", SimpleImputer(strategy="median")),
            ("escalar", StandardScaler()),
            (
                "modelo",
                LogisticRegression(
                    max_iter=3000, class_weight="balanced", random_state=semilla, **params
                ),
            ),
        ]
    )


def _random_forest(params: dict, semilla: int, peso_pos: float):
    return Pipeline(
        [
            ("imputar", SimpleImputer(strategy="median")),
            (
                "modelo",
                RandomForestClassifier(
                    class_weight="balanced_subsample", n_jobs=-1, random_state=semilla, **params
                ),
            ),
        ]
    )


def _lightgbm(params: dict, semilla: int, peso_pos: float):
    from lightgbm import LGBMClassifier  # dependencia opcional (extra "ml")

    return LGBMClassifier(
        scale_pos_weight=peso_pos, random_state=semilla, verbose=-1, n_jobs=-1, **params
    )


def _xgboost(params: dict, semilla: int, peso_pos: float):
    from xgboost import XGBClassifier

    return XGBClassifier(
        scale_pos_weight=peso_pos,
        random_state=semilla,
        n_jobs=-1,
        eval_metric="aucpr",
        tree_method="hist",
        **params,
    )


REGISTRO: dict[str, Callable] = {
    "logistica": _logistica,
    "random_forest": _random_forest,
    "lightgbm": _lightgbm,
    "xgboost": _xgboost,
}


def crear_modelo(nombre: str, params: dict | None, semilla: int, y_train: np.ndarray):
    if nombre not in REGISTRO:
        raise KeyError(f"Modelo '{nombre}' no registrado. Opciones: {sorted(REGISTRO)}")
    positivos = max(float(np.sum(y_train)), 1.0)
    peso_pos = (len(y_train) - positivos) / positivos
    return REGISTRO[nombre](dict(params or {}), semilla, peso_pos)
