"""Limpieza de fuentes y construcción del panel."""

import pandas as pd
import pytest

from dengue_alerta.contratos import CASOS, PANEL, ErrorContrato
from dengue_alerta.datos import minsa
from dengue_alerta.datos.clima import humedad_relativa
from dengue_alerta.io import normalizar_ubigeo
from dengue_alerta.panel.calendario import inicio_de_semana, semana_a_fecha


def test_ubigeo_recupera_cero_inicial():
    s = pd.Series([20101, "20101.0", " 150101 ", "010101"])
    assert normalizar_ubigeo(s).tolist() == ["020101", "020101", "150101", "010101"]


def test_limpieza_excluye_sospechosos_y_otras_enfermedades():
    crudo = pd.DataFrame(
        {
            "ubigeo": [20101, 20101, 20101, 20101],
            "ano": [2023, 2023, 2023, 2023],
            "semana": [10, 10, 10, 60],
            "enfermedad": [
                "DENGUE SIN SEÑALES DE ALARMA",
                "DENGUE GRAVE",
                "LEPTOSPIROSIS",
                "DENGUE GRAVE",
            ],
            "tipo_dx": ["C", "S", "C", "P"],
        }
    )
    limpio = minsa.limpiar(crudo, ["C", "P"])
    assert len(limpio) == 1  # S excluido, leptospirosis excluida, semana 60 inválida
    CASOS.validar(limpio)


def test_semana_epidemiologica_a_fecha():
    # La SE 1 de 2023 empezó el domingo 1 de enero de 2023
    assert semana_a_fecha(2023, 1) == pd.Timestamp("2023-01-01")
    # 2021 no tiene semana 53 -> NaT en lugar de error
    assert pd.isna(semana_a_fecha(2021, 53))


def test_inicio_de_semana_es_domingo():
    fechas = pd.Series(pd.to_datetime(["2023-01-01", "2023-01-04", "2023-01-07"]))
    assert (inicio_de_semana(fechas) == pd.Timestamp("2023-01-01")).all()


def test_panel_es_grilla_completa(panel):
    PANEL.validar(panel)
    por_distrito = panel.groupby("ubigeo").size()
    assert por_distrito.nunique() == 1  # todos los distritos tienen todas las semanas
    diferencias = panel.groupby("ubigeo")["fecha"].diff().dropna().unique()
    assert list(diferencias) == [pd.Timedelta(weeks=1)]


def test_panel_conserva_todos_los_casos(casos_limpios, panel):
    # La única pérdida posible es la semana 53 inexistente (se reporta como NaT)
    assert panel["casos"].sum() <= len(casos_limpios)
    assert panel["casos"].sum() >= 0.99 * len(casos_limpios)


def test_contrato_detecta_llave_repetida(panel):
    duplicado = pd.concat([panel.head(3), panel.head(1)])
    with pytest.raises(ErrorContrato, match="repetidas"):
        PANEL.validar(duplicado)


def test_humedad_relativa_saturada_cuando_temp_igual_rocio():
    hr = humedad_relativa(pd.Series([25.0, 30.0]), pd.Series([25.0, 20.0]))
    assert hr.iloc[0] == pytest.approx(100)
    assert 50 < hr.iloc[1] < 60


def test_clima_semanal_solo_semanas_completas(clima_semanal):
    assert clima_semanal["fecha"].dt.dayofweek.eq(6).all()  # todas empiezan en domingo
    assert clima_semanal[["precip_mm", "temp_c", "hum_rel"]].notna().all().all()
