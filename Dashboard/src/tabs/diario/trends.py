import pandas as pd
import streamlit as st

from components.charts import (
    build_bar_income_expense_combined,
    build_category_sparkline,
    build_savings_rate_line,
)
from constants import get_category_color
from services.analytics import get_sparkline_data

from .context import DiarioContext


def render_sparklines(ctx: DiarioContext) -> None:
    def _render_sparklines_internal(
        df_mov: pd.DataFrame, col_imp: str, is_exp: bool, color_override: str | None = None
    ) -> None:
        """Renderiza sparklines por categoría o concepto."""
        series_dict = get_sparkline_data(df_mov, col_imp)
        if not series_dict:
            st.info("Sin datos.")
            return

        for _cat, _series in series_dict.items():
            _color = color_override or get_category_color(_cat, is_expense=is_exp)
            _total = _series.sum()
            _last = _series.iloc[-1] if len(_series) else 0
            st.markdown(
                f"<div style='font-size:0.78rem; font-weight:600; color:{_color}; "
                f"margin-bottom:0; margin-top:8px;'>{_cat}</div>"
                f"<div style='font-size:0.72rem; color:#64748B;'>"
                f"Este mes: <b>{_last:,.0f} €</b> · Total: {_total:,.0f} €</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                build_category_sparkline(_series, _color, is_expense=is_exp),
                width="stretch",
                config={"displayModeBar": False},
                key=f"spark_{is_exp}_{_cat}",
            )

    if not ctx.is_filtered:
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        st.caption(
            "Ingresos (izquierda) y gastos (derecha) por categoría. "
            "**▲ verde ingresos** = sube · **▼ rojo gastos** = baja respecto al mes anterior."
        )
        _col_inc, _col_exp = st.columns(2)
        with _col_inc:
            st.markdown("#### Ingresos")
            _render_sparklines_internal(ctx.df_ingresos, "Haber", is_exp=False)
        with _col_exp:
            st.markdown("#### Gastos")
            _render_sparklines_internal(ctx.df_gastos, "Debe", is_exp=True)
    else:
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        st.caption(f"Tendencia mensual de cada concepto dentro de {ctx.filtered_cat}.")
        base_color = get_category_color(ctx.filtered_cat, is_expense=ctx.is_expense_filter)
        col_importe = "Debe" if ctx.is_expense_filter else "Haber"
        _render_sparklines_internal(
            ctx.filt_all, col_importe, is_exp=ctx.is_expense_filter, color_override=base_color
        )


def render_evolucion(ctx: DiarioContext) -> None:
    if not ctx.is_filtered:
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        tab_evol_cat, tab_evol_ahorro = st.tabs(
            [
                "📊 Ingresos vs Gastos por Categoría",
                "📈 Tasa de Ahorro",
            ]
        )

        with tab_evol_cat:
            fig_combined = build_bar_income_expense_combined(ctx.df_gastos, ctx.df_ingresos)
            if fig_combined:
                st.plotly_chart(fig_combined, width="stretch")
            else:
                st.info("No hay suficientes datos históricos para mostrar el desglose.")

        with tab_evol_ahorro:
            st.caption(
                "Evolución de la tasa de ahorro mensual: (Ingresos − Gastos) ÷ Ingresos × 100. "
                "Referencias: 20 % básico · 30 % recomendado."
            )
            fig_rate = build_savings_rate_line(ctx.df_gastos, ctx.df_ingresos)
            if fig_rate:
                st.plotly_chart(fig_rate, width="stretch")
            else:
                st.info("Se necesitan al menos dos meses de datos para mostrar la evolución.")
    else:
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        st.caption(f"Desglose mensual por concepto dentro de {ctx.filtered_cat}.")
        if ctx.is_expense_filter:
            fig_evol = build_bar_income_expense_combined(ctx.filt_all, pd.DataFrame())
        else:
            fig_evol = build_bar_income_expense_combined(pd.DataFrame(), ctx.filt_all)
        if fig_evol:
            st.plotly_chart(fig_evol, width="stretch")
        else:
            st.info("No hay datos suficientes para esta categoría.")
