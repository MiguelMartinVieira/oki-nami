"""
test_montecarlo.py — Tests para simulate_monte_carlo y calc_cumulative_opportunity_cost.
"""

import math

import numpy as np
import pandas as pd
import pytest

from services.analytics import calc_cumulative_opportunity_cost, simulate_monte_carlo

# ──────────────────────────────────────────────
# simulate_monte_carlo
# ──────────────────────────────────────────────


class TestSimulateMonteCarlo:
    def test_shapes(self):
        sim = simulate_monte_carlo(
            start_value=1_000.0,
            monthly_contribution=100.0,
            annual_return_pct=8.0,
            annual_volatility_pct=15.0,
            years=10,
            n_sims=200,
            seed=42,
        )
        assert sim["paths"].shape == (200, 10 * 12 + 1)
        assert sim["months"].shape == (10 * 12 + 1,)
        for k in ("p10", "p25", "p50", "p75", "p90"):
            assert k in sim["percentiles"]
            assert k in sim["final"]

    def test_zero_volatility_is_deterministic(self):
        """Con σ=0, todos los paths deben ser iguales y crecer monótonamente."""
        sim = simulate_monte_carlo(
            start_value=1_000.0,
            monthly_contribution=0.0,
            annual_return_pct=12.0,
            annual_volatility_pct=0.0,
            years=5,
            n_sims=10,
            seed=0,
        )
        paths = sim["paths"]
        # Todos los paths idénticos (σ=0)
        assert np.allclose(paths, paths[0])
        # Crecen monótonamente
        assert np.all(np.diff(paths[0]) >= 0)
        # Aproximación: capital final = 1000 × (1.12)^5
        expected = 1_000.0 * (1.12**5)
        assert math.isclose(paths[0, -1], expected, rel_tol=1e-3)

    def test_seed_reproduces(self):
        a = simulate_monte_carlo(1_000, 50, 8, 15, 5, n_sims=50, seed=123)
        b = simulate_monte_carlo(1_000, 50, 8, 15, 5, n_sims=50, seed=123)
        assert np.array_equal(a["paths"], b["paths"])

    def test_paths_no_negatives(self):
        """Los paths se clampan a 0; con σ grande podríamos ver el clamp activarse."""
        sim = simulate_monte_carlo(100, 0, 0, 80, 30, n_sims=200, seed=42)
        assert (sim["paths"] >= 0).all()

    def test_median_grows_with_higher_return(self):
        low = simulate_monte_carlo(1_000, 100, 4, 10, 10, n_sims=300, seed=42)
        high = simulate_monte_carlo(1_000, 100, 10, 10, 10, n_sims=300, seed=42)
        assert high["final"]["p50"] > low["final"]["p50"]

    def test_total_aportado_correcto(self):
        sim = simulate_monte_carlo(1_000, 200, 8, 15, 3, n_sims=10, seed=1)
        # 1_000 + 200 × 36 meses
        assert math.isclose(sim["total_aportado"], 1_000 + 200 * 36)


# ──────────────────────────────────────────────
# calc_cumulative_opportunity_cost
# ──────────────────────────────────────────────


class TestCumulativeOpportunity:
    def _df(self):
        today = pd.Timestamp.today()
        return pd.DataFrame(
            {
                "Fecha": pd.to_datetime(
                    [
                        today - pd.Timedelta(days=10),
                        today - pd.Timedelta(days=30),
                        today - pd.Timedelta(days=400),
                    ]
                ),  # fuera de ventana
                "Nº Cuenta": ["51", "52", "53"],
                "Cuenta": ["Gastos Comida", "Gastos Cafeína", "Gastos Alcohol & Friends"],
                "Debe": [50.0, 30.0, 999.0],
                "Haber": [0.0, 0.0, 0.0],
            }
        )

    def test_filtra_ventana_y_solo_5x(self):
        df = self._df()
        res = calc_cumulative_opportunity_cost(
            df, rent_anual_pct=8.0, years_horizon=10, months_lookback=6
        )
        # El 999 (hace 400 días) debe quedar fuera
        assert res["total_gastado"] == 80.0
        assert res["factor"] == pytest.approx((1.08) ** 10, rel=1e-6)
        assert res["oportunidad_total"] == pytest.approx(80.0 * (1.08**10), rel=1e-6)
        assert res["ganancia_neta"] == pytest.approx(
            res["oportunidad_total"] - res["total_gastado"], rel=1e-6
        )

    def test_top_categorias_ordenadas(self):
        df = self._df()
        res = calc_cumulative_opportunity_cost(df, rent_anual_pct=8.0, years_horizon=10)
        # Comida (50) > Cafeína (30)
        assert res["top_categorias"][0]["categoria"] == "Gastos Comida"
        assert res["top_categorias"][1]["categoria"] == "Gastos Cafeína"

    def test_filter_account(self):
        df = self._df()
        res = calc_cumulative_opportunity_cost(
            df,
            rent_anual_pct=8.0,
            years_horizon=10,
            filter_account="Gastos Cafeína",
        )
        assert res["total_gastado"] == 30.0

    def test_empty_df_returns_zeros(self):
        res = calc_cumulative_opportunity_cost(pd.DataFrame(), rent_anual_pct=8.0, years_horizon=10)
        assert res["total_gastado"] == 0.0
        assert res["oportunidad_total"] == 0.0
        assert res["top_categorias"] == []


# ──────────────────────────────────────────────
# build_monte_carlo_fan (Chart rendering)
# ──────────────────────────────────────────────


class TestMonteCarloChart:
    def test_build_monte_carlo_fan_renders_figure(self):
        """Verifica que build_monte_carlo_fan genere una figura de Plotly sin lanzar NameError u otras excepciones."""
        import plotly.graph_objects as go

        from components.charts.line import build_monte_carlo_fan

        sim = simulate_monte_carlo(
            start_value=1_000.0,
            monthly_contribution=100.0,
            annual_return_pct=8.0,
            annual_volatility_pct=15.0,
            years=5,
            n_sims=50,
            seed=42,
        )
        fig = build_monte_carlo_fan(sim, accent_color="#6366F1")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 5  # p10, p25, p50, p75, p90 traces
