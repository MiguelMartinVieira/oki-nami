"""
fiscal_sim.py — Componente para el simulador y análisis de impacto fiscal.
"""

import pandas as pd
import streamlit as st

from components.metric_card import render_metric_card
from constants import DATE_FORMAT
from services.analytics import build_fifo_lots, simulate_fifo_sale
from services.projections import TRAMOS_IRPF as _TRAMOS_IRPF
from services.projections import calc_tax_spain


def render_fiscal_section(
    asset_name: str,
    asset_color: str,
    total_invested: float,
    valor_actual: float,
    extra_class: str,
    df_account: pd.DataFrame | None = None,
    precio_actual_eur: float | None = None,
    cost_adjustment: float = 0.0,
) -> None:
    """
    Renderiza la sección de impacto fiscal de un activo:
    Plusvalía latente · Cuota estimada · Neto tras impuestos · Tipo efectivo.
    También incluye un simulador deslizable "¿Qué pasa si vendiera X €?".
    """
    plusvalia = valor_actual - total_invested
    cuota = calc_tax_spain(plusvalia)
    neto = plusvalia - cuota
    tipo_efectivo = (cuota / plusvalia * 100) if plusvalia > 0 else 0.0

    cf1, cf2, cf3, cf4 = st.columns(4)

    pv_sign = "+" if plusvalia >= 0 else ""
    pv_color = "#00C853" if plusvalia >= 0 else "#D50000"

    with cf1:
        st.markdown(
            render_metric_card(
                "Plusvalía Latente",
                f"{pv_sign}{plusvalia:,.2f} €",
                bg_color=pv_color,
                subtitle="Valor actual − Coste total",
                extra_class="fiscal-card",
            ),
            unsafe_allow_html=True,
        )

    with cf2:
        st.markdown(
            render_metric_card(
                "Cuota Estimada IRPF",
                f"−{cuota:,.2f} €",
                bg_color="#475569",
                subtitle=f"Tipo efectivo: {tipo_efectivo:.1f} %",
                extra_class="fiscal-card",
            ),
            unsafe_allow_html=True,
        )

    with cf3:
        neto_sign = "+" if neto >= 0 else ""
        neto_color = "#00C853" if neto >= 0 else "#D50000"
        st.markdown(
            render_metric_card(
                "Neto Tras Impuestos",
                f"{neto_sign}{neto:,.2f} €",
                bg_color=neto_color,
                subtitle="Plusvalía − Cuota",
                extra_class="fiscal-card",
            ),
            unsafe_allow_html=True,
        )

    with cf4:
        # Desglose de tramos
        tramos_lines = []
        remaining = plusvalia
        for limit, rate in _TRAMOS_IRPF:
            if remaining <= 0:
                break
            taxable = min(remaining, limit)
            tramos_lines.append(
                f'<div style="font-size:0.72rem; color:rgba(255,255,255,0.9); line-height:1.2; margin-top:2px;">'
                f"{rate * 100:.0f}% de {taxable:,.0f} € = <b>{taxable * rate:,.0f} €</b></div>"
            )
            remaining -= taxable
        tramos_html = (
            "".join(tramos_lines)
            if tramos_lines
            else '<div style="font-size:0.8rem; color:rgba(255,255,255,0.7);">Sin plusvalías</div>'
        )
        st.markdown(
            render_metric_card(
                "Desglose por Tramos",
                "",
                bg_color="#334155",
                extra_html=f'<div style="margin-top:2px; display:flex; flex-direction:column; justify-content:center; flex-grow:1;">{tramos_html}</div>',
                extra_class="fiscal-card",
            ),
            unsafe_allow_html=True,
        )

    # ── Cost-basis planning: lotes FIFO + simulador de venta ──
    if df_account is not None and precio_actual_eur is not None and not df_account.empty:
        _render_fifo_section(
            asset_name, asset_color, df_account, precio_actual_eur, cost_adjustment=cost_adjustment
        )


def _render_fifo_section(
    asset_name: str,
    asset_color: str,
    df_account: pd.DataFrame,
    precio_actual_eur: float,
    cost_adjustment: float = 0.0,
) -> None:
    """
    Tabla de lotes FIFO + simulador "¿qué lotes consume si vendo X €?".

    En España, FIFO es **obligatorio** para acciones/fondos del mismo ISIN,
    por lo que esta tabla refleja el orden real en el que Hacienda asume
    que vendes — no una elección.
    """
    st.markdown("---")

    df_lots = build_fifo_lots(
        df_account, precio_actual_eur=precio_actual_eur, cost_adjustment=cost_adjustment
    )
    if df_lots.empty:
        st.info("No hay lotes con metadatos `quantity:` para construir la tabla FIFO.")
        return

    # Tabla con format y colorbar
    df_show = df_lots.copy()
    df_show["Fecha"] = pd.to_datetime(df_show["Fecha"], errors="coerce").dt.strftime(DATE_FORMAT)

    def _color_pnl(v):
        try:
            f = float(v)
            return "color:#00C853;font-weight:600" if f >= 0 else "color:#D50000;font-weight:600"
        except (TypeError, ValueError):
            return ""

    st.dataframe(
        df_show.style.format(
            {
                "Acciones": "{:,.6f}",
                "Coste (€)": "{:,.2f}",
                "Precio Medio (€)": "{:,.2f}",
                "Valor Actual (€)": "{:,.2f}",
                "P&L (€)": "{:+,.2f}",
                "P&L (%)": "{:+.2f}%",
            }
        ).map(_color_pnl, subset=["P&L (€)", "P&L (%)"]),
        width="stretch",
        hide_index=True,
    )

    # ── Simulador FIFO de venta ──
    valor_total_lotes = float(df_lots["Valor Actual (€)"].sum())
    with st.expander("🔢 Simulador FIFO — ¿Qué lotes consumes si vendes X €?"):
        importe_venta = st.slider(
            "Importe a vender (€)",
            min_value=0.0,
            max_value=(float(round(valor_total_lotes, 2)) if valor_total_lotes > 0 else 1.0),
            value=(float(round(valor_total_lotes / 2, 2)) if valor_total_lotes > 0 else 0.0),
            step=10.0,
            key=f"fifo_sim_{asset_name}",
            format="%.2f €",
        )

        sim = simulate_fifo_sale(df_lots, importe_venta)
        cuota_sim = calc_tax_spain(sim["plusvalia"])
        neto_sim = sim["plusvalia"] - cuota_sim
        tipo_efectivo_sim = (cuota_sim / sim["plusvalia"] * 100.0) if sim["plusvalia"] > 0 else 0.0

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Lotes consumidos", len(sim["lotes_consumidos"]))
            st.metric("Acciones vendidas", f"{sim['acciones_total']:,.6f}")
        with col_s2:
            st.metric("Coste asignado (FIFO)", f"{sim['coste_total']:,.2f} €")
            st.metric("Valor de venta", f"{sim['valor_total']:,.2f} €")
        with col_s3:
            pv_sign = "+" if sim["plusvalia"] >= 0 else ""
            st.metric(
                "Plusvalía FIFO",
                f"{pv_sign}{sim['plusvalia']:,.2f} €",
                delta=f"Tipo efectivo: {tipo_efectivo_sim:.1f}%",
            )
            st.metric(
                "Neto en bolsillo",
                f"{neto_sim:,.2f} €",
                delta=f"−{cuota_sim:,.2f} € IRPF",
                delta_color="inverse",
            )

        if sim["lotes_consumidos"]:
            df_consumed = pd.DataFrame(sim["lotes_consumidos"])
            df_consumed["fecha"] = pd.to_datetime(
                df_consumed["fecha"], errors="coerce"
            ).dt.strftime(DATE_FORMAT)
            df_consumed = df_consumed.rename(
                columns={
                    "fecha": "Fecha lote",
                    "acciones": "Acciones",
                    "coste": "Coste asignado (€)",
                    "valor": "Valor venta (€)",
                    "plusvalia": "Plusvalía (€)",
                }
            )
            st.caption("Desglose del consumo lote a lote (orden FIFO):")
            st.dataframe(
                df_consumed.style.format(
                    {
                        "Acciones": "{:,.6f}",
                        "Coste asignado (€)": "{:,.2f}",
                        "Valor venta (€)": "{:,.2f}",
                        "Plusvalía (€)": "{:+,.2f}",
                    }
                ),
                width="stretch",
                hide_index=True,
            )
