"""Carga de datos del tablero (separada de la interfaz para poder probarla).

El tablero NO entrena ni calcula nada: solo lee lo que dejó el pipeline.
Así abrirlo es instantáneo y siempre muestra exactamente los resultados
reportados en la tesis.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dengue_alerta.config import Config, cargar_config

RAIZ = Path(__file__).resolve().parents[1]


@dataclass
class DatosTablero:
    cfg: Config
    predicciones: pd.DataFrame
    dataset: pd.DataFrame
    shap: pd.DataFrame | None
    geojson: dict | None


def cargar(ruta_config: str | None = None) -> DatosTablero:
    ruta = ruta_config or os.environ.get("DENGUE_CONFIG", str(RAIZ / "configs" / "base.yaml"))
    cfg = cargar_config(ruta)
    proc = cfg.carpeta("processed")

    predicciones = pd.read_parquet(proc / "predicciones_test.parquet")
    columnas = ["ubigeo", "fecha", "casos", "casos_4s", "brote_rt"]
    dataset = pd.read_parquet(proc / "dataset_modelado.parquet", columns=columnas)
    ruta_shap = proc / "shap_test.parquet"
    shap = pd.read_parquet(ruta_shap) if ruta_shap.exists() else None
    ruta_geo = cfg.fuente("geojson")
    geojson = json.loads(ruta_geo.read_text(encoding="utf-8")) if ruta_geo.exists() else None
    return DatosTablero(cfg, predicciones, dataset, shap, geojson)


def vista_semana(
    d: DatosTablero, horizonte: int, experimento: str, modelo: str, fecha: pd.Timestamp
) -> pd.DataFrame:
    """Una fila por distrito: riesgo predicho para t+h y situación actual en t."""
    p = d.predicciones
    sel = p[
        (p["horizonte"] == horizonte)
        & (p["experimento"] == experimento)
        & (p["modelo"] == modelo)
        & (p["fecha"] == fecha)
    ].drop(columns=["brote_rt"])
    actual = d.dataset[d.dataset["fecha"] == fecha]
    return sel.merge(actual, on=["ubigeo", "fecha"], how="left").sort_values(
        "riesgo", ascending=False
    )


def explicacion(
    d: DatosTablero, ubigeo: str, fecha: pd.Timestamp, horizonte: int
) -> pd.DataFrame | None:
    if d.shap is None:
        return None
    s = d.shap
    return s[(s["ubigeo"] == ubigeo) & (s["fecha"] == fecha) & (s["horizonte"] == horizonte)]
