"""Vigilancia epidemiológica de dengue (MINSA - CDC Perú, Plataforma Nacional de Datos Abiertos).

Cada fila del CSV es UN caso notificado con: departamento, provincia,
distrito, enfermedad, ano, semana, diagnostic, tipo_dx, diresa, ubigeo,
edad, tipo_edad, sexo. ``semana`` es la semana de inicio de síntomas y
``ubigeo`` el distrito probable de infección.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dengue_alerta.io import normalizar_ubigeo

# Nombre en el CSV del MINSA -> nombre interno
COLUMNAS = {
    "ubigeo": "ubigeo",
    "ano": "anio",
    "semana": "semana",
    "enfermedad": "enfermedad",
    "tipo_dx": "tipo_dx",
}


def leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee el CSV oficial probando las codificaciones habituales del portal."""
    for codificacion in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(ruta, dtype={"ubigeo": str}, encoding=codificacion, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {ruta} con utf-8 ni latin-1")


def limpiar(crudo: pd.DataFrame, tipos_validos: list[str]) -> pd.DataFrame:
    """Normaliza nombres, ubigeo y filtra registros válidos.

    1. Renombra columnas y se queda solo con las necesarias.
    2. Ubigeo como texto de 6 dígitos (recupera el cero inicial perdido).
    3. Solo dengue (el archivo puede traer otras enfermedades metaxénicas).
    4. Solo confirmados (C) y probables (P): los sospechosos (S) se excluyen
       porque muchos terminan descartados y meterían ruido en la etiqueta.
    5. Semanas válidas (1 a 53).
    """
    columnas = {k: v for k, v in COLUMNAS.items() if k in crudo.columns}
    df = crudo.rename(columns=columnas)[list(columnas.values())].copy()
    df["ubigeo"] = normalizar_ubigeo(df["ubigeo"])
    if "enfermedad" in df.columns:
        df = df[df["enfermedad"].astype(str).str.upper().str.contains("DENGUE", na=False)]
    df["tipo_dx"] = df["tipo_dx"].astype(str).str.strip().str.upper()
    df = df[df["tipo_dx"].isin(tipos_validos)]
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["semana"] = pd.to_numeric(df["semana"], errors="coerce")
    df = df.dropna(subset=["anio", "semana"])
    df = df[df["semana"].between(1, 53)]
    df[["anio", "semana"]] = df[["anio", "semana"]].astype("int64")
    return df.reset_index(drop=True)
