"""tabs.inversiones.ops — Últimas operaciones de inversión + historial fundacional."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from constants import DATE_FORMAT
from data.historical_investments import get_historical_investments
from services.analytics import calc_pnl_op
from services.utils import extract_quantity


def render_ops_and_history(df_diario: pd.DataFrame, portfolio: dict) -> None:
    tab_ops, tab_hist = st.tabs(["📊 Últimas Operaciones", "📖 Historial de Inversiones"])
    with tab_ops:
        _render_ops(df_diario, portfolio)
    with tab_hist:
        _render_history()


def _render_ops(df_diario: pd.DataFrame, portfolio: dict) -> None:
    st.subheader("Últimas Operaciones de Inversión")
    df_ops = df_diario[df_diario["Nº Cuenta"].str.startswith(("14", "31"))].copy()
    if df_ops.empty:
        st.info("Historial vacío.")
        return

    df_ops = df_ops.sort_values(by="Fecha", ascending=False).copy()
    df_ops[["P&L (€)", "P&L (%)"]] = df_ops.apply(
        lambda r: pd.Series(
            calc_pnl_op(
                r,
                portfolio["precio_brk_usd"],
                portfolio["usd_to_eur"],
                portfolio["precio_fondo"],
                extract_quantity,
            )
        ),
        axis=1,
    )
    df_ops["Fecha"] = pd.to_datetime(df_ops["Fecha"], errors="coerce").dt.strftime(DATE_FORMAT)

    def _color_pnl(val):
        if pd.isna(val) or val == "":
            return ""
        try:
            v = float(val)
            return (
                "color: #00C853; font-weight:600" if v >= 0 else "color: #D50000; font-weight:600"
            )
        except Exception:
            return ""

    cols_show = ["Fecha", "Categoría", "Descripción", "Debe", "P&L (€)", "P&L (%)"]
    df_show = df_ops[cols_show].head(15).copy()
    df_show["P&L (€)"] = df_show["P&L (€)"].apply(
        lambda x: f"+{x:,.2f}" if pd.notna(x) and x >= 0 else (f"{x:,.2f}" if pd.notna(x) else "—")
    )
    df_show["P&L (%)"] = df_show["P&L (%)"].apply(
        lambda x: f"+{x:.2f}%" if pd.notna(x) and x >= 0 else (f"{x:.2f}%" if pd.notna(x) else "—")
    )

    st.dataframe(
        df_show.style.format("{:,.2f}", subset=["Debe"]).map(
            _color_pnl, subset=["P&L (€)", "P&L (%)"]
        ),
        width="stretch",
        hide_index=True,
    )


def _render_history() -> None:
    st.subheader("Historial de Inversiones Anteriores (Pre-Dashboard)")
    st.caption(
        "Operaciones fundacionales que componen el coste base actual y los traspasos exentos."
    )
    df_hist = get_historical_investments()
    df_hist["Fecha"] = df_hist["Fecha"].dt.strftime(DATE_FORMAT)

    def _color_status(val):
        if val == "Activa":
            return "color: #00C853; font-weight:600; background-color: rgba(0,200,83,0.12)"
        elif val == "Completada":
            return "color: #A1A1AA; font-weight:400"
        return ""

    st.dataframe(
        df_hist.style.format("{:,.2f} €", subset=["Importe (€)"]).map(
            _color_status, subset=["Estado"]
        ),
        width="stretch",
        hide_index=True,
    )
