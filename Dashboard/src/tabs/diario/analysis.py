import pandas as pd
import streamlit as st

from components.charts import (
    build_annual_savings_heatmap,
    build_drill_bar,
    build_expense_radar_absolute,
    build_expense_radar_relative,
    build_income_radar_absolute,
    build_income_radar_relative,
    build_pie,
    build_radar_mom,
)
from constants import get_category_color
from services.analytics import get_drilldown_data

from .context import DiarioContext


def render_distribucion(ctx: DiarioContext) -> None:
    if ctx.date_mode != "🌐 Histórico Completo":
        st.caption(f"📅 Periodo de análisis: **{ctx.date_label}**")

    if not ctx.is_filtered:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            if not ctx.cat_incomes.empty:
                inc_color_map = {
                    c: get_category_color(c, is_expense=False) for c in ctx.cat_incomes.index
                }
                st.plotly_chart(
                    build_pie(
                        ctx.cat_incomes.index, ctx.cat_incomes.values, color_map=inc_color_map
                    ),
                    width="stretch",
                )
        with col_p2:
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            if not ctx.cat_expenses.empty:
                exp_color_map = {
                    c: get_category_color(c, is_expense=True) for c in ctx.cat_expenses.index
                }
                st.plotly_chart(
                    build_pie(
                        ctx.cat_expenses.index, ctx.cat_expenses.values, color_map=exp_color_map
                    ),
                    width="stretch",
                )
    else:
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        if not ctx.filt_cat_totals.empty:
            st.plotly_chart(
                build_pie(ctx.filt_cat_totals.index, ctx.filt_cat_totals.values),
                width="stretch",
            )
        else:
            st.info("No hay datos para esta categoría.")


def render_drilldown(ctx: DiarioContext) -> None:
    if not ctx.is_filtered:
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        col_dd1, col_dd2 = st.columns(2)

        with col_dd1:
            if not ctx.cat_incomes.empty:
                default_inc = ctx.cat_incomes.index[0]
                sel_inc = st.session_state.get("sel_inc", default_inc)
                drill = get_drilldown_data(ctx.df_ingresos, sel_inc, is_expense=False)
                if not drill.empty:
                    drill_color_inc = get_category_color(sel_inc, is_expense=False)
                    st.plotly_chart(
                        build_drill_bar(drill, "Haber", "Concepto", drill_color_inc),
                        width="stretch",
                    )
                st.selectbox(
                    "Selecciona Categoría a Analizar",
                    ctx.cat_incomes.index,
                    key="sel_inc",
                    label_visibility="collapsed",
                )

        with col_dd2:
            if not ctx.cat_expenses.empty:
                default_exp = ctx.cat_expenses.index[0]
                sel_exp = st.session_state.get("sel_exp", default_exp)
                drill = get_drilldown_data(ctx.df_gastos, sel_exp, is_expense=True)
                if not drill.empty:
                    drill_color_exp = get_category_color(sel_exp, is_expense=True)
                    st.plotly_chart(
                        build_drill_bar(drill, "Debe", "Concepto", drill_color_exp), width="stretch"
                    )
                st.selectbox(
                    "Selecciona Categoría a Analizar",
                    ctx.cat_expenses.index,
                    key="sel_exp",
                    label_visibility="collapsed",
                )
    else:
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        source = ctx.df_gastos if ctx.is_expense_filter else ctx.df_ingresos
        drill = get_drilldown_data(source, ctx.filtered_cat, is_expense=ctx.is_expense_filter)
        if not drill.empty:
            drill_color = get_category_color(ctx.filtered_cat, is_expense=ctx.is_expense_filter)
            col_imp = "Debe" if ctx.is_expense_filter else "Haber"
            st.plotly_chart(
                build_drill_bar(drill, col_imp, "Concepto", drill_color), width="stretch"
            )
        else:
            st.info("No hay datos para esta categoría.")


def render_heatmap(ctx: DiarioContext) -> None:
    years_disponibles = sorted(
        ctx.df_diario["Fecha"].dt.year.dropna().unique().tolist(), reverse=True
    )
    current_year = pd.Timestamp.today().year
    default_year = (
        current_year
        if current_year in years_disponibles
        else (years_disponibles[0] if years_disponibles else current_year)
    )
    default_year_list = years_disponibles or [default_year]
    default_idx = years_disponibles.index(default_year) if default_year in years_disponibles else 0

    if not ctx.is_filtered:
        year_selected = st.session_state.get("calendar_year", default_year_list[default_idx])
        year_int = int(year_selected)

        fig_mix = build_annual_savings_heatmap(ctx.df_diario, year=year_int, metric="mixto")
        if fig_mix:
            st.plotly_chart(fig_mix, width="stretch", key="cal_mixto")
        else:
            st.info(f"No hay datos para {year_int}.")

        fig_ing = build_annual_savings_heatmap(ctx.df_diario, year=year_int, metric="ingresos")
        if fig_ing:
            st.plotly_chart(fig_ing, width="stretch", key="cal_ingresos")
        else:
            st.info(f"No hay ingresos en {year_int}.")

        fig_gas = build_annual_savings_heatmap(ctx.df_diario, year=year_int, metric="gastos")
        if fig_gas:
            st.plotly_chart(fig_gas, width="stretch", key="cal_gastos")
        else:
            st.info(f"No hay gastos en {year_int}.")

        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
        _, col_c, _ = st.columns([1, 1, 1])
        with col_c:
            st.selectbox(
                "Año",
                default_year_list,
                index=default_idx,
                key="calendar_year",
                label_visibility="collapsed",
            )
    else:
        metric_key = "gastos" if ctx.is_expense_filter else "ingresos"
        year_selected = st.session_state.get(
            "calendar_year_filtered", default_year_list[default_idx]
        )

        df_diario_cat = ctx.df_diario[ctx.df_diario["Cuenta"] == ctx.filtered_cat]
        fig_filtered = build_annual_savings_heatmap(
            df_diario_cat, year=int(year_selected), metric=metric_key
        )
        if fig_filtered:
            st.plotly_chart(fig_filtered, width="stretch", key="cal_filtered")
        else:
            st.info("No hay datos para mostrar el calendario de esta categoría.")

        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
        _, col_c, _ = st.columns([1, 1, 1])
        with col_c:
            st.selectbox(
                "Año",
                default_year_list,
                index=default_idx,
                key="calendar_year_filtered",
                label_visibility="collapsed",
            )


def render_habitos(ctx: DiarioContext) -> None:
    if not ctx.is_filtered:
        # ── GASTOS ──
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        st.caption("Comparativa del perfil de gastos de este mes frente a tu promedio histórico.")

        fig_radar_abs = build_expense_radar_absolute(ctx.df_gastos_cm, ctx.df_gastos)
        fig_radar_rel = build_expense_radar_relative(ctx.df_gastos_cm, ctx.df_gastos)
        fig_mom_exp = build_radar_mom(ctx.df_gastos_cm, ctx.df_gastos, "Debe", is_expense=True)

        if fig_radar_abs or fig_radar_rel or fig_mom_exp:
            col_g1, col_g2, col_g3 = st.columns(3)
            with col_g1:
                st.markdown("**Visión Absoluta**")
                st.caption("Atenuada con raíz cuadrada para mitigar outliers.")
                if fig_radar_abs:
                    st.plotly_chart(fig_radar_abs, width="stretch", key="radar_abs_exp")
                else:
                    st.info("Sin datos.")
            with col_g2:
                st.markdown("**Visión Relativa (%)**")
                st.caption("Proporción exacta frente a la media de cada categoría.")
                if fig_radar_rel:
                    st.plotly_chart(fig_radar_rel, width="stretch", key="radar_rel_exp")
                else:
                    st.info("Sin datos.")
            with col_g3:
                st.markdown("**Mes Actual vs Anterior**")
                st.caption("Compara tu perfil de este mes contra el mes pasado.")
                if fig_mom_exp:
                    st.plotly_chart(fig_mom_exp, width="stretch", key="mom_exp")
                else:
                    st.info("Se necesitan al menos 2 meses de datos.")
        else:
            st.info("No hay suficientes datos para mostrar el análisis de hábitos de gasto.")

        st.markdown("---")

        # ── INGRESOS ──
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        st.caption("Comparativa del perfil de ingresos de este mes frente a tu promedio histórico.")

        fig_inc_radar_abs = build_income_radar_absolute(ctx.df_ingresos_cm, ctx.df_ingresos)
        fig_inc_radar_rel = build_income_radar_relative(ctx.df_ingresos_cm, ctx.df_ingresos)
        fig_mom_inc = build_radar_mom(
            ctx.df_ingresos_cm, ctx.df_ingresos, "Haber", is_expense=False
        )

        if fig_inc_radar_abs or fig_inc_radar_rel or fig_mom_inc:
            col_i1, col_i2, col_i3 = st.columns(3)
            with col_i1:
                st.markdown("**Visión Absoluta**")
                st.caption("Atenuada con raíz cuadrada para mitigar outliers.")
                if fig_inc_radar_abs:
                    st.plotly_chart(fig_inc_radar_abs, width="stretch", key="radar_abs_inc")
                else:
                    st.info("Sin datos.")
            with col_i2:
                st.markdown("**Visión Relativa (%)**")
                st.caption("Proporción exacta frente a la media de cada categoría.")
                if fig_inc_radar_rel:
                    st.plotly_chart(fig_inc_radar_rel, width="stretch", key="radar_rel_inc")
                else:
                    st.info("Sin datos.")
            with col_i3:
                st.markdown("**Mes Actual vs Anterior**")
                st.caption("Compara tu perfil de este mes contra el mes pasado.")
                if fig_mom_inc:
                    st.plotly_chart(fig_mom_inc, width="stretch", key="mom_inc")
                else:
                    st.info("Se necesitan al menos 2 meses de datos.")
        else:
            st.info("No hay suficientes datos para mostrar el análisis de hábitos de ingresos.")
    else:
        # ── Modo filtrado: radars por concepto ──
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        st.caption(f"Ejes = conceptos dentro de {ctx.filtered_cat}. Datos agrupados por concepto.")

        col_importe = "Debe" if ctx.is_expense_filter else "Haber"

        if ctx.is_expense_filter:
            fig_r_abs = build_expense_radar_absolute(ctx.filt_cm, ctx.filt_all)
            fig_r_rel = build_expense_radar_relative(ctx.filt_cm, ctx.filt_all)
            fig_r_mom = build_radar_mom(ctx.filt_cm, ctx.filt_all, col_importe, is_expense=True)
        else:
            fig_r_abs = build_income_radar_absolute(ctx.filt_cm, ctx.filt_all)
            fig_r_rel = build_income_radar_relative(ctx.filt_cm, ctx.filt_all)
            fig_r_mom = build_radar_mom(ctx.filt_cm, ctx.filt_all, col_importe, is_expense=False)

        if fig_r_abs or fig_r_rel or fig_r_mom:
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                st.markdown("**Visión Absoluta**")
                if fig_r_abs:
                    st.plotly_chart(fig_r_abs, width="stretch", key="radar_filt_abs")
                else:
                    st.info("Sin datos.")
            with col_f2:
                st.markdown("**Visión Relativa (%)**")
                if fig_r_rel:
                    st.plotly_chart(fig_r_rel, width="stretch", key="radar_filt_rel")
                else:
                    st.info("Sin datos.")
            with col_f3:
                st.markdown("**Mes Actual vs Anterior**")
                if fig_r_mom:
                    st.plotly_chart(fig_r_mom, width="stretch", key="radar_filt_mom")
                else:
                    st.info("Se necesitan al menos 2 meses.")
        else:
            st.info("No hay suficientes datos de conceptos para esta categoría.")
