"""Ensamblador: une el panel etiquetado con todos los grupos de variables.

Es el único lugar que conoce a todos los grupos. Si mañana se agrega un
grupo nuevo (p. ej. movilidad), basta con crear su archivo en ``features/``
y registrarlo aquí; el entrenamiento lo detecta por su nombre en el YAML.
"""

from __future__ import annotations

import pandas as pd

from dengue_alerta.datos.estructurales import distritos_bajo_altitud
from dengue_alerta.features import climaticas, epidemiologicas, espaciales, estructurales
from dengue_alerta.utils.log import obtener_logger

log = obtener_logger(__name__)


def construir_dataset(
    panel: pd.DataFrame,
    cfg_features: dict,
    altitud_max: float,
    adyacencia: pd.DataFrame | None = None,
    clima_semanal: pd.DataFrame | None = None,
    enso: pd.DataFrame | None = None,
    datos_estructurales: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    grupos: dict[str, list[str]] = {}

    d, grupos["epidemiologicas"] = epidemiologicas.agregar(panel, cfg_features["lags_casos"])

    # Los vecinos se calculan ANTES de filtrar por altitud: un distrito de
    # altura puede tener casos importados que igual informan a sus vecinos.
    if adyacencia is not None:
        d, grupos["espaciales"] = espaciales.agregar(d, adyacencia)

    if clima_semanal is not None:
        d, grupos["climaticas"] = climaticas.agregar(
            d,
            clima_semanal,
            enso,
            cfg_features["lags_clima"],
            cfg_features["rezago_publicacion_enso_meses"],
        )

    if datos_estructurales is not None:
        d, grupos["estructurales"] = estructurales.agregar(d, datos_estructurales)
        validos = distritos_bajo_altitud(datos_estructurales, altitud_max)
        antes = d["ubigeo"].nunique()
        d = d[d["ubigeo"].isin(validos)]
        log.info(
            "Filtro de altitud < %s m: %s -> %s distritos",
            altitud_max,
            antes,
            d["ubigeo"].nunique(),
        )

    for nombre, cols in grupos.items():
        log.info("Grupo %-15s %2d variables", nombre, len(cols))
    return d.sort_values(["ubigeo", "fecha"]).reset_index(drop=True), grupos
