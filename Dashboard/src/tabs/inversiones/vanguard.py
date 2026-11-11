"""tabs.inversiones.vanguard — Sub-tab "📈 Vanguard SP500"."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import build_dca_tracker
from components.fiscal_sim import render_fiscal_section
from components.metric_card import render_metric_card
from constants import (
    COLOR_SP500,
    HISTORY_START_DATE,
    TICKER_VANGUARD,
    VANGUARD_HISTORICAL_GAIN,
)
from data.yahoo import get_yahoo_history


def render_vanguard_tab(df_diario: pd.DataFrame, portfolio: dict, metrics: dict) -> None:
    df_van = metrics["df_van"]
    total_invested = metrics["total_invested_van"]
    valor_fondo_eur = portfolio["valor_fondo_eur"]
    acciones_vanguard = portfolio["acciones_vanguard"]
    precio_fondo = portfolio["precio_fondo"]
    precio_medio = metrics["precio_medio_van"]
    pnl_total = metrics["pnl_van"]
    pnl_pct = metrics["pnl_pct_van"]
    pnl_color = metrics["pnl_color_van"]
    pnl_sign = "+" if pnl_total >= 0 else ""

    cv1, cv2, cv3, cv4, cv5 = st.columns(5)
    with cv1:
        st.markdown(
            render_metric_card(
                "Total Invertido",
                f"{total_invested:,.2f} €",
                color=COLOR_SP500,
                subtitle="Inversión inicial Openbank",
                extra_class="vanguard-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cv2:
        st.markdown(
            render_metric_card(
                "Valor Actual",
                f"{valor_fondo_eur:,.2f} €",
                color=COLOR_SP500,
                subtitle=f"{acciones_vanguard:.5f} participaciones",
                extra_class="vanguard-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cv3:
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
                extra_class="vanguard-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cv4:
        st.markdown(
            render_metric_card(
                "Precio Medio",
                f"{precio_medio:,.2f} €",
                color=COLOR_SP500,
                subtitle="Coste medio por participación",
                extra_class="vanguard-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with cv5:
        st.markdown(
            render_metric_card(
                "Precio Actual",
                f"{precio_fondo:,.2f} €",
                color=COLOR_SP500,
                subtitle=f"Ticker: {TICKER_VANGUARD}",
                extra_class="vanguard-analysis-card",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    days = max((pd.Timestamp.today() - pd.to_datetime(HISTORY_START_DATE)).days + 10, 30)
    df_vanguard_hist = get_yahoo_history(TICKER_VANGUARD, days=days)

    # VANGUARD_HISTORICAL_GAIN representa las plusvalías previas acumuladas antes de la
    # fecha de corte/checkpoint en Openbank. Pasamos cost_adjustment=VANGUARD_HISTORICAL_GAIN
    # para que la línea de precio medio del gráfico DCA y los lotes FIFO coincidan exactamente
    # con la tarjeta superior (Precio Medio = 282.25 € en lugar del importe bruto 504.04 €).
    fig_dca = build_dca_tracker(
        df_van,
        df_vanguard_hist,
        usd_to_eur=1.0,
        line_color=COLOR_SP500,
        yaxis_title="Precio (€/participación)",
        is_usd=False,
        cost_adjustment=VANGUARD_HISTORICAL_GAIN,
    )
    if fig_dca:
        st.plotly_chart(fig_dca, width="stretch")
    else:
        st.info(
            "No hay suficientes datos de transacciones o de Yahoo Finance para mostrar el DCA Tracker."
        )

    st.markdown("---")
    render_fiscal_section(
        asset_name="Vanguard SP500",
        asset_color=COLOR_SP500,
        total_invested=total_invested,
        valor_actual=valor_fondo_eur,
        extra_class="vanguard-analysis-card",
        df_account=df_van,
        precio_actual_eur=precio_fondo,
        cost_adjustment=VANGUARD_HISTORICAL_GAIN,
    )
