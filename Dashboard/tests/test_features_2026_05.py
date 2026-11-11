"""
Tests para las funciones puras introducidas en la ronda de mejoras 2026-05-19
(items C, D, E, I, K, L, M).
"""

import pandas as pd
import pytest

from services.analytics import (
    build_fifo_lots,
    calc_meta_mensual,
    calc_real_cost,
    detect_header_alerts,
    simulate_fifo_sale,
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


class TestCalcMetaMensual:
    def test_meta_base_sin_historial(self):
        # Sin datos previos a este mes
        out = calc_meta_mensual(_diario([]), meta_anual=12000.0)
        assert out["meta_mes_base"] == pytest.approx(1000.0)
        assert out["meta_mes_objetivo"] == pytest.approx(1000.0)

    def test_catchup_aumenta_si_vienes_corto(self):
        # En el año actual, hasta el mes anterior no has ahorrado nada.
        # Con 5 meses transcurridos (mayo según fixture today), la meta acumulada esperada es 5*1000 = 5000
        # Como llevas 0 ahorrado pre-mes, este mes la meta sube a 5000
        year = pd.Timestamp.today().year
        out = calc_meta_mensual(
            _diario(
                [
                    {
                        "Fecha": f"{year}-01-10",
                        "Nº Cuenta": "51",
                        "Debe": 1000.0,
                    },  # gasto, sin ingresos
                ]
            ),
            meta_anual=12000.0,
        )
        # No podemos asumir el mes exacto, pero meta_objetivo debe ser ≥ meta_base
        assert out["meta_mes_objetivo"] >= out["meta_mes_base"]

    def test_floor_quarter_de_base(self):
        # Adelantado un montón → no baja por debajo de meta_base/4
        year = pd.Timestamp.today().year
        out = calc_meta_mensual(
            _diario(
                [
                    {"Fecha": f"{year}-01-10", "Nº Cuenta": "41", "Haber": 50000.0},
                ]
            ),
            meta_anual=12000.0,
        )
        assert out["meta_mes_objetivo"] >= 1000.0 / 4.0

    def test_meta_mensual_resta_ventas(self):
        from constants import HISTORY_START_DATE

        today = pd.Timestamp.today()
        year = today.year
        month = today.month
        rows = [
            {"Fecha": f"{year}-{month:02d}-02", "Nº Cuenta": "141", "Debe": 200.0, "Haber": 0.0},
            {"Fecha": f"{year}-{month:02d}-05", "Nº Cuenta": "141", "Debe": 0.0, "Haber": 50.0},
        ]
        history_start = pd.to_datetime(HISTORY_START_DATE)
        month_start = pd.to_datetime(f"{year}-{month:02d}-01")
        has_pre_period = (history_start + pd.Timedelta(days=5)) < month_start
        if has_pre_period:
            pre_date1 = (history_start + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            pre_date2 = (history_start + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
            rows.extend(
                [
                    {"Fecha": pre_date1, "Nº Cuenta": "141", "Debe": 1000.0, "Haber": 0.0},
                    {"Fecha": pre_date2, "Nº Cuenta": "141", "Debe": 0.0, "Haber": 300.0},
                ]
            )
        out = calc_meta_mensual(_diario(rows), meta_anual=12000.0)
        assert out["ahorro_mes"] == pytest.approx(150.0)
        if has_pre_period:
            assert out["ahorro_ytd_pre_mes"] == pytest.approx(700.0)


class TestDetectHeaderAlerts:
    def test_fondo_emergencia_bajo(self):
        df = _diario(
            [
                {"Fecha": "2026-03-01", "Nº Cuenta": "51", "Debe": 1000},
                {"Fecha": "2026-04-01", "Nº Cuenta": "51", "Debe": 1000},
            ]
        )
        alerts = detect_header_alerts(
            df_diario=df,
            df_historico=None,
            tr_cash=100.0,
            metalico_fisico=200.0,
            total_patrimonio=300.0,
        )
        assert any(a["title"].startswith("Fondo de emergencia") for a in alerts)

    def test_sin_alertas_si_todo_ok(self):
        df = _diario(
            [
                {"Fecha": "2026-03-01", "Nº Cuenta": "51", "Debe": 100},
                {"Fecha": "2026-04-01", "Nº Cuenta": "51", "Debe": 100},
            ]
        )
        alerts = detect_header_alerts(
            df_diario=df,
            df_historico=None,
            tr_cash=10000.0,
            metalico_fisico=1000.0,
            total_patrimonio=20000.0,
        )
        assert all("Fondo" not in a["title"] for a in alerts)

    def test_nuevo_maximo_patrimonio(self):
        df = _diario([{"Fecha": "2026-04-01", "Nº Cuenta": "51", "Debe": 50}])
        hist = pd.DataFrame({"Total": [1000.0, 1500.0, 2000.0]})
        alerts = detect_header_alerts(
            df_diario=df,
            df_historico=hist,
            tr_cash=10000.0,
            metalico_fisico=0.0,
            total_patrimonio=2500.0,
        )
        assert any("máximo" in a["title"].lower() for a in alerts)

    def test_categoria_sobre_gasto(self):
        # 3 meses de historial: 2 anteriores con gasto medio y 1 actual disparado
        rows = []
        for mes in (1, 2):
            rows.append(
                {
                    "Fecha": f"2026-0{mes}-15",
                    "Nº Cuenta": "51",
                    "Cuenta": "Gastos Comida",
                    "Debe": 100.0,
                }
            )
        rows.append(
            {"Fecha": "2026-03-15", "Nº Cuenta": "51", "Cuenta": "Gastos Comida", "Debe": 300.0}
        )
        df = _diario(rows)
        alerts = detect_header_alerts(
            df_diario=df,
            df_historico=None,
            tr_cash=10000.0,
            metalico_fisico=0.0,
            total_patrimonio=10000.0,
        )
        assert any("Gastos Comida" in a["title"] for a in alerts)


class TestCalcRealCost:
    def test_bruto_equivalente(self):
        res = calc_real_cost(gasto=100.0, tasa_ahorro_pct=30.0, rent_anual_pct=8.0, years=10)
        # 100 / (1 - 0.30) ≈ 142.86
        assert res["bruto_equivalente"] == pytest.approx(142.86, abs=0.01)

    def test_oportunidad_10y_al_8pct(self):
        res = calc_real_cost(gasto=100.0, tasa_ahorro_pct=30.0, rent_anual_pct=8.0, years=10)
        # 100 * 1.08^10 ≈ 215.89
        assert res["oportunidad"] == pytest.approx(215.89, abs=0.1)

    def test_tasa_negativa_clampa(self):
        # Tasa negativa → factor = 1 (no rebaja por debajo de gasto)
        res = calc_real_cost(gasto=50.0, tasa_ahorro_pct=-5.0, rent_anual_pct=0.0, years=5)
        assert res["bruto_equivalente"] == pytest.approx(50.0)
        assert res["oportunidad"] == pytest.approx(50.0)

    def test_tasa_extrema(self):
        res = calc_real_cost(gasto=10.0, tasa_ahorro_pct=99.5, rent_anual_pct=5.0, years=10)
        # Se clampa a 0.99 → 10 / 0.01 = 1000
        assert res["bruto_equivalente"] == pytest.approx(1000.0, abs=0.5)


class TestFifoLots:
    def test_construccion_y_pnl(self):
        df = _diario(
            [
                {
                    "Fecha": "2026-01-10",
                    "Nº Cuenta": "141",
                    "Debe": 100.0,
                    "Descripción": "BRK quantity: 0.50",
                },
                {
                    "Fecha": "2026-02-10",
                    "Nº Cuenta": "141",
                    "Debe": 200.0,
                    "Descripción": "BRK quantity: 1.00",
                },
            ]
        )
        lots = build_fifo_lots(df, precio_actual_eur=300.0)
        assert len(lots) == 2
        # Primer lote: 0.5 × 300 = 150 → P&L = +50 sobre coste 100
        assert lots.iloc[0]["P&L (€)"] == pytest.approx(50.0)
        # Segundo lote: 1.0 × 300 = 300 → P&L = +100 sobre coste 200
        assert lots.iloc[1]["P&L (€)"] == pytest.approx(100.0)

    def test_orden_cronologico(self):
        df = _diario(
            [
                {
                    "Fecha": "2026-03-10",
                    "Nº Cuenta": "142",
                    "Debe": 50.0,
                    "Descripción": "q quantity: 1.0",
                },
                {
                    "Fecha": "2026-01-10",
                    "Nº Cuenta": "142",
                    "Debe": 50.0,
                    "Descripción": "q quantity: 1.0",
                },
            ]
        )
        lots = build_fifo_lots(df, precio_actual_eur=100.0)
        fechas = pd.to_datetime(lots["Fecha"]).tolist()
        assert fechas == sorted(fechas)

    def test_simulate_consume_lotes(self):
        df = _diario(
            [
                {
                    "Fecha": "2026-01-10",
                    "Nº Cuenta": "141",
                    "Debe": 100.0,
                    "Descripción": "quantity: 1.0",
                },
                {
                    "Fecha": "2026-02-10",
                    "Nº Cuenta": "141",
                    "Debe": 300.0,
                    "Descripción": "quantity: 2.0",
                },
            ]
        )
        lots = build_fifo_lots(df, precio_actual_eur=200.0)
        # Valor total: 1.0*200 + 2.0*200 = 600
        sim = simulate_fifo_sale(lots, importe_venta_eur=250.0)
        # Consume primer lote (200 €) + parte del segundo (50 € → 0.25 acciones)
        assert sim["acciones_total"] == pytest.approx(1.25, abs=0.001)
        assert sim["valor_total"] == pytest.approx(250.0, abs=0.01)
        # Coste asignado: 100 (lote 1) + 300*(0.25/2.0)=37.5 = 137.5
        assert sim["coste_total"] == pytest.approx(137.5, abs=0.01)
        # Plusvalía: 250 - 137.5 = 112.5
        assert sim["plusvalia"] == pytest.approx(112.5, abs=0.01)

    def test_simulate_empty_returns_zeros(self):
        sim = simulate_fifo_sale(pd.DataFrame(), 100.0)
        assert sim["plusvalia"] == 0.0
        assert sim["lotes_consumidos"] == []

    def test_cost_adjustment_fifo(self):
        """Verifica que cost_adjustment descuenta el importe de plusvalías históricas del primer lote."""
        df = _diario(
            [
                {
                    "Fecha": "2026-03-18",
                    "Nº Cuenta": "142",
                    "Debe": 7875.44,
                    "Descripción": "quantity: 15.62463",
                }
            ]
        )
        # Con cost_adjustment = 3465.35: Coste = 4410.09 € -> Precio Medio = 282.25 €
        lots = build_fifo_lots(df, precio_actual_eur=583.35, cost_adjustment=3465.35)
        assert len(lots) == 1
        assert lots.iloc[0]["Coste (€)"] == pytest.approx(4410.09, abs=0.01)
        assert lots.iloc[0]["Precio Medio (€)"] == pytest.approx(282.25, abs=0.01)
        assert lots.iloc[0]["P&L (€)"] == pytest.approx(4704.54, abs=0.01)

    def test_cost_adjustment_dca_tracker(self):
        """Verifica que build_dca_tracker descuenta cost_adjustment del coste invertido acumulado."""
        from components.charts.line import build_dca_tracker

        df_van = _diario(
            [
                {
                    "Fecha": "2026-03-18",
                    "Nº Cuenta": "142",
                    "Debe": 7875.44,
                    "Descripción": "quantity: 15.62463",
                }
            ]
        )
        df_hist = pd.DataFrame(
            {
                "Date": ["2026-03-18", "2026-03-19"],
                "Price": [500.0, 583.35],
            }
        )
        fig = build_dca_tracker(
            df_van, df_hist, usd_to_eur=1.0, is_usd=False, cost_adjustment=3465.35
        )
        assert fig is not None
        # La traza de precio medio (modo lines) debe tener y = 282.25
        dca_trace = next(t for t in fig.data if t.name == "Precio Medio (DCA)")
        assert float(dca_trace.y[-1]) == pytest.approx(282.25, abs=0.01)
