#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Configura GitHub para el proyecto: etiquetas, hitos (milestones) y las
# tareas iniciales de cada módulo. Se ejecuta UNA vez, desde la raíz del repo,
# después de `gh auth login` y del primer `git push`.
#
#   bash scripts/github_setup.sh
# ---------------------------------------------------------------------------
set -euo pipefail

echo "==> Etiquetas"
gh label create "modulo-1-panel"     --color 1f77b4 --description "Panel y etiqueta de brote" --force
gh label create "modulo-2-clima"     --color 2ca02c --description "Clima y El Niño" --force
gh label create "modulo-3-espacial"  --color 9467bd --description "Vecinos y estructurales" --force
gh label create "modulo-4-modelado"  --color d62728 --description "Modelos, métricas y SHAP" --force
gh label create "modulo-5-tablero"   --color ff7f0e --description "Tablero Streamlit" --force
gh label create "tarea"              --color c5def5 --force
gh label create "experimento"        --color fbca04 --description "Hipótesis y resultado" --force
gh label create "datos"              --color 0e8a16 --description "Descarga o limpieza de fuentes" --force
gh label create "tesis"              --color 5319e7 --description "Redacción / figuras para el documento" --force

echo "==> Hitos (uno por entrega)"
crear_hito () { gh api "repos/{owner}/{repo}/milestones" -f title="$1" -f description="$2" >/dev/null || true; }
crear_hito "v0.1 Datos reales y Módulo 1" "Panel distrito-semana real, etiqueta validada contra el CDC"
crear_hito "v0.2 Clima, El Niño y vecinos" "Módulos 2 y 3 con fuentes reales"
crear_hito "v0.3 Modelado y explicabilidad" "Ablación, tuning, SHAP y comparación con líneas base"
crear_hito "v1.0 Sustentación" "Tablero, resultados finales y release citable"

echo "==> Tareas iniciales"
tarea () { gh issue create --title "$1" --label "$2" --milestone "$3" --body "$(printf '%b' "$4")" >/dev/null; echo "   + $1"; }

tarea "[Módulo 1] Descargar CSV de vigilancia de dengue (MINSA) y ubicarlo en data/raw" \
  "modulo-1-panel,datos" "v0.1 Datos reales y Módulo 1" \
  "- [ ] Descargar de datosabiertos.gob.pe\n- [ ] Revisar separador, codificación y columnas\n- [ ] Correr \`python -m dengue_alerta panel\`"
tarea "[Módulo 1] Validar la etiqueta de brote contra las salas situacionales del CDC" \
  "modulo-1-panel,tesis" "v0.1 Datos reales y Módulo 1" \
  "Comparar los brotes detectados en 2017 y 2023 con los distritos reportados por el CDC. Documentar coincidencias."
tarea "[Módulo 2] Extraer clima diario por distrito en Google Earth Engine" \
  "modulo-2-clima,datos" "v0.2 Clima, El Niño y vecinos" \
  "Usar scripts/gee/clima_distrital.js. Las exportaciones tardan horas: iniciar cuanto antes."
tarea "[Módulo 2] Armar CSV mensual de ICEN (IGP) y ONI (NOAA)" \
  "modulo-2-clima,datos" "v0.2 Clima, El Niño y vecinos" "Columnas: anio, mes, icen, oni"
tarea "[Módulo 3] Generar adyacencia y GeoJSON desde el shapefile del INEI" \
  "modulo-3-espacial,datos" "v0.2 Clima, El Niño y vecinos" \
  "dengue_alerta.datos.geografia.adyacencia_desde_shapefile(ruta, ruta_geojson=...)"
tarea "[Módulo 3] Tabular Censo 2017 por distrito (REDATAM) y altitud SRTM" \
  "modulo-3-espacial,datos" "v0.2 Clima, El Niño y vecinos" \
  "poblacion, superficie_km2, altitud_m, pct_sin_agua_red, pct_sin_desague, pct_hacinamiento"
tarea "[EXP] Ablación E1-E4 con datos reales" \
  "modulo-4-modelado,experimento" "v0.3 Modelado y explicabilidad" \
  "Hipótesis: cada grupo de variables mejora la PR-AUC en distritos sin brote hoy."
tarea "[Módulo 4] Tuning de LightGBM con Optuna (h=2 y h=4)" \
  "modulo-4-modelado,experimento" "v0.3 Modelado y explicabilidad" \
  "python -m dengue_alerta tunear --horizonte 2 --trials 60"
tarea "[Módulo 4] Curva de calibración y análisis de errores por región" \
  "modulo-4-modelado,tesis" "v0.3 Modelado y explicabilidad" ""
tarea "[Módulo 5] Desplegar el tablero en Streamlit Community Cloud" \
  "modulo-5-tablero" "v1.0 Sustentación" "Usar resultados agregados (sin datos personales)."

echo "Listo. Revisa: gh issue list"
