# Notebooks

| Notebook | Para qué sirve |
|---|---|
| `00_modulo1_explicado_paso_a_paso.ipynb` | Versión **didáctica** y autocontenida del Módulo 1 (funciona sola en Google Colab). Conserva sus salidas para leerse en GitHub. |
| `01_resultados.ipynb` | Lee los resultados del pipeline y arma tablas y figuras para la tesis. |

## Reglas

1. **La lógica vive en `src/dengue_alerta/`**. Un notebook importa funciones del paquete; no las copia.
   Si algo de un notebook se vuelve útil, se mueve al paquete con su prueba.
2. Nombre: `NN_descripcion_corta.ipynb` (el número indica el orden de lectura).
3. Antes de subirlos, las salidas se borran automáticamente (`nbstripout`), salvo el notebook `00_`.
