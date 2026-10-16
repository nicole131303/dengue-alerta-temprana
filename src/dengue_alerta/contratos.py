"""Contratos de datos entre módulos.

Cada etapa del pipeline entrega un archivo Parquet. Antes de escribirlo y
después de leerlo se valida contra un *contrato*: qué columnas debe tener,
de qué tipo y cuál es su llave (combinación que no puede repetirse).

Si alguien cambia un módulo y rompe el formato, el error aparece en el
punto exacto donde se produjo y no tres etapas después como un resultado raro.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


class ErrorContrato(ValueError):
    """El DataFrame no cumple el contrato declarado."""


@dataclass(frozen=True)
class Contrato:
    nombre: str
    columnas: dict[str, str]  # columna -> tipo esperado: "texto", "entero", "real", "fecha"
    llave: list[str] = field(default_factory=list)

    def validar(self, df: pd.DataFrame) -> pd.DataFrame:
        faltan = [c for c in self.columnas if c not in df.columns]
        if faltan:
            raise ErrorContrato(f"[{self.nombre}] faltan columnas: {faltan}")

        for col, tipo in self.columnas.items():
            s = df[col]
            ok = {
                "texto": pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s),
                "entero": pd.api.types.is_integer_dtype(s),
                "real": pd.api.types.is_numeric_dtype(s),
                "fecha": pd.api.types.is_datetime64_any_dtype(s),
            }[tipo]
            if not ok:
                raise ErrorContrato(f"[{self.nombre}] '{col}' debería ser {tipo}, es {s.dtype}")

        if self.llave:
            if df[self.llave].isna().any().any():
                raise ErrorContrato(f"[{self.nombre}] hay valores nulos en la llave {self.llave}")
            if df.duplicated(self.llave).any():
                n = int(df.duplicated(self.llave).sum())
                raise ErrorContrato(f"[{self.nombre}] {n} filas repetidas en la llave {self.llave}")

        if "ubigeo" in self.columnas and not df["ubigeo"].astype(str).str.fullmatch(r"\d{6}").all():
            raise ErrorContrato(f"[{self.nombre}] hay ubigeos que no tienen 6 dígitos")
        return df


# ---------------------------------------------------------------------
# Contratos del pipeline (en orden de ejecución)
# ---------------------------------------------------------------------
CASOS = Contrato(
    "casos_limpios",
    {"ubigeo": "texto", "anio": "entero", "semana": "entero", "tipo_dx": "texto"},
)

PANEL = Contrato(
    "panel_etiquetado",
    {
        "ubigeo": "texto",
        "fecha": "fecha",
        "anio_epi": "entero",
        "semana_epi": "entero",
        "casos": "entero",
        "brote": "entero",  # etiqueta retrospectiva (solo como objetivo)
        "brote_rt": "entero",  # estado causal en tiempo real (puede ser predictor)
        "sin_brote_hoy": "entero",
    },
    llave=["ubigeo", "fecha"],
)

CLIMA_SEMANAL = Contrato(
    "clima_semanal",
    {"ubigeo": "texto", "fecha": "fecha", "precip_mm": "real", "temp_c": "real", "hum_rel": "real"},
    llave=["ubigeo", "fecha"],
)

ENSO = Contrato(
    "indices_enso", {"anio": "entero", "mes": "entero", "icen": "real"}, ["anio", "mes"]
)

ADYACENCIA = Contrato("adyacencia", {"ubigeo": "texto", "vecino": "texto"}, ["ubigeo", "vecino"])

ESTRUCTURALES = Contrato(
    "estructurales",
    {"ubigeo": "texto", "poblacion": "real", "altitud_m": "real"},
    llave=["ubigeo"],
)

DATASET = Contrato(
    "dataset_modelado",
    {"ubigeo": "texto", "fecha": "fecha", "casos": "entero", "brote_rt": "entero"},
    llave=["ubigeo", "fecha"],
)

PREDICCIONES = Contrato(
    "predicciones",
    {
        "ubigeo": "texto",
        "fecha": "fecha",
        "horizonte": "entero",
        "experimento": "texto",
        "modelo": "texto",
        "riesgo": "real",
    },
    llave=["ubigeo", "fecha", "horizonte", "experimento", "modelo"],
)
