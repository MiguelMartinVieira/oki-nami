"""
test_demo_data.py — Tests para `services/demo_data.py`.

Cubre:
  - `is_demo_mode` lee la env var en todos los formatos válidos
  - `generate_demo_diario` produce un DataFrame válido (cols, partida doble cuadrada)
  - Determinismo: misma semilla → mismo dataset
  - `block_writes_in_demo` solo bloquea cuando demo está activo
  - Integración: `get_diario` / `get_saldos` / `append_to_diario` respetan demo mode
"""

import os
from unittest.mock import patch

import pandas as pd
import pytest

from services.demo_data import (
    block_writes_in_demo,
    generate_demo_diario,
    generate_demo_saldos,
    is_demo_mode,
)

# ──────────────────────────────────────────────
# is_demo_mode
# ──────────────────────────────────────────────


class TestIsDemoMode:
    @pytest.mark.parametrize("val", ["true", "TRUE", "True", "1", "yes", "Yes", "on"])
    def test_truthy_values(self, val, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", val)
        assert is_demo_mode() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", "off", "", "random"])
    def test_falsy_values(self, val, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", val)
        assert is_demo_mode() is False

    def test_unset(self, monkeypatch):
        monkeypatch.delenv("DEMO_MODE", raising=False)
        assert is_demo_mode() is False


# ──────────────────────────────────────────────
# generate_demo_diario
# ──────────────────────────────────────────────


class TestGenerateDemoDiario:
    def test_returns_dataframe(self):
        df = generate_demo_diario()
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_has_required_columns(self):
        df = generate_demo_diario()
        for col in ("Fecha", "Nº Cuenta", "Cuenta", "Categoría", "Debe", "Haber", "Descripción"):
            assert col in df.columns, f"falta {col}"

    def test_double_entry_balances(self):
        """Cada fila tiene SOLO Debe o SOLO Haber (no ambos)."""
        df = generate_demo_diario()
        # En partida doble: Debe>0 XOR Haber>0
        debe = df["Debe"].fillna(0) > 0
        haber = df["Haber"].fillna(0) > 0
        # Filas con ambos a la vez = 0
        ambos = debe & haber
        assert ambos.sum() == 0

    def test_total_debe_equals_total_haber(self):
        """Invariante de partida doble: suma global de Debe = suma global de Haber."""
        df = generate_demo_diario()
        total_debe = df["Debe"].fillna(0).sum()
        total_haber = df["Haber"].fillna(0).sum()
        assert total_debe == pytest.approx(total_haber, abs=0.01)

    def test_deterministic_with_same_seed(self):
        df1 = generate_demo_diario(seed=42)
        df2 = generate_demo_diario(seed=42)
        # Comparamos por valores serializados (DataFrames pueden tener tipos sutiles)
        assert df1.shape == df2.shape
        assert df1["Debe"].fillna(0).sum() == df2["Debe"].fillna(0).sum()

    def test_different_seed_different_data(self):
        df1 = generate_demo_diario(seed=42)
        df2 = generate_demo_diario(seed=999)
        # No deberían tener exactamente la misma forma (alta probabilidad)
        assert df1["Debe"].fillna(0).sum() != pytest.approx(df2["Debe"].fillna(0).sum())

    def test_includes_investment_accounts(self):
        df = generate_demo_diario()
        cuentas = set(df["Nº Cuenta"].unique())
        assert "141" in cuentas  # Berkshire
        assert "142" in cuentas  # Vanguard
        assert "44" in cuentas  # Sueldo
        assert "121" in cuentas  # TR

    def test_investment_rows_have_quantity_metadata(self):
        """Las filas de BRK/Vanguard deben llevar `quantity: X` para que
        el cálculo dinámico de acciones funcione en demo."""
        df = generate_demo_diario()
        df_inv = df[df["Nº Cuenta"].isin(["141", "142"]) & (df["Debe"] > 0)]
        # Al menos un buen porcentaje debe tener quantity
        with_qty = df_inv["Descripción"].str.contains("quantity:", case=False).sum()
        assert with_qty > 0

    def test_covers_expected_date_range(self):
        df = generate_demo_diario(days_back=180)
        fechas = pd.to_datetime(df["Fecha"])
        rango = (fechas.max() - fechas.min()).days
        assert 170 <= rango <= 181  # ~6 meses

    def test_smaller_days_back_smaller_dataset(self):
        small = generate_demo_diario(days_back=30)
        large = generate_demo_diario(days_back=180)
        assert len(small) < len(large)


# ──────────────────────────────────────────────
# generate_demo_saldos
# ──────────────────────────────────────────────


class TestGenerateDemoSaldos:
    def test_columns_present(self):
        df = generate_demo_saldos()
        # Debe tener las columnas que get_saldos espera
        for col in ("CUENTAS", "Tipo cuenta para resumen", "Saldo para resumen"):
            assert col in df.columns

    def test_contains_key_accounts(self):
        df = generate_demo_saldos()
        cuentas = set(df["CUENTAS"].astype(str))
        assert "121" in cuentas
        assert "141" in cuentas


# ──────────────────────────────────────────────
# block_writes_in_demo
# ──────────────────────────────────────────────


class TestBlockWritesInDemo:
    def test_blocks_when_active(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "true")
        assert block_writes_in_demo("test_op") is True

    def test_does_not_block_when_inactive(self, monkeypatch):
        monkeypatch.delenv("DEMO_MODE", raising=False)
        assert block_writes_in_demo("test_op") is False


# ──────────────────────────────────────────────
# Integración con gsheets
# ──────────────────────────────────────────────


class TestGsheetsIntegration:
    def test_get_diario_returns_demo_when_active(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "true")
        from data.gsheets import get_diario

        get_diario.clear()
        df = get_diario()
        # En demo NUNCA tocamos GSheets ni CSV → siempre hay data
        assert not df.empty
        assert "Nº Cuenta" in df.columns
        get_diario.clear()

    def test_get_saldos_returns_demo_when_active(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "true")
        from data.gsheets import get_saldos

        get_saldos.clear()
        df = get_saldos()
        assert not df.empty
        assert "CUENTAS" in df.columns
        get_saldos.clear()

    def test_append_to_diario_blocked_in_demo(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "true")
        from data.gsheets import append_to_diario

        result = append_to_diario([["2026-05-23", "51", None, "X", 10.0, None, "test"]])
        assert result is False


# ──────────────────────────────────────────────
# Demo offline completa: saldos, precios, histórico
# ──────────────────────────────────────────────


class TestDemoOffline:
    def test_quantities_never_in_scientific_notation(self):
        # "quantity: 8.9e-05" se leía como 8.9 acciones (bug real del generador)
        from services.utils import extract_quantity

        df = generate_demo_diario()
        rows = df[df["Descripción"].str.contains("quantity", case=False)]
        assert not rows["Descripción"].str.contains(r"e-\d", regex=True).any()
        brk = rows[rows["Nº Cuenta"] == "141"]
        # Ninguna compra semanal de 60 € ni un saveback llega a 1 acción de BRK
        assert brk["Descripción"].map(extract_quantity).max() < 1.0

    def test_saldos_match_diario(self):
        df = generate_demo_diario()
        saldos = generate_demo_saldos().set_index("CUENTAS")["Saldo para resumen"]
        tr = df[df["Nº Cuenta"] == "121"]
        assert saldos["121"] == pytest.approx(tr["Debe"].sum() - tr["Haber"].sum(), abs=0.01)
        assert saldos["121"] > 0

    def test_price_history_is_deterministic_and_ends_at_spot(self):
        from services.demo_data import demo_price, demo_price_history

        a = demo_price_history("BRK-B", 30)
        b = demo_price_history("BRK-B", 30)
        pd.testing.assert_frame_equal(a, b)
        assert len(a) == 31
        assert a["Price"].iloc[-1] == pytest.approx(demo_price("BRK-B"))
        assert (a["Price"] > 0).all()

    def test_historico_is_daily_and_consistent(self):
        from services.demo_data import generate_demo_historico

        h = generate_demo_historico()
        assert not h.empty
        assert h["Fecha"].is_monotonic_increasing
        parts = h[["Efectivo Fisico", "Efectivo TR", "BRK Value", "Vanguard Value", "Te Deben"]]
        assert (parts.sum(axis=1) - h["Total"]).abs().max() < 0.05
        assert (h["Total"] > 0).all()

    def test_yahoo_not_called_in_demo(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "true")
        from data import yahoo

        yahoo.get_yahoo_price.clear()
        yahoo.get_yahoo_history.clear()
        with patch.object(yahoo, "_fetch_yahoo_json", side_effect=AssertionError("network")):
            assert yahoo.get_yahoo_price("BRK-B") > 0
            assert not yahoo.get_yahoo_history("BRK-B", 10).empty
        yahoo.get_yahoo_price.clear()
        yahoo.get_yahoo_history.clear()

    def test_historico_writes_blocked_in_demo(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEMO_MODE", "true")
        from data import gsheets

        target = tmp_path / "hist.csv"
        monkeypatch.setattr(gsheets, "CSV_HISTORICO", str(target))
        assert gsheets.append_to_historico([["2026-01-01", 1, 2, 3, 4, 0, 10]]) is False
        assert not target.exists()

    def test_cipher_mode_is_independent_of_demo(self, monkeypatch):
        from services.demo_data import is_cipher_mode

        monkeypatch.setenv("CIPHER_MODE", "true")
        monkeypatch.delenv("DEMO_MODE", raising=False)
        assert is_cipher_mode() is True
        assert is_demo_mode() is False
