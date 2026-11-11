"""
test_roundup.py — Tests para `services/roundup.py`.

Cubre el cálculo de céntimos, el filtrado de gastos elegibles
(excluye Saveback/RoundUp/Cashback de TR + ya-redondeados) y la
construcción de la partida doble 112 Hucha ← 121 TR.
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from constants import CUENTA_BERKSHIRE, CUENTA_TR
from services.roundup import (
    build_roundup_journal_rows,
    get_pending_roundups,
    round_up_cents,
)

# ──────────────────────────────────────────────
# round_up_cents
# ──────────────────────────────────────────────


class TestRoundUpCents:
    @pytest.mark.parametrize(
        "amount, expected",
        [
            (15.30, 0.70),
            (0.01, 0.99),
            (99.99, 0.01),
            (1.50, 0.50),
            (3.33, 0.67),
        ],
    )
    def test_partial_amounts(self, amount, expected):
        assert round_up_cents(amount) == pytest.approx(expected, abs=1e-9)

    def test_already_integer(self):
        assert round_up_cents(15.00) == 0.0
        assert round_up_cents(100.0) == 0.0

    def test_zero_or_negative(self):
        assert round_up_cents(0.0) == 0.0
        assert round_up_cents(-5.50) == 0.0


# ──────────────────────────────────────────────
# get_pending_roundups
# ──────────────────────────────────────────────


def _make_row(fecha, cuenta, debe, desc="", cat="", haber=None):
    return {
        "Fecha": pd.Timestamp(fecha),
        "Nº Cuenta": str(cuenta),
        "Cuenta": f"Acc {cuenta}",
        "Categoría": cat,
        "Debe": debe,
        "Haber": haber,
        "Descripción": desc,
    }


def _pair(fecha, gasto_cuenta, importe, pago_cuenta, desc="", cat=""):
    """Construye un par de partida doble: Debe gasto / Haber pago."""
    return [
        _make_row(fecha, gasto_cuenta, importe, desc=desc, cat=cat),
        _make_row(fecha, pago_cuenta, None, desc=desc, cat=cat, haber=importe),
    ]


class TestGetPendingRoundups:
    def test_empty_input(self):
        df = pd.DataFrame()
        result = get_pending_roundups(df)
        assert result.empty

    def test_basic_eligible_when_paid_in_cash(self):
        """Gastos pagados desde 111 (Cartera, NO TR) → elegibles."""
        rows = _pair("2026-05-20", "51", 15.30, "111", desc="Mercadona") + _pair(
            "2026-05-21", "52", 3.45, "111", desc="Starbucks"
        )
        result = get_pending_roundups(pd.DataFrame(rows))
        assert len(result) == 2
        assert set(result["Céntimos"].round(2)) == {0.70, 0.55}

    def test_excludes_when_paid_via_tr(self):
        """REGLA CLAVE: gastos pagados desde 121 (TR) NO son elegibles
        — TR ya aplica su Round-Up automático."""
        rows = _pair("2026-05-20", "51", 15.30, "121", desc="Mercadona TR") + _pair(  # excluido
            "2026-05-20", "52", 3.45, "111", desc="Café Cash"
        )  # incluido
        result = get_pending_roundups(pd.DataFrame(rows))
        assert len(result) == 1
        assert result.iloc[0]["Descripción"] == "Café Cash"

    def test_excludes_paid_from_hucha(self):
        """112 (Hucha) NO es TR — debería incluirse (es ahorro físico)."""
        rows = _pair("2026-05-20", "51", 7.30, "112", desc="Compra Hucha")
        result = get_pending_roundups(pd.DataFrame(rows))
        assert len(result) == 1

    def test_excludes_integers(self):
        rows = _pair("2026-05-20", "51", 15.00, "111", desc="Pago exacto") + _pair(
            "2026-05-20", "51", 7.50, "111", desc="Mitad"
        )
        result = get_pending_roundups(pd.DataFrame(rows))
        assert len(result) == 1
        assert "Pago exacto" not in result["Descripción"].values

    def test_excludes_passive_categories(self):
        """Gastos con Saveback/RoundUp/Cashback en cat o desc no se muestran."""
        rows = (
            _pair("2026-05-20", "51", 15.30, "111", desc="Compra normal")
            + _pair("2026-05-20", "51", 15.30, "111", desc="Saveback BRK")
            + _pair("2026-05-20", "51", 7.45, "111", desc="X", cat="Round Up")
            + _pair("2026-05-20", "51", 7.45, "111", desc="Cashback Amazon")
            + _pair("2026-05-20", "51", 7.45, "111", desc="Interest Payment")
            + _pair("2026-05-20", "51", 7.45, "111", desc="Bonificación enero")
        )
        result = get_pending_roundups(pd.DataFrame(rows))
        assert len(result) == 1
        assert result.iloc[0]["Descripción"] == "Compra normal"

    def test_excludes_non_expense_accounts(self):
        rows = (
            _pair("2026-05-20", "51", 15.30, "111", desc="Gasto OK")
            + _pair("2026-05-20", "44", 1500.30, "121", desc="Sueldo")  # no gasto
            + _pair("2026-05-20", "31", 200.30, "121", desc="Capital")  # no gasto
        )
        result = get_pending_roundups(pd.DataFrame(rows))
        assert len(result) == 1
        assert result.iloc[0]["Descripción"] == "Gasto OK"

    def test_filters_old_dates(self):
        old_date = (pd.Timestamp.today() - pd.Timedelta(days=120)).strftime("%Y-%m-%d")
        recent_date = (pd.Timestamp.today() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        rows = _pair(old_date, "51", 15.30, "111", desc="Antiguo") + _pair(
            recent_date, "51", 15.30, "111", desc="Reciente"
        )
        result = get_pending_roundups(pd.DataFrame(rows), days_back=60)
        assert len(result) == 1
        assert result.iloc[0]["Descripción"] == "Reciente"

    def test_excludes_already_done_fingerprints(self):
        rows = _pair("2026-05-20", "51", 15.30, "111", desc="A") + _pair(
            "2026-05-20", "51", 7.45, "111", desc="B"
        )
        df = pd.DataFrame(rows)
        all_pending = get_pending_roundups(df)
        done = {all_pending.iloc[0]["Fingerprint"]}
        result = get_pending_roundups(df, already_done_fingerprints=done)
        assert len(result) == 1
        assert result.iloc[0]["Fingerprint"] not in done

    def test_respects_limit(self):
        rows: list[dict] = []
        for i in range(50):
            rows.extend(_pair("2026-05-20", "51", 5.30 + i * 0.01, "111", desc=f"Op{i}"))
        result = get_pending_roundups(pd.DataFrame(rows), limit=5)
        assert len(result) == 5

    def test_negative_debe_excluded(self):
        rows = (
            _pair("2026-05-20", "51", 0.0, "111", desc="cero")
            + _pair("2026-05-20", "51", -5.30, "111", desc="neg")
            + _pair("2026-05-20", "51", 5.30, "111", desc="ok")
        )
        result = get_pending_roundups(pd.DataFrame(rows))
        assert len(result) == 1
        assert result.iloc[0]["Descripción"] == "ok"


# ──────────────────────────────────────────────
# build_roundup_journal_rows
# ──────────────────────────────────────────────


class TestBuildRoundupJournalRows:
    def test_returns_double_entry(self):
        rows = build_roundup_journal_rows(0.70, "Mercadona")
        assert len(rows) == 2

    def test_debe_to_berkshire(self):
        """REGLA: el destino es BRK (141), no Hucha."""
        rows = build_roundup_journal_rows(0.55, "Café")
        debe_row, haber_row = rows
        assert debe_row[1] == CUENTA_BERKSHIRE
        assert debe_row[4] == 0.55
        assert debe_row[5] is None

    def test_haber_from_tr(self):
        rows = build_roundup_journal_rows(0.55, "Café")
        _, haber_row = rows
        assert haber_row[1] == CUENTA_TR
        assert haber_row[5] == 0.55
        assert haber_row[4] is None

    def test_description_contains_source(self):
        rows = build_roundup_journal_rows(0.70, "Mercadona Sant Cugat")
        assert "Mercadona Sant Cugat" in rows[0][6]
        assert "Round-up artificial" in rows[0][6]

    def test_categoria_is_marker(self):
        rows = build_roundup_journal_rows(0.70, "X")
        assert rows[0][3] == "Round-up Manual"
        assert rows[1][3] == "Round-up Manual"

    def test_no_quantity_when_price_missing(self):
        """Sin precio BRK → descripción sin metadata `quantity:`."""
        rows = build_roundup_journal_rows(0.70, "X", brk_price_eur=None)
        assert "quantity" not in rows[0][6].lower()

    def test_no_quantity_when_price_zero(self):
        rows = build_roundup_journal_rows(0.70, "X", brk_price_eur=0.0)
        assert "quantity" not in rows[0][6].lower()

    def test_quantity_appended_when_price_given(self):
        """Con precio → quantity = cents / precio."""
        rows = build_roundup_journal_rows(0.70, "X", brk_price_eur=350.0)
        # qty esperada = 0.70 / 350 = 0.002000
        assert "quantity: 0.002000" in rows[0][6]
        # Ambas filas comparten la misma descripción (par de partida doble)
        assert rows[0][6] == rows[1][6]
