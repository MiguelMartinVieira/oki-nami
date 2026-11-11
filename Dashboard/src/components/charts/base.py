import plotly.graph_objects as go
import plotly.io as pio

pio.templates["fintech_dark"] = go.layout.Template(
    layout=go.Layout(
        xaxis=dict(
            showgrid=False, zeroline=False, showline=False, tickfont=dict(color="#71717A", size=10)
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showline=False, tickfont=dict(color="#71717A", size=10)
        ),
    )
)
pio.templates.default = "plotly_dark+fintech_dark"

_TRANSPARENT = "rgba(0,0,0,0)"
_LAYOUT_BASE = dict(
    paper_bgcolor=_TRANSPARENT,
    plot_bgcolor=_TRANSPARENT,
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#71717A", size=11),
)


def _hex_to_rgba(color: str, alpha: float) -> str:
    """`#RRGGBB` → `rgba(r,g,b,alpha)`. Pasa-through si no es hex de 7 chars."""
    if isinstance(color, str) and color.startswith("#") and len(color) == 7:
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        return f"rgba({r},{g},{b},{alpha})"
    return color


def _apply_crystal_aesthetic(fig: go.Figure) -> go.Figure:
    """Aplica estética cristalina a gráficos (relleno transparente, borde sólido brillante) y texto blanco."""

    def _to_rgba(c, alpha=0.35):
        # Wrapper delgado: el módulo expone `_hex_to_rgba` como API pública.
        return _hex_to_rgba(c, alpha)

    def _apply_trace(trace):
        # Texto blanco
        if hasattr(trace, "textfont"):
            if trace.textfont is None:
                trace.textfont = dict()
            trace.textfont.color = "#FFFFFF"
        if hasattr(trace, "insidetextfont"):
            if trace.insidetextfont is None:
                trace.insidetextfont = dict()
            trace.insidetextfont.color = "#FFFFFF"

        # Transparencia y bordes brillantes
        t_type = getattr(trace, "type", "")
        if t_type == "bar":
            if hasattr(trace, "marker"):
                c = getattr(trace.marker, "color", None)
                if isinstance(c, str) and c.startswith("#"):
                    if getattr(trace.marker, "line", None) is None:
                        trace.marker.line = dict()
                    trace.marker.line.color = c
                    trace.marker.line.width = 1.5
                    trace.marker.color = _to_rgba(c)
                elif isinstance(c, (list, tuple)):
                    if getattr(trace.marker, "line", None) is None:
                        trace.marker.line = dict()
                    trace.marker.line.color = [val for val in c]
                    trace.marker.line.width = 1.5
                    trace.marker.color = [_to_rgba(val) for val in c]
        elif t_type in ("treemap", "pie"):
            if hasattr(trace, "marker") and getattr(trace.marker, "colors", None) is not None:
                c_list = trace.marker.colors
                if getattr(trace.marker, "line", None) is None:
                    trace.marker.line = dict()
                trace.marker.line.color = [val for val in c_list]
                trace.marker.line.width = 1.5
                trace.marker.colors = [_to_rgba(val) for val in c_list]

    for trace in fig.data:
        _apply_trace(trace)

    if getattr(fig, "frames", None):
        for frame in fig.frames:
            for trace in frame.data:
                _apply_trace(trace)

    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode():
            if hasattr(fig.layout, "annotations") and fig.layout.annotations:
                for ann in fig.layout.annotations:
                    if hasattr(ann, "text") and ann.text:
                        ann.text = scramble_numbers(ann.text)

            for trace in fig.data:
                if (
                    hasattr(trace, "node")
                    and isinstance(trace.node, dict)
                    and "label" in trace.node
                ):
                    if trace.node["label"] and isinstance(trace.node["label"], (list, tuple)):
                        trace.node["label"] = [scramble_numbers(x) for x in trace.node["label"]]
                if hasattr(trace, "text") and trace.text is not None:
                    if isinstance(trace.text, str):
                        trace.text = scramble_numbers(trace.text)
                    elif isinstance(trace.text, (list, tuple)):
                        trace.text = [scramble_numbers(x) for x in trace.text]
                if hasattr(trace, "hovertext") and trace.hovertext is not None:
                    if isinstance(trace.hovertext, str):
                        trace.hovertext = scramble_numbers(trace.hovertext)
                    elif isinstance(trace.hovertext, (list, tuple)):
                        trace.hovertext = [scramble_numbers(x) for x in trace.hovertext]
            # 4. Cifrado explícito de ejes X e Y a nivel de Plotly layout en Python
            _scramble_fig_axes(fig)
    except Exception:
        pass

    return fig


def _scramble_fig_axes(fig: go.Figure) -> None:
    try:
        import pandas as pd

        from services.demo_data import scramble_numbers
    except Exception:
        return

    if not hasattr(fig, "layout"):
        return

    # 1. Cifrar ejes Y (valores numéricos e importes k/€)
    for y_name in ("yaxis", "yaxis2"):
        y_ax = getattr(fig.layout, y_name, None)
        if not y_ax:
            continue

        if hasattr(y_ax, "title") and hasattr(y_ax.title, "text") and y_ax.title.text:
            y_ax.title.text = scramble_numbers(str(y_ax.title.text))

        if getattr(y_ax, "ticktext", None):
            y_ax.tickmode = "array"
            y_ax.ticktext = [scramble_numbers(str(t)) for t in y_ax.ticktext]
        else:
            all_y = []
            for tr in fig.data:
                if hasattr(tr, "y") and tr.y is not None:
                    for val in tr.y:
                        try:
                            if isinstance(val, (int, float)) and not pd.isna(val):
                                all_y.append(float(val))
                        except Exception:
                            pass
            if all_y:
                y_min, y_max = min(all_y), max(all_y)
                if y_max > y_min:
                    step = (y_max - y_min) / 5.0
                    vals = [y_min + i * step for i in range(6)]
                    use_k = max(abs(y_min), abs(y_max)) >= 1000
                    txts = [
                        scramble_numbers(f"{v / 1000:.0f}k" if use_k else f"{v:,.0f}") for v in vals
                    ]
                    y_ax.tickmode = "array"
                    y_ax.tickvals = list(vals)
                    y_ax.ticktext = txts

    # 2. Cifrar ejes X (fechas / texto)
    for x_name in ("xaxis", "xaxis2"):
        x_ax = getattr(fig.layout, x_name, None)
        if not x_ax:
            continue

        if hasattr(x_ax, "title") and hasattr(x_ax.title, "text") and x_ax.title.text:
            x_ax.title.text = scramble_numbers(str(x_ax.title.text))

        if getattr(x_ax, "ticktext", None):
            x_ax.tickmode = "array"
            x_ax.ticktext = [scramble_numbers(str(t)) for t in x_ax.ticktext]
        else:
            all_x = []
            for tr in fig.data:
                if hasattr(tr, "x") and tr.x is not None:
                    for val in tr.x:
                        if val is not None:
                            all_x.append(str(val))
            if all_x:
                unique_x = list(dict.fromkeys(all_x))
                if len(unique_x) > 1:
                    st_val = max(1, len(unique_x) // 7)
                    sample_x = unique_x[::st_val]

                    def _fmt_x(val):
                        try:
                            dt = pd.to_datetime(val)
                            if not pd.isna(dt):
                                return dt.strftime("%b %d %Y")
                        except Exception:
                            pass
                        return str(val)

                    txts = [scramble_numbers(_fmt_x(x)) for x in sample_x]
                    x_ax.tickmode = "array"
                    x_ax.tickvals = sample_x
                    x_ax.ticktext = txts
