"""Geografía distrital: adyacencia entre distritos y GeoJSON para el mapa.

Requiere el extra ``geo`` (geopandas) solo si se parte del shapefile del INEI.
El resto del pipeline únicamente necesita el CSV de adyacencia resultante.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dengue_alerta.io import normalizar_ubigeo


def adyacencia_desde_shapefile(
    ruta_shp: Path, col_ubigeo: str = "UBIGEO", ruta_geojson: Path | None = None
) -> pd.DataFrame:
    """Vecindad tipo "reina": dos distritos son vecinos si sus límites se tocan.

    Devuelve una tabla larga (ubigeo, vecino). Si se indica ``ruta_geojson``,
    exporta además una versión simplificada del mapa para el tablero.
    """
    import geopandas as gpd  # importación diferida: dependencia opcional

    gdf = gpd.read_file(ruta_shp)[[col_ubigeo, "geometry"]].rename(columns={col_ubigeo: "ubigeo"})
    gdf["ubigeo"] = normalizar_ubigeo(gdf["ubigeo"])
    gdf = gdf.to_crs(epsg=4326)

    pares = gpd.sjoin(gdf, gdf, how="inner", predicate="touches")
    ady = (
        pares[["ubigeo_left", "ubigeo_right"]]
        .rename(columns={"ubigeo_left": "ubigeo", "ubigeo_right": "vecino"})
        .query("ubigeo != vecino")
        .drop_duplicates()
        .reset_index(drop=True)
    )
    if ruta_geojson is not None:
        simple = gdf.copy()
        simple["geometry"] = simple.geometry.simplify(0.005, preserve_topology=True)
        simple.to_file(ruta_geojson, driver="GeoJSON")
    return ady


def leer_adyacencia(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype=str)
    df["ubigeo"] = normalizar_ubigeo(df["ubigeo"])
    df["vecino"] = normalizar_ubigeo(df["vecino"])
    return df[["ubigeo", "vecino"]].drop_duplicates().reset_index(drop=True)
