"""tabs.inversiones.brk — Sub-tab "📈 Berkshire Hathaway"."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import build_dca_tracker
from components.fiscal_sim import render_fiscal_section
from components.metric_card import render_metric_card
from constants import (
    COLOR_BERKSHIRE,
    HISTORY_START_DATE,
    TICKER_BRK,
)
from data.yahoo import get_yahoo_history


def render_brk_tab(df_diario: pd.DataFrame, portfolio: dict, metrics: dict) -> None:
    df_brk = metrics["df_brk"]
    total_invested = metrics["total_invested_brk"]
    valor_brk_eur = portfolio["valor_brk_eur"]
    acciones_brk = portfolio["acciones_brk"]
    precio_brk_usd = portfolio["precio_brk_usd"]
    usd_to_eur = portfolio["usd_to_eur"]
    precio_actual_eur = metrics["precio_brk_eur"]
    precio_medio_eur = metrics["precio_medio_brk"]
    pnl_total = metrics["pnl_brk"]
    pnl_pct = metrics["pnl_pct_brk"]
    pnl_color = metrics["pnl_color_brk"]
    pnl_sign = "+" if pnl_total >= 0 else ""
    n_operaciones = metrics["n_operaciones_brk"]

    cb1, cb2, cb3, cb4, cb5 = st.columns(5)
    with cb1:
        st.markdown(
            render_metric_card(
                "Total Invertido",
                f"{total_invested:,.2f} €",
                color=COLOR_BERKSHIRE,
                subtitle=f"{n_operaciones} operaciones",
                extra_class="brk-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cb2:
        st.markdown(
            render_metric_card(
                "Valor Actual",
                f"{valor_brk_eur:,.2f} €",
                color=COLOR_BERKSHIRE,
                subtitle=f"{acciones_brk:.6f} acciones",
                extra_class="brk-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cb3:
        pnl_values = (
            f'<div style="font-size:1.6rem; font-weight:600; color:white; margin:4px 0 0;">'
            f"{pnl_sign}{pnl_total:,.2f} €</div>"
            f'<div style="font-size:1.6rem; font-weight:600; color:white; margin:0;">'
            f"{pnl_sign}{pnl_pct:.2f}%</div>"
        )
        st.markdown(
            render_metric_card(
                "P&L Total",
                "",
                bg_color=pnl_color,
                extra_html=pnl_values,
                extra_class="brk-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cb4:
        st.markdown(
            render_metric_card(
                "Precio Medio",
                f"{precio_medio_eur:,.2f} €",
                color=COLOR_BERKSHIRE,
                subtitle="Coste medio por acción",
                extra_class="brk-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cb5:
        st.markdown(
            render_metric_card(
                "Precio Actual",
                f"{precio_actual_eur:,.2f} €",
                color=COLOR_BERKSHIRE,
                subtitle=f"{precio_brk_usd:,.2f} $ × {usd_to_eur:.4f}",
                extra_class="brk-analysis-card",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    days = max((pd.Timestamp.today() - pd.to_datetime(HISTORY_START_DATE)).days + 10, 30)
    df_brk_hist = get_yahoo_history(TICKER_BRK, days=days)
    fig_dca = build_dca_tracker(
        df_brk,
        df_brk_hist,
        usd_to_eur,
        line_color=COLOR_BERKSHIRE,
        yaxis_title="Precio (€/acción)",
        is_usd=True,
        show_lumpsum=True,
    )
    if fig_dca:
        st.plotly_chart(fig_dca, width="stretch")
    else:
        st.info(
            "No hay suficientes datos de transacciones o de Yahoo Finance para mostrar el DCA Tracker."
        )

    st.markdown("---")
    render_fiscal_section(
        asset_name="Berkshire Hathaway",
        asset_color=COLOR_BERKSHIRE,
        total_invested=total_invested,
        valor_actual=valor_brk_eur,
        extra_class="brk-analysis-card",
        df_account=df_brk,
        precio_actual_eur=precio_actual_eur,
    )
