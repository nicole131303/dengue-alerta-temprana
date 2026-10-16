"""Interfaz de línea de comandos.

Ejemplos:
    python -m dengue_alerta sintetico                    # crea datos de prueba
    python -m dengue_alerta panel                        # Módulo 1
    python -m dengue_alerta todo --config configs/ci.yaml
    python -m dengue_alerta tunear --horizonte 2 --trials 50
"""

from __future__ import annotations

import argparse
import time

from dengue_alerta.config import cargar_config
from dengue_alerta.pipeline import ETAPAS, SECUENCIA_TODO
from dengue_alerta.utils.log import obtener_logger

log = obtener_logger("dengue_alerta.cli")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="dengue_alerta",
        description="Alerta temprana explicable de brotes de dengue (distrito-semana, Perú)",
    )
    parser.add_argument(
        "etapa",
        choices=[*ETAPAS, "todo", "tunear"],
        help="etapa a ejecutar ('todo' = panel -> features -> auditar -> entrenar -> explicar)",
    )
    parser.add_argument("--config", default="configs/base.yaml", help="archivo YAML")
    parser.add_argument("--horizonte", type=int, default=2, help="(tunear) semanas de anticipación")
    parser.add_argument("--trials", type=int, default=40, help="(tunear) número de pruebas")
    args = parser.parse_args(argv)

    cfg = cargar_config(args.config)
    log.info("Configuración: %s", cfg.ruta.name)

    if args.etapa == "tunear":
        from dengue_alerta.modelado.tunear import tunear_lightgbm

        tunear_lightgbm(cfg, args.horizonte, args.trials)
        return

    secuencia = SECUENCIA_TODO if args.etapa == "todo" else [args.etapa]
    for nombre in secuencia:
        inicio = time.time()
        log.info("========== %s ==========", nombre.upper())
        ETAPAS[nombre](cfg)
        log.info("%s terminado en %.1f s", nombre, time.time() - inicio)


if __name__ == "__main__":
    main()
