"""Bucle experimental: horizontes x experimentos (ablación) x modelos.

Para cada combinación:
    1. partición temporal con frontera
    2. entrenamiento en train
    3. umbral elegido en validación (maximiza F1)
    4. evaluación en prueba (total y sin_brote_hoy)
    5. guardado del modelo, sus métricas y sus predicciones

Salidas:
    reports/metricas/resultados.csv         una fila por (h, experimento, modelo, subgrupo)
    data/processed/predicciones_test.parquet riesgo predicho por distrito-semana en prueba
    models/<experimento>__<modelo>__h<h>.joblib
"""

from __future__ import annotations

import json
import time
from contextlib import nullcontext

import joblib
import pandas as pd

from dengue_alerta import contratos
from dengue_alerta.config import Config
from dengue_alerta.io import guardar, leer
from dengue_alerta.modelado import baselines, metricas
from dengue_alerta.modelado.modelos import crear_modelo
from dengue_alerta.modelado.particion import particionar
from dengue_alerta.utils.log import obtener_logger

log = obtener_logger(__name__)


def columnas_de(experimento: list[str], grupos: dict[str, list[str]]) -> list[str]:
    faltan = [g for g in experimento if g not in grupos]
    if faltan:
        raise KeyError(f"Grupos de variables no disponibles en el dataset: {faltan}")
    columnas: list[str] = []
    for g in experimento:
        columnas += [c for c in grupos[g] if c not in columnas]
    return columnas


def _mlflow(cfg: Config):
    """Devuelve el módulo mlflow si está activado e instalado; si no, None."""
    if not cfg["modelado"].get("mlflow"):
        return None
    try:
        import mlflow
    except ImportError:
        log.warning("mlflow no está instalado: se omite el registro de experimentos")
        return None
    mlflow.set_experiment(cfg["proyecto"]["nombre"])
    return mlflow


def _filas(metr: list[dict], **contexto) -> list[dict]:
    return [{**contexto, **m} for m in metr]


def entrenar_todo(cfg: Config) -> pd.DataFrame:
    proc, interim = cfg.carpeta("processed"), cfg.carpeta("interim")
    datos = leer(proc / "dataset_modelado.parquet", contratos.DATASET)
    panel = leer(interim / "panel_etiquetado.parquet", contratos.PANEL)
    grupos = json.loads((proc / "grupos_features.json").read_text(encoding="utf-8"))

    m_cfg, p_cfg = cfg["modelado"], cfg["particion"]
    semilla, k = cfg["proyecto"]["semilla"], m_cfg["k_ranking"]
    mlflow = _mlflow(cfg)
    resultados, predicciones = [], []

    for h in cfg["objetivo"]["horizontes"]:
        y_col = f"y_h{h}"
        part = particionar(datos, h, p_cfg["fin_train"], p_cfg["fin_val"])
        log.info("h=%s | partición %s", h, part.resumen())
        y_tr, y_va = part.train[y_col].astype(int), part.val[y_col].astype(int)
        test = part.test.copy()

        # ---------- Líneas base ----------
        for nombre in sorted(baselines.LINEAS_BASE):
            if nombre == "persistencia":
                test["_p"] = baselines.persistencia(test)
            else:
                test["_p"] = baselines.estacional_ingenua(test, h, panel)
            met = metricas.evaluar_estratificado(test, y_col, "_p", umbral=0.5, k=k)
            resultados += _filas(
                met,
                horizonte=h,
                experimento="linea_base",
                modelo=nombre,
                pr_auc_val=float("nan"),
                segundos=0.0,
            )

        # ---------- Modelos de ML (ablación) ----------
        for exp, grupos_exp in m_cfg["experimentos"].items():
            try:
                cols = columnas_de(grupos_exp, grupos)
            except KeyError as e:
                log.warning("Se omite %s: %s", exp, e)
                continue
            for nombre in m_cfg["modelos"]:
                inicio = time.time()
                params = m_cfg.get("hiperparametros", {}).get(nombre, {})
                modelo = crear_modelo(nombre, params, semilla, y_tr.to_numpy())
                modelo.fit(part.train[cols], y_tr)

                p_va = modelo.predict_proba(part.val[cols])[:, 1]
                umbral = metricas.umbral_optimo_f1(y_va.to_numpy(), p_va)
                pr_auc_val = metricas.calcular(y_va.to_numpy(), p_va, umbral)["pr_auc"]
                test["_p"] = modelo.predict_proba(test[cols])[:, 1]
                met = metricas.evaluar_estratificado(test, y_col, "_p", umbral, k)
                seg = round(time.time() - inicio, 1)
                resultados += _filas(
                    met,
                    horizonte=h,
                    experimento=exp,
                    modelo=nombre,
                    pr_auc_val=pr_auc_val,
                    segundos=seg,
                )

                ruta = cfg.carpeta("modelos") / f"{exp}__{nombre}__h{h}.joblib"
                joblib.dump(
                    {
                        "modelo": modelo,
                        "columnas": cols,
                        "umbral": umbral,
                        "horizonte": h,
                        "experimento": exp,
                        "nombre": nombre,
                    },
                    ruta,
                )

                predicciones.append(
                    pd.DataFrame(
                        {
                            "ubigeo": test["ubigeo"],
                            "fecha": test["fecha"],
                            "horizonte": h,
                            "experimento": exp,
                            "modelo": nombre,
                            "riesgo": test["_p"],
                            "alerta": (test["_p"] >= umbral).astype("int64"),
                            "y_real": test[y_col].astype("int64"),
                            "brote_rt": test["brote_rt"],
                        }
                    )
                )

                total = met[0]
                log.info(
                    "h=%s %-12s %-14s PR-AUC test=%.3f (sin_brote_hoy=%.3f) %ss",
                    h,
                    exp,
                    nombre,
                    total["pr_auc"],
                    met[1]["pr_auc"],
                    seg,
                )

                with mlflow.start_run(run_name=f"{exp}-{nombre}-h{h}") if mlflow else nullcontext():
                    if mlflow:
                        mlflow.log_params(
                            {
                                "horizonte": h,
                                "experimento": exp,
                                "modelo": nombre,
                                "n_variables": len(cols),
                                **params,
                            }
                        )
                        for m in met:
                            mlflow.log_metrics(
                                {
                                    f"{m['subgrupo']}_{c}": m[c]
                                    for c in ("pr_auc", "roc_auc", "f1", "precision_at_k")
                                }
                            )

    tabla = pd.DataFrame(resultados)
    (cfg.carpeta("reportes") / "metricas").mkdir(parents=True, exist_ok=True)
    tabla.to_csv(cfg.carpeta("reportes") / "metricas" / "resultados.csv", index=False)
    guardar(
        pd.concat(predicciones, ignore_index=True),
        proc / "predicciones_test.parquet",
        contratos.PREDICCIONES,
    )
    return tabla
