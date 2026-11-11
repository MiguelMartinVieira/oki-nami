"""tabs.inversiones.summary — Sub-tab "📊 Inversiones" (visión global + comparativa rebased)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import build_normalized_comparison
from components.metric_card import render_metric_card
from constants import (
    COLOR_BERKSHIRE,
    COLOR_SP500,
    CUENTA_BERKSHIRE,
    TICKER_BRK,
    TICKER_VWRL_PROXY,
)
from data.yahoo import get_yahoo_history


def render_summary_tab(df_diario: pd.DataFrame, portfolio: dict, metrics: dict) -> None:
    total_invested_portfolio = metrics["total_invested_portfolio"]
    if total_invested_portfolio <= 0:
        st.info("No hay inversiones registradas aún.")
        return

    valor_brk_eur = portfolio["valor_brk_eur"]
    valor_fondo_eur = portfolio["valor_fondo_eur"]
    valor_cartera_pura = metrics["valor_cartera_pura"]
    pnl_portfolio = metrics["pnl_portfolio"]
    pnl_pct_portfolio = metrics["pnl_pct_portfolio"]
    pnl_color_p = metrics["pnl_color_portfolio"]
    pnl_sign_p = "+" if pnl_portfolio >= 0 else ""
    peso_brk = metrics["peso_brk"]
    peso_van = metrics["peso_van"]

    cp1, cp2, cp3, cp4, cp5 = st.columns(5)
    with cp1:
        st.markdown(
            render_metric_card(
                "Total Invertido",
                f"{total_invested_portfolio:,.2f} €",
                color="#7E57C2",
                subtitle="BRK + Vanguard combinado",
                extra_class="portfolio-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cp2:
        st.markdown(
            render_metric_card(
                "Valor Actual",
                f"{valor_cartera_pura:,.2f} €",
                color="#7E57C2",
                subtitle="Activos combinados",
                extra_class="portfolio-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cp3:
        pnl_values_p = (
            f'<div style="font-size:1.6rem; font-weight:600; color:#7E57C2; margin:4px 0 0;">'
            f"{pnl_sign_p}{pnl_portfolio:,.2f} €</div>"
            f'<div style="font-size:1.6rem; font-weight:600; color:#7E57C2; margin:0;">'
            f"{pnl_sign_p}{pnl_pct_portfolio:.2f}%</div>"
        )
        try:
            from services.demo_data import is_cipher_mode, scramble_numbers

            if is_cipher_mode():
                pnl_values_p = scramble_numbers(pnl_values_p)
        except Exception:
            pass
        st.markdown(
            render_metric_card(
                "P&L Total",
                "",
                bg_color=pnl_color_p,
                extra_html=pnl_values_p,
                extra_class="portfolio-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cp4:
        st.markdown(
            render_metric_card(
                "Berkshire Hathaway",
                f"{valor_brk_eur:,.2f} €",
                color=COLOR_BERKSHIRE,
                subtitle=f"Peso: {peso_brk:.2f}% de la cartera",
                extra_class="portfolio-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cp5:
        st.markdown(
            render_metric_card(
                "Vanguard SP500",
                f"{valor_fondo_eur:,.2f} €",
                color=COLOR_SP500,
                subtitle=f"Peso: {peso_van:.2f}% de la cartera",
                extra_class="portfolio-analysis-card",
            ),
            unsafe_allow_html=True,
        )

    # ── BRK vs S&P 500 normalizado ──
    st.markdown("---")

    df_brk_first = df_diario[df_diario["Nº Cuenta"] == CUENTA_BERKSHIRE].copy()
    df_brk_first["Fecha"] = pd.to_datetime(df_brk_first["Fecha"], errors="coerce")
    df_brk_first = df_brk_first[df_brk_first["Debe"] > 0].dropna(subset=["Fecha"])

    if df_brk_first.empty:
        st.info("Necesitas al menos una compra de BRK para ver la comparativa rebased.")
        return

    first_brk_date = df_brk_first["Fecha"].min()
    days_norm = max((pd.Timestamp.today() - first_brk_date).days + 5, 30)
    df_brk_norm = get_yahoo_history(TICKER_BRK, days=days_norm)
    df_sp_norm = get_yahoo_history(TICKER_VWRL_PROXY, days=days_norm)
    fig_cmp = build_normalized_comparison(
        df_brk_norm,
        df_sp_norm,
        start_date=first_brk_date,
        label_a="BRK-B",
        label_b="S&P 500 (VWRL.AS)",
        color_a=COLOR_BERKSHIRE,
        color_b=COLOR_SP500,
    )
    if fig_cmp:
        st.plotly_chart(fig_cmp, width="stretch")
    else:
        st.info("No hay suficientes datos de Yahoo para construir la comparativa.")
