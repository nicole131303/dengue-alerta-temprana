"""Variables predictoras. Regla única para TODOS los archivos de esta carpeta:

    Una variable de la semana t solo puede usar información disponible
    al cierre de la semana t.

Cada función devuelve ``(DataFrame, lista_de_columnas_nuevas)`` para que el
ensamblador sepa qué columnas pertenecen a qué grupo (necesario para la
ablación: E1 epidemiológicas -> E2 + vecinos -> E3 + clima -> E4 + estructurales).
"""
