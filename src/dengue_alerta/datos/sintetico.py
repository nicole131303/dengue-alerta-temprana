"""Generador de datos sintéticos con EXACTAMENTE el formato de las fuentes reales.

Sirve para tres cosas:
1. Desarrollar y depurar el pipeline sin esperar a descargar los datos reales.
2. Correr la integración continua en GitHub (los datos reales no se suben).
3. Verificar que el modelo recupera relaciones que SÍ sabemos que existen,
   porque las pusimos nosotros: lluvia y temperatura con rezago, contagio
   desde distritos vecinos y El Niño costero en 2017 y 2023.

IMPORTANTE: los resultados con estos datos NO son hallazgos de la tesis;
solo demuestran que el software funciona.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from epiweeks import Week

DEPARTAMENTOS = ["24", "20", "13", "02", "22", "16", "25"]  # Tumbes, Piura, La Libertad, ...


@dataclass
class DatosSinteticos:
    casos: pd.DataFrame  # formato CSV MINSA (una fila por caso)
    clima_diario: pd.DataFrame
    enso: pd.DataFrame
    adyacencia: pd.DataFrame
    estructurales: pd.DataFrame
    geojson: dict


def _ubigeos(n_filas: int, n_cols: int) -> list[str]:
    salida = []
    for r in range(n_filas):
        dep = DEPARTAMENTOS[r % len(DEPARTAMENTOS)]
        for c in range(n_cols):
            salida.append(f"{dep}{c + 1:02d}{r // len(DEPARTAMENTOS) + 1:02d}")
    return salida


def _icen_mensual(anios: range, rng: np.random.Generator) -> pd.DataFrame:
    """Serie AR(1) con episodios de El Niño costero en 2017 y 2023 (como ocurrió)."""
    filas, valor = [], 0.0
    eventos = {
        (2017, 2): 1.4,
        (2017, 3): 1.8,
        (2017, 4): 1.2,
        (2023, 3): 1.6,
        (2023, 4): 2.2,
        (2023, 5): 2.4,
        (2023, 6): 2.0,
        (2023, 7): 1.5,
        (2015, 12): 1.3,
        (2016, 1): 1.1,
    }
    for a in anios:
        for m in range(1, 13):
            valor = 0.75 * valor + rng.normal(0, 0.25)
            filas.append((a, m, round(valor + eventos.get((a, m), 0.0), 2)))
    return pd.DataFrame(filas, columns=["anio", "mes", "icen"])


def generar(
    n_filas: int = 8,
    n_columnas: int = 5,
    anio_inicio: int = 2010,
    anio_fin: int = 2023,
    semilla: int = 7,
) -> DatosSinteticos:
    rng = np.random.default_rng(semilla)
    ubigeos = _ubigeos(n_filas, n_columnas)
    n = len(ubigeos)
    pos = {u: (i // n_columnas, i % n_columnas) for i, u in enumerate(ubigeos)}

    # --- Vecindad en grilla (arriba, abajo, izquierda, derecha) ---
    ady = []
    for u, (r, c) in pos.items():
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            rr, cc = r + dr, c + dc
            if 0 <= rr < n_filas and 0 <= cc < n_columnas:
                ady.append((u, ubigeos[rr * n_columnas + cc]))
    adyacencia = pd.DataFrame(ady, columns=["ubigeo", "vecino"])
    matriz = np.zeros((n, n))
    idx = {u: i for i, u in enumerate(ubigeos)}
    for u, v in ady:
        matriz[idx[u], idx[v]] = 1
    matriz = matriz / matriz.sum(axis=1, keepdims=True)

    # --- Estructurales: algunos distritos de altura (sin transmisión) ---
    altitud = rng.uniform(5, 1200, n)
    altos = rng.choice(n, size=max(2, n // 12), replace=False)
    altitud[altos] = rng.uniform(2700, 3800, len(altos))
    sin_agua = rng.beta(2, 5, n) * 100
    poblacion = rng.lognormal(10, 0.8, n).round()
    estructurales = pd.DataFrame(
        {
            "ubigeo": ubigeos,
            "poblacion": poblacion,
            "superficie_km2": rng.uniform(20, 900, n).round(1),
            "altitud_m": altitud.round(0),
            "pct_sin_agua_red": sin_agua.round(1),
            "pct_sin_desague": np.clip(sin_agua * 1.2 + rng.normal(0, 8, n), 0, 100).round(1),
            "pct_hacinamiento": rng.beta(2, 8, n).round(3) * 100,
        }
    )

    # --- Calendario semanal ---
    semanas, w = [], Week(anio_inicio, 1)
    while w.year <= anio_fin:
        semanas.append(w)
        w += 1
    fechas = pd.to_datetime([s.startdate() for s in semanas])
    T = len(fechas)

    # --- ENSO y clima semanal ---
    enso = _icen_mensual(range(anio_inicio - 1, anio_fin + 1), rng)
    icen_sem = (
        pd.DataFrame({"anio": fechas.year, "mes": fechas.month})
        .merge(enso, on=["anio", "mes"], how="left")["icen"]
        .to_numpy()
    )
    fase = 2 * np.pi * (np.array([s.week for s in semanas]) - 9) / 52.18
    precip = np.clip(
        25
        * (1 + np.cos(fase))[:, None]
        * (1 + 0.45 * np.clip(icen_sem, 0, None))[:, None]
        * rng.lognormal(0, 0.45, (T, n)),
        0,
        None,
    )
    temp = (
        25.5
        + 2.2 * np.cos(fase)[:, None]
        + 0.9 * icen_sem[:, None]
        - 0.0055 * altitud[None, :]
        + rng.normal(0, 0.6, (T, n))
    )
    hum = np.clip(72 + 8 * np.cos(fase)[:, None] + rng.normal(0, 3, (T, n)), 35, 98)

    # --- Proceso de transmisión autoexcitado con contagio espacial ---
    #   lambda = importación * clima(t-4) + reproducción local + contagio desde vecinos
    base = rng.choice([0.03, 0.10, 0.30], size=n, p=[0.45, 0.35, 0.20])
    base = base * (1 + sin_agua / 100) * (altitud < 2500)
    casos = np.zeros((T, n))
    acumulado = np.zeros(n)
    for t in range(T):
        tl = max(0, t - 4)
        clima = np.exp(0.018 * (precip[tl] - 25) + 0.35 * (temp[tl] - 25.5))
        susceptibles = np.exp(-acumulado / (60 + poblacion / 800))
        repro = np.clip(0.62 * clima * susceptibles, 0, 1.15)
        previo = casos[t - 1] if t > 0 else np.zeros(n)
        lam = base * clima + repro * (previo + 0.6 * matriz @ previo)
        casos[t] = rng.poisson(np.minimum(lam, 400))
        acumulado = 0.985 * acumulado + casos[t]

    # --- Explotar conteos semanales a una fila por caso (formato MINSA) ---
    t_idx, d_idx = np.nonzero(casos)
    repeticiones = casos[t_idx, d_idx].astype(int)
    t_rep, d_rep = np.repeat(t_idx, repeticiones), np.repeat(d_idx, repeticiones)
    m = len(t_rep)
    tipo = rng.choice(
        ["DENGUE SIN SEÑALES DE ALARMA", "DENGUE CON SEÑALES DE ALARMA", "DENGUE GRAVE"],
        size=m,
        p=[0.85, 0.13, 0.02],
    )
    casos_df = pd.DataFrame(
        {
            "departamento": "SINTETICO",
            "provincia": "SINTETICO",
            "distrito": "SINTETICO",
            "enfermedad": tipo,
            "ano": [semanas[t].year for t in t_rep],
            "semana": [semanas[t].week for t in t_rep],
            "diagnostic": "A97.0",
            "tipo_dx": rng.choice(["C", "P", "S"], size=m, p=[0.45, 0.45, 0.10]),
            "diresa": "SINTETICO",
            "ubigeo": [int(ubigeos[d]) for d in d_rep],  # como número: se pierde el cero inicial
            "edad": rng.integers(1, 85, m),
            "tipo_edad": "A",
            "sexo": rng.choice(["M", "F"], m),
        }
    )

    # --- Clima diario (como lo exporta Google Earth Engine) ---
    dias = pd.date_range(fechas[0], fechas[-1] + pd.Timedelta(days=6), freq="D")
    semana_de_dia = np.repeat(np.arange(T), 7)[: len(dias)]
    reparto = rng.dirichlet(np.ones(7) * 0.6, size=(T, n))  # la lluvia semanal en 7 días
    precip_d = (precip[:, None, :] * reparto.transpose(0, 2, 1)).reshape(T * 7, n)[: len(dias)]
    temp_d = temp[semana_de_dia] + rng.normal(0, 0.8, (len(dias), n))
    hum_d = hum[semana_de_dia]
    rocio_d = temp_d - (100 - hum_d) / 5
    clima_diario = pd.DataFrame(
        {
            "ubigeo": np.tile(ubigeos, len(dias)),
            "fecha": np.repeat(dias, n),
            "precip_mm": precip_d.ravel().round(2),
            "temp_c": temp_d.ravel().round(2),
            "rocio_c": rocio_d.ravel().round(2),
        }
    )

    # --- GeoJSON de cuadrados (para que el mapa del tablero funcione) ---
    features = []
    for u, (r, c) in pos.items():
        x0, y0, lado = -81.0 + c * 0.35, -3.6 - r * 0.35, 0.35
        anillo = [[x0, y0], [x0 + lado, y0], [x0 + lado, y0 - lado], [x0, y0 - lado], [x0, y0]]
        features.append(
            {
                "type": "Feature",
                "properties": {"ubigeo": u, "nombre": f"Distrito {u}"},
                "geometry": {"type": "Polygon", "coordinates": [anillo]},
            }
        )
    geojson = {"type": "FeatureCollection", "features": features}

    return DatosSinteticos(casos_df, clima_diario, enso, adyacencia, estructurales, geojson)


def escribir(datos: DatosSinteticos, rutas: dict[str, Path]) -> None:
    """Escribe cada archivo donde el pipeline espera encontrar la fuente real."""
    for p in rutas.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    datos.casos.to_csv(rutas["minsa_csv"], index=False)
    datos.clima_diario.to_csv(rutas["clima_csv"], index=False)
    datos.enso.to_csv(rutas["enso_csv"], index=False)
    datos.adyacencia.to_csv(rutas["adyacencia_csv"], index=False)
    datos.estructurales.to_csv(rutas["estructurales_csv"], index=False)
    rutas["geojson"].write_text(json.dumps(datos.geojson), encoding="utf-8")
