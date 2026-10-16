"""Orquestador: define las ETAPAS del pipeline y qué archivo lee/escribe cada una.

    sintetico  ->  data/raw + data/external          (solo para pruebas)
    panel      ->  data/interim/panel_etiquetado.parquet          (Módulo 1)
    features   ->  data/processed/dataset_modelado.parquet        (Módulos 2 y 3)
    auditar    ->  reports/metricas/auditoria_fuga.json
    entrenar   ->  models/*.joblib, resultados.csv, predicciones  (Módulo 4)
    explicar   ->  shap_test.parquet, figuras SHAP                (Módulo 4)
    (tablero)  ->  app/streamlit_app.py lee lo anterior           (Módulo 5)

Cada etapa es una función ``etapa_x(cfg)`` independiente: se puede correr
sola (si existe la salida de la anterior) o todas en cadena con ``todo``.
"""

from __future__ import annotations

import json

import numpy as np

from dengue_alerta import contratos
from dengue_alerta.config import Config
from dengue_alerta.datos import clima, enso, estructurales, geografia, minsa, sintetico
from dengue_alerta.features.dataset import construir_dataset
from dengue_alerta.io import guardar, leer
from dengue_alerta.panel.construir import construir_panel
from dengue_alerta.panel.etiquetas import etiquetar_panel, retraso_de_deteccion
from dengue_alerta.utils.log import obtener_logger

log = obtener_logger(__name__)


def _guardar_json(cfg: Config, nombre: str, contenido: dict) -> None:
    ruta = cfg.carpeta("reportes") / "metricas" / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")


def etapa_sintetico(cfg: Config) -> None:
    s = cfg["sintetico"]
    datos = sintetico.generar(
        s["n_filas"],
        s["n_columnas"],
        s["anio_inicio"],
        s["anio_fin"],
        semilla=cfg["proyecto"]["semilla"],
    )
    rutas = {k: cfg.fuente(k) for k in cfg["fuentes"]}
    sintetico.escribir(datos, rutas)
    log.info(
        "Datos sintéticos: %s casos, %s distritos",
        f"{len(datos.casos):,}",
        datos.estructurales.shape[0],
    )


def etapa_panel(cfg: Config) -> None:
    interim = cfg.carpeta("interim")
    crudo = minsa.leer_csv(cfg.fuente("minsa_csv"))
    casos = minsa.limpiar(crudo, cfg["limpieza"]["tipos_dx_validos"])
    log.info("Limpieza: %s -> %s registros", f"{len(crudo):,}", f"{len(casos):,}")
    guardar(casos, interim / "casos_limpios.parquet", contratos.CASOS)

    panel = construir_panel(casos)
    panel = etiquetar_panel(panel, cfg["etiqueta"], cfg["objetivo"]["horizontes"])
    guardar(panel, interim / "panel_etiquetado.parquet", contratos.PANEL)

    retrasos = []
    for _, g in panel.groupby("ubigeo"):
        retrasos += retraso_de_deteccion(g["brote"].to_numpy(), g["brote_rt"].to_numpy())
    resumen = {
        "registros_crudos": len(crudo),
        "registros_validos": len(casos),
        "distritos": int(panel["ubigeo"].nunique()),
        "semanas": int(panel["fecha"].nunique()),
        "filas_panel": len(panel),
        "pct_semanas_sin_casos": round(float((panel["casos"] == 0).mean()), 4),
        "pct_semanas_en_brote": round(float(panel["brote"].mean()), 4),
        "brotes_detectados": len(retrasos),
        "retraso_deteccion_mediana": float(np.median(retrasos)) if retrasos else None,
        "retraso_deteccion_media": round(float(np.mean(retrasos)), 2) if retrasos else None,
    }
    _guardar_json(cfg, "resumen_panel.json", resumen)
    log.info("Panel: %s", resumen)


def etapa_features(cfg: Config) -> None:
    interim, proc = cfg.carpeta("interim"), cfg.carpeta("processed")
    panel = leer(interim / "panel_etiquetado.parquet", contratos.PANEL)

    def si_existe(nombre: str, lector):
        ruta = cfg.fuente(nombre)
        if ruta.exists():
            return lector(ruta)
        log.warning("No se encontró %s: se omite ese grupo de variables", ruta.name)
        return None

    ady = si_existe("adyacencia_csv", geografia.leer_adyacencia)
    est = si_existe("estructurales_csv", estructurales.leer_estructurales)
    ind = si_existe("enso_csv", enso.leer_indices)
    diario = si_existe("clima_csv", clima.leer_clima_diario)
    semanal = None
    if diario is not None:
        semanal = clima.a_semana_epidemiologica(diario)
        guardar(semanal, interim / "clima_semanal.parquet", contratos.CLIMA_SEMANAL)
    if ady is not None:
        contratos.ADYACENCIA.validar(ady)
    if est is not None:
        contratos.ESTRUCTURALES.validar(est)

    dataset, grupos = construir_dataset(
        panel,
        cfg["features"],
        cfg["limpieza"]["altitud_max_m"],
        adyacencia=ady,
        clima_semanal=semanal,
        enso=ind,
        datos_estructurales=est,
    )
    guardar(dataset, proc / "dataset_modelado.parquet", contratos.DATASET)
    (proc / "grupos_features.json").write_text(json.dumps(grupos, indent=2), encoding="utf-8")


def etapa_auditar(cfg: Config) -> dict:
    from dengue_alerta.modelado.auditoria import prueba_perturbacion

    panel = leer(cfg.carpeta("interim") / "panel_etiquetado.parquet", contratos.PANEL)
    ruta_ady = cfg.fuente("adyacencia_csv")
    ady = geografia.leer_adyacencia(ruta_ady) if ruta_ady.exists() else None
    reporte = prueba_perturbacion(
        panel,
        cfg["particion"]["fin_train"],
        cfg["etiqueta"],
        cfg["objetivo"]["horizontes"],
        ady,
        cfg["features"]["lags_casos"],
    )
    _guardar_json(cfg, "auditoria_fuga.json", reporte)
    if reporte["variables_que_cambiaron"]:
        raise RuntimeError(f"FUGA DE INFORMACIÓN en: {reporte['variables_que_cambiaron']}")
    log.info(
        "Auditoría de fuga OK: %s variables sin cambios; %s semanas de etiqueta cambiaron "
        "(esperado)",
        reporte["variables_revisadas"],
        reporte["semanas_con_etiqueta_cambiada"],
    )
    return reporte


def etapa_entrenar(cfg: Config) -> None:
    from dengue_alerta.modelado.entrenar import entrenar_todo

    tabla = entrenar_todo(cfg)
    vista = tabla[tabla["subgrupo"] == "sin_brote_hoy"].pivot_table(
        index=["experimento", "modelo"], columns="horizonte", values="pr_auc"
    )
    log.info("PR-AUC en prueba, distritos sin brote hoy:\n%s", vista.round(3).to_string())


def etapa_explicar(cfg: Config) -> None:
    from dengue_alerta.modelado.explicar import explicar

    explicar(cfg)


ETAPAS = {
    "sintetico": etapa_sintetico,
    "panel": etapa_panel,
    "features": etapa_features,
    "auditar": etapa_auditar,
    "entrenar": etapa_entrenar,
    "explicar": etapa_explicar,
}
SECUENCIA_TODO = ["panel", "features", "auditar", "entrenar", "explicar"]
