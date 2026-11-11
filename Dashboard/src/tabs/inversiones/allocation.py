"""tabs.inversiones.allocation — Selector de series, donut/treemap y evolución."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from components.charts import build_donut, build_portfolio_treemap, build_stacked_area
from components.styles import inject_multiselect_colors
from constants import (
    COLOR_BERKSHIRE,
    COLOR_EFECTIVO_FISICO,
    COLOR_EFECTIVO_TR,
    COLOR_SP500,
    COLOR_TE_DEBEN,
)
from data.gsheets import get_historico

_ALL_SERIES = ["SP500", "Berkshire", "Trade Republic", "Efectivo", "Te Deben"]


def render_allocation(
    df_diario: pd.DataFrame,
    portfolio: dict,
    metalico_fisico: float,
) -> None:
    """Selector de series + Asset Allocation + Evolución (con modo animado)."""
    # Contenedor para renderizar los gráficos arriba del selector
    chart_container = st.container()
    st.markdown("<br>", unsafe_allow_html=True)

    col_sel, col_tog = st.columns([1, 0.2])
    with col_sel:
        selected_series = st.multiselect(
            "Mostrar series:",
            _ALL_SERIES,
            default=_ALL_SERIES,
            key="inv_series_filter",
        )
    with col_tog:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        animate_mode = st.toggle("Time-Lapse", value=False, key="inv_animate_toggle")

    inject_multiselect_colors(
        selected_series,
        {
            "SP500": COLOR_SP500,
            "Berkshire": COLOR_BERKSHIRE,
            "Trade Republic": COLOR_EFECTIVO_TR,
            "Efectivo": COLOR_EFECTIVO_FISICO,
            "Te Deben": COLOR_TE_DEBEN,
        },
    )

    series_map = {
        "SP500": {"label": "SP500", "value": portfolio["valor_fondo_eur"], "color": COLOR_SP500},
        "Berkshire": {
            "label": "Berkshire Hathaway",
            "value": portfolio["valor_brk_eur"],
            "color": COLOR_BERKSHIRE,
        },
        "Trade Republic": {
            "label": "Efectivo TR",
            "value": portfolio["tr_cash"],
            "color": COLOR_EFECTIVO_TR,
        },
        "Efectivo": {"label": "Efectivo", "value": metalico_fisico, "color": COLOR_EFECTIVO_FISICO},
        "Te Deben": {
            "label": "Te Deben",
            "value": portfolio["padres_total"],
            "color": COLOR_TE_DEBEN,
        },
    }
    donut_labels = [series_map[s]["label"] for s in selected_series if s in series_map]
    donut_values = [series_map[s]["value"] for s in selected_series if s in series_map]
    donut_colors = [series_map[s]["color"] for s in selected_series if s in series_map]
    valor_visible = sum(donut_values)

    with chart_container:
        df_plot = _build_portfolio_history(df_diario)

        if not animate_mode:
            _render_static(
                df_plot, selected_series, donut_labels, donut_values, donut_colors, valor_visible
            )
        else:
            _render_timelapse()


def _render_static(
    df_plot: pd.DataFrame | None,
    selected_series: list[str],
    donut_labels: list[str],
    donut_values: list[float],
    donut_colors: list[str],
    valor_visible: float,
) -> None:
    c_chart1, c_chart2 = st.columns([1, 1.5])
    with c_chart1:
        chart1_container = st.container()

        chart_type = st.radio(
            "Tipo de visualización",
            ["Donut", "Treemap"],
            horizontal=True,
            label_visibility="collapsed",
            key="alloc_chart_type",
        )

        with chart1_container:
            if selected_series:
                if chart_type == "Donut":
                    fig_donut = build_donut(
                        donut_labels, donut_values, donut_colors, f"{valor_visible:,.0f} €"
                    )
                    if fig_donut:
                        st.plotly_chart(fig_donut, width="stretch")
                    else:
                        st.info("No hay activos positivos para mostrar en el Donut.")
                else:
                    root_name = f"Patrimonio<br>({valor_visible:,.0f} €)"
                    df_tree = pd.DataFrame(
                        {
                            "Activo": donut_labels,
                            "Valor": donut_values,
                            "Color": donut_colors,
                            "Raíz": root_name,
                        }
                    )
                    fig_tree = build_portfolio_treemap(df_tree, root_name, "rgba(0,0,0,0)")
                    if fig_tree:
                        st.plotly_chart(fig_tree, width="stretch")
                    else:
                        st.info("No hay activos positivos para mostrar en el Treemap.")
            else:
                st.info("Selecciona series para ver la distribución.")

    with c_chart2:
        st.markdown("<div style='min-height: 35px;'></div>", unsafe_allow_html=True)
        if df_plot is not None:
            fig_area = build_stacked_area(df_plot, selected_series)
            if fig_area:
                st.plotly_chart(fig_area, width="stretch")
            elif not selected_series:
                st.info("Selecciona al menos una serie para mostrar el gráfico.")
        else:
            from components.skeleton import render_skeleton_chart

            render_skeleton_chart(height=540)


def _render_timelapse() -> None:
    from constants import CACHE_DIR

    frame_path = Path(CACHE_DIR) / "frames" / "timelapse.webp"

    if frame_path.exists():
        import base64

        with open(frame_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(
            f'<img src="data:image/webp;base64,{b64}" style="width: 100%; object-fit: contain;">',
            unsafe_allow_html=True,
        )
    else:
        st.info("El archivo animado del time-lapse no está disponible en la caché local.")


def _build_portfolio_history(df_diario: pd.DataFrame) -> pd.DataFrame | None:
    df_hist = get_historico()
    if df_hist.empty or "Fecha" not in df_hist.columns:
        return None
    df_plot = df_hist.copy().rename(
        columns={
            "Fecha": "Date",
            "Vanguard Value": "SP500",
            "BRK Value": "Berkshire",
            "Efectivo TR": "Trade Republic",
            "Efectivo Fisico": "Efectivo",
        }
    )
    if "Date" in df_plot.columns:
        df_plot["Date"] = pd.to_datetime(df_plot["Date"])
    for col in ("SP500", "Berkshire", "Trade Republic", "Efectivo", "Te Deben"):
        if col in df_plot.columns:
            df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")
    return df_plot
