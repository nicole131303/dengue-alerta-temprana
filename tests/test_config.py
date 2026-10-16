"""Carga y herencia de configuración."""

from pathlib import Path

from dengue_alerta.config import cargar_config

RAIZ = Path(__file__).resolve().parents[1]


def test_base_tiene_las_secciones_necesarias():
    cfg = cargar_config(RAIZ / "configs" / "base.yaml")
    for seccion in ("rutas", "fuentes", "etiqueta", "objetivo", "particion", "modelado"):
        assert seccion in cfg.datos
    assert cfg.raiz == RAIZ


def test_ci_hereda_y_sobrescribe():
    base = cargar_config(RAIZ / "configs" / "base.yaml")
    ci = cargar_config(RAIZ / "configs" / "ci.yaml")
    assert ci["etiqueta"] == base["etiqueta"]  # heredado
    assert ci["modelado"]["modelos"] == ["logistica", "lightgbm"]  # sobrescrito
    # fusión profunda: conserva hiperparámetros de base que ci no menciona
    assert ci["modelado"]["hiperparametros"]["lightgbm"]["subsample"] == 0.8
    assert ci["modelado"]["hiperparametros"]["lightgbm"]["n_estimators"] == 80


def test_experimentos_de_ablacion_son_acumulativos():
    exps = list(cargar_config(RAIZ / "configs" / "base.yaml")["modelado"]["experimentos"].values())
    for anterior, siguiente in zip(exps, exps[1:], strict=False):
        assert set(anterior) < set(siguiente)
