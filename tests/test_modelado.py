"""Partición temporal, métricas y entrenamiento de punta a punta."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dengue_alerta.modelado import metricas
from dengue_alerta.modelado.baselines import persistencia
from dengue_alerta.modelado.modelos import REGISTRO, crear_modelo
from dengue_alerta.modelado.particion import particionar

FIN_TRAIN, FIN_VAL = "2021-12-31", "2022-12-31"
RAIZ = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("h", [2, 4])
def test_particion_respeta_la_frontera(panel, h):
    d = panel.assign(casos_12s=0)
    part = particionar(d, h, FIN_TRAIN, FIN_VAL)
    assert (part.train["fecha"] + pd.Timedelta(weeks=h)).max() <= pd.Timestamp(FIN_TRAIN)
    assert part.val["fecha"].min() > pd.Timestamp(FIN_TRAIN)
    assert (part.val["fecha"] + pd.Timedelta(weeks=h)).max() <= pd.Timestamp(FIN_VAL)
    assert part.test["fecha"].min() > pd.Timestamp(FIN_VAL)
    # Sin intersección entre conjuntos
    llaves = [
        set(zip(x["ubigeo"], x["fecha"], strict=True)) for x in (part.train, part.val, part.test)
    ]
    assert not (llaves[0] & llaves[1]) and not (llaves[1] & llaves[2])


def test_persistencia_no_anticipa_brotes_nuevos(panel):
    d = panel.dropna(subset=["y_h2"])
    nuevos = d[d["sin_brote_hoy"] == 1]
    pred = persistencia(nuevos)
    assert pred.sum() == 0  # por construcción, nunca alerta donde hoy no hay brote


def test_metricas_casos_conocidos():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    m = metricas.calcular(y, p, umbral=0.5)
    assert m["pr_auc"] == pytest.approx(1.0)
    assert m["f1"] == pytest.approx(1.0)
    assert m["brier"] == pytest.approx((0.01 + 0.04 + 0.04 + 0.01) / 4)


def test_precision_en_k():
    df = pd.DataFrame(
        {
            "fecha": ["s1"] * 4,
            "y": [1, 0, 1, 0],
            "p": [0.9, 0.8, 0.7, 0.1],
        }
    )
    assert metricas.precision_en_k(df, "y", "p", k=2) == pytest.approx(0.5)


def test_umbral_optimo_entre_0_y_1():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 300)
    p = np.clip(y * 0.4 + rng.uniform(0, 0.6, 300), 0, 1)
    u = metricas.umbral_optimo_f1(y, p)
    assert 0 < u < 1


def test_fabrica_de_modelos_conoce_los_del_yaml():
    assert {"logistica", "random_forest"} <= set(REGISTRO)
    with pytest.raises(KeyError):
        crear_modelo("modelo_inexistente", {}, 0, np.array([0, 1]))


@pytest.mark.lento
def test_pipeline_completo_con_datos_sinteticos(tmp_path, monkeypatch):
    """Corre todas las etapas en una carpeta temporal (lo mismo que hace la CI)."""
    from dengue_alerta.config import cargar_config
    from dengue_alerta.pipeline import ETAPAS, SECUENCIA_TODO

    raiz = tmp_path / "repo"
    (raiz / "configs").mkdir(parents=True)
    (raiz / "pyproject.toml").write_text("")
    for nombre in ("base.yaml", "ci.yaml"):
        texto = (RAIZ / "configs" / nombre).read_text(encoding="utf-8")
        (raiz / "configs" / nombre).write_text(texto, encoding="utf-8")
    cfg = cargar_config(raiz / "configs" / "ci.yaml")

    ETAPAS["sintetico"](cfg)
    for etapa in SECUENCIA_TODO:
        if etapa == "explicar":
            pytest.importorskip("shap")
        if etapa == "entrenar":
            pytest.importorskip("lightgbm")
        ETAPAS[etapa](cfg)

    resultados = pd.read_csv(raiz / "reports" / "metricas" / "resultados.csv")
    assert {"persistencia", "logistica"} <= set(resultados["modelo"])
    auditoria = json.loads((raiz / "reports" / "metricas" / "auditoria_fuga.json").read_text())
    assert auditoria["variables_que_cambiaron"] == []
    # El modelo debe superar a la persistencia en distritos sin brote hoy
    nuevos = resultados[
        (resultados["subgrupo"] == "sin_brote_hoy") & (resultados["horizonte"] == 2)
    ]
    mejor_ml = nuevos[nuevos["experimento"] != "linea_base"]["pr_auc"].max()
    persist = nuevos[nuevos["modelo"] == "persistencia"]["pr_auc"].iloc[0]
    assert mejor_ml > persist

    # La búsqueda de hiperparámetros funciona (2 pruebas basta para verificar el flujo)
    if importlib.util.find_spec("optuna"):
        from dengue_alerta.modelado.tunear import tunear_lightgbm

        mejores = tunear_lightgbm(cfg, h=2, n_trials=2)
        assert "learning_rate" in mejores

    # El tablero abre sin errores con estos resultados
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DENGUE_CONFIG", str(raiz / "configs" / "ci.yaml"))
    app = AppTest.from_file(str(RAIZ / "app" / "streamlit_app.py"), default_timeout=60).run()
    assert not app.exception
    assert len(app.metric) == 4
