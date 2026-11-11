import streamlit as st

from components.metric_card import render_metric_card
from constants import COLOR_GASTOS, COLOR_INGRESOS

from .context import DiarioContext


def render_summary(ctx: DiarioContext) -> None:
    st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    gi = ctx.gi
    cm_ingresos = gi["cm_ingresos"]
    pm_ingresos = gi["pm_ingresos"]
    cm_gastos = gi["cm_gastos"]
    pm_gastos = gi["pm_gastos"]
    current_month = gi["current_month"]
    total_hist_ingresos = gi["total_hist_ingresos"]
    total_hist_gastos = gi["total_hist_gastos"]

    delta_ingresos = cm_ingresos - pm_ingresos
    delta_gastos = cm_gastos - pm_gastos

    # Estilo común del delta "vs mes ant." cuando va ENCIMA del valor.
    _delta_top_style = "font-size:0.85rem; font-weight:500; color:#A1A1AA; margin: 2px 0 -2px;"

    with col1:
        delta_str = (
            f"+{delta_ingresos:,.2f} €" if delta_ingresos >= 0 else f"{delta_ingresos:,.2f} €"
        )
        delta_html = f'<div style="{_delta_top_style}">{delta_str} vs mes ant.</div>'
        hist_html = f'<hr><div style="font-size:0.8rem; color:#71717A;">Ingresos Históricos</div><div style="font-size:1.1rem; color:#E4E4E7; font-weight:600;">+{total_hist_ingresos:,.2f} €</div>'
        st.markdown(
            render_metric_card(
                f"Ingresos del Mes ({current_month})",
                f"+{cm_ingresos:,.2f} €",
                color=COLOR_INGRESOS,
                extra_html_top=delta_html,
                extra_html=hist_html,
                extra_class="resumen-card",
            ),
            unsafe_allow_html=True,
        )

    with col2:
        ahorro_hist = total_hist_ingresos - total_hist_gastos
        tasa_hist = (ahorro_hist / total_hist_ingresos * 100.0) if total_hist_ingresos else 0.0
        color_acum = COLOR_INGRESOS if ahorro_hist >= 0 else COLOR_GASTOS
        color_tasa_hist = COLOR_INGRESOS if tasa_hist >= 0 else COLOR_GASTOS
        tasa_top_html = (
            '<div style="font-size:0.85rem; font-weight:600; color:#FFFFFF; '
            'margin: 2px 0 -2px;">'
            f"{ctx.tasa_ahorro_mes:.1f}% tasa de ahorro"
            "</div>"
        )
        ahorro_html = (
            "<hr>"
            '<div style="display:flex; justify-content:space-between; gap:8px;">'
            '<div style="display:flex; flex-direction:column;">'
            '<div style="font-size:0.8rem; color:#71717A;">Acumulado</div>'
            f'<div style="font-size:1.1rem; color:{color_acum}; '
            f'font-weight:600;">{ahorro_hist:,.2f} €</div>'
            "</div>"
            '<div style="display:flex; flex-direction:column; text-align:right;">'
            '<div style="font-size:0.8rem; color:#71717A;">Tasa Histórica</div>'
            f'<div style="font-size:1.1rem; color:{color_tasa_hist}; '
            f'font-weight:600;">{tasa_hist:.1f}%</div>'
            "</div>"
            "</div>"
        )
        st.markdown(
            render_metric_card(
                f"Ahorro del Mes ({current_month})",
                f"{ctx.ahorro_mes:,.2f} €",
                color=ctx.color_ahorro,
                extra_html_top=tasa_top_html,
                extra_html=ahorro_html,
                extra_class="resumen-card",
            ),
            unsafe_allow_html=True,
        )

    with col3:
        delta_str_exp = f"+{delta_gastos:,.2f} €" if delta_gastos >= 0 else f"{delta_gastos:,.2f} €"
        delta_html_exp = f'<div style="{_delta_top_style}">{delta_str_exp} vs mes ant.</div>'
        hist_html_exp = f'<hr><div style="font-size:0.8rem; color:#71717A;">Gastos Históricos</div><div style="font-size:1.1rem; color:#E4E4E7; font-weight:600;">-{total_hist_gastos:,.2f} €</div>'
        st.markdown(
            render_metric_card(
                f"Gastos del Mes ({current_month})",
                f"-{cm_gastos:,.2f} €",
                color=COLOR_GASTOS,
                extra_html_top=delta_html_exp,
                extra_html=hist_html_exp,
                extra_class="resumen-card",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
