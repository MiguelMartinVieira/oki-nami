"""tabs.inversiones.montecarlo — Proyección Monte Carlo de patrimonio.

Simula la evolución del patrimonio a N años con retornos mensuales normales
y una aportación periódica constante. Renderiza un fan chart con bandas
P10-P90 / P25-P75 y la mediana, más 3 metric cards con los percentiles
finales.
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from components.charts import build_monte_carlo_fan
from components.metric_card import render_metric_card
from config.paths import BASE_DIR
from services.analytics import simulate_monte_carlo

# Color de acento del módulo — coherente con el sub-tab "📊 Inversiones".
_ACCENT = "#7E57C2"


def render_montecarlo(df_diario: pd.DataFrame, portfolio: dict) -> None:
    """Renderiza el bloque Monte Carlo."""
    # Eliminar titulo y markdown inicial

    start_default = float(portfolio.get("total_patrimonio", 0.0))

    suggested_contrib = _load_mc_contrib()

    # ── Contenedores de visualización ──
    chart_container = st.container()
    cards_container = st.container()
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    inputs_container = st.container()

    # ── Inputs (abajo) ──
    with inputs_container:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            start_value = st.number_input(
                "Patrimonio inicial (€)",
                min_value=0.0,
                value=round(start_default, 2),
                step=100.0,
                format="%.2f",
                key="mc_start",
            )
        with c2:
            contrib = st.number_input(
                "Aportación mensual (€)",
                min_value=0.0,
                value=float(suggested_contrib),
                step=25.0,
                format="%.2f",
                key="mc_contrib",
                help="Aportación constante al final de cada mes. Valor guardado y recuperado automáticamente.",
            )
            if contrib != suggested_contrib:
                _save_mc_contrib(float(contrib))
        with c3:
            ret_pct = st.slider(
                "Rentabilidad anual esperada (%)",
                min_value=1.0,
                max_value=15.0,
                value=8.0,
                step=0.5,
                key="mc_return",
            )
        with c4:
            sigma_pct = st.slider(
                "Volatilidad anual (σ %)",
                min_value=2.0,
                max_value=35.0,
                value=15.0,
                step=0.5,
                key="mc_sigma",
                help="Desviación típica anual de los retornos. S&P 500 ≈ 15–18 %; "
                "cartera más defensiva ≈ 10–12 %.",
            )

        years = st.slider(
            "Horizonte (años)",
            min_value=1,
            max_value=40,
            value=20,
            step=1,
            key="mc_years",
        )

    # ── Simulación ──
    sim = simulate_monte_carlo(
        start_value=float(start_value),
        monthly_contribution=float(contrib),
        annual_return_pct=float(ret_pct),
        annual_volatility_pct=float(sigma_pct),
        years=int(years),
        n_sims=1000,
        seed=42,  # determinista para que recargas idénticas den lo mismo
    )

    # ── Fan chart ──
    with chart_container:
        fig = build_monte_carlo_fan(sim, accent_color=_ACCENT)
        st.plotly_chart(fig, width="stretch")

    # ── 3 Metric cards: P10, P50, P90 finales ──
    final = sim["final"]
    total_aportado = sim["total_aportado"]
    median = final["p50"]
    ganancia_media = median - total_aportado

    with cards_container:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(
                render_metric_card(
                    "Escenario pesimista (P10)",
                    f"{final['p10']:,.0f} €",
                    color="#9575CD",
                    subtitle="10 % de los escenarios quedan por debajo",
                    extra_class="portfolio-analysis-card",
                ),
                unsafe_allow_html=True,
            )
        with col_b:
            st.markdown(
                render_metric_card(
                    "Escenario mediano (P50)",
                    f"{median:,.0f} €",
                    color=_ACCENT,
                    subtitle=f"Mediana — ganancia neta esperada: {ganancia_media:,.0f} €",
                    extra_class="portfolio-analysis-card",
                ),
                unsafe_allow_html=True,
            )
        with col_c:
            st.markdown(
                render_metric_card(
                    "Escenario optimista (P90)",
                    f"{final['p90']:,.0f} €",
                    color="#B388FF",
                    subtitle="10 % de los escenarios quedan por encima",
                    extra_class="portfolio-analysis-card",
                ),
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


MC_CONFIG_FILE = BASE_DIR.parent / ".cache" / "montecarlo_config.json"


def _load_mc_contrib() -> float:
    """Carga la aportación mensual almacenada en caché o devuelve 50.0 por defecto."""
    if MC_CONFIG_FILE.exists():
        try:
            with open(MC_CONFIG_FILE, encoding="utf-8") as f:
                return float(json.load(f).get("aportacion_mensual", 50.0))
        except Exception:
            pass
    return 50.0


def _save_mc_contrib(value: float) -> None:
    """Guarda la aportación mensual configurada por el usuario."""
    try:
        MC_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MC_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"aportacion_mensual": value}, f)
    except Exception:
        pass
