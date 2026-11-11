"""
test_date_filter.py — Pruebas unitarias para el selector de periodo temporal de análisis.
"""

import pandas as pd
import pytest

from services.accounting import calc_gastos_ingresos, filter_df_by_date_range
from tabs.diario.date_filter import get_available_period_options, get_date_range_from_mode


def _make_sample_diario() -> pd.DataFrame:
    rows = [
        {
            "Fecha": "2026-04-10",
            "Nº Cuenta": "500",
            "Cuenta": "Gastos Comida",
            "Debe": 50.0,
            "Haber": 0.0,
        },
        {
            "Fecha": "2026-05-15",
            "Nº Cuenta": "400",
            "Cuenta": "Ingresos Sueldo",
            "Debe": 0.0,
            "Haber": 2000.0,
        },
        {
            "Fecha": "2026-06-20",
            "Nº Cuenta": "501",
            "Cuenta": "Gastos Ocio",
            "Debe": 100.0,
            "Haber": 0.0,
        },
        {
            "Fecha": "2026-07-01",
            "Nº Cuenta": "400",
            "Cuenta": "Ingresos Sueldo",
            "Debe": 0.0,
            "Haber": 2200.0,
        },
        {
            "Fecha": "2026-08-01",
            "Nº Cuenta": "500",
            "Cuenta": "Gastos Comida",
            "Debe": 80.0,
            "Haber": 0.0,
        },
    ]
    df = pd.DataFrame(rows)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    return df


class TestDateFilterLogic:
    def test_historico_completo(self):
        df = _make_sample_diario()
        start, end, label = get_date_range_from_mode(df, "🌐 Histórico Completo")
        assert start is None
        assert end is None
        assert "Histórico Completo" in label

    def test_ano_actual(self):
        df = _make_sample_diario()
        start, end, label = get_date_range_from_mode(df, "📅 Año Actual")
        assert start == pd.Timestamp("2026-01-01")
        assert end.year == 2026
        assert label == "Año 2026"

        filtered = filter_df_by_date_range(df, start, end)
        assert len(filtered) == 5
        assert set(filtered["Fecha"].dt.year) == {2026}

    def test_ultimos_12_meses(self):
        df = _make_sample_diario()
        start, end, label = get_date_range_from_mode(df, "📆 Últimos 12 Meses")
        assert start is not None and end is not None
        assert "Últimos 12 meses" in label

    def test_mes_actual(self):
        df = _make_sample_diario()
        start, end, label = get_date_range_from_mode(df, "🗓️ Mes Actual")
        assert start == pd.Timestamp("2026-08-01")
        assert label == "Mes 2026-08"

        filtered = filter_df_by_date_range(df, start, end)
        assert len(filtered) == 1

    def test_ano_concreto(self):
        df = _make_sample_diario()
        start, end, label = get_date_range_from_mode(df, "🎯 Año Concreto", year_val=2026)
        assert start == pd.Timestamp("2026-01-01")
        assert end.year == 2026
        assert label == "Año 2026"

        filtered = filter_df_by_date_range(df, start, end)
        assert len(filtered) == 5

    def test_mes_concreto(self):
        df = _make_sample_diario()
        start, end, label = get_date_range_from_mode(df, "📆 Mes Concreto", month_val="2026-06")
        assert start == pd.Timestamp("2026-06-01")
        assert label == "Mes 2026-06"

        filtered = filter_df_by_date_range(df, start, end)
        assert len(filtered) == 1
        assert filtered.iloc[0]["Cuenta"] == "Gastos Ocio"

    def test_rango_personalizado(self):
        df = _make_sample_diario()
        range_tuple = (pd.Timestamp("2026-05-01").date(), pd.Timestamp("2026-06-30").date())
        start, end, label = get_date_range_from_mode(
            df, "⚙️ Rango Personalizado", range_val=range_tuple
        )
        assert start == pd.Timestamp("2026-05-01")
        assert label.startswith("Rango")

        filtered = filter_df_by_date_range(df, start, end)
        assert len(filtered) == 2

    def test_calc_gastos_ingresos_with_filtered_data(self):
        df = _make_sample_diario()
        start, end, _ = get_date_range_from_mode(
            df,
            "⚙️ Rango Personalizado",
            range_val=(pd.Timestamp("2026-05-01").date(), pd.Timestamp("2026-06-30").date()),
        )
        df_filtered = filter_df_by_date_range(df, start, end)

        gi = calc_gastos_ingresos(df_filtered)
        assert gi["total_hist_ingresos"] == pytest.approx(2000.0)
        assert gi["total_hist_gastos"] == pytest.approx(100.0)
        assert "Ingresos Sueldo" in gi["cat_incomes"]
        assert "Gastos Ocio" in gi["cat_expenses"]

    def test_get_available_period_options(self):
        df = _make_sample_diario()
        opts = get_available_period_options(df)
        assert 2026 in opts["years"]
        assert "2026-08" in opts["months"]
