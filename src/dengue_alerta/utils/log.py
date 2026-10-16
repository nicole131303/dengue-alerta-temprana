"""Registro de eventos uniforme para todo el proyecto (en lugar de usar print)."""

from __future__ import annotations

import logging

_FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def obtener_logger(nombre: str) -> logging.Logger:
    raiz = logging.getLogger("dengue_alerta")
    if not raiz.handlers:
        manejador = logging.StreamHandler()
        manejador.setFormatter(logging.Formatter(_FORMATO, datefmt="%H:%M:%S"))
        raiz.addHandler(manejador)
        raiz.setLevel(logging.INFO)
    return logging.getLogger(nombre)
