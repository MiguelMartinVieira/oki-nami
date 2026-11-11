"""tabs.diario.libro — Tabla "Libro Diario" con badge de anomalías.

Muestra las últimas 50 transacciones (filtradas si hay filtro de
categoría global) enriquecidas con la columna `Alerta`:

    "⚠ inusual (+2.3σ)" si el importe del gasto sale fuera del
    comportamiento histórico de su categoría (z-score > 2).

Implementación: `services.anomaly.compute_anomalies(df_diario)` se
calcula sobre el Diario COMPLETO (para que la base estadística sea
representativa) y luego se mergea con las 50 filas que se muestran.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from constants import DATE_FORMAT
from services.anomaly import compute_anomalies, make_anomaly_label

from .context import DiarioContext


def render_libro(ctx: DiarioContext) -> None:
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    # 1. Anomalías sobre el Diario completo (no las últimas 50 — la
    #    media/std tiene que verse sobre todo el historial).
    df_anom = compute_anomalies(ctx.df_diario, z_threshold=2.0, min_samples=5)
    # Construir un lookup `idx → z_score` para las anomalías
    anomaly_lookup: dict = {}
    if not df_anom.empty:
        anomalies = df_anom[df_anom["is_anomaly"]]
        for idx, row in anomalies.iterrows():
            anomaly_lookup[idx] = float(row["z_score"])

    # 2. Filtrado por categoría global (si está activo) + últimas 50
    if not ctx.is_filtered:
        df_show = ctx.df_diario.sort_values(by="Fecha", ascending=False).head(50).copy()
    else:
        df_show = (
            ctx.df_diario[ctx.df_diario["Cuenta"] == ctx.filtered_cat]
            .sort_values(by="Fecha", ascending=False)
            .head(50)
            .copy()
        )

    # Formatear la fecha con el formato universal del dashboard (tras ordenar)
    if "Fecha" in df_show.columns:
        df_show["Fecha"] = pd.to_datetime(df_show["Fecha"], errors="coerce").dt.strftime(
            DATE_FORMAT
        )

    # 3. Inyectar columna "Alerta" con badge por fila anómala
    df_show["Alerta"] = df_show.index.map(
        lambda i: make_anomaly_label(anomaly_lookup[i]) if i in anomaly_lookup else ""
    )

    # Mostrar Alerta como primera o última columna según preferencia
    # (la dejamos al final para no romper el orden mental Fecha → Cuenta → …)
    cols_order = [c for c in df_show.columns if c != "Alerta"] + ["Alerta"]
    df_show = df_show[cols_order]

    def _color_alert(val: str) -> str:
        if not val:
            return ""
        return "color: #FF7A92; font-weight: 600;background-color: rgba(255,23,68,0.10);"

    n_anom = int((df_show["Alerta"] != "").sum())
    if n_anom > 0:
        st.caption(
            f"⚠ {n_anom} gasto{'s' if n_anom != 1 else ''} marcado{'s' if n_anom != 1 else ''} "
            "como inusual (importe fuera del rango histórico de su categoría · |z| > 2)."
        )

    st.dataframe(
        df_show.style.format("{:,.2f}", subset=["Debe", "Haber"]).map(
            _color_alert, subset=["Alerta"]
        ),
        width="stretch",
        hide_index=True,
    )
