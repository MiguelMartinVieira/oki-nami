import pandas as pd
import plotly.graph_objects as go

from .base import _LAYOUT_BASE, _apply_crystal_aesthetic


def build_pie(
    names, values, color_sequence=None, color_map: dict | None = None
) -> go.Figure | None:
    """
    Donut chart genérico con estilo cristalino (borde sólido, relleno transparente).
    Filtra automáticamente valores no positivos para evitar distorsiones en SVG.
    """
    filtered = [
        (n, float(v))
        for n, v in zip(names, values, strict=False)
        if v is not None and not pd.isna(v) and float(v) > 0
    ]
    if not filtered:
        return None

    n_list = [f[0] for f in filtered]
    v_list = [f[1] for f in filtered]

    solid_colors = []
    if color_map is not None:
        solid_colors = [color_map.get(n, "#888888") for n in n_list]
    elif color_sequence is not None:
        solid_colors = [color_sequence[i % len(color_sequence)] for i in range(len(n_list))]
    else:
        solid_colors = ["#888888"] * len(n_list)

    rgba_colors = []
    for c in solid_colors:
        if isinstance(c, str) and c.startswith("#") and len(c) == 7:
            r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
            rgba_colors.append(f"rgba({r}, {g}, {b}, 0.35)")
        else:
            rgba_colors.append(c)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=n_list,
                values=v_list,
                hole=0.6,
                marker=dict(colors=rgba_colors, line=dict(color=solid_colors, width=2)),
                textinfo="percent",
                hoverinfo="label+value+percent",
                textfont=dict(color="#FFFFFF"),
                insidetextfont=dict(color="#FFFFFF"),
                sort=False,
            )
        ]
    )
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), **_LAYOUT_BASE)
    return fig


def build_donut(
    labels: list, values: list, colors: list, center_text: str = ""
) -> go.Figure | None:
    """
    Donut chart con colores específicos y texto central.
    Filtra automáticamente valores <= 0 para evitar distorsiones de arcos en SVG.
    """
    filtered = [
        (lbl, float(v), c)
        for lbl, v, c in zip(labels, values, colors, strict=False)
        if v is not None and not pd.isna(v) and float(v) > 0
    ]
    if not filtered:
        return None

    labels = [f[0] for f in filtered]
    values = [f[1] for f in filtered]
    colors = [f[2] for f in filtered]
    rgba_colors = []
    for c in colors:
        if isinstance(c, str) and c.startswith("#") and len(c) == 7:
            rgba_colors.append(
                f"rgba({int(c[1:3], 16)}, {int(c[3:5], 16)}, {int(c[5:7], 16)}, 0.2)"
            )
        else:
            rgba_colors.append(c)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.65,
                marker=dict(colors=rgba_colors, line=dict(color=colors, width=1.5)),
                textinfo="percent",
                hoverinfo="label+value+percent",
                textfont=dict(color="#FFFFFF"),
                insidetextfont=dict(color="#FFFFFF"),
                sort=False,
            )
        ]
    )
    fig.update_layout(
        height=525,
        showlegend=False,
        margin=dict(t=20, b=20, l=10, r=10),
        **_LAYOUT_BASE,
    )
    if center_text:
        fig.add_annotation(
            text=f"<b>{center_text}</b>",
            x=0.5,
            y=0.5,
            font_size=24,
            font_family="Plus Jakarta Sans, sans-serif",
            font_color="#FFFFFF",
            showarrow=False,
        )
    return fig


def build_portfolio_treemap(
    df_tree: pd.DataFrame, root_name: str, root_color: str
) -> go.Figure | None:
    """
    Treemap del portfolio de inversión usando go.Treemap.
    df_tree debe tener: ["Activo", "Valor", "Color", "Raíz"].
    Filtra automáticamente activos con valor <= 0.
    """
    if df_tree is None or df_tree.empty:
        return None

    df_valid = df_tree.copy()
    df_valid["Valor"] = pd.to_numeric(df_valid["Valor"], errors="coerce").fillna(0)
    df_valid = df_valid[df_valid["Valor"] > 0]
    if df_valid.empty:
        return None

    labels = [root_name] + df_valid["Activo"].tolist()
    parents = [""] + df_valid["Raíz"].tolist()

    # Asegurar que el root suma exactamente los hijos
    root_val = df_valid["Valor"].sum()
    values = [root_val] + df_valid["Valor"].tolist()

    colors = [root_color] + df_valid["Color"].tolist()

    rgba_colors = []
    for c in colors:
        if isinstance(c, str) and c.startswith("#") and len(c) == 7:
            rgba_colors.append(
                f"rgba({int(c[1:3], 16)}, {int(c[3:5], 16)}, {int(c[5:7], 16)}, 0.2)"
            )
        else:
            rgba_colors.append(c)

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(colors=rgba_colors, line=dict(color=colors, width=1.5)),
            textinfo="label+value+percent parent",
            hovertemplate="<b>%{label}</b><br>%{value:,.2f} €<extra></extra>",
            branchvalues="total",
        )
    )

    fig.update_layout(height=450, margin=dict(t=20, l=10, r=10, b=10), **_LAYOUT_BASE)
    return _apply_crystal_aesthetic(fig)
