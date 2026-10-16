# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

## [0.1.0] - 2026-10-13
### Agregado
- Estructura del repositorio, paquete `dengue_alerta` instalable y CLI `python -m dengue_alerta`.
- Módulo 1: limpieza MINSA, calendario epidemiológico, panel distrito-semana, etiqueta de brote
  retrospectiva y en tiempo real, retraso de detección.
- Módulos 2 y 3: variables epidemiológicas, espaciales (vecinos), climáticas con rezago,
  ICEN con rezago de publicación y estructurales; filtro de altitud.
- Módulo 4: partición temporal con frontera, líneas base, fábrica de modelos, métricas
  estratificadas, ablación E1–E4, SHAP, auditoría de fuga y tuning con Optuna.
- Módulo 5: tablero Streamlit (mapa, ranking, explicación SHAP, repetición).
- Generador de datos sintéticos con el formato de las fuentes reales.
- 42 pruebas automáticas, CI en GitHub Actions, plantillas de issues y PR.
