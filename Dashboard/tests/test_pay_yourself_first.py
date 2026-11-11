"""
Tests para las funciones de analítica "Pay Yourself First" y correlación de gasto oportunista
introducidas en services.analytics.
"""

import pandas as pd
import pytest

from services.analytics import (
    calc_balance_spending_correlation,
    calc_pay_yourself_first_stats,
)


def _diario(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "Fecha": "2026-05-15",
        "Nº Cuenta": "121",
        "Cuenta": "",
        "Categoría": "",
        "Debe": 0.0,
        "Haber": 0.0,
        "Descripción": "",
    }
    if not rows:
        return pd.DataFrame(columns=list(defaults.keys()))
    data = [{**defaults, **r} for r in rows]
    df = pd.DataFrame(data)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Debe"] = pd.to_numeric(df["Debe"])
    df["Haber"] = pd.to_numeric(df["Haber"])
    return df


class TestPayYourselfFirstStats:
    def test_empty_dataframe(self):
        avg_days, lags = calc_pay_yourself_first_stats(_diario([]))
        assert avg_days == 0.0
        assert lags == []

    def test_no_incomes_or_no_investments(self):
        # Solo ingresos
        df_only_inc = _diario(
            [
                {
                    "Fecha": "2026-05-01",
                    "Nº Cuenta": "41",
                    "Haber": 1000.0,
                    "Descripción": "Sueldo",
                },
            ]
        )
        avg_days, lags = calc_pay_yourself_first_stats(df_only_inc)
        assert avg_days == 0.0
        assert lags == []

        # Solo inversiones
        df_only_inv = _diario(
            [
                {
                    "Fecha": "2026-05-02",
                    "Nº Cuenta": "141",
                    "Debe": 200.0,
                    "Descripción": "BRK purchase",
                },
            ]
        )
        avg_days, lags = calc_pay_yourself_first_stats(df_only_inv)
        assert avg_days == 0.0
        assert lags == []

    def test_calculation_normal(self):
        # Ingreso el 2026-05-01 y primera inversión el 2026-05-03 (lag = 2)
        # Ingreso el 2026-05-10 y primera inversión el 2026-05-15 (lag = 5)
        # Inversión intermedia el 2026-05-05 no cuenta como primer emparejamiento para el segundo ingreso
        df = _diario(
            [
                {
                    "Fecha": "2026-05-01",
                    "Nº Cuenta": "41",
                    "Haber": 1000.0,
                    "Descripción": "Sueldo 1",
                },
                {
                    "Fecha": "2026-05-03",
                    "Nº Cuenta": "141",
                    "Debe": 200.0,
                    "Descripción": "Compra BRK 1",
                },
                {
                    "Fecha": "2026-05-05",
                    "Nº Cuenta": "142",
                    "Debe": 100.0,
                    "Descripción": "Compra Vanguard",
                },
                {
                    "Fecha": "2026-05-10",
                    "Nº Cuenta": "43",
                    "Haber": 500.0,
                    "Descripción": "Sueldo 2",
                },
                {
                    "Fecha": "2026-05-15",
                    "Nº Cuenta": "141",
                    "Debe": 300.0,
                    "Descripción": "Compra BRK 2",
                },
            ]
        )
        avg_days, lags = calc_pay_yourself_first_stats(df)
        # Promedio: (2 días + 5 días) / 2 = 3.5 días
        assert avg_days == pytest.approx(3.5)
        assert len(lags) == 2
        assert lags[0]["days"] == 2
        assert lags[1]["days"] == 5
        assert lags[0]["income_amount"] == 1000.0
        assert lags[0]["investment_amount"] == 200.0


class TestBalanceSpendingCorrelation:
    def test_empty_dataframe(self):
        corr, df_corr = calc_balance_spending_correlation(_diario([]))
        assert corr == 0.0
        assert df_corr.empty

    def test_insufficient_data(self):
        # Menos de 10 días de datos
        df = _diario(
            [
                {"Fecha": "2026-05-01", "Nº Cuenta": "121", "Debe": 1000.0},
                {"Fecha": "2026-05-02", "Nº Cuenta": "51", "Debe": 50.0},
            ]
        )
        corr, df_corr = calc_balance_spending_correlation(df)
        assert corr == 0.0
        assert len(df_corr) == 2

    def test_positive_correlation_trend(self):
        # 15 días. Generamos saldo creciente y gastos crecientes para forzar correlación positiva.
        rows = []
        for i in range(1, 16):
            fecha = f"2026-05-{i:02d}"
            # Saldo TR (cuenta 121) se incrementa cada día (Debe > 0 aumenta saldo acumulado)
            rows.append({"Fecha": fecha, "Nº Cuenta": "121", "Debe": 100.0, "Haber": 0.0})
            # Gasto (cuenta 51) se incrementa cada día
            rows.append({"Fecha": fecha, "Nº Cuenta": "51", "Debe": float(i * 10), "Haber": 0.0})

        df = _diario(rows)
        corr, df_corr = calc_balance_spending_correlation(df)
        assert corr > 0.5  # Debe haber una correlación positiva muy alta
        assert not df_corr.empty
        assert "balance" in df_corr.columns
        assert "spend" in df_corr.columns
        # balance en el día 15 debe ser 1500
        assert df_corr.iloc[-1]["balance"] == pytest.approx(1500.0)
