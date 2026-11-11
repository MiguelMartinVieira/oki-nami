"""tabs.inversiones.header — Controles laterales, warnings y 6 metric cards."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_card import render_metric_card
from constants import (
    COLOR_BERKSHIRE,
    COLOR_EFECTIVO_FISICO,
    COLOR_EFECTIVO_TR,
    COLOR_SP500,
    COLOR_TE_DEBEN,
    CUENTA_BERKSHIRE,
    CUENTA_SP500,
)
from data.gsheets import get_centro_control_data


def render_sidebar_controls(df_diario: pd.DataFrame) -> None:
    """Controles laterales (ahora centralizados en el sidebar principal)."""
    pass


def render_validation_warnings(df_diario: pd.DataFrame) -> None:
    """Avisa de operaciones de inversión sin `quantity:` en la descripción."""
    df_inv = df_diario[df_diario["Nº Cuenta"].isin([CUENTA_BERKSHIRE, CUENTA_SP500])]
    missing_qty = df_inv[df_inv["Debe"] > 0].copy()
    missing_qty["has_qty"] = missing_qty["Descripción"].apply(
        lambda x: "quantity:" in str(x).lower()
    )
    n_missing = int(len(missing_qty[~missing_qty["has_qty"]]))
    if n_missing > 0:
        st.warning(
            f"⚠️ Se han detectado **{n_missing}** operaciones de inversión sin el "
            "metadato `quantity: X.X` en la descripción. Esto afecta al cálculo "
            "de participaciones y P&L. Por favor, revísalo en Google Sheets."
        )


def render_top_cards(portfolio: dict, metalico_fisico: float, df_diario=None) -> None:
    """6 metric cards superiores: Patrimonio · SP500 · BRK · TR · Efectivo · Te Deben."""
    cc_data = get_centro_control_data()
    val_tr = ((cc_data["H4"] - cc_data["L2"]) / 2.0 - cc_data["F7"]) - cc_data["J7"]
    val_efectivo = cc_data["J7"]

    color_tr = "#009624" if val_tr >= 0 else "#EF4444"
    color_ef = "#009624" if val_efectivo >= 0 else "#EF4444"
    str_tr = f"<div style='position:absolute; bottom:-14px; left:0; color:{color_tr}; font-size:0.65rem; font-weight:bold;'>[{val_tr:+.2f} €]</div>"
    str_ef = f"<div style='position:absolute; bottom:-14px; left:0; color:{color_ef}; font-size:0.65rem; font-weight:bold;'>[{val_efectivo:+.2f} €]</div>"

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c6:
        st.markdown(
            render_metric_card(
                "Patrimonio Total",
                f"{portfolio['total_patrimonio']:,.2f} €",
                premium=True,
                subtitle="Global + Acciones + Efectivo",
                extra_class="portfolio-card",
            ),
            unsafe_allow_html=True,
        )
    with c1:
        st.markdown(
            render_metric_card(
                "SP500",
                f"{portfolio['valor_fondo_eur']:,.2f} €",
                color=COLOR_SP500,
                subtitle=(
                    f"{portfolio['acciones_vanguard']:.5f} part. a "
                    f"{portfolio['precio_fondo']:.2f} €"
                ),
                extra_class="portfolio-card",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card(
                "Berkshire Hathaway",
                f"{portfolio['valor_brk_eur']:,.2f} €",
                color=COLOR_BERKSHIRE,
                subtitle=(
                    f"{portfolio['acciones_brk']:.6f} acc. a {portfolio['precio_brk_usd']:.2f} $"
                ),
                extra_class="portfolio-card",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        tr_total = portfolio["tr_cash"] + portfolio["bokatas_saldo"]
        st.markdown(
            render_metric_card(
                "Trade Republic",
                f"{portfolio['tr_cash']:,.2f} €",
                color=COLOR_EFECTIVO_TR,
                subtitle=f'Liquidez (Banco: <span style="color:#FFFFFF; font-weight:700;">{tr_total:,.2f} €</span>)',
                extra_html=str_tr,
                extra_class="portfolio-card",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            render_metric_card(
                "Efectivo",
                f"{metalico_fisico:,.2f} €",
                color=COLOR_EFECTIVO_FISICO,
                subtitle="Cartera (111) y Hucha (112)",
                extra_html=str_ef,
                extra_class="portfolio-card",
            ),
            unsafe_allow_html=True,
        )
        # CSS para posicionar el botón en la esquina superior derecha de la tarjeta
        st.markdown(
            """
            <style>
            [class*="st-key-btn_cash_breakdown"] {
                margin-top: -168px !important;
                align-self: flex-end !important;
                margin-right: 8px !important;
                width: 32px !important;
                height: 32px !important;
                z-index: 10 !important;
            }
            [class*="st-key-btn_cash_breakdown"] button {
                background-color: transparent !important;
                border: 1px solid transparent !important;
                border-radius: 8px !important;
                width: 32px !important;
                height: 32px !important;
                min-height: 32px !important;
                padding: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: none !important;
                color: initial !important;
            }
            [class*="st-key-btn_cash_breakdown"] button:hover {
                background-color: rgba(133, 77, 14, 0.3) !important;
                border-color: #854D0E !important;
            }
            [class*="st-key-btn_cash_breakdown"] button p {
                font-size: 1rem !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🔍",
            key="btn_cash_breakdown",
            help="Desglose de efectivo por denominación",
        ):
            if df_diario is not None:
                from components.cash_dialog import render_cash_dialog
                from services.accounting import calc_metalico_desglose

                desglose = calc_metalico_desglose(df_diario)
                render_cash_dialog(
                    metalico_fisico,
                    desglose["cartera"],
                    desglose["hucha"],
                )
    with c5:
        st.markdown(
            render_metric_card(
                "Te Deben",
                f"{portfolio['padres_total']:,.2f} €",
                color=COLOR_TE_DEBEN,
                subtitle="Cuentas 131, 132 y 134",
                extra_class="portfolio-card",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)
