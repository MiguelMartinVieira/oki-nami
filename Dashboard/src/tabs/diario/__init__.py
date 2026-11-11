"""
tab_diario.py — Tab "Finanzas Diarias".

Muestra: Resumen general, Sankey, pies, drill-down, evolución mensual, tabla.
Refactorizado modularmente.
"""

import pandas as pd
import streamlit as st

from data.gsheets import get_historico
from services.accounting import (
    calc_ahorro,
    calc_gastos_ingresos,
    calc_portfolio_summary,
    filter_df_by_date_range,
    get_color_smooth,
)
from services.analytics import enrich_with_concepto

from .analysis import render_distribucion, render_drilldown, render_habitos, render_heatmap
from .context import DiarioContext
from .coste_real import render_coste_real
from .date_filter import get_available_period_options, get_date_range_from_mode
from .libro import render_libro
from .roundup import render_roundup
from .sankey_view import render_sankey_view
from .subscriptions import render_subscriptions
from .summary import render_summary
from .trends import render_evolucion, render_sparklines


def render(df_diario: pd.DataFrame, df_saldos: pd.DataFrame, metalico_fisico: float) -> None:
    """Renderiza el tab completo de Finanzas Diarias."""

    # ── Cálculos de Resumen Mensual (sin filtro temporal) ──
    gi_summary = calc_gastos_ingresos(df_diario)

    ahorro_mes, tasa_ahorro_mes = calc_ahorro(gi_summary["cm_ingresos"], gi_summary["cm_gastos"])
    color_ahorro = get_color_smooth(tasa_ahorro_mes)

    # Patrimonio Total centralizado
    portfolio = calc_portfolio_summary(df_diario, metalico_fisico)
    total_patrimonio = portfolio["total_patrimonio"]

    # Delta patrimonio vs último día del mes anterior (vía histórico)
    delta_patrimonio: float | None = None
    try:
        df_hist = get_historico()
        if not df_hist.empty and "Fecha" in df_hist.columns and "Total" in df_hist.columns:
            today = pd.Timestamp.today().normalize()
            month_start = pd.Timestamp(year=today.year, month=today.month, day=1)
            df_prev = df_hist[df_hist["Fecha"] < month_start].dropna(subset=["Total"])
            if not df_prev.empty:
                last_prev = float(df_prev.sort_values("Fecha").iloc[-1]["Total"])
                delta_patrimonio = float(total_patrimonio) - last_prev
    except Exception:
        delta_patrimonio = None

    # Contexto para Summary (resumen mensual)
    ctx_summary = DiarioContext(
        df_diario=df_diario,
        gi=gi_summary,
        total_patrimonio=total_patrimonio,
        delta_patrimonio=delta_patrimonio,
        ahorro_mes=ahorro_mes,
        tasa_ahorro_mes=tasa_ahorro_mes,
        color_ahorro=color_ahorro,
        is_filtered=False,
        filtered_cat=None,
        is_expense_filter=False,
        filt_all=pd.DataFrame(),
        filt_cm=pd.DataFrame(),
        filt_cat_totals=pd.Series(dtype=float),
    )

    render_summary(ctx_summary)

    # ── 1. Leemos filtros desde session_state para calcular gráficos ANTES de pintar controles al pie ──
    opts = get_available_period_options(df_diario)
    period_options = [
        "🌐 Histórico Completo",
        "📅 Año Actual",
        "📆 Últimos 12 Meses",
        "🗓️ Mes Actual",
        "🎯 Año Concreto",
        "📆 Mes Concreto",
        "⚙️ Rango Personalizado",
    ]

    analysis_options = [
        "🍩 Distribución",
        "🔍 Drill-down",
        "🌡️ Mapa de Calor",
        "🕸️ Hábitos",
        "📈 Tendencias",
        "📊 Evolución Mensual",
        "💸 Coste Real",
        "🔁 Round-up",
        "💳 Suscripciones",
        "📒 Libro Diario",
    ]

    selected_period_mode = st.session_state.get("analysis_period_mode", "🌐 Histórico Completo")
    if selected_period_mode not in period_options:
        selected_period_mode = "🌐 Histórico Completo"

    year_val = st.session_state.get("analysis_period_year")
    month_val = st.session_state.get("analysis_period_month")
    range_val = st.session_state.get("analysis_period_range")

    # Calculamos el rango de fechas [start_date, end_date] y la etiqueta
    start_date, end_date, date_label = get_date_range_from_mode(
        df_diario, selected_period_mode, year_val, month_val, range_val
    )

    # Filtrar df_diario para el análisis de ingresos/gastos
    df_diario_analysis = filter_df_by_date_range(df_diario, start_date, end_date)
    gi_analysis = calc_gastos_ingresos(df_diario_analysis)

    ctx_analysis = DiarioContext(
        df_diario=df_diario_analysis,
        gi=gi_analysis,
        total_patrimonio=total_patrimonio,
        delta_patrimonio=delta_patrimonio,
        ahorro_mes=ahorro_mes,
        tasa_ahorro_mes=tasa_ahorro_mes,
        color_ahorro=color_ahorro,
        is_filtered=False,
        filtered_cat=None,
        is_expense_filter=False,
        filt_all=pd.DataFrame(),
        filt_cm=pd.DataFrame(),
        filt_cat_totals=pd.Series(dtype=float),
        date_mode=selected_period_mode,
        date_label=date_label,
        start_date=start_date,
        end_date=end_date,
    )

    # Render Sankey Flujo de Caja
    render_sankey_view(ctx_analysis)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filtro Global por Categoría ──
    cat_incomes = gi_analysis["cat_incomes"]
    cat_expenses = gi_analysis["cat_expenses"]

    all_cat_names: list[str] = []
    if not cat_incomes.empty:
        all_cat_names.extend(cat_incomes.index.tolist())
    if not cat_expenses.empty:
        all_cat_names.extend(cat_expenses.index.tolist())

    filter_options = ["📊 Todas las categorías"] + sorted(all_cat_names)
    selected_filter = st.session_state.get("global_cat_filter", "📊 Todas las categorías")

    is_filtered = selected_filter != "📊 Todas las categorías"
    filtered_cat = selected_filter if is_filtered else None

    # Si hay filtro, calculamos los DataFrames filtrados
    if is_filtered:
        is_expense_filter = filtered_cat in (
            cat_expenses.index.tolist() if not cat_expenses.empty else []
        )
        source_df = gi_analysis["df_gastos"] if is_expense_filter else gi_analysis["df_ingresos"]
        source_df_cm = (
            gi_analysis["df_gastos_cm"] if is_expense_filter else gi_analysis["df_ingresos_cm"]
        )
        # Filtrar a la categoría y reemplazar Cuenta por Concepto
        filt_all = source_df[source_df["Cuenta"] == filtered_cat].copy()
        filt_cm = source_df_cm[source_df_cm["Cuenta"] == filtered_cat].copy()
        filt_all = enrich_with_concepto(filt_all, rename_to_cuenta=True)
        filt_cm = enrich_with_concepto(filt_cm, rename_to_cuenta=True)
        col_importe = "Debe" if is_expense_filter else "Haber"
        filt_cat_totals = filt_all.groupby("Cuenta")[col_importe].sum().sort_values(ascending=False)

        # Actualizamos el context
        ctx_analysis.is_filtered = is_filtered
        ctx_analysis.filtered_cat = filtered_cat
        ctx_analysis.is_expense_filter = is_expense_filter
        ctx_analysis.filt_all = filt_all
        ctx_analysis.filt_cm = filt_cm
        ctx_analysis.filt_cat_totals = filt_cat_totals

    active_analysis = st.session_state.get("analysis_subview", "🍩 Distribución")

    if active_analysis == "🔍 Drill-down":
        render_drilldown(ctx_analysis)
    elif active_analysis == "🌡️ Mapa de Calor":
        render_heatmap(ctx_analysis)
    elif active_analysis == "🕸️ Hábitos":
        render_habitos(ctx_analysis)
    elif active_analysis == "📈 Tendencias":
        render_sparklines(ctx_analysis)
    elif active_analysis == "📊 Evolución Mensual":
        render_evolucion(ctx_analysis)
    elif active_analysis == "💸 Coste Real":
        render_coste_real(ctx_analysis)
    elif active_analysis == "🔁 Round-up":
        render_roundup(ctx_analysis)
    elif active_analysis == "💳 Suscripciones":
        render_subscriptions(ctx_analysis)
    elif active_analysis == "📒 Libro Diario":
        render_libro(ctx_analysis)
    else:
        render_distribucion(ctx_analysis)

    # ── Barra Inferior de Controles de Análisis (Periodo Temporal + Sub-vistas) ──
    st.markdown("<br>", unsafe_allow_html=True)
    col_period, col_extra, col_popover = st.columns([4.2, 4.2, 1.6])

    with col_period:
        st.selectbox(
            "Periodo de Análisis",
            period_options,
            key="analysis_period_mode",
            help="Cambia el rango temporal para los gráficos de ingresos y gastos",
        )

    with col_extra:
        if selected_period_mode == "🎯 Año Concreto":
            st.selectbox(
                "Año a analizar",
                opts["years"],
                key="analysis_period_year",
                label_visibility="collapsed",
            )
        elif selected_period_mode == "📆 Mes Concreto":
            st.selectbox(
                "Mes a analizar",
                opts["months"],
                key="analysis_period_month",
                label_visibility="collapsed",
            )
        elif selected_period_mode == "⚙️ Rango Personalizado":
            st.date_input(
                "Rango de Fechas",
                value=(opts["min_date"], opts["max_date"]),
                min_value=opts["min_date"],
                max_value=opts["max_value"],
                key="analysis_period_range",
                label_visibility="collapsed",
            )
        else:
            st.markdown("<div style='margin-bottom: 0.2rem;'></div>", unsafe_allow_html=True)

    with col_popover:
        with st.popover("☰", help="Vistas de Análisis"):
            st.markdown(
                "<h5 style='margin:0 0 6px 0; font-family: var(--font-primary, sans-serif); color:#F4F4F5;'>📊 Módulos de Análisis</h5>",
                unsafe_allow_html=True,
            )
            current_analysis = st.session_state.get("analysis_subview", "🍩 Distribución")
            a_idx = (
                analysis_options.index(current_analysis)
                if current_analysis in analysis_options
                else 0
            )

            sel_analysis = st.radio(
                "Vista de Análisis",
                options=analysis_options,
                index=a_idx,
                key="analysis_pop_radio",
                label_visibility="collapsed",
            )
            if sel_analysis != st.session_state.get("analysis_subview"):
                st.session_state["analysis_subview"] = sel_analysis
                st.rerun()

    # ── Selector Global de Categoría (Inferior) ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.selectbox(
        "Filtrar por categoría",
        filter_options,
        key="global_cat_filter",
        label_visibility="collapsed",
    )
