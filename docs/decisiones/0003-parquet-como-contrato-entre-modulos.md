# ADR 0003 · Los módulos se comunican mediante archivos Parquet con contrato

- **Estado:** aceptada
- **Fecha:** 2026-10-13

## Contexto
El sistema tiene cinco módulos con ritmos distintos: el clima se extrae una vez (horas en
Earth Engine), el modelado se repite decenas de veces y el tablero solo lee resultados.
Encadenarlos en memoria obligaría a recalcular todo en cada prueba.

## Decisión
Cada etapa escribe un Parquet en `data/interim` o `data/processed`, y `contratos.py`
valida columnas, tipos y llave (sin duplicados ni nulos) al escribir y al leer.

## Consecuencias
- (+) Cada etapa se puede correr, probar y depurar por separado.
- (+) Un cambio que rompe el formato falla en el punto exacto donde ocurrió.
- (+) El tablero abre al instante: no entrena nada.
- (−) Hay que recordar re-ejecutar las etapas siguientes tras un cambio
  (`python -m dengue_alerta todo` lo resuelve). Si el proyecto creciera, el siguiente paso
  sería DVC o un orquestador (Prefect, Dagster).
