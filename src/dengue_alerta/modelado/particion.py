"""Partición temporal con frontera (sin barajar filas).

Con series de tiempo NUNCA se usa ``train_test_split`` aleatorio: el modelo
vería semanas de 2023 al entrenar y "predeciría" 2022 conociendo el futuro.

Además se aplica una frontera: una fila de entrenamiento de la semana t
tiene como objetivo el estado en t+h. Si t+h cae en el periodo de
validación, esa fila filtraría información de validación al entrenamiento.
Por eso se exige que la FECHA DEL OBJETIVO (t+h) esté dentro del periodo.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Particion:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame

    def resumen(self) -> dict[str, int]:
        return {"train": len(self.train), "val": len(self.val), "test": len(self.test)}


def particionar(
    df: pd.DataFrame,
    h: int,
    fin_train: str,
    fin_val: str,
    requeridas: tuple[str, ...] = ("casos_12s",),
) -> Particion:
    objetivo = f"y_h{h}"
    # Se descartan filas sin objetivo (últimas h semanas) y el "calentamiento" inicial
    d = df.dropna(subset=[objetivo, *requeridas])
    fecha_objetivo = d["fecha"] + pd.Timedelta(weeks=h)
    fin_train, fin_val = pd.Timestamp(fin_train), pd.Timestamp(fin_val)

    train = d[fecha_objetivo <= fin_train]
    val = d[(d["fecha"] > fin_train) & (fecha_objetivo <= fin_val)]
    test = d[d["fecha"] > fin_val]
    return Particion(train.copy(), val.copy(), test.copy())
