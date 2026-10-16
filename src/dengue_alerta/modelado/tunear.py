"""Búsqueda de hiperparámetros con Optuna (solo con train y validación).

El resultado NO se escribe solo en la configuración: se guarda en un YAML
aparte para que la persona lo revise y lo copie a ``configs/`` en un commit
propio ("exp: hiperparámetros LightGBM h=2"). Así queda trazado qué cambió.
"""

from __future__ import annotations

import json

import yaml

from dengue_alerta import contratos
from dengue_alerta.config import Config
from dengue_alerta.io import leer
from dengue_alerta.modelado.entrenar import columnas_de
from dengue_alerta.modelado.metricas import calcular
from dengue_alerta.modelado.modelos import crear_modelo
from dengue_alerta.modelado.particion import particionar
from dengue_alerta.utils.log import obtener_logger

log = obtener_logger(__name__)


def tunear_lightgbm(cfg: Config, h: int, n_trials: int = 40) -> dict:
    import optuna

    proc = cfg.carpeta("processed")
    datos = leer(proc / "dataset_modelado.parquet", contratos.DATASET)
    grupos = json.loads((proc / "grupos_features.json").read_text(encoding="utf-8"))
    cols = columnas_de(
        cfg["modelado"]["experimentos"][cfg["modelado"]["experimento_final"]], grupos
    )
    part = particionar(datos, h, cfg["particion"]["fin_train"], cfg["particion"]["fin_val"])
    y_tr = part.train[f"y_h{h}"].astype(int).to_numpy()
    y_va = part.val[f"y_h{h}"].astype(int).to_numpy()

    def objetivo(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 150, 900, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 8, 96, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 150, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "subsample_freq": 1,
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
        }
        modelo = crear_modelo("lightgbm", params, cfg["proyecto"]["semilla"], y_tr)
        modelo.fit(part.train[cols], y_tr)
        return calcular(y_va, modelo.predict_proba(part.val[cols])[:, 1], 0.5)["pr_auc"]

    estudio = optuna.create_study(
        direction="maximize", sampler=optuna.samplers.TPESampler(seed=cfg["proyecto"]["semilla"])
    )
    estudio.optimize(objetivo, n_trials=n_trials, show_progress_bar=False)
    mejores = {**estudio.best_params, "subsample_freq": 1}
    ruta = cfg.carpeta("reportes") / "metricas" / f"mejores_hiperparametros_lightgbm_h{h}.yaml"
    ruta.write_text(
        yaml.safe_dump({"lightgbm": mejores, "pr_auc_val": estudio.best_value}), encoding="utf-8"
    )
    log.info("Mejor PR-AUC en validación: %.3f -> %s", estudio.best_value, ruta.name)
    return mejores
