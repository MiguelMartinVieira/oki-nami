import pandas as pd
import plotly.graph_objects as go

from constants import (
    get_category_color,
)

from .base import _LAYOUT_BASE, _apply_crystal_aesthetic


def build_bar_income_expense_combined(
    df_gastos: pd.DataFrame, df_ingresos: pd.DataFrame
) -> go.Figure | None:
    """
    Barras apiladas combinadas: ingresos por categoría (izquierda, verdes) y
    gastos por categoría (derecha, rojos), agrupadas por mes.

    Cada mes tiene dos grupos de barras apiladas lado a lado, lo que permite
    comparar la composición de ingresos vs gastos en un único vistazo.
    """
    if df_gastos.empty and df_ingresos.empty:
        return None

    # ── Mes string ordenado ──
    all_months_raw = (
        pd.concat(
            [
                df_gastos["Mes"] if not df_gastos.empty else pd.Series(dtype="object"),
                df_ingresos["Mes"] if not df_ingresos.empty else pd.Series(dtype="object"),
            ]
        )
        .dropna()
        .unique()
    )
    month_order = sorted(all_months_raw)
    month_labels = {m: m.strftime("%b %Y") for m in month_order}

    fig = go.Figure()

    # ── Ingresos por categoría (offsetgroup="ingresos") ──
    if not df_ingresos.empty:
        df_i = df_ingresos.copy()
        df_i["MesStr"] = df_i["Mes"].map(month_labels)
        df_i_grp = df_i.groupby(["MesStr", "Cuenta"])["Haber"].sum().reset_index()
        cats_inc = df_i_grp.groupby("Cuenta")["Haber"].sum().sort_values(ascending=False).index
        for cat in cats_inc:
            color = get_category_color(cat, is_expense=False)
            df_cat = df_i_grp[df_i_grp["Cuenta"] == cat]
            fig.add_trace(
                go.Bar(
                    name=cat,
                    x=[month_labels[m] for m in month_order],
                    y=[
                        df_cat.loc[df_cat["MesStr"] == month_labels[m], "Haber"].sum()
                        for m in month_order
                    ],
                    marker_color=color,
                    marker_line_width=0,
                    offsetgroup="ingresos",
                    legendgroup="ingresos",
                    legendgrouptitle_text="Ingresos" if cat == cats_inc[0] else None,
                    hovertemplate=f"<b>{cat}</b><br>%{{x}}: %{{y:,.2f}} €<extra></extra>",
                )
            )

    # ── Gastos por categoría (offsetgroup="gastos") ──
    if not df_gastos.empty:
        df_g = df_gastos.copy()
        df_g["MesStr"] = df_g["Mes"].map(month_labels)
        df_g_grp = df_g.groupby(["MesStr", "Cuenta"])["Debe"].sum().reset_index()
        cats_exp = df_g_grp.groupby("Cuenta")["Debe"].sum().sort_values(ascending=False).index
        for cat in cats_exp:
            color = get_category_color(cat, is_expense=True)
            df_cat = df_g_grp[df_g_grp["Cuenta"] == cat]
            fig.add_trace(
                go.Bar(
                    name=cat,
                    x=[month_labels[m] for m in month_order],
                    y=[
                        df_cat.loc[df_cat["MesStr"] == month_labels[m], "Debe"].sum()
                        for m in month_order
                    ],
                    marker_color=color,
                    marker_line_width=0,
                    offsetgroup="gastos",
                    legendgroup="gastos",
                    legendgrouptitle_text="Gastos" if cat == cats_exp[0] else None,
                    hovertemplate=f"<b>{cat}</b><br>%{{x}}: %{{y:,.2f}} €<extra></extra>",
                )
            )

    fig.update_layout(
        barmode="stack",
        xaxis_title="",
        yaxis_title="Importe (€)",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            tracegroupgap=12,
        ),
        margin=dict(t=10, b=120, l=10, r=10),
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)


def build_drill_bar(df: pd.DataFrame, x: str, y: str, color: str) -> go.Figure:
    """
    Bar chart horizontal para drill-down por categoría.
    Las etiquetas de concepto se muestran dentro de la barra para evitar
    que el margen izquierdo sea excesivo.
    """

    # Color de texto dentro de la barra: blanco si el color es oscuro, negro si es claro
    def _text_color(hex_color: str) -> str:
        try:
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#FFFFFF" if luminance < 0.55 else "#1E293B"
        except Exception:
            return "#FFFFFF"

    txt_color = _text_color(color) if color.startswith("#") else "#FFFFFF"

    fig = go.Figure(
        go.Bar(
            x=df[x],
            y=df[y],
            orientation="h",
            marker_color=color,
            marker_line_width=0,
            text=df[y],
            textposition="inside",
            insidetextanchor="start",
            textfont=dict(color=txt_color, size=12),
            hovertemplate="<b>%{y}</b><br>%{x:,.2f} €<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Total (€)",
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        xaxis=dict(showgrid=True, zeroline=False),
        margin=dict(t=10, b=10, l=4, r=10),
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)


def build_current_month_income_vs_expense_bar(
    cm_ingresos: float,
    cm_gastos: float,
    month_str: str = "",
    cat_incomes_cm: pd.Series | None = None,
    cat_expenses_cm: pd.Series | None = None,
) -> go.Figure:
    """
    Gráfico de barras horizontales apiladas (sumatorios por colores de categorías):
    Muestra los gastos (arriba) e ingresos (abajo) compuestos por segmentos de color de cada categoría, sin texto sobrepuesto.
    """
    from constants import get_category_color

    fig = go.Figure()

    # 1. Barra de Gastos (Arriba, apilada por categorías)
    if cat_expenses_cm is not None and not cat_expenses_cm.empty:
        for cat, val in cat_expenses_cm.items():
            if val > 0:
                color = get_category_color(str(cat), is_expense=True)
                fig.add_trace(
                    go.Bar(
                        y=["Gastos"],
                        x=[val],
                        name=str(cat),
                        orientation="h",
                        marker_color=color,
                        marker_line_width=0.5,
                        marker_line_color="rgba(0,0,0,0.3)",
                        hovertemplate=f"<b>{cat} (Gasto)</b><br>{val:,.2f} €<extra></extra>",
                    )
                )
    else:
        fig.add_trace(
            go.Bar(
                y=["Gastos"],
                x=[cm_gastos],
                name="Gastos",
                orientation="h",
                marker_color="rgba(255, 23, 68, 0.85)",
                hovertemplate=f"<b>Gastos</b><br>{cm_gastos:,.2f} €<extra></extra>",
            )
        )

    # 2. Barra de Ingresos (Abajo, apilada por categorías)
    if cat_incomes_cm is not None and not cat_incomes_cm.empty:
        for cat, val in cat_incomes_cm.items():
            if val > 0:
                color = get_category_color(str(cat), is_expense=False)
                fig.add_trace(
                    go.Bar(
                        y=["Ingresos"],
                        x=[val],
                        name=str(cat),
                        orientation="h",
                        marker_color=color,
                        marker_line_width=0.5,
                        marker_line_color="rgba(0,0,0,0.3)",
                        hovertemplate=f"<b>{cat} (Ingreso)</b><br>{val:,.2f} €<extra></extra>",
                    )
                )
    else:
        fig.add_trace(
            go.Bar(
                y=["Ingresos"],
                x=[cm_ingresos],
                name="Ingresos",
                orientation="h",
                marker_color="rgba(0, 230, 118, 0.85)",
                hovertemplate=f"<b>Ingresos</b><br>{cm_ingresos:,.2f} €<extra></extra>",
            )
        )

    max_val = max(cm_ingresos, cm_gastos, 1.0)

    # Anotaciones de total al final de cada barra apilada
    if cm_gastos > 0:
        fig.add_annotation(
            x=cm_gastos,
            y="Gastos",
            text=f" <b>{cm_gastos:,.2f} €</b>",
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(color="#FF1744", size=11, family="Plus Jakarta Sans"),
        )

    if cm_ingresos > 0:
        fig.add_annotation(
            x=cm_ingresos,
            y="Ingresos",
            text=f" <b>{cm_ingresos:,.2f} €</b>",
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(color="#00E676", size=11, family="Plus Jakarta Sans"),
        )

    fig.update_layout(
        barmode="stack",
        height=85,
        margin=dict(t=2, b=2, l=2, r=2),
        xaxis=dict(range=[0, max_val * 1.28], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, autorange="reversed", showticklabels=False),
        showlegend=False,
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)
