"""
test_subscriptions.py — Tests para `services/subscriptions.py`.

Cubre:
  - Detección de patrones mensuales / semanales / anuales
  - Normalización de descripciones
  - Filtrado por número mínimo de ocurrencias
  - Cálculo de coste anual estimado
  - Cálculo de próximo pago previsto
  - Casos límite (sin recurrencias, intervalos irregulares)
"""

from datetime import timedelta

import pandas as pd
import pytest

from services.subscriptions import (
    _classify_interval,
    _normalize_desc,
    detect_subscriptions,
)


def _make_row(fecha, debe, desc, cuenta_num="56", cat_name="Gastos Test"):
    return {
        "Fecha": pd.Timestamp(fecha),
        "Nº Cuenta": str(cuenta_num),
        "Cuenta": cat_name,
        "Categoría": "",
        "Debe": debe,
        "Haber": 0.0,
        "Descripción": desc,
    }


# ──────────────────────────────────────────────
# _normalize_desc
# ──────────────────────────────────────────────


class TestNormalizeDesc:
    def test_lowercase(self):
        assert _normalize_desc("NETFLIX SUBSCRIPTION") == "netflix subscription"

    def test_strips_digits(self):
        assert "1234" not in _normalize_desc("Netflix 1234 ref")

    def test_strips_punctuation(self):
        assert "," not in _normalize_desc("Netflix, Inc.")
        assert "." not in _normalize_desc("Netflix, Inc.")

    def test_collapses_whitespace(self):
        assert _normalize_desc("Net   flix    sub") == "net flix sub"

    def test_truncates_to_30_chars(self):
        long_desc = "Netflix " * 20
        assert len(_normalize_desc(long_desc)) <= 30

    def test_empty(self):
        assert _normalize_desc("") == ""
        assert _normalize_desc(None) == ""

    def test_same_subscription_different_refs_same_fp(self):
        """Netflix con código de transacción diferente → mismo fingerprint."""
        fp1 = _normalize_desc("Netflix 49382 ref")
        fp2 = _normalize_desc("Netflix 12345 ref")
        assert fp1 == fp2


# ──────────────────────────────────────────────
# _classify_interval
# ──────────────────────────────────────────────


class TestClassifyInterval:
    @pytest.mark.parametrize(
        "days, expected_label",
        [
            (7, "Semanal"),
            (30, "Mensual"),
            (90, "Trimestral"),
            (365, "Anual"),
            (31, "Mensual"),
            (29, "Mensual"),
        ],
    )
    def test_recognized_intervals(self, days, expected_label):
        result = _classify_interval(days)
        assert result is not None
        assert result[0] == expected_label

    @pytest.mark.parametrize("days", [3, 15, 50, 200, 500])
    def test_irregular_returns_none(self, days):
        assert _classify_interval(days) is None

    def test_annualization_factor(self):
        assert _classify_interval(7)[1] == 52.0
        assert _classify_interval(30)[1] == 12.0
        assert _classify_interval(90)[1] == 4.0
        assert _classify_interval(365)[1] == 1.0


# ──────────────────────────────────────────────
# detect_subscriptions
# ──────────────────────────────────────────────


class TestDetectSubscriptions:
    def test_empty(self):
        result = detect_subscriptions(pd.DataFrame())
        assert result.empty
        # Columnas presentes aunque vacío
        assert "Nombre" in result.columns

    def test_detects_monthly_subscription(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=90), 12.99, "Netflix subscription"),
            _make_row(today - timedelta(days=60), 12.99, "Netflix subscription"),
            _make_row(today - timedelta(days=30), 12.99, "Netflix subscription"),
        ]
        result = detect_subscriptions(pd.DataFrame(rows))
        assert len(result) == 1
        sub = result.iloc[0]
        assert sub["Intervalo"] == "Mensual"
        assert sub["Importe medio"] == pytest.approx(12.99, abs=0.01)
        assert sub["Ocurrencias"] == 3
        # Coste anual = 12.99 × 12
        assert sub["Coste anual est."] == pytest.approx(12.99 * 12, abs=0.05)

    def test_detects_weekly_subscription(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=21), 5.0, "Gym daily X"),
            _make_row(today - timedelta(days=14), 5.0, "Gym daily X"),
            _make_row(today - timedelta(days=7), 5.0, "Gym daily X"),
        ]
        result = detect_subscriptions(pd.DataFrame(rows))
        assert len(result) == 1
        assert result.iloc[0]["Intervalo"] == "Semanal"

    def test_detects_annual_subscription(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=730), 89.99, "Dominio anual"),
            _make_row(today - timedelta(days=365), 89.99, "Dominio anual"),
            _make_row(today - timedelta(days=3), 89.99, "Dominio anual"),
        ]
        result = detect_subscriptions(pd.DataFrame(rows), lookback_days=800)
        assert len(result) == 1
        assert result.iloc[0]["Intervalo"] == "Anual"

    def test_skips_irregular_pattern(self):
        """Cargos sin patrón regular: no se considera suscripción."""
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=100), 10.0, "Compra rara"),
            _make_row(today - timedelta(days=45), 10.0, "Compra rara"),
            _make_row(today - timedelta(days=5), 10.0, "Compra rara"),
        ]
        # Intervalos irregulares 55 y 40 días → mediana ~47 → ni mensual ni trimestral
        result = detect_subscriptions(pd.DataFrame(rows))
        assert result.empty

    def test_min_occurrences_respected(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=60), 12.99, "Netflix"),
            _make_row(today - timedelta(days=30), 12.99, "Netflix"),
        ]
        # Solo 2 ocurrencias < min_occurrences=3 → no se detecta
        result = detect_subscriptions(pd.DataFrame(rows))
        assert result.empty

    def test_proximo_pago_in_the_future(self):
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=60), 9.99, "Spotify"),
            _make_row(today - timedelta(days=30), 9.99, "Spotify"),
            _make_row(today - timedelta(days=1), 9.99, "Spotify"),
        ]
        result = detect_subscriptions(pd.DataFrame(rows))
        proximo = pd.Timestamp(result.iloc[0]["Próximo pago"]).normalize()
        # El próximo pago debe ser ~30 días después de la última
        ultima = pd.Timestamp(result.iloc[0]["Última fecha"]).normalize()
        delta = (proximo - ultima).days
        assert 25 <= delta <= 35

    def test_excludes_passive_categories(self):
        """Saveback / Round Up / Cashback no cuentan como suscripciones."""
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=60), 0.5, "Saveback BRK"),
            _make_row(today - timedelta(days=30), 0.5, "Saveback BRK"),
            _make_row(today - timedelta(days=0), 0.5, "Saveback BRK"),
        ]
        result = detect_subscriptions(pd.DataFrame(rows))
        assert result.empty

    def test_only_expenses(self):
        """Movimientos a TR (121) o ingresos (4x) se ignoran."""
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=60), 1500, "Sueldo", cuenta_num="44"),
            _make_row(today - timedelta(days=30), 1500, "Sueldo", cuenta_num="44"),
            _make_row(today - timedelta(days=0), 1500, "Sueldo", cuenta_num="44"),
        ]
        result = detect_subscriptions(pd.DataFrame(rows))
        assert result.empty

    def test_lookback_window_respected(self):
        """Pagos fuera de la ventana lookback_days no se consideran."""
        today = pd.Timestamp.today().normalize()
        rows = [
            _make_row(today - timedelta(days=400), 9.99, "Old sub"),
            _make_row(today - timedelta(days=370), 9.99, "Old sub"),
            _make_row(today - timedelta(days=340), 9.99, "Old sub"),
            _make_row(today - timedelta(days=310), 9.99, "Old sub"),
        ]
        result = detect_subscriptions(pd.DataFrame(rows), lookback_days=180)
        assert result.empty

    def test_sorted_by_annual_cost_desc(self):
        today = pd.Timestamp.today().normalize()
        rows: list[dict] = []
        # Suscripción cara
        for d in (90, 60, 30):
            rows.append(_make_row(today - timedelta(days=d), 50.0, "Sub Cara X"))
        # Suscripción barata
        for d in (90, 60, 30):
            rows.append(_make_row(today - timedelta(days=d), 5.0, "Sub Barata Y"))
        result = detect_subscriptions(pd.DataFrame(rows))
        assert len(result) == 2
        assert result.iloc[0]["Coste anual est."] > result.iloc[1]["Coste anual est."]
