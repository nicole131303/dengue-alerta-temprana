# Catálogo de datos

> Los datos **no se suben a GitHub** (ver `.gitignore`). Este archivo explica de dónde
> sale cada uno, en qué carpeta va y con qué nombre, para que cualquiera pueda
> reproducir el proyecto desde cero.

## Estructura

| Carpeta | Qué contiene | ¿Se modifica? |
|---|---|---|
| `raw/` | Datos tal como se descargan | **Nunca** (solo lectura) |
| `external/` | Fuentes complementarias ya en formato tabular | Solo al descargar |
| `interim/` | Salidas intermedias entre módulos (Parquet) | Las genera el pipeline |
| `processed/` | Dataset de modelado, predicciones y SHAP | Las genera el pipeline |

## Fuentes

| Archivo esperado | Fuente | Cómo obtenerlo |
|---|---|---|
| `raw/vigilancia_dengue.csv` | MINSA – CDC Perú, *Vigilancia epidemiológica de dengue* (2000–2023) | Plataforma Nacional de Datos Abiertos: datosabiertos.gob.pe → buscar "dengue" → descargar CSV |
| `external/clima_distrital_diario.csv` | CHIRPS (lluvia) + ERA5-Land (temperatura, punto de rocío) | `scripts/gee/clima_distrital.js` en Google Earth Engine |
| `external/indices_enso.csv` | ICEN – IGP/ENFEN (y opcionalmente ONI – NOAA) | Copiar la tabla mensual a un CSV con columnas `anio, mes, icen[, oni]` |
| `external/estructurales_distritales.csv` | Censo 2017 (INEI, REDATAM) + altitud SRTM | Tabulados por distrito: población, viviendas sin agua de red / sin desagüe, hacinamiento |
| `external/adyacencia_distritos.csv` | Límites distritales del INEI | `dengue_alerta.datos.geografia.adyacencia_desde_shapefile()` |
| `external/distritos.geojson` | Límites distritales simplificados (para el mapa) | Se genera junto con la adyacencia |

## Diccionario mínimo del CSV del MINSA

| Columna | Significado | Uso |
|---|---|---|
| `ubigeo` | Distrito probable de infección (6 dígitos) | Llave del panel |
| `ano`, `semana` | Año y semana epidemiológica de **inicio de síntomas** | Eje temporal |
| `enfermedad` | Dengue sin señales de alarma / con señales / grave | Filtro |
| `tipo_dx` | C = confirmado, P = probable, S = sospechoso | Se usan C y P |
| `edad`, `sexo` | Datos del caso | No se usan en el modelo (privacidad) |

## Datos sintéticos

`python -m dengue_alerta sintetico` crea todos estos archivos con el **mismo formato**
para desarrollar y probar sin los datos reales. Sus resultados **no son hallazgos de la
tesis**. Antes de correr con datos reales, borra los sintéticos (`make limpiar` y los
archivos de `raw/` y `external/`).
