"""tabs.inversiones — Tab Portfolio dividido en submódulos cohesivos.

`render(df_diario, metalico_fisico)` es el punto de entrada que orquesta
los submódulos especializados:

- `header.py` — sidebar de gestión + warnings + 6 metric cards superiores
- `allocation.py` — selector de series + donut/treemap + evolución (incl. modo time-lapse)
- `info.py` — Concentración, Beta, Rebalanceo, Pay Yourself First
- `brk.py` — análisis Berkshire Hathaway (cards, DCA, fiscal)
- `vanguard.py` — análisis Vanguard SP500 (cards, DCA, fiscal)
- `ops.py` — últimas operaciones e historial fundacional
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from constants import (
    COLOR_BERKSHIRE,
    COLOR_NEGATIVO,
    COLOR_POSITIVO,
    COLOR_SP500,
    CUENTA_BERKSHIRE,
    CUENTA_SP500,
    VANGUARD_HISTORICAL_GAIN,
)
from services.accounting import calc_portfolio_summary
from services.history import update_historico
from services.utils import extract_quantity

from .allocation import render_allocation
from .brk import render_brk_tab
from .header import render_sidebar_controls, render_top_cards, render_validation_warnings
from .info import render_info_tab
from .montecarlo import render_montecarlo
from .ops import render_ops_and_history
from .vanguard import render_vanguard_tab


def render(df_diario: pd.DataFrame, metalico_fisico: float) -> None:
    """Punto de entrada del tab Portfolio."""
    render_sidebar_controls(df_diario)

    # Sincronizar histórico si es necesario
    updated = update_historico(df_diario)
    if updated:
        st.toast("Historial sincronizado con éxito ✅")

    render_validation_warnings(df_diario)

    # ── Patrimonio centralizado ──
    portfolio = calc_portfolio_summary(df_diario, metalico_fisico)
    if portfolio["precio_fondo"] == 0.0 or portfolio["precio_brk_usd"] == 0.0:
        st.warning(
            "⚠️ No se pudieron obtener algunos precios de Yahoo Finance. "
            "Los valores pueden no ser exactos."
        )

    render_top_cards(portfolio, metalico_fisico, df_diario)

    # ── Allocation + Evolución ──
    render_allocation(df_diario, portfolio, metalico_fisico)

    # ── Pre-cálculos por activo ──
    metrics = _build_asset_metrics(df_diario, portfolio)

    # ── Sub-tabs ──
    st.markdown("---")
    _inject_inversiones_tabs_style()
    tab_inv, tab_brk, tab_van, tab_info = st.tabs(
        [
            "Inversiones",
            "Berkshire Hathaway",
            "Vanguard SP500",
            "Info",
        ]
    )

    with tab_inv:
        from .summary import render_summary_tab

        render_summary_tab(df_diario, portfolio, metrics)

        # ── Proyección Monte Carlo ──
        st.markdown("---")
        render_montecarlo(df_diario, portfolio)

    with tab_brk:
        render_brk_tab(df_diario, portfolio, metrics)

    with tab_van:
        render_vanguard_tab(df_diario, portfolio, metrics)

    with tab_info:
        render_info_tab(df_diario, portfolio, metrics)

    # ── Ops y Historial ──
    st.markdown("---")
    render_ops_and_history(df_diario, portfolio)


def _build_asset_metrics(df_diario: pd.DataFrame, portfolio: dict) -> dict:
    """Calcula los derivados por activo (totales invertidos, P&L, pesos)."""
    valor_fondo_eur = portfolio["valor_fondo_eur"]
    valor_brk_eur = portfolio["valor_brk_eur"]
    precio_brk_usd = portfolio["precio_brk_usd"]
    usd_to_eur = portfolio["usd_to_eur"]
    acciones_brk = portfolio["acciones_brk"]
    acciones_vanguard = portfolio["acciones_vanguard"]

    df_brk = df_diario[df_diario["Nº Cuenta"] == CUENTA_BERKSHIRE]
    df_van = df_diario[df_diario["Nº Cuenta"] == CUENTA_SP500]

    # Compras acumuladas y participaciones para Berkshire
    compras_brk = df_brk[df_brk["Debe"] > 0]
    total_bought_cost_brk = float(compras_brk["Debe"].sum())
    total_bought_shares_brk = (
        float(compras_brk["Descripción"].apply(extract_quantity).sum())
        if not compras_brk.empty
        else 0.0
    )

    if total_bought_shares_brk > 0 and acciones_brk < total_bought_shares_brk:
        precio_medio_brk = total_bought_cost_brk / total_bought_shares_brk
        total_invested_brk = acciones_brk * precio_medio_brk
    else:
        total_invested_brk = total_bought_cost_brk
        precio_medio_brk = total_invested_brk / acciones_brk if acciones_brk > 0 else 0.0

    # Compras acumuladas y participaciones para Vanguard
    compras_van = df_van[df_van["Debe"] > 0]
    total_bought_cost_van = float(compras_van["Debe"].sum()) - VANGUARD_HISTORICAL_GAIN
    total_bought_shares_van = (
        float(compras_van["Descripción"].apply(extract_quantity).sum())
        if not compras_van.empty
        else 0.0
    )

    if total_bought_shares_van > 0 and acciones_vanguard < total_bought_shares_van:
        precio_medio_van = total_bought_cost_van / total_bought_shares_van
        total_invested_van = acciones_vanguard * precio_medio_van
    else:
        total_invested_van = total_bought_cost_van
        precio_medio_van = total_invested_van / acciones_vanguard if acciones_vanguard > 0 else 0.0

    total_invested_portfolio = total_invested_brk + total_invested_van
    valor_cartera_pura = valor_brk_eur + valor_fondo_eur

    precio_brk_eur = precio_brk_usd * usd_to_eur

    pnl_brk = valor_brk_eur - total_invested_brk
    pnl_pct_brk = (pnl_brk / total_invested_brk * 100) if total_invested_brk > 0 else 0.0
    pnl_van = valor_fondo_eur - total_invested_van
    pnl_pct_van = (pnl_van / total_invested_van * 100) if total_invested_van > 0 else 0.0
    pnl_portfolio = valor_cartera_pura - total_invested_portfolio
    pnl_pct_portfolio = (
        (pnl_portfolio / total_invested_portfolio * 100) if total_invested_portfolio > 0 else 0.0
    )

    peso_brk = (valor_brk_eur / valor_cartera_pura * 100) if valor_cartera_pura > 0 else 0.0
    peso_van = (valor_fondo_eur / valor_cartera_pura * 100) if valor_cartera_pura > 0 else 0.0

    n_operaciones_brk = int(len(df_brk[df_brk["Debe"] > 0]))

    return {
        "df_brk": df_brk,
        "df_van": df_van,
        "total_invested_brk": total_invested_brk,
        "total_invested_van": total_invested_van,
        "total_invested_portfolio": total_invested_portfolio,
        "valor_cartera_pura": valor_cartera_pura,
        "precio_brk_eur": precio_brk_eur,
        "precio_medio_brk": precio_medio_brk,
        "precio_medio_van": precio_medio_van,
        "pnl_brk": pnl_brk,
        "pnl_pct_brk": pnl_pct_brk,
        "pnl_van": pnl_van,
        "pnl_pct_van": pnl_pct_van,
        "pnl_portfolio": pnl_portfolio,
        "pnl_pct_portfolio": pnl_pct_portfolio,
        "peso_brk": peso_brk,
        "peso_van": peso_van,
        "n_operaciones_brk": n_operaciones_brk,
        "pnl_color_brk": COLOR_POSITIVO if pnl_brk >= 0 else COLOR_NEGATIVO,
        "pnl_color_van": COLOR_POSITIVO if pnl_van >= 0 else COLOR_NEGATIVO,
        "pnl_color_portfolio": COLOR_POSITIVO if pnl_portfolio >= 0 else COLOR_NEGATIVO,
    }


def _inject_inversiones_tabs_style() -> None:
    """Aplica colores propios a los sub-tabs del portfolio."""
    st.markdown(
        f"""
        <div id="portfolio-tabs-marker" style="display:none;"></div>
        <style>
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(1),
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(1) * {{
                color: #7E57C2 !important; font-weight: 600 !important;
            }}
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(2),
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(2) * {{
                color: {COLOR_BERKSHIRE} !important; font-weight: 600 !important;
            }}
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(3),
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(3) * {{
                color: {COLOR_SP500} !important; font-weight: 600 !important;
            }}
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(4),
            div.element-container:has(#portfolio-tabs-marker) + div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:nth-child(4) * {{
                color: #F59E0B !important; font-weight: 600 !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
