import pandas as pd
import plotly.graph_objects as go

from constants import (
    COLOR_GASTOS,
    COLOR_INGRESOS,
)

from .base import _LAYOUT_BASE, _apply_crystal_aesthetic


def build_expense_radar_relative(
    df_gastos: pd.DataFrame, df_gastos_hist: pd.DataFrame
) -> go.Figure | None:
    """
    Radar chart que compara los gastos por categoría del mes actual
    frente a la media histórica mensual. (Vista Relativa)
    """
    if df_gastos.empty or df_gastos_hist.empty:
        return None

    # Mes actual (suma por categoría)
    current = df_gastos.groupby("Cuenta")["Debe"].sum().reset_index()
    current = current.rename(columns={"Debe": "Mes Actual"})

    # Media histórica (suma por cuenta y mes, luego media)
    hist_monthly = df_gastos_hist.groupby(["Mes", "Cuenta"])["Debe"].sum().reset_index()
    hist_mean = hist_monthly.groupby("Cuenta")["Debe"].mean().reset_index()
    hist_mean = hist_mean.rename(columns={"Debe": "Media Histórica"})

    # Unir ambos
    df_radar = pd.merge(current, hist_mean, on="Cuenta", how="outer").fillna(0)

    # Filtrar categorías que no tienen ni gasto actual ni histórico
    df_radar = df_radar[(df_radar["Mes Actual"] > 0) | (df_radar["Media Histórica"] > 0)]

    if df_radar.empty:
        return None

    categories = df_radar["Cuenta"].tolist()
    # Cerrar el radar añadiendo el primer elemento al final
    categories.append(categories[0])

    val_current = df_radar["Mes Actual"].tolist()
    val_current.append(val_current[0])

    val_hist = df_radar["Media Histórica"].tolist()
    val_hist.append(val_hist[0])

    # Normalizar al % sobre la media histórica (media = 100%)
    # Así cada categoría tiene su propia escala y forma un polígono regular
    r_hist = []
    r_current = []
    for c, h in zip(val_current, val_hist, strict=False):
        if h > 0:
            r_hist.append(100.0)
            r_current.append(min((c / h) * 100.0, 250.0))  # Capear al 250% visualmente
        else:
            r_hist.append(10.0)  # pequeño valor base si no hay histórico
            r_current.append(250.0 if c > 0 else 0.0)

    fig = go.Figure()

    # Histórico (Gris claro) - Ahora forma un polígono regular
    fig.add_trace(
        go.Scatterpolar(
            r=r_hist,
            theta=categories,
            customdata=val_hist,
            fill="toself",
            name="Media Histórica",
            line=dict(color="rgba(100, 116, 139, 0.5)", dash="dash", width=1.5),
            fillcolor="rgba(100, 116, 139, 0.08)",
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Media)<extra></extra>",
        )
    )

    # Extraemos RGB de COLOR_GASTOS para la transparencia
    if COLOR_GASTOS.startswith("#"):
        r, g, b = int(COLOR_GASTOS[1:3], 16), int(COLOR_GASTOS[3:5], 16), int(COLOR_GASTOS[5:7], 16)
        fill_rgba = f"rgba({r}, {g}, {b}, 0.35)"
    else:
        fill_rgba = "rgba(244, 63, 94, 0.35)"

    # Mes Actual (Color dinámico)
    fig.add_trace(
        go.Scatterpolar(
            r=r_current,
            theta=categories,
            customdata=val_current,
            fill="toself",
            name="Mes Actual",
            line=dict(color=COLOR_GASTOS, width=2),
            fillcolor=fill_rgba,
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Actual)<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,
                ticks="",
                showline=False,
                range=[-35, 250],
            ),
            angularaxis=dict(tickfont=dict(size=11, color="#71717A"), showline=False),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=30, b=40, l=40, r=40),
        **_LAYOUT_BASE,
    )
    return fig


def build_expense_radar_absolute(
    df_gastos: pd.DataFrame, df_gastos_hist: pd.DataFrame
) -> go.Figure | None:
    """
    Gráfico de radar comparando gastos del mes actual vs media histórica.
    Vista absoluta (euros) suavizada con raíz cuadrada para atenuar outliers.
    """
    # 1. Agrupar gastos del mes actual
    current = df_gastos.groupby("Cuenta")["Debe"].sum().reset_index()
    current = current.rename(columns={"Debe": "Mes Actual"})

    # 2. Calcular media mensual histórica
    df_gastos_hist = df_gastos_hist.copy()
    df_gastos_hist["Mes"] = df_gastos_hist["Fecha"].dt.to_period("M")
    hist_monthly = df_gastos_hist.groupby(["Mes", "Cuenta"])["Debe"].sum().reset_index()
    hist_mean = hist_monthly.groupby("Cuenta")["Debe"].mean().reset_index()
    hist_mean = hist_mean.rename(columns={"Debe": "Media Histórica"})

    # Unir ambos
    df_radar = pd.merge(current, hist_mean, on="Cuenta", how="outer").fillna(0)

    # Filtrar categorías que no tienen ni gasto actual ni histórico
    df_radar = df_radar[(df_radar["Mes Actual"] > 0) | (df_radar["Media Histórica"] > 0)]

    if df_radar.empty:
        return None

    categories = df_radar["Cuenta"].tolist()
    # Cerrar el radar añadiendo el primer elemento al final
    categories.append(categories[0])

    val_current = df_radar["Mes Actual"].tolist()
    val_current.append(val_current[0])

    val_hist = df_radar["Media Histórica"].tolist()
    val_hist.append(val_hist[0])

    fig = go.Figure()

    # Histórico (Gris claro)
    fig.add_trace(
        go.Scatterpolar(
            r=[v**0.5 for v in val_hist],
            theta=categories,
            customdata=val_hist,
            fill="toself",
            name="Media Histórica",
            line=dict(color="rgba(100, 116, 139, 0.5)", dash="dash", width=1.5),
            fillcolor="rgba(100, 116, 139, 0.08)",
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Media)<extra></extra>",
        )
    )

    # Extraemos RGB de COLOR_GASTOS para la transparencia
    if COLOR_GASTOS.startswith("#"):
        r, g, b = int(COLOR_GASTOS[1:3], 16), int(COLOR_GASTOS[3:5], 16), int(COLOR_GASTOS[5:7], 16)
        fill_rgba = f"rgba({r}, {g}, {b}, 0.35)"
    else:
        fill_rgba = "rgba(244, 63, 94, 0.35)"

    # Mes Actual (Color dinámico)
    fig.add_trace(
        go.Scatterpolar(
            r=[v**0.5 for v in val_current],
            theta=categories,
            customdata=val_current,
            fill="toself",
            name="Mes Actual",
            line=dict(color=COLOR_GASTOS, width=2),
            fillcolor=fill_rgba,
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Actual)<extra></extra>",
        )
    )

    max_val = max(
        max([v**0.5 for v in val_hist], default=0),
        max([v**0.5 for v in val_current], default=0),
    )
    if max_val <= 0:
        max_val = 1.0

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,
                ticks="",
                showline=False,
                range=[-0.18 * max_val, max_val],
            ),
            angularaxis=dict(tickfont=dict(size=11, color="#71717A"), showline=False),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=30, b=40, l=40, r=40),
        **_LAYOUT_BASE,
    )
    return fig


def build_radar_mom(
    df_current_month: pd.DataFrame,
    df_all: pd.DataFrame,
    col_importe: str,
    is_expense: bool,
) -> go.Figure | None:
    """
    Radar chart de variación mes-sobre-mes.

    Compara el perfil del mes actual contra el mes inmediatamente anterior,
    revelando cambios de comportamiento a corto plazo (a diferencia de los
    otros radars que comparan contra la media histórica a largo plazo).

    Usa escala raíz cuadrada (como el radar absoluto) para atenuar outliers.
    - Gastos: rojo para mes actual.
    - Ingresos: verde para mes actual.

    Args:
        df_current_month: Movimientos del mes actual.
        df_all: Movimientos históricos completos (incluyendo mes actual).
        col_importe: Columna de importe ("Debe" para gastos, "Haber" para ingresos).
        is_expense: True para gastos, False para ingresos.
    """
    if df_current_month.empty or df_all.empty:
        return None

    # ── Mes actual ──
    current = df_current_month.groupby("Cuenta")[col_importe].sum().reset_index()
    current = current.rename(columns={col_importe: "Mes Actual"})

    # ── Mes anterior ──
    all_months = df_all["Mes"].dropna().unique()
    if len(all_months) < 2:
        return None

    sorted_months = sorted(all_months)
    prev_month = sorted_months[-2]
    df_prev = df_all[df_all["Mes"] == prev_month]
    previous = df_prev.groupby("Cuenta")[col_importe].sum().reset_index()
    previous = previous.rename(columns={col_importe: "Mes Anterior"})

    # ── Unir ──
    df_radar = pd.merge(current, previous, on="Cuenta", how="outer").fillna(0)
    df_radar = df_radar[(df_radar["Mes Actual"] > 0) | (df_radar["Mes Anterior"] > 0)]

    if df_radar.empty:
        return None

    categories = df_radar["Cuenta"].tolist()
    categories.append(categories[0])

    val_current = df_radar["Mes Actual"].tolist()
    val_current.append(val_current[0])

    val_prev = df_radar["Mes Anterior"].tolist()
    val_prev.append(val_prev[0])

    # Color principal según tipo
    if is_expense:
        main_color = COLOR_GASTOS
        fill_color = "rgba(244, 63, 94, 0.35)"
    else:
        main_color = COLOR_INGRESOS
        fill_color = "rgba(16, 185, 129, 0.30)"

    # Nombre legible del mes anterior
    prev_label = (
        prev_month.strftime("%b %Y") if hasattr(prev_month, "strftime") else str(prev_month)
    )

    fig = go.Figure()

    # Mes Anterior (gris punteado)
    fig.add_trace(
        go.Scatterpolar(
            r=[v**0.5 for v in val_prev],
            theta=categories,
            customdata=val_prev,
            fill="toself",
            name=f"{prev_label}",
            line=dict(color="rgba(100, 116, 139, 0.5)", dash="dash", width=1.5),
            fillcolor="rgba(100, 116, 139, 0.08)",
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Anterior)<extra></extra>",
        )
    )

    # Mes Actual (color principal)
    fig.add_trace(
        go.Scatterpolar(
            r=[v**0.5 for v in val_current],
            theta=categories,
            customdata=val_current,
            fill="toself",
            name="Mes Actual",
            line=dict(color=main_color, width=2),
            fillcolor=fill_color,
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Actual)<extra></extra>",
        )
    )

    max_val = max(
        max([v**0.5 for v in val_prev], default=0),
        max([v**0.5 for v in val_current], default=0),
    )
    if max_val <= 0:
        max_val = 1.0

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,
                ticks="",
                showline=False,
                range=[-0.18 * max_val, max_val],
            ),
            angularaxis=dict(tickfont=dict(size=11, color="#71717A"), showline=False),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=30, b=40, l=40, r=40),
        **_LAYOUT_BASE,
    )
    return fig


def build_income_radar_absolute(
    df_ingresos_cm: pd.DataFrame,
    df_ingresos_hist: pd.DataFrame,
) -> go.Figure | None:
    """
    Radar chart comparando ingresos del mes actual vs media histórica.
    Vista absoluta (euros) suavizada con raíz cuadrada para atenuar outliers.
    """
    if df_ingresos_cm.empty or df_ingresos_hist.empty:
        return None

    # Mes actual
    current = df_ingresos_cm.groupby("Cuenta")["Haber"].sum().reset_index()
    current = current.rename(columns={"Haber": "Mes Actual"})

    # Media histórica
    df_hist = df_ingresos_hist.copy()
    df_hist["Mes"] = df_hist["Fecha"].dt.to_period("M")
    hist_monthly = df_hist.groupby(["Mes", "Cuenta"])["Haber"].sum().reset_index()
    hist_mean = hist_monthly.groupby("Cuenta")["Haber"].mean().reset_index()
    hist_mean = hist_mean.rename(columns={"Haber": "Media Histórica"})

    df_radar = pd.merge(current, hist_mean, on="Cuenta", how="outer").fillna(0)
    df_radar = df_radar[(df_radar["Mes Actual"] > 0) | (df_radar["Media Histórica"] > 0)]

    if df_radar.empty:
        return None

    categories = df_radar["Cuenta"].tolist()
    categories.append(categories[0])

    val_current = df_radar["Mes Actual"].tolist()
    val_current.append(val_current[0])

    val_hist = df_radar["Media Histórica"].tolist()
    val_hist.append(val_hist[0])

    # Extraemos RGB de COLOR_INGRESOS para la transparencia
    if COLOR_INGRESOS.startswith("#"):
        r, g, b = (
            int(COLOR_INGRESOS[1:3], 16),
            int(COLOR_INGRESOS[3:5], 16),
            int(COLOR_INGRESOS[5:7], 16),
        )
        fill_rgba = f"rgba({r}, {g}, {b}, 0.30)"
    else:
        fill_rgba = "rgba(16, 185, 129, 0.30)"

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=[v**0.5 for v in val_hist],
            theta=categories,
            customdata=val_hist,
            fill="toself",
            name="Media Histórica",
            line=dict(color="rgba(100, 116, 139, 0.5)", dash="dash", width=1.5),
            fillcolor="rgba(100, 116, 139, 0.08)",
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Media)<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[v**0.5 for v in val_current],
            theta=categories,
            customdata=val_current,
            fill="toself",
            name="Mes Actual",
            line=dict(color=COLOR_INGRESOS, width=2),
            fillcolor=fill_rgba,
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Actual)<extra></extra>",
        )
    )

    max_val = max(
        max([v**0.5 for v in val_hist], default=0),
        max([v**0.5 for v in val_current], default=0),
    )
    if max_val <= 0:
        max_val = 1.0

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,
                ticks="",
                showline=False,
                range=[-0.18 * max_val, max_val],
            ),
            angularaxis=dict(tickfont=dict(size=11, color="#71717A"), showline=False),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=30, b=40, l=40, r=40),
        **_LAYOUT_BASE,
    )
    return fig


def build_income_radar_relative(
    df_ingresos_cm: pd.DataFrame,
    df_ingresos_hist: pd.DataFrame,
) -> go.Figure | None:
    """
    Radar chart comparando ingresos del mes actual vs media histórica.
    Vista relativa (%) — media histórica = 100%.
    """
    if df_ingresos_cm.empty or df_ingresos_hist.empty:
        return None

    current = df_ingresos_cm.groupby("Cuenta")["Haber"].sum().reset_index()
    current = current.rename(columns={"Haber": "Mes Actual"})

    hist_monthly = df_ingresos_hist.groupby(["Mes", "Cuenta"])["Haber"].sum().reset_index()
    hist_mean = hist_monthly.groupby("Cuenta")["Haber"].mean().reset_index()
    hist_mean = hist_mean.rename(columns={"Haber": "Media Histórica"})

    df_radar = pd.merge(current, hist_mean, on="Cuenta", how="outer").fillna(0)
    df_radar = df_radar[(df_radar["Mes Actual"] > 0) | (df_radar["Media Histórica"] > 0)]

    if df_radar.empty:
        return None

    categories = df_radar["Cuenta"].tolist()
    categories.append(categories[0])

    val_current = df_radar["Mes Actual"].tolist()
    val_current.append(val_current[0])

    val_hist = df_radar["Media Histórica"].tolist()
    val_hist.append(val_hist[0])

    r_hist = []
    r_current = []
    for c, h in zip(val_current, val_hist, strict=False):
        if h > 0:
            r_hist.append(100.0)
            r_current.append(min((c / h) * 100.0, 250.0))
        else:
            r_hist.append(10.0)
            r_current.append(250.0 if c > 0 else 0.0)

    # Nota: el `fill_rgba` que se calculaba aquí desde COLOR_INGRESOS
    # nunca se usaba (los `fillcolor` de los traces son fijos abajo).
    # Bloque retirado en la limpieza de 2026-05-24.

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=r_hist,
            theta=categories,
            customdata=val_hist,
            fill="toself",
            name="Media Histórica",
            line=dict(color="rgba(100, 116, 139, 0.5)", dash="dash", width=1.5),
            fillcolor="rgba(100, 116, 139, 0.08)",
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Media)<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=r_current,
            theta=categories,
            customdata=val_current,
            fill="toself",
            name="Mes Actual",
            line=dict(color=COLOR_INGRESOS, width=2),
            fillcolor="rgba(16, 185, 129, 0.30)",
            hovertemplate="%{theta}: <b>%{customdata:.2f} €</b> (Actual)<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,
                ticks="",
                showline=False,
                range=[-35, 250],
            ),
            angularaxis=dict(tickfont=dict(size=11, color="#71717A"), showline=False),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=30, b=40, l=40, r=40),
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)
