"""
tabs/resumen/main.py — Tab principal "Resumen" (Bento Grid Ultra-Limpio sin Solapamientos de Texto).

Toda la información visual sin ruido tipográfico:
 1. Donut: Sin etiquetas de porcentaje sobre las rebanadas (hover activo).
 2. Sankey: Flujos puros de color sin etiquetas de nodos amontonadas (hover activo).
 3. Stacked Area: Ejes limpios sin rótulos de eje Y gigantes.
 4. Horizontal Bar & Mini Donuts: Sin marcas de fecha/horas ni ticks redundantes.
 5. Radars: Ejes polares (radiales y angulares) ocultos para mostrar solo las redes limpias.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import (
    build_annual_savings_heatmap,
    build_current_month_income_vs_expense_bar,
    build_donut,
    build_expense_radar_absolute,
    build_expense_radar_relative,
    build_income_radar_absolute,
    build_income_radar_relative,
    build_pie,
    build_radar_mom,
    build_sankey,
    build_stacked_area,
)
from components.metric_card import render_metric_card
from components.tab_markers import render_tab_accent_marker
from constants import (
    COLOR_BERKSHIRE,
    COLOR_EFECTIVO_FISICO,
    COLOR_EFECTIVO_TR,
    COLOR_SP500,
    COLOR_TE_DEBEN,
    get_category_color,
)
from data.gsheets import get_centro_control_data
from services.accounting import (
    calc_gastos_ingresos,
    calc_portfolio_summary,
)
from tabs.inversiones.allocation import _build_portfolio_history


def render(df_diario: pd.DataFrame, df_saldos: pd.DataFrame, metalico_fisico: float) -> None:
    """Renderiza la pestaña principal Resumen en estilo Bento Grid limpio."""
    render_tab_accent_marker("resumen-tab-marker", "#00E676")

    # CSS Scoped de compresión Bento y limpieza
    st.markdown(
        """
        <style>
        .stApp div[data-testid="stBlock"] {
            gap: 0.4rem !important;
        }
        .bento-card {
            background-color: #18181B;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 8px;
            margin-bottom: 4px;
        }
        .compact-resumen-card {
            height: 136px !important;
            padding: 14px 18px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
        }
        .compact-resumen-card .metric-label {
            font-size: clamp(0.62rem, 3.8cqi, 0.78rem) !important;
            margin-bottom: 0 !important;
        }
        .compact-resumen-card .metric-value {
            font-size: clamp(1.1rem, 14cqi, 2.0rem) !important;
            margin: 2px 0 !important;
            line-height: 1.1 !important;
        }
        .compact-resumen-card .metric-subtitle {
            font-size: clamp(0.55rem, 3.8cqi, 0.75rem) !important;
            margin-top: 2px !important;
        }
        @media (max-width: 1200px) {
            div[data-testid="stHorizontalBlock"]:has(.compact-resumen-card) {
                display: grid !important;
                grid-template-columns: repeat(3, 1fr) !important;
                gap: 10px !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.compact-resumen-card) > div[data-testid="stColumn"] {
                width: 100% !important;
                flex: none !important;
            }
        }
        @media (max-width: 768px) {
            div[data-testid="stHorizontalBlock"]:has(.compact-resumen-card) {
                grid-template-columns: repeat(2, 1fr) !important;
            }
        }
        @media (max-width: 480px) {
            div[data-testid="stHorizontalBlock"]:has(.compact-resumen-card) {
                grid-template-columns: repeat(1, 1fr) !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Pre-cálculos generales
    gi = calc_gastos_ingresos(df_diario)
    portfolio = calc_portfolio_summary(df_diario, metalico_fisico)
    cc_data = get_centro_control_data()
    val_tr = ((cc_data["H4"] - cc_data["L2"]) / 2.0 - cc_data["F7"]) - cc_data["J7"]
    val_efectivo = cc_data["J7"]

    # ── FILA 1: TARJETAS COMPACTAS + NOTIFICACIÓN AUDITORÍA ──
    _render_row1_metrics_and_audit(portfolio, metalico_fisico, val_tr, val_efectivo, df_diario)

    # Separación visual entre tarjetas y gráficos
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # ── FILA 2: PORTFOLIO & BALANCE MENSUAL ──
    _render_row2_portfolio_and_monthly(portfolio, metalico_fisico, df_diario, gi)

    # ── FILA 3: SANKEY + HEATMAP ──
    _render_row3_sankey_and_heatmap(df_diario, gi)

    # ── FILA 4: RADAR CHARTS HÁBITOS ──
    _render_row4_radars(gi)


def _render_row1_metrics_and_audit(
    portfolio: dict,
    metalico_fisico: float,
    val_tr: float,
    val_efectivo: float,
    df_diario: pd.DataFrame,
) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    color_tr = "#009624" if val_tr >= 0 else "#EF4444"
    color_ef = "#009624" if val_efectivo >= 0 else "#EF4444"
    str_tr = f"<div style='position:absolute; bottom:-12px; left:0; color:{color_tr}; font-size:0.62rem; font-weight:bold;'>[{val_tr:+.2f} €]</div>"
    str_ef = f"<div style='position:absolute; bottom:-12px; left:0; color:{color_ef}; font-size:0.62rem; font-weight:bold;'>[{val_efectivo:+.2f} €]</div>"

    with c1:
        st.markdown(
            render_metric_card(
                "SP500",
                f"{portfolio['valor_fondo_eur']:,.2f} €",
                color=COLOR_SP500,
                subtitle=f"{portfolio['acciones_vanguard']:.2f} part.",
                extra_class="compact-resumen-card",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card(
                "Berkshire",
                f"{portfolio['valor_brk_eur']:,.2f} €",
                color=COLOR_BERKSHIRE,
                subtitle=f"{portfolio['acciones_brk']:.2f} acc.",
                extra_class="compact-resumen-card",
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
                extra_class="compact-resumen-card",
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
                extra_class="compact-resumen-card",
            ),
            unsafe_allow_html=True,
        )
        # CSS para posicionar el botón de la lupa sin envoltorio ni bordes
        st.markdown(
            """
            <style>
            div[data-testid="stColumn"]:has([class*="st-key-btn_cash_breakdown_resumen"]) {
                position: relative !important;
            }
            [class*="st-key-btn_cash_breakdown_resumen"],
            [class*="st-key-btn_cash_breakdown_resumen"] div[data-testid="stButton"] {
                position: absolute !important;
                top: 10px !important;
                right: 12px !important;
                z-index: 20 !important;
                margin: 0 !important;
                padding: 0 !important;
                background: transparent !important;
                border: none !important;
                width: auto !important;
                height: auto !important;
            }
            div.element-container:has(#resumen-tab-marker) ~ div [class*="st-key-btn_cash_breakdown_resumen"] button,
            div.element-container:has(#resumen-tab-marker) ~ div [class*="st-key-btn_cash_breakdown_resumen"] button:hover,
            div.element-container:has(#resumen-tab-marker) ~ div [class*="st-key-btn_cash_breakdown_resumen"] button:focus,
            div.element-container:has(#resumen-tab-marker) ~ div [class*="st-key-btn_cash_breakdown_resumen"] button:active,
            [class*="st-key-btn_cash_breakdown_resumen"] button,
            [class*="st-key-btn_cash_breakdown_resumen"] button:hover,
            [class*="st-key-btn_cash_breakdown_resumen"] button:focus,
            [class*="st-key-btn_cash_breakdown_resumen"] button:active {
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                border-left: none !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                outline: none !important;
                padding: 0 !important;
                margin: 0 !important;
                min-height: unset !important;
                height: auto !important;
                width: auto !important;
                cursor: pointer !important;
            }
            [class*="st-key-btn_cash_breakdown_resumen"] button p {
                font-size: 1.15rem !important;
                margin: 0 !important;
                padding: 0 !important;
                line-height: 1 !important;
                opacity: 0.8 !important;
                transition: transform 0.15s ease, opacity 0.15s ease !important;
            }
            [class*="st-key-btn_cash_breakdown_resumen"] button:hover p {
                opacity: 1 !important;
                transform: scale(1.2) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🔍",
            key="btn_cash_breakdown_resumen",
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
                subtitle="Cuentas 131, 132, 134",
                extra_class="compact-resumen-card",
            ),
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            render_metric_card(
                "Patrimonio Total",
                f"{portfolio['total_patrimonio']:,.2f} €",
                premium=True,
                subtitle="Global Activos",
                extra_class="compact-resumen-card",
            ),
            unsafe_allow_html=True,
        )

    # Auditoría compacta
    padres_unreg = []
    bokatas_unreg = []
    try:
        from services.automation import check_pending_tickets

        status = check_pending_tickets(df_diario)
        padres_unreg = status["padres"]["unregistered"] + status["padres"]["unrenamed"]
        bokatas_unreg = status["bokatas"]["unregistered"] + status["bokatas"]["unprocessed"]
    except Exception:
        pass

    total_pending = len(padres_unreg) + len(bokatas_unreg)

    if total_pending > 0:
        c_left, c_right = st.columns([4, 1])
        with c_left:
            st.warning(
                f"⚠️ **{total_pending} tickets sin procesar** ({len(padres_unreg)} Padres, {len(bokatas_unreg)} Bokatas)"
            )
        with c_right:
            target_tab = "Padres" if len(padres_unreg) > 0 else "Bokatas"
            if st.button(f"👉 Procesar en {target_tab}", key="resumen_btn_audit", width="stretch"):
                st.session_state["nav_main_tab"] = target_tab
                st.rerun()


def _render_row2_portfolio_and_monthly(
    portfolio: dict, metalico_fisico: float, df_diario: pd.DataFrame, gi: dict
) -> None:
    col_donut, col_area, col_month = st.columns([0.8, 2.4, 0.8])

    # 1. Donut Asset Allocation (limpio de texto sobre slices)
    with col_donut:
        series_map = [
            ("SP500", portfolio["valor_fondo_eur"], COLOR_SP500),
            ("Berkshire", portfolio["valor_brk_eur"], COLOR_BERKSHIRE),
            ("Efectivo TR", portfolio["tr_cash"], COLOR_EFECTIVO_TR),
            ("Efectivo", metalico_fisico, COLOR_EFECTIVO_FISICO),
            ("Te Deben", portfolio["padres_total"], COLOR_TE_DEBEN),
        ]
        donut_labels = [s[0] for s in series_map]
        donut_values = [s[1] for s in series_map]
        donut_colors = [s[2] for s in series_map]

        fig_donut = build_donut(donut_labels, donut_values, donut_colors, "")
        if fig_donut:
            fig_donut.update_traces(textinfo="none")
            fig_donut.update_layout(
                height=235,
                margin=dict(t=2, b=2, l=2, r=2),
                showlegend=False,
                annotations=[],
            )
            st.plotly_chart(fig_donut, width="stretch", key="resumen_donut_p")
        else:
            from components.skeleton import render_skeleton_chart

            render_skeleton_chart(height=235)

    # 2. Stacked Area Evolución (ampliado en ancho y alto)
    with col_area:
        df_plot = _build_portfolio_history(df_diario)
        if df_plot is not None and not df_plot.empty and "Date" in df_plot.columns:
            max_date = df_plot["Date"].max()
            if pd.notnull(max_date):
                cutoff_date = max_date - pd.DateOffset(months=2)
                df_plot = df_plot[df_plot["Date"] >= cutoff_date]

            _ALL_SERIES = ["SP500", "Berkshire", "Trade Republic", "Efectivo", "Te Deben"]
            fig_stacked = build_stacked_area(df_plot, _ALL_SERIES)
            if fig_stacked:
                fig_stacked.update_layout(
                    height=235,
                    margin=dict(t=0, b=0, l=0, r=0),
                    yaxis=dict(title="", showticklabels=False, ticks=""),
                    xaxis=dict(title="", showticklabels=False, ticks=""),
                    showlegend=False,
                )
                st.plotly_chart(fig_stacked, width="stretch", key="resumen_area_p")
        else:
            from components.skeleton import render_skeleton_chart

            render_skeleton_chart(height=235)

    # 3. Balance del Mes + Mini Donuts
    with col_month:
        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        current_month_str = str(gi.get("current_month", ""))
        fig_bar_cm = build_current_month_income_vs_expense_bar(
            gi["cm_ingresos"],
            gi["cm_gastos"],
            current_month_str,
            cat_incomes_cm=gi["cat_incomes_cm"],
            cat_expenses_cm=gi["cat_expenses_cm"],
        )
        if fig_bar_cm:
            fig_bar_cm.update_layout(
                height=90,
                margin=dict(t=6, b=6, l=2, r=2),
                showlegend=False,
                yaxis=dict(showticklabels=False, title=""),
                xaxis=dict(showticklabels=False, title=""),
            )
            st.plotly_chart(fig_bar_cm, width="stretch", key="resumen_bar_cm")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if not gi["cat_incomes_cm"].empty:
                inc_colors = {
                    c: get_category_color(c, is_expense=False) for c in gi["cat_incomes_cm"].index
                }
                fig_inc = build_pie(
                    gi["cat_incomes_cm"].index, gi["cat_incomes_cm"].values, color_map=inc_colors
                )
                if fig_inc:
                    fig_inc.update_traces(textinfo="none")
                    fig_inc.update_layout(
                        height=100, margin=dict(t=2, b=2, l=2, r=2), showlegend=False
                    )
                    st.plotly_chart(fig_inc, width="stretch", key="resumen_pie_inc")
        with col_d2:
            if not gi["cat_expenses_cm"].empty:
                exp_colors = {
                    c: get_category_color(c, is_expense=True) for c in gi["cat_expenses_cm"].index
                }
                fig_exp = build_pie(
                    gi["cat_expenses_cm"].index, gi["cat_expenses_cm"].values, color_map=exp_colors
                )
                if fig_exp:
                    fig_exp.update_traces(textinfo="none")
                    fig_exp.update_layout(
                        height=100, margin=dict(t=2, b=2, l=2, r=2), showlegend=False
                    )
                    st.plotly_chart(fig_exp, width="stretch", key="resumen_pie_exp")


def _render_row3_sankey_and_heatmap(df_diario: pd.DataFrame, gi: dict) -> None:
    col_sankey, col_heatmap = st.columns([1.4, 1.0])

    # 1. Sankey Macro (nodos limpios de texto encimado)
    with col_sankey:
        fig_sankey = build_sankey(
            gi["cat_incomes"],
            gi["cat_expenses"],
            gi["total_hist_ingresos"],
            gi["total_hist_gastos"],
            df_ingresos=gi["df_ingresos"],
            df_gastos=gi["df_gastos"],
            total_inversiones=gi["total_inversiones"],
            df_inversiones=gi["df_inversiones"],
            mode="categories",
        )
        if fig_sankey:
            # Ocultar etiquetas de texto de nodos para flujo puro visual sin ruido
            labels_len = len(fig_sankey.data[0].node.label)
            fig_sankey.update_traces(
                node=dict(label=[""] * labels_len),
                textfont=dict(color="rgba(0,0,0,0)"),
            )
            fig_sankey.update_layout(height=195, margin=dict(t=5, b=5, l=5, r=5))
            st.plotly_chart(fig_sankey, width="stretch", key="resumen_sankey")

    # 2. Heatmap Calendario (celdas cuadradas perfectas de las últimas 18 semanas)
    with col_heatmap:
        current_year = pd.Timestamp.today().year
        fig_heatmap = build_annual_savings_heatmap(
            df_diario, year=current_year, metric="gastos", recent_weeks=18
        )
        if fig_heatmap:
            fig_heatmap.update_layout(
                height=195,
                margin=dict(t=2, b=2, l=2, r=2),
                coloraxis_showscale=False,
                xaxis=dict(title="", showticklabels=False, ticks=""),
                yaxis=dict(title="", showticklabels=False, ticks=""),
            )
            st.plotly_chart(fig_heatmap, width="stretch", key="resumen_heatmap")


def _render_row4_radars(gi: dict) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    fig_r_exp_abs = build_expense_radar_absolute(gi["df_gastos_cm"], gi["df_gastos"])
    fig_r_exp_rel = build_expense_radar_relative(gi["df_gastos_cm"], gi["df_gastos"])
    fig_r_exp_mom = build_radar_mom(gi["df_gastos_cm"], gi["df_gastos"], "Debe", is_expense=True)

    fig_r_inc_abs = build_income_radar_absolute(gi["df_ingresos_cm"], gi["df_ingresos"])
    fig_r_inc_rel = build_income_radar_relative(gi["df_ingresos_cm"], gi["df_ingresos"])
    fig_r_inc_mom = build_radar_mom(
        gi["df_ingresos_cm"], gi["df_ingresos"], "Haber", is_expense=False
    )

    radars = [
        (c1, fig_r_exp_abs, "resumen_r_e_abs"),
        (c2, fig_r_exp_rel, "resumen_r_e_rel"),
        (c3, fig_r_exp_mom, "resumen_r_e_mom"),
        (c4, fig_r_inc_abs, "resumen_r_i_abs"),
        (c5, fig_r_inc_rel, "resumen_r_i_rel"),
        (c6, fig_r_inc_mom, "resumen_r_i_mom"),
    ]

    for col, fig, k in radars:
        with col:
            if fig:
                # Ocultar etiquetas polares radiales y angulares para limpiar solapamientos
                fig.update_polars(
                    radialaxis=dict(visible=False),
                    angularaxis=dict(showticklabels=False, ticks=""),
                )
                fig.update_layout(height=165, margin=dict(t=5, b=5, l=5, r=5), showlegend=False)
                st.plotly_chart(fig, width="stretch", key=k)
