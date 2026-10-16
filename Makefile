# Atajos del proyecto. Uso: `make <objetivo>`  (en Windows: usar los comandos de la derecha)
CONFIG ?= configs/base.yaml
PY ?= python

.PHONY: ayuda instalar sintetico panel features entrenar explicar pipeline app test lint formato limpiar

ayuda:            ## Muestra esta ayuda
	@grep -E '^[a-z]+:.*## ' Makefile | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

instalar:         ## Instala el paquete en modo editable con todas las herramientas
	$(PY) -m pip install -e ".[ml,app,dev]"
	pre-commit install

sintetico:        ## Genera datos sintéticos con el formato de las fuentes reales
	$(PY) -m dengue_alerta sintetico --config $(CONFIG)

panel:            ## Módulo 1: casos MINSA -> panel distrito-semana + etiqueta de brote
	$(PY) -m dengue_alerta panel --config $(CONFIG)

features:         ## Módulos 2 y 3: clima, ENSO, vecinos, estructurales -> dataset de modelado
	$(PY) -m dengue_alerta features --config $(CONFIG)

entrenar:         ## Módulo 4: ablación, líneas base, modelos y métricas
	$(PY) -m dengue_alerta entrenar --config $(CONFIG)

explicar:         ## Módulo 4: valores SHAP del modelo final
	$(PY) -m dengue_alerta explicar --config $(CONFIG)

pipeline:         ## Ejecuta todo, de los datos crudos a las explicaciones
	$(PY) -m dengue_alerta todo --config $(CONFIG)

app:              ## Módulo 5: abre el tablero de alerta temprana
	streamlit run app/streamlit_app.py

test:             ## Corre las pruebas automáticas
	$(PY) -m pytest

lint:             ## Revisa estilo y errores comunes
	ruff check . && ruff format --check .

formato:          ## Corrige formato automáticamente
	ruff check --fix . && ruff format .

limpiar:          ## Borra datos intermedios, modelos y reportes generados
	rm -rf data/interim/*.parquet data/processed/*.parquet models/*.joblib reports/metricas/* reports/figuras/*
