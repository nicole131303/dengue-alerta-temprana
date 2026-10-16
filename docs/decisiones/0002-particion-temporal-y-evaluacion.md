# ADR 0002 · Partición temporal con frontera y evaluación en distritos sin brote

- **Estado:** aceptada
- **Fecha:** 2026-10-13

## Contexto
Una partición aleatoria mezcla semanas futuras en el entrenamiento y produce métricas
infladas (fuga de información; Kapoor y Narayanan, 2023). Además, los brotes duran varias
semanas: un modelo que repite "si hoy hay brote, mañana también" obtiene métricas altas sin
anticipar nada.

## Decisión
1. Entrenamiento ≤ 2021, validación 2022, prueba 2023 (año del Niño costero).
2. **Frontera:** una fila de la semana *t* pertenece a un periodo solo si *t + h* también.
3. El umbral de alerta se elige en validación (máximo F1) y se congela para prueba.
4. Toda métrica se reporta en el total **y** en el subgrupo `sin_brote_hoy`.
5. Se comparan siempre contra dos líneas base: persistencia y estacional ingenua.

## Consecuencias
- (+) Los resultados reflejan el uso real: predecir el futuro con lo que se sabe hoy.
- (+) El subgrupo `sin_brote_hoy` aísla la capacidad de anticipar brotes nuevos (la
  persistencia tiene sensibilidad 0 ahí por construcción).
- (−) Prueba de un solo año: se complementa, si hay tiempo, con validación *rolling origin*.
