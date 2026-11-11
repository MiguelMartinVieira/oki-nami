"""tabs.diario.subscriptions — Pestaña "💳 Suscripciones".

Muestra los gastos recurrentes detectados automáticamente (Netflix,
gimnasio, IPTV, seguros, etc.) con coste anual estimado y próximo
cargo previsto. El objetivo es hacer visibles las "fugas" silenciosas.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_card import render_metric_card
from constants import COLOR_EFECTIVO_TR, COLOR_GASTOS
from services.subscriptions import detect_subscriptions

from .context import DiarioContext

_INTERVAL_COLOR = {
    "Semanal": "#FF4D6D",
    "Mensual": COLOR_GASTOS,
    "Trimestral": "#FB923C",
    "Anual": COLOR_EFECTIVO_TR,
}


def render_subscriptions(ctx: DiarioContext) -> None:
    df_subs = detect_subscriptions(ctx.df_diario, lookback_days=365, min_occurrences=3)

    if df_subs.empty:
        st.caption(
            "No se han detectado suscripciones recurrentes en los últimos "
            "12 meses. Se requieren al menos 3 cargos con descripción similar "
            "e intervalo regular (semanal / mensual / trimestral / anual)."
        )
        return

    total_anual = float(df_subs["Coste anual est."].sum())
    n_subs = len(df_subs)
    coste_mensual_equiv = total_anual / 12.0

    # ── 3 metric cards: visión rápida ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            render_metric_card(
                "COSTE ANUAL ESTIMADO",
                f"{total_anual:,.2f} €",
                color=COLOR_GASTOS,
                bg_color=COLOR_GASTOS,
                subtitle=f"{n_subs} suscripci{'ones' if n_subs != 1 else 'ón'} activa{'s' if n_subs != 1 else ''}",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card(
                "EQUIVALENTE MENSUAL",
                f"{coste_mensual_equiv:,.2f} €",
                color="#A1A1AA",
                subtitle="Anual ÷ 12",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        # Próxima carga (la más cercana en el futuro)
        proxima = df_subs.copy()
        proxima["dias"] = (
            pd.to_datetime(proxima["Próximo pago"]) - pd.Timestamp.today().normalize()
        ).dt.days
        prox_pos = proxima[proxima["dias"] >= 0].sort_values("dias")
        if not prox_pos.empty:
            siguiente = prox_pos.iloc[0]
            sub_label = f"{siguiente['Nombre'][:32]} · {siguiente['Importe medio']:,.2f} €"
            st.markdown(
                render_metric_card(
                    "PRÓXIMO CARGO",
                    f"En {int(siguiente['dias'])} días",
                    color=COLOR_EFECTIVO_TR,
                    subtitle=sub_label,
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                render_metric_card(
                    "PRÓXIMO CARGO",
                    "—",
                    color="#71717A",
                    subtitle="Sin previsión activa",
                ),
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

    # ── Tabla detallada ──
    df_show = df_subs.copy()
    df_show["Última fecha"] = pd.to_datetime(df_show["Última fecha"]).dt.strftime("%d %b %Y")
    df_show["Próximo pago"] = pd.to_datetime(df_show["Próximo pago"]).dt.strftime("%d %b %Y")
    df_show = df_show.drop(columns=["Fingerprint"])

    def _color_intervalo(val: str) -> str:
        color = _INTERVAL_COLOR.get(val, "#A1A1AA")
        return f"color: {color}; font-weight: 600;background-color: rgba(255,255,255,0.03);"

    styled = df_show.style.format(
        {
            "Importe medio": "{:,.2f} €",
            "Coste anual est.": "{:,.2f} €",
        }
    ).map(_color_intervalo, subset=["Intervalo"])
    st.dataframe(styled, width="stretch", hide_index=True)

    # ── Hint accionable ──
    if total_anual > 0:
        st.caption(
            f"💡 Si cancelaras todas las suscripciones marcadas como recurrentes "
            f"ahorrarías {total_anual:,.0f} €/año "
            f"({coste_mensual_equiv:,.2f} €/mes). Revisa cuáles usas de verdad."
        )
