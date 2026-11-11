"""test_cost_per_day.py — Tests para `services/cost_per_day.py`."""

from datetime import timedelta

import pandas as pd
import pytest

from services.cost_per_day import (
    DIAS_MES,
    HORAS_JORNADA,
    compute_cost_per_day,
    estimate_sueldo_hora_from_ingresos,
)


def _make_row(fecha, cuenta_num, debe, cuenta_name="Gastos Test", desc=""):
    return {
        "Fecha": pd.Timestamp(fecha),
        "Nº Cuenta": str(cuenta_num),
        "Cuenta": cuenta_name,
        "Categoría": "",
        "Debe": debe,
        "Haber": 0.0,
        "Descripción": desc,
    }


def _income_row(fecha, cuenta_num, haber, name="Ingreso"):
    return {
        "Fecha": pd.Timestamp(fecha),
        "Nº Cuenta": str(cuenta_num),
        "Cuenta": name,
        "Categoría": "",
        "Debe": 0.0,
        "Haber": haber,
        "Descripción": "",
    }


class TestComputeCostPerDay:
    def test_empty_returns_empty(self):
        df = compute_cost_per_day(pd.DataFrame(), sueldo_hora_eur=10.0)
        assert df.empty

    def test_zero_sueldo_returns_empty(self):
        rows = [_make_row("2026-05-20", "52", 3.0, "Gastos Cafeína")]
        df = compute_cost_per_day(pd.DataFrame(rows), sueldo_hora_eur=0.0)
        assert df.empty

    def test_basic_calculation(self):
        """3 meses lookback: 90€ gastados → 30€/mes → 1€/día → 0.1h/día @ 10€/h."""
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=10), "52", 30.0, "Gastos Cafeína"),
            _make_row(today - timedelta(days=40), "52", 30.0, "Gastos Cafeína"),
            _make_row(today - timedelta(days=70), "52", 30.0, "Gastos Cafeína"),
        ]
        result = compute_cost_per_day(pd.DataFrame(rows), sueldo_hora_eur=10.0, months_lookback=3)
        assert len(result) == 1
        row = result.iloc[0]
        assert row["€/mes"] == pytest.approx(30.0, abs=0.01)
        assert row["€/día"] == pytest.approx(30.0 / DIAS_MES, abs=0.01)
        assert row["Horas/día"] == pytest.approx(30.0 / DIAS_MES / 10.0, abs=0.01)
        assert row["Horas/mes"] == pytest.approx(3.0, abs=0.1)
        assert row["Jornadas/mes"] == pytest.approx(3.0 / HORAS_JORNADA, abs=0.01)

    def test_sorted_by_eur_mes_desc(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=10), "52", 5.0, "Cat Pequeña"),
            _make_row(today - timedelta(days=10), "51", 100.0, "Cat Grande"),
        ]
        result = compute_cost_per_day(pd.DataFrame(rows), sueldo_hora_eur=10.0, months_lookback=3)
        assert result.iloc[0]["Categoría"] == "Cat Grande"

    def test_excludes_non_expenses(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=10), "52", 30.0, "Cafeína"),
            _income_row(today - timedelta(days=10), "44", 1500.0),
            _make_row(today - timedelta(days=10), "121", 50.0, "TR"),
        ]
        result = compute_cost_per_day(pd.DataFrame(rows), sueldo_hora_eur=10.0, months_lookback=3)
        assert len(result) == 1
        assert result.iloc[0]["Categoría"] == "Cafeína"

    def test_excludes_passive_rows(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=10), "52", 30.0, "Cafeína", desc="Café"),
            _make_row(today - timedelta(days=10), "52", 30.0, "Cafeína", desc="Saveback BRK"),
        ]
        result = compute_cost_per_day(pd.DataFrame(rows), sueldo_hora_eur=10.0, months_lookback=3)
        # Solo cuenta el "Café" (30€), no el Saveback
        assert result.iloc[0]["€/mes"] == pytest.approx(30.0 / 3.0, abs=0.01)

    def test_lookback_window(self):
        """Gastos fuera de la ventana lookback no cuentan."""
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=10), "52", 30.0, "Cafeína"),
            _make_row(today - timedelta(days=200), "52", 999.0, "Cafeína"),
        ]
        result = compute_cost_per_day(pd.DataFrame(rows), sueldo_hora_eur=10.0, months_lookback=3)
        # Solo se considera el de 30€
        assert result.iloc[0]["€/mes"] == pytest.approx(10.0, abs=0.01)


class TestEstimateSueldoHora:
    def test_empty_returns_zero(self):
        assert estimate_sueldo_hora_from_ingresos(pd.DataFrame()) == 0.0

    def test_basic(self):
        today = pd.Timestamp.today().normalize()
        rows = [_income_row(today - timedelta(days=10), "44", 1600.0)]
        # 1600€ / 3 meses = 533.33/mes... pero solo hay 1 ingreso así
        # que dividir entre 3 meses dará 533.33 / 160h = 3.33 €/h
        result = estimate_sueldo_hora_from_ingresos(
            pd.DataFrame(rows), months_lookback=3, horas_mes_referencia=160.0
        )
        assert result == pytest.approx(1600.0 / 3.0 / 160.0, abs=0.05)

    def test_combines_ingresos_43_and_44(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _income_row(today - timedelta(days=10), "44", 800.0),
            _income_row(today - timedelta(days=10), "43", 800.0),
        ]
        result = estimate_sueldo_hora_from_ingresos(
            pd.DataFrame(rows), months_lookback=1, horas_mes_referencia=160.0
        )
        # 1600€/mes / 160h = 10€/h
        assert result == pytest.approx(10.0, abs=0.05)

    def test_no_income_returns_zero(self):
        today = pd.Timestamp.today().normalize()
        rows = [_make_row(today - timedelta(days=10), "52", 30.0)]
        assert estimate_sueldo_hora_from_ingresos(pd.DataFrame(rows)) == 0.0
