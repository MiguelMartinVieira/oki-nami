"""tabs.inversiones.info — Sub-tab "ℹ️ Info": sólo Pay Yourself First.

Un único bloque, foco máximo:
  - **Pay Yourself First & Gasto Oportunista** — velocidad de inversión
    **activa** (excluyendo Saveback / Round Up / Cashback / etc.) y
    correlación Pearson saldo TR ↔ gasto discrecional, con gráfico dual
    y tabla colapsada de los últimos emparejamientos.

Nota: el bloque "DCA vs Lump-Sum" se eliminó de aquí — sus dos métricas
clave (coste medio DCA y precio del día 1) ahora se visualizan directamente
en el DCA Tracker del sub-tab "📈 Berkshire Hathaway" como líneas
horizontales, con un veredicto "DCA gana / Lump-Sum gana" anotado en el
propio gráfico. Ver `components/charts/line.py:build_dca_tracker` con
`show_lumpsum=True`.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.metric_card import render_metric_card
from constants import COLOR_EFECTIVO_TR
from services.analytics import (
    calc_balance_spending_correlation,
    calc_pay_yourself_first_stats,
)

# Acento del sub-tab ℹ️ Info — ámbar de `COLOR_EFECTIVO_TR` (#F59E0B), igual
# que la línea de Saldo TR del chart inferior.
_INFO_ACCENT = COLOR_EFECTIVO_TR


def render_info_tab(df_diario: pd.DataFrame, portfolio: dict, metrics: dict) -> None:
    """Renderiza el sub-tab ℹ️ Info. Los argumentos `portfolio` y `metrics`
    se mantienen por compatibilidad con el orquestador."""
    _render_pay_yourself_first(df_diario)


# ─────────────────────────── PAY YOURSELF FIRST ───────────────────────────


def _render_pay_yourself_first(df_diario: pd.DataFrame) -> None:
    avg_lag_days, lag_details = calc_pay_yourself_first_stats(df_diario)
    corr_coeff, df_corr = calc_balance_spending_correlation(df_diario)

    # ── 2 metric cards compactas (números en ámbar TR, sin subtítulo) ──
    col_pay1, col_pay2 = st.columns(2)
    with col_pay1:
        st.markdown(
            render_metric_card(
                "Velocidad de Inversión Activa",
                f"{avg_lag_days:.1f} días" if avg_lag_days > 0 else "—",
                color=_INFO_ACCENT,
                extra_class="pay-analysis-card",
            ),
            unsafe_allow_html=True,
        )
    with col_pay2:
        st.markdown(
            render_metric_card(
                "Índice de Gasto Oportunista (r)",
                f"{corr_coeff:+.3f}" if not df_corr.empty else "—",
                color=_INFO_ACCENT,
                extra_class="pay-analysis-card",
            ),
            unsafe_allow_html=True,
        )

    # ── Gráfico de correlación (sin título superior) ──
    if not df_corr.empty:
        _render_correlation_chart(df_corr)

    # ── Tabla de últimos lags (compacta, colapsada) ──
    if lag_details:
        with st.expander(
            f"📋 Últimos {min(8, len(lag_details))} emparejamientos ingreso → inversión activa",
            expanded=False,
        ):
            df = pd.DataFrame(lag_details).sort_values("income_date", ascending=False).head(8)
            df = df.rename(
                columns={
                    "income_date": "Fecha Ingreso",
                    "income_desc": "Descripción Ingreso",
                    "income_amount": "Importe (€)",
                    "investment_date": "Fecha Inversión",
                    "investment_desc": "Primer Activo Invertido",
                    "days": "Días",
                }
            )
            st.dataframe(
                df[
                    [
                        "Fecha Ingreso",
                        "Descripción Ingreso",
                        "Importe (€)",
                        "Fecha Inversión",
                        "Primer Activo Invertido",
                        "Días",
                    ]
                ].style.format(
                    {
                        "Importe (€)": "{:,.2f} €",
                        "Días": "{:.0f}",
                    }
                ),
                width="stretch",
                hide_index=True,
            )


def _render_correlation_chart(df_corr: pd.DataFrame) -> None:
    # Color del saldo TR = mismo que en el donut/treemap superior
    # (`COLOR_EFECTIVO_TR`, ámbar `#F59E0B`). Línea de gasto unificada con
    # el color del eje y del título "Gasto 7d (€)" (rosa salmón claro).
    tr_color = COLOR_EFECTIVO_TR
    tr_axis_color = "#FCD34D"  # Amber-300, más claro para los ticks
    spend_axis_color = "rgba(255,122,146,0.35)"
    spend_color = spend_axis_color

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_corr["Fecha"],
            y=df_corr["balance"],
            name="Saldo TR (121)",
            line=dict(color=tr_color, width=2.5),
            hovertemplate="Fecha: %{x|%d %b %Y}<br>Saldo: %{y:,.2f} €",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_corr["Fecha"],
            y=df_corr["spend"],
            name="Gasto acumulado 7d (5x)",
            line=dict(color=spend_color, width=2.5, dash="dash"),
            yaxis="y2",
            hovertemplate="Fecha: %{x|%d %b %Y}<br>Gasto 7d: %{y:,.2f} €",
        )
    )
    fig.update_layout(
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(
            title=dict(text="Saldo TR (€)", font=dict(color=tr_axis_color)),
            tickfont=dict(color=tr_axis_color),
            showgrid=True,
            gridcolor="rgba(255,255,255,0.04)",
        ),
        yaxis2=dict(
            title=dict(text="Gasto 7d (€)", font=dict(color=spend_axis_color)),
            tickfont=dict(color=spend_axis_color),
            anchor="x",
            overlaying="y",
            side="right",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        font_family="'Plus Jakarta Sans', sans-serif",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
        height=320,
    )
    st.plotly_chart(fig, width="stretch", key="chart_correlation_pay")
