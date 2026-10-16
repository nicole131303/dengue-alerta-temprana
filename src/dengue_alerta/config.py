"""Carga de la configuración YAML.

Permite herencia entre archivos (``hereda: base.yaml``) para que una
configuración de experimento solo declare lo que cambia respecto a la base.
Las rutas se resuelven siempre respecto a la raíz del repositorio, de modo
que el código funciona igual desde la terminal, un notebook o GitHub Actions.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def _fusionar(base: dict, extra: dict) -> dict:
    """Fusión recursiva: los valores de ``extra`` reemplazan a los de ``base``."""
    salida = copy.deepcopy(base)
    for clave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(salida.get(clave), dict):
            salida[clave] = _fusionar(salida[clave], valor)
        else:
            salida[clave] = valor
    return salida


def _leer_yaml(ruta: Path) -> dict:
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f) or {}
    padre = datos.pop("hereda", None)
    if padre:
        datos = _fusionar(_leer_yaml(ruta.parent / padre), datos)
    return datos


def encontrar_raiz(desde: Path) -> Path:
    """Sube por las carpetas hasta encontrar ``pyproject.toml`` (raíz del repo)."""
    for carpeta in [desde, *desde.parents]:
        if (carpeta / "pyproject.toml").exists():
            return carpeta
    return Path.cwd()


@dataclass(frozen=True)
class Config:
    """Envoltorio de solo lectura sobre el diccionario de configuración."""

    datos: dict[str, Any]
    raiz: Path
    ruta: Path

    def __getitem__(self, clave: str) -> Any:
        return self.datos[clave]

    def get(self, clave: str, defecto: Any = None) -> Any:
        return self.datos.get(clave, defecto)

    def ruta_abs(self, relativa: str | Path) -> Path:
        """Convierte una ruta del YAML en absoluta respecto a la raíz del repo."""
        return (self.raiz / relativa).resolve()

    def carpeta(self, nombre: str) -> Path:
        """Ruta absoluta de una carpeta declarada en ``rutas`` (la crea si no existe)."""
        p = self.ruta_abs(self.datos["rutas"][nombre])
        p.mkdir(parents=True, exist_ok=True)
        return p

    def fuente(self, nombre: str) -> Path:
        return self.ruta_abs(self.datos["fuentes"][nombre])


def cargar_config(ruta: str | Path = "configs/base.yaml") -> Config:
    ruta = Path(ruta).resolve()
    return Config(datos=_leer_yaml(ruta), raiz=encontrar_raiz(ruta.parent), ruta=ruta)
