"""Lectura y escritura de los archivos intermedios (siempre validados)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dengue_alerta.contratos import Contrato
from dengue_alerta.utils.log import obtener_logger

log = obtener_logger(__name__)


def guardar(df: pd.DataFrame, ruta: Path, contrato: Contrato | None = None) -> Path:
    if contrato is not None:
        contrato.validar(df)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ruta, index=False)
    log.info("Guardado %s (%s filas x %s columnas)", ruta.name, f"{len(df):,}", df.shape[1])
    return ruta


def leer(ruta: Path, contrato: Contrato | None = None) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecuta primero la etapa anterior del pipeline "
            "(ver `python -m dengue_alerta --help`)."
        )
    df = pd.read_parquet(ruta)
    if contrato is not None:
        contrato.validar(df)
    return df


def normalizar_ubigeo(serie: pd.Series) -> pd.Series:
    """Devuelve el ubigeo como texto de 6 dígitos.

    Excel y pandas suelen leer el ubigeo como número y se pierde el cero
    inicial (``020101`` -> ``20101``, o incluso ``20101.0``). Sin esta
    corrección los cruces con clima, censo y mapas fallan en silencio.
    """
    return serie.astype(str).str.strip().str.split(".").str[0].str.zfill(6)
