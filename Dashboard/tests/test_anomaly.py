"""
test_anomaly.py — Tests para `services/anomaly.py`.

Cubre:
  - z-score correcto sobre datos sintéticos
  - Umbral configurable
  - Filtrado de categorías con < min_samples y std == 0
  - Solo gastos (5x), excluye filas pasivas TR
"""

import pandas as pd
import pytest

from services.anomaly import compute_anomalies, make_anomaly_label


def _make_row(fecha, cuenta_num, debe, cat_name="Gastos Test", desc=""):
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
# compute_anomalies
# ──────────────────────────────────────────────


class TestComputeAnomalies:
    def test_empty_input(self):
        df = compute_anomalies(pd.DataFrame())
        assert df.empty

    def test_detects_clear_outlier(self):
        """5 importes de ~10 € + 1 de 100 €: el de 100 € es anomalía."""
        rows = [_make_row(f"2026-05-{20 + i}", "51", 10.0) for i in range(5)]
        rows.append(_make_row("2026-05-26", "51", 100.0))
        df = compute_anomalies(pd.DataFrame(rows), z_threshold=2.0, min_samples=5)
        anomalies = df[df["is_anomaly"]]
        assert len(anomalies) == 1
        assert anomalies.iloc[0]["Debe"] == 100.0
        assert anomalies.iloc[0]["z_score"] > 2.0

    def test_no_anomaly_within_threshold(self):
        """6 importes en rango estrecho: ninguno debe marcarse."""
        rows = [_make_row(f"2026-05-{20 + i}", "51", 10.0 + i * 0.5) for i in range(6)]
        df = compute_anomalies(pd.DataFrame(rows), z_threshold=2.0, min_samples=5)
        if not df.empty:
            assert df["is_anomaly"].sum() == 0

    def test_skips_categories_with_few_samples(self):
        """Categorías con < min_samples no se analizan en absoluto."""
        rows = [_make_row(f"2026-05-{20 + i}", "51", 10.0) for i in range(3)]
        rows.append(_make_row("2026-05-23", "51", 9999.0))
        df = compute_anomalies(pd.DataFrame(rows), min_samples=5)
        # < 5 samples → no entra en el resultado
        assert df.empty

    def test_skips_zero_variance_category(self):
        """Si todos los importes son iguales (std=0), no hay anomalías."""
        rows = [_make_row(f"2026-05-{20 + i}", "51", 10.0) for i in range(10)]
        df = compute_anomalies(pd.DataFrame(rows), min_samples=5)
        assert df.empty  # std=0 → categoría descartada

    def test_only_gastos_analyzed(self):
        """Ingresos (4x) y otros no aparecen en el resultado."""
        rows = [_make_row(f"2026-05-{20 + i}", "51", 10.0) for i in range(5)]
        rows.append(_make_row("2026-05-21", "51", 100.0))
        # Ruido de otras cuentas
        rows.append(_make_row("2026-05-21", "44", 1500.0, cat_name="Ingresos Sueldo"))
        rows.append(_make_row("2026-05-22", "121", 50.0, cat_name="TR"))
        df = compute_anomalies(pd.DataFrame(rows), min_samples=5)
        # Solo deben aparecer filas de la cuenta 51
        assert set(df["Nº Cuenta"]) == {"51"}

    def test_passive_rows_excluded(self):
        """Saveback / RoundUp / Cashback se excluyen del cálculo."""
        rows = [_make_row(f"2026-05-{20 + i}", "51", 10.0) for i in range(5)]
        rows.append(_make_row("2026-05-26", "51", 0.50, desc="Saveback BRK"))
        rows.append(_make_row("2026-05-27", "51", 0.30, desc="Round Up"))
        df = compute_anomalies(pd.DataFrame(rows), min_samples=5)
        # Las pasivas no deben verse aunque su Debe sea muy distinto al resto
        if not df.empty:
            assert not df["Descripción"].str.contains("Saveback|Round Up", regex=True).any()

    def test_threshold_strict_marks_fewer(self):
        """|z|>3 marca menos anomalías que |z|>2 para los mismos datos."""
        rows = [
            _make_row(f"2026-05-{i:02d}", "51", 10.0 + (1 if i % 2 == 0 else 0))
            for i in range(1, 11)
        ]
        rows.append(_make_row("2026-05-15", "51", 30.0))
        df_sens = compute_anomalies(pd.DataFrame(rows), z_threshold=2.0, min_samples=5)
        df_strict = compute_anomalies(pd.DataFrame(rows), z_threshold=10.0, min_samples=5)
        n_sens = int(df_sens["is_anomaly"].sum())
        n_strict = int(df_strict["is_anomaly"].sum())
        assert n_strict <= n_sens

    def test_stats_columns_present(self):
        rows = [_make_row(f"2026-05-{20 + i}", "51", 10.0 + i) for i in range(6)]
        df = compute_anomalies(pd.DataFrame(rows), min_samples=5)
        for col in ("cat_mean", "cat_std", "cat_count", "z_score", "is_anomaly"):
            assert col in df.columns


# ──────────────────────────────────────────────
# make_anomaly_label
# ──────────────────────────────────────────────


class TestMakeAnomalyLabel:
    def test_positive_z(self):
        assert "+" in make_anomaly_label(2.5)
        assert "⚠ inusual" in make_anomaly_label(2.5)

    def test_negative_z(self):
        label = make_anomaly_label(-3.2)
        assert "-" in label
        assert "3.2" in label

    @pytest.mark.parametrize(
        "z, expected_substr",
        [
            (2.0, "+2.0σ"),
            (3.45, "+3.5σ"),
            (-2.5, "-2.5σ"),
        ],
    )
    def test_formats(self, z, expected_substr):
        assert expected_substr in make_anomaly_label(z)
