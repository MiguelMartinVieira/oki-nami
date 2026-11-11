"""Tests para services/accounting.py — cálculos contables."""

import pandas as pd
import pytest

from services.accounting import (
    calc_ahorro,
    calc_ahorro_ytd,
    calc_bokatas_detalle,
    calc_bokatas_saldo,
    calc_brk_shares,
    calc_gastos_ingresos,
    calc_metalico_fisico,
    calc_padres_saldo,
    calc_padres_total,
    calc_tr_cash,
    calc_vanguard_shares,
    filter_cuenta,
    get_color_smooth,
)


def _make_diario(rows: list[dict]) -> pd.DataFrame:
    """Helper: crea un DataFrame tipo Diario con las columnas mínimas."""
    defaults = {
        "Fecha": "2026-03-25",
        "Nº Cuenta": "121",
        "Cuenta": "",
        "Categoría": "",
        "Debe": 0.0,
        "Haber": 0.0,
        "Descripción": "",
    }
    data = []
    for row in rows:
        r = {**defaults, **row}
        data.append(r)
    df = pd.DataFrame(data)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Debe"] = pd.to_numeric(df["Debe"])
    df["Haber"] = pd.to_numeric(df["Haber"])
    return df


class TestCalcMetalicoFisico:
    def test_empty(self):
        assert calc_metalico_fisico(pd.DataFrame()) == 0.0

    def test_cartera_y_hucha(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "111", "Debe": 50, "Haber": 0},
                {"Nº Cuenta": "112", "Debe": 100, "Haber": 20},
                {"Nº Cuenta": "121", "Debe": 500, "Haber": 0},  # No debe contar
            ]
        )
        assert calc_metalico_fisico(df) == pytest.approx(130.0)

    def test_only_haber(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "111", "Debe": 0, "Haber": 30},
            ]
        )
        assert calc_metalico_fisico(df) == pytest.approx(-30.0)


class TestCalcBokatas:
    def test_saldo_basico(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "133", "Haber": 100, "Debe": 0},
                {"Nº Cuenta": "133", "Haber": 0, "Debe": 30},
            ]
        )
        assert calc_bokatas_saldo(df) == pytest.approx(70.0)

    def test_saldo_nunca_negativo(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "133", "Haber": 10, "Debe": 50},
            ]
        )
        assert calc_bokatas_saldo(df) == 0.0

    def test_detalle(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "133", "Haber": 200, "Debe": 0},
                {"Nº Cuenta": "133", "Haber": 0, "Debe": 75},
            ]
        )
        det = calc_bokatas_detalle(df)
        assert det["total_recibido"] == pytest.approx(200.0)
        assert det["total_pagado"] == pytest.approx(75.0)
        assert det["saldo_disponible"] == pytest.approx(125.0)


class TestCalcPadres:
    def test_saldo_pendiente(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "131", "Debe": 50, "Haber": 0},
                {"Nº Cuenta": "131", "Debe": 0, "Haber": 20},
            ]
        )
        s = calc_padres_saldo(df)
        assert s["saldo_pendiente"] == pytest.approx(30.0)


class TestCalcTrCash:
    def test_descuenta_bokatas(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "121", "Debe": 500, "Haber": 0},
                {"Nº Cuenta": "133", "Haber": 100, "Debe": 0},  # ONG
            ]
        )
        # TR bruto = 500, bokatas = 100 → personal = 400
        assert calc_tr_cash(df) == pytest.approx(400.0)


class TestCalcBrkShares:
    def test_base_only(self):
        from constants import BASE_ACCIONES_BRK

        df = pd.DataFrame(columns=["Fecha", "Nº Cuenta", "Debe", "Haber", "Descripción"])
        assert calc_brk_shares(df) == pytest.approx(BASE_ACCIONES_BRK)

    def test_with_extra_purchase(self):
        from constants import BASE_ACCIONES_BRK, BRK_CHECKPOINT_DATE

        df = _make_diario(
            [
                {
                    "Nº Cuenta": "141",
                    "Fecha": "2026-12-31",  # Posterior al checkpoint
                    "Debe": 50,
                    "Descripción": "Buy BRK-B quantity: 0.100000",
                },
                {
                    "Nº Cuenta": "141",
                    "Fecha": "2020-01-01",  # Anterior al checkpoint, no debe sumar
                    "Debe": 50,
                    "Descripción": "quantity: 99.0",
                },
            ]
        )
        assert calc_brk_shares(df) == pytest.approx(BASE_ACCIONES_BRK + 0.1)

    def test_regex_formats(self):
        from constants import BASE_ACCIONES_BRK

        df = _make_diario(
            [
                {"Nº Cuenta": "141", "Fecha": "2026-12-31", "Descripción": "quantity:0,5"},  # Coma
                {"Nº Cuenta": "141", "Fecha": "2026-12-31", "Descripción": "QUANTITY: 0.5"},  # Caps
            ]
        )
        assert calc_brk_shares(df) == pytest.approx(BASE_ACCIONES_BRK + 1.0)

    def test_with_sale_subtracts_shares(self):
        from constants import BASE_ACCIONES_BRK

        df = _make_diario(
            [
                {
                    "Nº Cuenta": "141",
                    "Fecha": "2026-06-01",
                    "Debe": 200,
                    "Haber": 0,
                    "Categoría": "Compra Berkshire",
                    "Descripción": "quantity: 1.0",
                },
                {
                    "Nº Cuenta": "141",
                    "Fecha": "2026-10-06",
                    "Debe": 0,
                    "Haber": 150,
                    "Categoría": "Venta Berkshire",
                    "Descripción": "quantity: 0.4",
                },
            ]
        )
        # 1.0 comprada - 0.4 vendida = +0.6 neta
        assert calc_brk_shares(df) == pytest.approx(BASE_ACCIONES_BRK + 0.6)


class TestCalcVanguardShares:
    def test_basico(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "142", "Descripción": "quantity: 10.5"},
                {"Nº Cuenta": "142", "Descripción": "quantity: 2.5"},
                {"Nº Cuenta": "111", "Descripción": "quantity: 100.0"},  # Otra cuenta
            ]
        )
        assert calc_vanguard_shares(df) == pytest.approx(13.0)

    def test_with_sale_subtracts_shares(self):
        df = _make_diario(
            [
                {
                    "Nº Cuenta": "142",
                    "Debe": 500,
                    "Haber": 0,
                    "Categoría": "Compra Vanguard",
                    "Descripción": "quantity: 10.0",
                },
                {
                    "Nº Cuenta": "142",
                    "Debe": 0,
                    "Haber": 200,
                    "Categoría": "Venta Vanguard",
                    "Descripción": "quantity: 3.5",
                },
            ]
        )
        assert calc_vanguard_shares(df) == pytest.approx(6.5)


class TestCalcPadresTotal:
    def test_total_both_accounts(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "131", "Debe": 100, "Haber": 20},  # Pendiente 80
                {"Nº Cuenta": "132", "Debe": 50, "Haber": 0},  # Pendiente 50
                {"Nº Cuenta": "134", "Debe": 70, "Haber": 10},  # Pendiente 60
                {"Nº Cuenta": "133", "Debe": 0, "Haber": 500},  # Bokatas ONG -> NO DEBE CONTAR
            ]
        )
        # 80 + 50 + 60 = 190
        assert calc_padres_total(df) == pytest.approx(190.0)

    def test_as_of_date(self):
        import datetime

        df = _make_diario(
            [
                {"Fecha": "2026-01-01", "Nº Cuenta": "131", "Debe": 100},
                {"Fecha": "2026-02-01", "Nº Cuenta": "131", "Debe": 200},
            ]
        )
        limit = datetime.date(2026, 1, 15)
        assert calc_padres_total(df, as_of_date=limit) == pytest.approx(100.0)


class TestFilterCuenta:
    def test_filters_correctly(self):
        df = _make_diario(
            [
                {"Nº Cuenta": "111", "Debe": 10},
                {"Nº Cuenta": "121", "Debe": 20},
                {"Nº Cuenta": "111", "Debe": 30},
            ]
        )
        result = filter_cuenta(df, "111")
        assert len(result) == 2

    def test_strips_whitespace(self):
        df = _make_diario([{"Nº Cuenta": " 111 ", "Debe": 10}])
        result = filter_cuenta(df, "111")
        assert len(result) == 1


class TestCalcAhorro:
    def test_positive_savings(self):
        ahorro, tasa = calc_ahorro(1000, 600)
        assert ahorro == pytest.approx(400)
        assert tasa == pytest.approx(40.0)

    def test_zero_income(self):
        _, tasa = calc_ahorro(0, 100)
        assert tasa == 0.0


class TestGetColorSmooth:
    def test_returns_hsl(self):
        color = get_color_smooth(25.0)
        assert color.startswith("hsl(")

    def test_clamps_low(self):
        color = get_color_smooth(-100)
        assert "hsl(0" in color  # clamped to -20 → hue=0

    def test_clamps_high(self):
        color = get_color_smooth(200)
        assert "hsl(140" in color  # clamped to 50 → hue=140


class TestCalcPortfolioSummary:
    """
    Regresión: el patrimonio debe usar las participaciones *dinámicas* de Vanguard
    (`calc_vanguard_shares`) y no la constante `PARTICIPACIONES_VANGUARD`.
    """

    def test_uses_dynamic_vanguard_shares(self, monkeypatch):
        from services import accounting as acc

        df = _make_diario(
            [
                # Vanguard: 2 compras → 12.0 + 3.5 = 15.5 participaciones dinámicas
                {
                    "Nº Cuenta": "142",
                    "Debe": 1000.0,
                    "Descripción": "Compra inicial quantity: 12.0",
                },
                {"Nº Cuenta": "142", "Debe": 400.0, "Descripción": "Aporte quantity: 3.5"},
                # BRK: una sola compra
                {
                    "Nº Cuenta": "141",
                    "Fecha": "2026-04-01",
                    "Debe": 200.0,
                    "Descripción": "Compra BRK quantity: 0.05",
                },
                # Algo de cash en TR
                {"Nº Cuenta": "121", "Debe": 800.0, "Haber": 0.0},
            ]
        )

        # Stub de precios para no llamar a Yahoo
        monkeypatch.setattr(
            acc,
            "get_yahoo_price",
            lambda t: {
                "0P00012SJB.F": 100.0,  # Vanguard
                "BRK-B": 400.0,  # USD
                "EUR=X": 0.9,  # USD→EUR
            }.get(t, 0.0),
            raising=False,
        )

        # Patch get_yahoo_price en el módulo de origen también
        from data import yahoo as yahoo_mod

        monkeypatch.setattr(
            yahoo_mod,
            "get_yahoo_price",
            lambda t: {
                "0P00012SJB.F": 100.0,
                "BRK-B": 400.0,
                "EUR=X": 0.9,
            }.get(t, 0.0),
        )

        summary = acc.calc_portfolio_summary(df, metalico_fisico=50.0)

        # Vanguard: 15.5 part. × 100 € = 1550 €
        assert summary["acciones_vanguard"] == pytest.approx(15.5)
        assert summary["valor_fondo_eur"] == pytest.approx(1550.0)

        # BRK: BASE + 0.05 → valor = (BASE+0.05) * 400 * 0.9
        from constants import BASE_ACCIONES_BRK

        expected_brk_eur = (BASE_ACCIONES_BRK + 0.05) * 400.0 * 0.9
        assert summary["valor_brk_eur"] == pytest.approx(expected_brk_eur)

        # Total = Vanguard + BRK + TR cash + metálico
        # TR cash = 800 (no hay bokatas en este df)
        expected_total = 1550.0 + expected_brk_eur + 800.0 + 50.0
        assert summary["total_patrimonio"] == pytest.approx(expected_total)

    def test_does_not_fallback_to_static_constant(self, monkeypatch):
        """Si NO hay quantity: en la descripción, el valor debe ser 0, NO la constante histórica."""
        from services import accounting as acc

        # PARTICIPACIONES_VANGUARD se eliminó de logic.py en la limpieza
        # 2026-05-23; preservamos su valor histórico aquí solo para verificar
        # que el cálculo dinámico NO reproduce ese fallback.
        _LEGACY_STATIC_SHARES = 15.62463

        df = _make_diario(
            [
                # Compra Vanguard pero sin metadata `quantity:` → calc_vanguard_shares devuelve 0
                {"Nº Cuenta": "142", "Debe": 1000.0, "Descripción": "Compra sin quantity"},
            ]
        )

        monkeypatch.setattr(
            acc, "get_yahoo_price", lambda t: 100.0 if t == "0P00012SJB.F" else 0.0, raising=False
        )
        from data import yahoo as yahoo_mod

        monkeypatch.setattr(
            yahoo_mod, "get_yahoo_price", lambda t: 100.0 if t == "0P00012SJB.F" else 0.0
        )

        summary = acc.calc_portfolio_summary(df, metalico_fisico=0.0)
        # Las participaciones dinámicas son 0 → valor 0
        assert summary["acciones_vanguard"] == pytest.approx(0.0)
        assert summary["valor_fondo_eur"] == pytest.approx(0.0)
        # Si se hubiese usado la constante, el valor sería PARTICIPACIONES_VANGUARD * 100
        # Verificamos explícitamente que NO ha caído al fallback
        assert summary["valor_fondo_eur"] != pytest.approx(_LEGACY_STATIC_SHARES * 100.0)


class TestCalcAhorroYtd:
    def test_calc_ahorro_ytd_includes_inversiones_after_history_start(self):
        from constants import HISTORY_START_DATE

        df = _make_diario(
            [
                # Anterior a HISTORY_START_DATE (no debe contar)
                {"Fecha": "2026-03-18", "Nº Cuenta": "141", "Debe": 8000.0, "Haber": 0.0},
                # A partir de HISTORY_START_DATE
                {"Fecha": "2026-03-20", "Nº Cuenta": "400", "Haber": 1000.0, "Debe": 0.0},
                {"Fecha": "2026-03-22", "Nº Cuenta": "500", "Debe": 300.0, "Haber": 0.0},
                {"Fecha": "2026-03-25", "Nº Cuenta": "141", "Debe": 500.0, "Haber": 0.0},
            ]
        )
        # Ahorro = Inversiones post-19Mar (500) = 500
        assert calc_ahorro_ytd(df) == pytest.approx(500.0)

    def test_calc_ahorro_ytd_subtracts_sales(self):
        df = _make_diario(
            [
                {"Fecha": "2026-03-25", "Nº Cuenta": "141", "Debe": 1000.0, "Haber": 0.0},
                {"Fecha": "2026-04-10", "Nº Cuenta": "141", "Debe": 0.0, "Haber": 400.0},
            ]
        )
        # 1000 - 400 = 600 net savings
        assert calc_ahorro_ytd(df) == pytest.approx(600.0)
