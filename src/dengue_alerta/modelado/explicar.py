"""Explicabilidad con SHAP (SHapley Additive exPlanations).

Para cada predicción, SHAP reparte la diferencia entre el riesgo predicho y
el riesgo promedio entre las variables: "este distrito tiene riesgo alto
porque sus vecinos acumulan 40 casos (+0.18), llovió el doble de lo
normal hace 4 semanas (+0.07) y ...". Eso convierte la caja negra en una
alerta que un epidemiólogo puede revisar y cuestionar.

Salidas por horizonte:
    reports/metricas/shap_importancia_h<h>.csv   importancia global (media de |SHAP|)
    reports/figuras/shap_resumen_h<h>.png        gráfico resumen
    data/processed/shap_test.parquet             top de contribuciones por distrito-semana
"""

from __future__ import annotations

import joblib
import matplotlib

matplotlib.use("Agg")  # sin ventana: funciona en servidores y en GitHub Actions
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from dengue_alerta import contratos  # noqa: E402
from dengue_alerta.config import Config  # noqa: E402
from dengue_alerta.io import guardar, leer  # noqa: E402
from dengue_alerta.modelado.particion import particionar  # noqa: E402
from dengue_alerta.utils.log import obtener_logger  # noqa: E402

log = obtener_logger(__name__)


def valores_shap(modelo, X: pd.DataFrame) -> tuple[np.ndarray, float]:
    import warnings

    import shap

    explicador = shap.TreeExplainer(modelo)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*shap values output has changed.*")
        valores = explicador.shap_values(X)
    if isinstance(valores, list):  # versiones antiguas: una matriz por clase
        valores = valores[1]
    if valores.ndim == 3:
        valores = valores[:, :, 1]
    base = explicador.expected_value
    base = float(np.ravel(base)[-1])
    return valores, base


def explicar(cfg: Config, top: int = 8) -> pd.DataFrame:
    m_cfg, p_cfg = cfg["modelado"], cfg["particion"]
    exp, nombre = m_cfg["experimento_final"], m_cfg["modelo_explicable"]
    datos = leer(cfg.carpeta("processed") / "dataset_modelado.parquet", contratos.DATASET)
    largas = []
    (cfg.carpeta("reportes") / "figuras").mkdir(parents=True, exist_ok=True)
    (cfg.carpeta("reportes") / "metricas").mkdir(parents=True, exist_ok=True)

    for h in cfg["objetivo"]["horizontes"]:
        ruta = cfg.carpeta("modelos") / f"{exp}__{nombre}__h{h}.joblib"
        if not ruta.exists():
            log.warning("No existe %s: ejecuta primero `entrenar`", ruta.name)
            continue
        paquete = joblib.load(ruta)
        cols = paquete["columnas"]
        test = particionar(datos, h, p_cfg["fin_train"], p_cfg["fin_val"]).test
        X = test[cols]
        valores, base = valores_shap(paquete["modelo"], X)

        # 1) Importancia global
        imp = pd.DataFrame(
            {"variable": cols, "media_abs_shap": np.abs(valores).mean(axis=0)}
        ).sort_values("media_abs_shap", ascending=False)
        imp.to_csv(cfg.carpeta("reportes") / "metricas" / f"shap_importancia_h{h}.csv", index=False)

        # 2) Figura resumen (barras horizontales de las 15 variables más importantes)
        top15 = imp.head(15).iloc[::-1]
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.barh(top15["variable"], top15["media_abs_shap"], color="#2a6f97")
        ax.set_xlabel("Media de |SHAP| (impacto en el log-odds del riesgo)")
        ax.set_title(f"Variables más influyentes - {nombre}, {exp}, h={h}")
        fig.tight_layout()
        fig.savefig(cfg.carpeta("reportes") / "figuras" / f"shap_resumen_h{h}.png", dpi=150)
        plt.close(fig)

        # 3) Explicación local: las `top` contribuciones más fuertes de cada distrito-semana
        orden = np.argsort(-np.abs(valores), axis=1)[:, :top]
        filas = np.repeat(np.arange(len(X)), top)
        idx_col = orden.ravel()
        largas.append(
            pd.DataFrame(
                {
                    "ubigeo": test["ubigeo"].to_numpy()[filas],
                    "fecha": test["fecha"].to_numpy()[filas],
                    "horizonte": h,
                    "variable": np.array(cols)[idx_col],
                    "valor": X.to_numpy(dtype=float)[filas, idx_col],
                    "shap": valores[filas, idx_col],
                    "base": base,
                }
            )
        )
        log.info(
            "h=%s | SHAP calculado para %s filas; top 3: %s",
            h,
            f"{len(X):,}",
            ", ".join(imp["variable"].head(3)),
        )

    salida = pd.concat(largas, ignore_index=True) if largas else pd.DataFrame()
    if not salida.empty:
        guardar(salida, cfg.carpeta("processed") / "shap_test.parquet")
    return salida
