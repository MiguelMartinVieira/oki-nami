import streamlit as st

from components.charts import build_sankey
from services.accounting import calc_gastos_ingresos

from .context import DiarioContext


def render_sankey_view(ctx: DiarioContext) -> None:
    # Botón hamburguesa minimalista (☰) en la esquina superior derecha del Sankey
    _col_sankey_title, col_sankey_pop = st.columns([9.2, 0.8])
    with col_sankey_pop:
        with st.popover("☰", help="Configuración de Vista Sankey"):
            st.markdown(
                "<h5 style='margin:0 0 6px 0; font-family: var(--font-primary, sans-serif); color:#F4F4F5;'>📅 Periodo</h5>",
                unsafe_allow_html=True,
            )
            current_period = st.session_state.get("sankey_period", "Histórico")
            period_options = ["Mes Actual", "Histórico", "Personalizado"]
            p_idx = period_options.index(current_period) if current_period in period_options else 1

            sel_period = st.radio(
                "Periodo",
                options=period_options,
                index=p_idx,
                key="sankey_pop_period",
                label_visibility="collapsed",
            )
            if sel_period != st.session_state.get("sankey_period"):
                st.session_state["sankey_period"] = sel_period
                st.rerun()

            st.markdown(
                "<h5 style='margin:10px 0 6px 0; font-family: var(--font-primary, sans-serif); color:#F4F4F5;'>📊 Vista Sankey</h5>",
                unsafe_allow_html=True,
            )
            current_mode = st.session_state.get("sankey_mode_label", "Desglose Detallado")
            mode_options = ["Visión General", "Desglose Detallado", "Solo Gastos"]
            m_idx = mode_options.index(current_mode) if current_mode in mode_options else 1

            sel_mode = st.radio(
                "Granularidad Sankey",
                options=mode_options,
                index=m_idx,
                key="sankey_pop_mode",
                label_visibility="collapsed",
            )
            if sel_mode != st.session_state.get("sankey_mode_label"):
                st.session_state["sankey_mode_label"] = sel_mode
                mode_map = {
                    "Visión General": "categories",
                    "Desglose Detallado": "detailed",
                    "Solo Gastos": "expenses",
                }
                st.session_state["sankey_granularity_mode"] = mode_map.get(sel_mode, "detailed")
                st.rerun()

    period = st.session_state.get("sankey_period", "Histórico")
    s_mode = st.session_state.get("sankey_granularity_mode", "detailed")

    gi = ctx.gi

    if period == "Mes Actual":
        fig_sankey_cm = build_sankey(
            gi["cat_incomes_cm"],
            gi["cat_expenses_cm"],
            gi["cm_ingresos"],
            gi["cm_gastos"],
            df_ingresos=gi["df_ingresos_cm"],
            df_gastos=gi["df_gastos_cm"],
            total_inversiones=gi["total_inversiones_cm"],
            df_inversiones=gi["df_inversiones_cm"],
            mode=s_mode,
        )
        if fig_sankey_cm:
            st.plotly_chart(
                fig_sankey_cm, width="stretch", config={"responsive": True}, key="sankey_mes_actual"
            )
        else:
            st.info("No hay flujos de ingresos/gastos registrados en el mes actual.")

    elif period == "Histórico":
        fig_sankey = build_sankey(
            gi["cat_incomes"],
            gi["cat_expenses"],
            gi["total_hist_ingresos"],
            gi["total_hist_gastos"],
            df_ingresos=gi["df_ingresos"],
            df_gastos=gi["df_gastos"],
            total_inversiones=gi["total_inversiones"],
            df_inversiones=gi["df_inversiones"],
            mode=s_mode,
        )
        if fig_sankey:
            st.plotly_chart(
                fig_sankey, width="stretch", config={"responsive": True}, key="sankey_historico"
            )
        else:
            st.info("No hay flujos de ingresos/gastos en el histórico.")

    else:
        col_start, col_end = st.columns(2)
        min_date = ctx.df_diario["Fecha"].min().date()
        max_date = ctx.df_diario["Fecha"].max().date()
        with col_start:
            start_date = st.date_input(
                "Fecha Inicio",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key="sankey_start",
            )
        with col_end:
            end_date = st.date_input(
                "Fecha Fin",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key="sankey_end",
            )

        if start_date <= end_date:
            df_custom = ctx.df_diario[
                (ctx.df_diario["Fecha"].dt.date >= start_date)
                & (ctx.df_diario["Fecha"].dt.date <= end_date)
            ].copy()
            if not df_custom.empty:
                gi_custom = calc_gastos_ingresos(df_custom)
                fig_sankey_custom = build_sankey(
                    gi_custom["cat_incomes"],
                    gi_custom["cat_expenses"],
                    gi_custom["total_hist_ingresos"],
                    gi_custom["total_hist_gastos"],
                    df_ingresos=gi_custom["df_ingresos"],
                    df_gastos=gi_custom["df_gastos"],
                    total_inversiones=gi_custom["total_inversiones"],
                    df_inversiones=gi_custom["df_inversiones"],
                    mode=s_mode,
                )
                if fig_sankey_custom:
                    st.plotly_chart(
                        fig_sankey_custom,
                        width="stretch",
                        config={"responsive": True},
                        key="sankey_custom",
                    )
                else:
                    st.info("No hay flujos de ingresos/gastos en este rango de fechas.")
            else:
                st.info("No hay movimientos registrados en este periodo.")
        else:
            st.error("La fecha de inicio debe ser anterior o igual a la fecha de fin.")
