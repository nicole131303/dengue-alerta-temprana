"""Módulo 5 - Tablero de alerta temprana de dengue.

Ejecutar desde la raíz del repositorio:
    streamlit run app/streamlit_app.py

Pestañas:
    Mapa de riesgo   -> dónde se espera un brote dentro de h semanas
    Ranking          -> a qué distritos sin brote hoy conviene priorizar
    ¿Por qué?        -> explicación SHAP de un distrito
    Repetición 2023  -> cómo se habría comportado la alerta semana a semana
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from carga import DatosTablero, cargar, explicacion, vista_semana

st.set_page_config(page_title="Alerta temprana de dengue", page_icon="🦟", layout="wide")


@st.cache_resource(show_spinner="Cargando resultados del pipeline...")
def datos() -> DatosTablero:
    return cargar()


try:
    d = datos()
except FileNotFoundError:
    st.error(
        "No se encontraron resultados. Ejecuta primero el pipeline:\n\n"
        "`python -m dengue_alerta sintetico` (solo para pruebas) y luego "
        "`python -m dengue_alerta todo`"
    )
    st.stop()

cfg_m = d.cfg["modelado"]
pred = d.predicciones

# ---------------------------------------------------------------- barra lateral
st.sidebar.title("🦟 Alerta temprana")
horizonte = st.sidebar.radio(
    "Anticipación",
    [int(h) for h in sorted(pred["horizonte"].unique())],
    format_func=lambda h: f"{h} semanas",
)
experimentos = sorted(pred["experimento"].unique())
experimento = st.sidebar.selectbox(
    "Experimento",
    experimentos,
    index=experimentos.index(cfg_m["experimento_final"])
    if cfg_m["experimento_final"] in experimentos
    else 0,
)
modelos = sorted(pred.loc[pred["experimento"] == experimento, "modelo"].unique())
modelo = st.sidebar.selectbox(
    "Modelo",
    modelos,
    index=modelos.index(cfg_m["modelo_explicable"]) if cfg_m["modelo_explicable"] in modelos else 0,
)
fechas = [pd.Timestamp(f) for f in sorted(pred["fecha"].unique())]
# Por defecto: 3 semanas antes de la semana con más brotes nuevos (momento ideal para alertar)
nuevos = pred[(pred["brote_rt"] == 0) & (pred["y_real"] == 1)].groupby("fecha").size()
pico = pd.Timestamp(nuevos.idxmax()) if len(nuevos) else fechas[0]
fecha = st.sidebar.select_slider(
    "Semana de emisión de la alerta",
    options=fechas,
    value=min(fechas, key=lambda f: abs(f - pico)),
    format_func=lambda f: f.strftime("%d/%m/%Y"),
)
solo_nuevos = st.sidebar.checkbox("Solo distritos SIN brote hoy", value=True)
st.sidebar.caption(
    "El riesgo es la probabilidad estimada de que el distrito esté en brote "
    f"dentro de {horizonte} semanas. Umbral de alerta elegido en validación."
)

vista = vista_semana(d, horizonte, experimento, modelo, fecha)
if solo_nuevos:
    vista = vista[vista["brote_rt"] == 0]

# ---------------------------------------------------------------- indicadores
st.title("Predicción temprana de brotes de dengue por distrito")
st.caption(
    f"Semana del {fecha:%d/%m/%Y} · objetivo: {fecha + pd.Timedelta(weeks=horizonte):%d/%m/%Y}"
    f" · {experimento} · {modelo}"
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Distritos evaluados", len(vista))
c2.metric("En alerta", int(vista["alerta"].sum()))
c3.metric("Con brote activo hoy", int(d.dataset.loc[d.dataset["fecha"] == fecha, "brote_rt"].sum()))
acertadas = int(((vista["alerta"] == 1) & (vista["y_real"] == 1)).sum())
c4.metric("Alertas que se confirmaron", f"{acertadas} / {int(vista['alerta'].sum())}")

mapa, ranking, porque, repeticion = st.tabs(
    ["🗺️ Mapa de riesgo", "📋 Ranking", "🔎 ¿Por qué?", "⏪ Repetición"]
)

with mapa:
    if d.geojson is None:
        st.info("Agrega `data/external/distritos.geojson` para ver el mapa.")
    else:
        fig = px.choropleth(
            vista,
            geojson=d.geojson,
            locations="ubigeo",
            featureidkey="properties.ubigeo",
            color="riesgo",
            range_color=(0, 1),
            color_continuous_scale="YlOrRd",
            hover_data={"riesgo": ":.2f", "casos_4s": True, "y_real": True},
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=520)
        st.plotly_chart(fig, width="stretch")

with ranking:
    k = cfg_m["k_ranking"]
    tabla = vista.head(k)[["ubigeo", "riesgo", "alerta", "casos", "casos_4s", "y_real"]]
    st.dataframe(
        tabla.rename(
            columns={
                "riesgo": "Riesgo",
                "alerta": "Alerta",
                "casos": "Casos (sem. actual)",
                "casos_4s": "Casos (4 sem.)",
                "y_real": "¿Hubo brote? (validación)",
            }
        ),
        hide_index=True,
        width="stretch",
        column_config={"Riesgo": st.column_config.ProgressColumn(min_value=0, max_value=1)},
    )
    st.caption(f"Los {k} distritos con mayor riesgo. La última columna solo existe en la prueba.")

with porque:
    opciones = vista["ubigeo"].tolist()
    if not opciones:
        st.info("No hay distritos para esta selección.")
    else:
        ubigeo = st.selectbox("Distrito", opciones, key="dist_shap")
        exp = explicacion(d, ubigeo, fecha, horizonte)
        if exp is None or exp.empty:
            st.info("Ejecuta `python -m dengue_alerta explicar` para generar las explicaciones.")
        else:
            if (experimento, modelo) != (cfg_m["experimento_final"], cfg_m["modelo_explicable"]):
                st.caption(
                    f"Explicación del modelo final ({cfg_m['modelo_explicable']}, "
                    f"{cfg_m['experimento_final']})."
                )
            e = exp.sort_values("shap")
            colores = ["#c0392b" if v > 0 else "#2471a3" for v in e["shap"]]
            fig = go.Figure(
                go.Bar(
                    x=e["shap"],
                    y=[f"{v} = {x:.2f}" for v, x in zip(e["variable"], e["valor"], strict=True)],
                    orientation="h",
                    marker_color=colores,
                )
            )
            fig.update_layout(
                height=380,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="Contribución al riesgo (SHAP, log-odds)",
            )
            st.plotly_chart(fig, width="stretch")
            st.caption("Rojo: empuja el riesgo hacia arriba. Azul: lo reduce.")

with repeticion:
    todos = sorted(pred["ubigeo"].unique())
    ubigeo_r = st.selectbox("Distrito", todos, key="dist_rep")
    serie = pred[
        (pred["ubigeo"] == ubigeo_r)
        & (pred["horizonte"] == horizonte)
        & (pred["experimento"] == experimento)
        & (pred["modelo"] == modelo)
    ].merge(d.dataset[["ubigeo", "fecha", "casos"]], on=["ubigeo", "fecha"])
    serie["fecha_objetivo"] = serie["fecha"] + pd.Timedelta(weeks=horizonte)
    fig = go.Figure()
    fig.add_bar(
        x=serie["fecha"], y=serie["casos"], name="Casos semanales", yaxis="y2", opacity=0.35
    )
    fig.add_scatter(x=serie["fecha"], y=serie["riesgo"], name=f"Riesgo a {horizonte} sem.")
    fig.add_scatter(
        x=serie["fecha"],
        y=serie["y_real"],
        name="Brote real en t+h",
        line=dict(dash="dot"),
        mode="lines",
    )
    fig.update_layout(
        height=420,
        yaxis=dict(title="Riesgo", range=[0, 1.05]),
        yaxis2=dict(title="Casos", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, width="stretch")
