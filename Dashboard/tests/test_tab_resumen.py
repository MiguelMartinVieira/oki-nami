"""
test_tab_resumen.py — Pruebas unitarias para el tab principal Resumen (Bento Grid).

Verifica que el paquete tabs/resumen/ y su módulo principal expongan la interfaz
pública esperada y que los cálculos de datos de cartera, ingresos/gastos y KPIs
asociados funcionen correctamente con datos sintéticos y casos límite (DataFrames vacíos).
"""

from unittest.mock import patch

import pandas as pd
import pytest

from services.accounting import calc_ahorro, calc_gastos_ingresos, calc_portfolio_summary
from tabs.resumen import render
from tabs.resumen.main import (
    _render_row1_metrics_and_audit,
    _render_row2_portfolio_and_monthly,
    _render_row3_sankey_and_heatmap,
    _render_row4_radars,
)


def _make_diario(rows: list[dict]) -> pd.DataFrame:
    """Helper: crea un DataFrame tipo Diario con tipos normalizados."""
    defaults = {
        "Fecha": "2026-03-25",
        "Nº Cuenta": "121",
        "Cuenta": "",
        "Categoría": "",
        "Debe": 0.0,
        "Haber": 0.0,
        "Descripción": "",
    }
    data = [{**defaults, **r} for r in rows] if rows else []
    df = pd.DataFrame(data, columns=list(defaults.keys()))
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0)
    df["Haber"] = pd.to_numeric(df["Haber"], errors="coerce").fillna(0.0)
    return df


def test_package_exports_render():
    """tabs.resumen debe exponer render callable."""
    assert callable(render)


def test_internal_render_functions_callable():
    """Las funciones de fila del Bento Grid deben ser invocables."""
    assert callable(_render_row1_metrics_and_audit)
    assert callable(_render_row2_portfolio_and_monthly)
    assert callable(_render_row3_sankey_and_heatmap)
    assert callable(_render_row4_radars)


def test_resumen_kpi_portfolio_integration():
    """Valida los cálculos de portfolio que alimentan las métricas de la fila 1 de Resumen."""
    df_sample = _make_diario(
        [
            {
                "Fecha": "2026-04-01",
                "Nº Cuenta": "121",
                "Debe": 500.0,
                "Haber": 0.0,
                "Descripción": "Saldo TR",
            },
            {
                "Fecha": "2026-04-05",
                "Nº Cuenta": "141",
                "Debe": 300.0,
                "Haber": 0.0,
                "Descripción": "BRK purchase",
            },
            {
                "Fecha": "2026-04-10",
                "Nº Cuenta": "131",
                "Debe": 150.0,
                "Haber": 0.0,
                "Descripción": "Préstamo Padres",
            },
        ]
    )

    with patch("data.yahoo.get_yahoo_price", return_value=100.0):
        portfolio = calc_portfolio_summary(df_sample, metalico_fisico=75.0)

        assert isinstance(portfolio, dict)
        assert "valor_fondo_eur" in portfolio
        assert "valor_brk_eur" in portfolio
        assert "tr_cash" in portfolio
        assert "padres_total" in portfolio
        assert "total_patrimonio" in portfolio
        assert portfolio["padres_total"] == 150.0
        assert portfolio["tr_cash"] == 500.0
        assert portfolio["total_patrimonio"] > 0


def test_resumen_calc_gastos_ingresos_integration():
    """Valida el cálculo de flujos que alimenta las filas 2, 3 y 4 del Bento Grid."""
    df_sample = _make_diario(
        [
            {
                "Fecha": "2026-05-01",
                "Nº Cuenta": "41",
                "Debe": 0.0,
                "Haber": 2000.0,
                "Descripción": "Nómina",
            },
            {
                "Fecha": "2026-05-03",
                "Nº Cuenta": "51",
                "Debe": 50.0,
                "Haber": 0.0,
                "Descripción": "Mercadona",
            },
            {
                "Fecha": "2026-05-04",
                "Nº Cuenta": "52",
                "Debe": 20.0,
                "Haber": 0.0,
                "Descripción": "Restaurante",
            },
        ]
    )

    gi = calc_gastos_ingresos(df_sample)
    assert gi["total_hist_ingresos"] == 2000.0
    assert gi["total_hist_gastos"] == 70.0
    ahorro, tasa = calc_ahorro(gi["total_hist_ingresos"], gi["total_hist_gastos"])
    assert ahorro == 1930.0
    assert pytest.approx(tasa) == 96.5
    assert not gi["cat_expenses"].empty


def test_resumen_empty_dataframe_resilience():
    """Garantiza que calc_gastos_ingresos y calc_portfolio_summary manejan DF vacíos sin excepciones."""
    df_empty = _make_diario([])

    with patch("data.yahoo.get_yahoo_price", return_value=0.0):
        portfolio = calc_portfolio_summary(df_empty, metalico_fisico=0.0)
        assert portfolio["total_patrimonio"] == 0.0

        gi = calc_gastos_ingresos(df_empty)
        assert gi["total_hist_ingresos"] == 0.0
        assert gi["total_hist_gastos"] == 0.0


def test_resumen_row2_none_portfolio_history_graceful():
    """Valida que _render_row2_portfolio_and_monthly no lance excepción si _build_portfolio_history retorna None."""
    df_empty = _make_diario([])
    portfolio = {
        "valor_fondo_eur": 1000.0,
        "valor_brk_eur": 500.0,
        "tr_cash": 100.0,
        "padres_total": 50.0,
    }
    gi = {
        "current_month": "2026-10",
        "cm_ingresos": 0.0,
        "cm_gastos": 0.0,
        "cat_incomes_cm": pd.Series(dtype=float),
        "cat_expenses_cm": pd.Series(dtype=float),
    }

    with (
        patch("tabs.resumen.main._build_portfolio_history", return_value=None),
        patch("components.skeleton.render_skeleton_chart") as mock_skeleton,
    ):
        _render_row2_portfolio_and_monthly(
            portfolio, metalico_fisico=10.0, df_diario=df_empty, gi=gi
        )
        mock_skeleton.assert_called_once()


def test_build_stacked_area_none_and_empty_resilience():
    """build_stacked_area debe retornar None de forma segura si df_plot es None, vacío o sin Date."""
    from components.charts.line import build_stacked_area

    assert build_stacked_area(None, ["SP500"]) is None
    assert build_stacked_area(pd.DataFrame(), ["SP500"]) is None
    assert build_stacked_area(pd.DataFrame({"SP500": [100]}), ["SP500"]) is None
    assert build_stacked_area(pd.DataFrame({"Date": ["2026-01-01"]}), []) is None


def test_build_donut_filters_negative_and_zero_values():
    """build_donut debe ignorar valores <= 0 para no distorsionar arcos en SVG."""
    from components.charts.pie_donut import build_donut

    labels = ["SP500", "Berkshire", "Trade Republic", "Efectivo", "Te Deben"]
    values = [0.0, 0.0, -143.13, 6.35, 780.51]
    colors = ["#64748B", "#2563EB", "#F59E0B", "#854D0E", "#EA580C"]

    fig = build_donut(labels, values, colors)
    assert fig is not None
    # Solo deben quedar las partidas positivas: Efectivo (6.35) y Te Deben (780.51)
    pie_trace = fig.data[0]
    assert list(pie_trace.labels) == ["Efectivo", "Te Deben"]
    assert list(pie_trace.values) == [6.35, 780.51]


def test_build_donut_all_non_positive_returns_none():
    """Si no hay ningún valor positivo, build_donut debe retornar None sin romper."""
    from components.charts.pie_donut import build_donut

    labels = ["SP500", "Trade Republic"]
    values = [0.0, -50.0]
    colors = ["#64748B", "#F59E0B"]

    assert build_donut(labels, values, colors) is None
