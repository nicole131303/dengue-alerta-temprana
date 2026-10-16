"""dengue_alerta: alerta temprana explicable de brotes de dengue a nivel distrital (Perú).

Organización del paquete (una carpeta = una responsabilidad):

    datos/      lectura y limpieza de cada fuente (MINSA, clima, ENSO, censo, mapas)
    panel/      calendario epidemiológico, panel distrito-semana y etiqueta de brote
    features/   variables predictoras causales (epidemiológicas, espaciales, climáticas, estructurales)
    modelado/   partición temporal, líneas base, modelos, métricas, entrenamiento y SHAP
    utils/      utilidades transversales (registro de eventos)

Los módulos se comunican SOLO a través de archivos Parquet validados por un contrato
(ver ``contratos.py``). Así cada etapa puede probarse y reemplazarse por separado.
"""

__version__ = "0.1.0"
