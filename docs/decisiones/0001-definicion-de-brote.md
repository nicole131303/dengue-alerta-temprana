# ADR 0001 · Definición operacional de brote

- **Estado:** aceptada
- **Fecha:** 2026-10-13

## Contexto
El MINSA no publica una clasificación oficial de "distrito en brote" por semana. Sin una
etiqueta reproducible no hay variable objetivo que aprender ni forma de comparar con la
literatura.

## Decisión
Se adopta la regla de Dostal et al. (2022): un episodio es brote si acumula **≥ 5 casos en
≥ 3 semanas consecutivas con casos**; el episodio termina tras **2 semanas seguidas sin
casos**. Se implementa en dos versiones:

- `etiquetar_brotes` (retrospectiva): marca todo el episodio → solo como **objetivo**.
- `brote_en_tiempo_real` (causal): se enciende cuando la regla ya se cumplió → **predictor**.

Los tres parámetros viven en `configs/base.yaml` → `etiqueta`.

## Consecuencias
- (+) Reproducible y comparable; permite análisis de sensibilidad cambiando el YAML.
- (+) La diferencia entre ambas versiones define el **retraso de detección**, que es la
  ventana que el modelo debe adelantar.
- (−) La regla depende del subregistro de casos; se valida contra las salas situacionales
  del CDC Perú (issue de validación en el hito v0.1).
