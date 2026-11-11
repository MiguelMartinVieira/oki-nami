import pandas as pd
import plotly.graph_objects as go

from constants import (
    COLOR_BERKSHIRE,
    COLOR_EFECTIVO_FISICO,
    COLOR_EFECTIVO_TR,
    COLOR_INGRESOS,
    COLOR_SP500,
    COLOR_TE_DEBEN,
)

from .base import _LAYOUT_BASE, _TRANSPARENT, _apply_crystal_aesthetic, _hex_to_rgba


def build_savings_rate_line(df_gastos: pd.DataFrame, df_ingresos: pd.DataFrame) -> go.Figure | None:
    """
    Línea temporal de la tasa de ahorro mensual (%).

    Incluye líneas de referencia en 0 % (rojo), 20 % (amarillo) y 30 % (verde)
    y, si hay ≥ 2 meses de datos, una línea horizontal con la **media móvil
    de los últimos 6 meses** (benchmark personal dinámico).
    Cada punto se colorea según si la tasa es negativa, básica o saludable.
    """
    if df_gastos is None or df_ingresos is None or df_gastos.empty or df_ingresos.empty:
        return None

    g = df_gastos.groupby("Mes")["Debe"].sum()
    i = df_ingresos.groupby("Mes")["Haber"].sum()
    combined = pd.DataFrame({"gastos": g, "ingresos": i}).dropna()
    if combined.empty:
        return None

    combined["tasa"] = (combined["ingresos"] - combined["gastos"]) / combined["ingresos"] * 100
    combined["MesStr"] = combined.index.strftime("%b %Y")

    # Color por punto según la tasa
    def _rate_color(t):
        if t < 0:
            return "#D50000"
        if t < 20:
            return "#F59E0B"
        if t < 30:
            return "#10B981"
        return "#00C853"

    point_colors = [_rate_color(t) for t in combined["tasa"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=combined["MesStr"],
            y=combined["tasa"],
            mode="lines+markers",
            name="Tasa de Ahorro",
            line=dict(color=COLOR_INGRESOS, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(0, 227, 150, 0.05)",
            marker=dict(size=10, color=point_colors, line=dict(width=1.5, color="#09090B")),
            hovertemplate="%{x}: <b>%{y:.1f}%</b><extra></extra>",
        )
    )

    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color="#D50000",
        line_width=1.5,
        annotation_text="0%",
        annotation_position="right",
    )
    fig.add_hline(
        y=20,
        line_dash="dash",
        line_color="#F59E0B",
        line_width=1.2,
        annotation_text="20%",
        annotation_position="right",
    )
    fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="#00C853",
        line_width=1.2,
        annotation_text="30%",
        annotation_position="right",
    )

    # Media móvil 6m (benchmark personal). Se calcula sobre los últimos 6 meses
    # disponibles y se dibuja como línea horizontal punteada para comparar
    # el mes actual contra tu propia tendencia reciente.
    if len(combined) >= 2:
        media_6m = combined["tasa"].tail(6).mean()
        fig.add_hline(
            y=media_6m,
            line_dash="dot",
            line_color="#6366F1",
            line_width=1.5,
            annotation_text=f"Tu media 6m: {media_6m:.1f}%",
            annotation_position="left",
        )

    fig.update_layout(
        xaxis_title="",
        yaxis_title="Tasa de Ahorro (%)",
        yaxis=dict(ticksuffix="%"),
        showlegend=False,
        margin=dict(t=20, b=20, l=10, r=60),
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)


def build_dca_tracker(
    df_brk: pd.DataFrame,
    df_hist: pd.DataFrame,
    usd_to_eur: float,
    line_color: str = "#213083",  # default COLOR_BERKSHIRE
    yaxis_title: str = "Precio (€/acción)",
    is_usd: bool = True,
    show_lumpsum: bool = False,
    cost_adjustment: float = 0.0,
) -> go.Figure | None:
    """
    DCA Tracker: evolución del precio medio de compra acumulado vs precio de mercado (€).

    - Línea de mercado: precio de mercado histórico (€).
    - Línea ámbar punteada: precio medio de compra (DCA) acumulado.
    - Área de fondo: color de marca transparente.
    - Si `show_lumpsum=True`: añade línea horizontal gris dashed con el
      "Coste Lump-Sum" (precio del día 1, lo que habrías pagado por acción
      si hubieras puesto todo el capital ese día) + anotación con el delta
      €/acc indicando quién gana (DCA o Lump-Sum).
    - `cost_adjustment`: importe (€) a restar del total invertido acumulado
      (ej. plusvalías históricas previas como `VANGUARD_HISTORICAL_GAIN`)
      para alinear el precio medio del gráfico con el capital neto desembolsado
      mostrado en las tarjetas superiores.
    """
    from services.utils import extract_quantity

    if df_brk.empty or df_hist.empty:
        return None

    # ── Construir serie DCA desde las transacciones ──
    ops = df_brk[df_brk["Debe"] > 0].copy().sort_values("Fecha")

    ops["qty"] = ops["Descripción"].apply(extract_quantity)
    ops = ops[ops["qty"] > 0].copy()
    if ops.empty:
        return None

    # Ajuste por plusvalías históricas previas (ej. Vanguard antes del checkpoint):
    # Descontamos cost_adjustment para que cum_invested refleje el capital neto
    # desembolsado (out-of-pocket), igual que las tarjetas métricas del dashboard.
    ops["cum_invested"] = (ops["Debe"].cumsum() - cost_adjustment).clip(lower=0.0)
    ops["cum_shares"] = ops["qty"].cumsum()
    ops["avg_cost_eur"] = ops["cum_invested"] / ops["cum_shares"]

    # ── Preparar precios históricos ──
    df_hist = df_hist.copy()
    df_hist["Date"] = pd.to_datetime(df_hist["Date"])
    if is_usd:
        df_hist["price_eur"] = df_hist["Price"] * usd_to_eur
    else:
        df_hist["price_eur"] = df_hist["Price"]

    # Filtrar solo desde la primera compra
    first_date = ops["Fecha"].min()
    df_hist = df_hist[df_hist["Date"] >= first_date]

    if df_hist.empty:
        return None

    last_avg = float(ops["avg_cost_eur"].iloc[-1])

    # ── Zoom dinámico en el Eje Y ──
    min_val = min(df_hist["price_eur"].min(), ops["avg_cost_eur"].min())
    max_val = max(df_hist["price_eur"].max(), ops["avg_cost_eur"].max())
    margin = (max_val - min_val) * 0.15 if max_val > min_val else max_val * 0.1
    if margin == 0:
        margin = 10.0
    y_min = max(0.0, min_val - margin)
    y_max = max_val + margin

    fig = go.Figure()

    # ── Área de fondo con color de marca transparente ──
    # Use imported _hex_to_rgba

    fill_color = _hex_to_rgba(line_color, alpha=0.08)

    fig.add_trace(
        go.Scatter(
            x=df_hist["Date"],
            y=df_hist["price_eur"],
            fill="tozeroy",
            fillcolor=fill_color,
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # ── Precio de mercado ──
    fig.add_trace(
        go.Scatter(
            x=df_hist["Date"],
            y=df_hist["price_eur"],
            name="Precio Mercado",
            line=dict(color=line_color, width=2.5),
            hovertemplate="%{x|%d %b %Y}: <b>%{y:.2f} €</b><extra>Mercado</extra>",
        )
    )

    # ── Precio medio (DCA) — línea escalonada ──
    fig.add_trace(
        go.Scatter(
            x=ops["Fecha"],
            y=ops["avg_cost_eur"],
            name="Precio Medio (DCA)",
            mode="lines",
            line=dict(color="rgba(245, 158, 11, 0.6)", width=1.5, dash="dot", shape="hv"),
            hovertemplate="%{x|%d %b %Y}: <b>%{y:.2f} €</b><extra>DCA</extra>",
        )
    )

    # ── Línea del precio medio DCA actual ──
    fig.add_hline(
        y=last_avg,
        line_dash="dot",
        line_color="rgba(245, 158, 11, 0.5)",
        line_width=1.2,
        annotation_text=f"Coste medio DCA: {last_avg:.2f} €",
        annotation_position="bottom left",
        annotation_font_color="rgba(245, 158, 11, 0.85)",
    )

    # ── Línea de Lump-Sum (opt-in) ──
    if show_lumpsum:
        # precio del primer día con datos del histórico (= lo que pagarías
        # por acción al hacer lump-sum el día 1)
        df_hist_sorted = df_hist.sort_values("Date")
        lump_price = float(df_hist_sorted.iloc[0]["price_eur"])
        delta = last_avg - lump_price  # negativo = DCA más barato = DCA gana
        if delta <= 0:
            winner_text = f"DCA gana · {abs(delta):.2f} €/acc más barato"
        else:
            winner_text = f"Lump-Sum gana · {abs(delta):.2f} €/acc más barato"

        # Texto azul Berkshire para coherencia visual con el sub-tab.
        # El color NO codifica el ganador (la palabra "DCA gana" / "Lump-Sum gana"
        # del propio texto ya lo dice); aquí prima la identidad cromática del tab.
        brk_text_color = "rgba(37, 99, 235, 0.95)"  # COLOR_BERKSHIRE con alpha

        fig.add_hline(
            y=lump_price,
            line_dash="dash",
            line_color="rgba(161, 161, 170, 0.6)",
            line_width=1.4,
            annotation_text=f"Lump-Sum día 1: {lump_price:.2f} €",
            annotation_position="top left",
            annotation_font_color=brk_text_color,
        )
        # Anotación con el veredicto en el lateral derecho — texto en azul BRK
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.995,
            y=0.05,
            xanchor="right",
            yanchor="bottom",
            showarrow=False,
            text=f"<b>{winner_text}</b>",
            font=dict(color=brk_text_color, size=12, family="Plus Jakarta Sans, sans-serif"),
            bgcolor="rgba(24,24,27,0.85)",
            bordercolor=brk_text_color,
            borderwidth=1,
            borderpad=6,
        )

    fig.update_layout(
        xaxis_title="",
        yaxis_title=yaxis_title,
        yaxis=dict(range=[y_min, y_max]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=30, b=20, l=10, r=10),
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)


def build_category_sparkline(
    monthly_series: pd.Series, color: str, is_expense: bool = True
) -> go.Figure:
    """
    Mini sparkline de una categoría de gasto.
    - Con ≥2 meses: línea + markers + área rellena.
    - Con 1 mes: barra única (línea invisible con un solo punto).

    Args:
        monthly_series: Series con índice de mes y valores (€).
        color: Color hex de la categoría.
    """
    # Convertir hex a rgba para fillcolor
    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        _fill = f"rgba({r},{g},{b},0.2)"
    else:
        _fill = color

    x = [m.strftime("%b %y") if hasattr(m, "strftime") else str(m) for m in monthly_series.index]
    y = list(monthly_series.values)

    fig = go.Figure()

    if len(y) >= 2:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines+markers",
                line=dict(color=color, width=2.5),
                marker=dict(size=5, color=color),
                fill="tozeroy",
                fillcolor=_fill,
                hovertemplate="%{x}: <b>%{y:,.0f} €</b><extra></extra>",
            )
        )
        # Anotación tendencia vs mes anterior
        # Gastos: subir = malo (rojo), bajar = bueno (verde)
        # Ingresos: subir = bueno (verde), bajar = malo (rojo)
        last_two = monthly_series.tail(2)
        if last_two.iloc[-2] != 0:
            delta_pct = (last_two.iloc[-1] - last_two.iloc[-2]) / last_two.iloc[-2] * 100
            arrow = "▲" if delta_pct >= 0 else "▼"
            going_up = delta_pct >= 0
            t_color = (
                ("#EF4444" if going_up else "#22C55E")
                if is_expense
                else ("#22C55E" if going_up else "#EF4444")
            )
            annotations = [
                dict(
                    text=f"<span style='color:{t_color};font-weight:600'>{arrow} {abs(delta_pct):.0f}%</span>",
                    x=1,
                    y=1,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=11),
                    xanchor="right",
                    yanchor="top",
                )
            ]
        else:
            annotations = []
    else:
        # Un solo mes: barra simple
        fig.add_trace(
            go.Bar(
                x=x,
                y=y,
                marker_color=_fill,
                marker_line_color=color,
                marker_line_width=2,
                hovertemplate="%{x}: <b>%{y:,.0f} €</b><extra></extra>",
            )
        )
        annotations = []

    fig.update_layout(
        height=100,
        margin=dict(t=8, b=4, l=4, r=4),
        paper_bgcolor=_TRANSPARENT,
        plot_bgcolor=_TRANSPARENT,
        showlegend=False,
        xaxis=dict(
            showticklabels=True,
            tickfont=dict(size=9, color="#94A3B8"),
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(visible=False),
        annotations=annotations,
        bargap=0.3,
    )
    return fig


def build_stacked_area(df_plot: pd.DataFrame, selected_series: list[str]) -> go.Figure | None:
    """
    Gráfico de área apilada para evolución de cartera.

    Ajusta dinámicamente el eje Y para resaltar las variaciones del patrimonio
    total, evitando que el eje comience siempre en cero si el valor es muy alto.
    """
    if df_plot is None or df_plot.empty or not selected_series or "Date" not in df_plot.columns:
        return None

    series_config = {
        "SP500": ("SP500", COLOR_SP500),
        "Berkshire": ("Berkshire", COLOR_BERKSHIRE),
        "Trade Republic": ("Trade Republic", COLOR_EFECTIVO_TR),
        "Efectivo": ("Efectivo", COLOR_EFECTIVO_FISICO),
        "Te Deben": ("Te Deben", COLOR_TE_DEBEN),
    }

    fig = go.Figure()
    active_cols = []
    for name in selected_series:
        if name in series_config:
            col, color = series_config[name]
            if col in df_plot.columns:
                active_cols.append(col)
                rgba_fill = color
                if color.startswith("#") and len(color) == 7:
                    rgba_fill = f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2)"

                fig.add_trace(
                    go.Scatter(
                        x=df_plot["Date"],
                        y=df_plot[col],
                        name=name,
                        stackgroup="one",
                        line=dict(width=1.5, color=color),
                        fillcolor=rgba_fill,
                        hovertemplate="%{x|%d %b %Y}: <b>%{y:,.0f} €</b><extra></extra>",
                    )
                )

    # ── Ajuste dinámico del eje Y ──
    if active_cols:
        # Calculamos la suma total diaria de las series visibles
        totals = df_plot[active_cols].sum(axis=1)
        y_min, y_max = totals.min(), totals.max()

        # Margen del 15% del valor para dar 'aire' y que no sea hipersensible
        # Esto evita que variaciones pequeñas parezcan enormes (sobreestimación visual)
        margin = y_min * 0.15

        # Establecemos el rango con un suelo de 0
        y_start = max(0, y_min - margin)
        y_end = y_max + (margin * 0.5)  # Menos margen arriba para aprovechar el espacio
        fig.update_layout(yaxis=dict(range=[y_start, y_end]))

    fig.update_layout(
        height=540,
        xaxis_title="",
        yaxis_title="Patrimonio Total (€)",
        showlegend=False,
        margin=dict(t=20, b=20, l=10, r=10),
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)


def build_normalized_comparison(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    start_date,
    label_a: str = "BRK-B",
    label_b: str = "S&P 500",
    color_a: str = COLOR_BERKSHIRE,
    color_b: str = COLOR_SP500,
) -> go.Figure | None:
    """
    Compara dos series de precios rebased a 100 desde `start_date`.

    Espera DataFrames con columnas `Date` y `Price` (los devueltos por
    `data.yahoo.get_yahoo_history`). Útil para visualizar el "exceso de
    retorno" entre un activo y su benchmark.
    """
    if df_a is None or df_b is None or df_a.empty or df_b.empty:
        return None

    def _prep(df_in: pd.DataFrame) -> pd.DataFrame:
        d = df_in.copy()
        d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
        d = d.dropna(subset=["Date", "Price"]).sort_values("Date")
        d = d[d["Date"] >= pd.to_datetime(start_date)]
        return d

    a = _prep(df_a)
    b = _prep(df_b)
    if a.empty or b.empty:
        return None

    base_a = float(a["Price"].iloc[0])
    base_b = float(b["Price"].iloc[0])
    if base_a <= 0 or base_b <= 0:
        return None
    a = a.assign(Norm=a["Price"] / base_a * 100.0)
    b = b.assign(Norm=b["Price"] / base_b * 100.0)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=a["Date"],
            y=a["Norm"],
            mode="lines",
            name=label_a,
            line=dict(color=color_a, width=2.5),
            hovertemplate=f"<b>{label_a}</b><br>%{{x|%d %b %Y}}<br>%{{y:.2f}}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=b["Date"],
            y=b["Norm"],
            mode="lines",
            name=label_b,
            line=dict(color=color_b, width=2.5),
            hovertemplate=f"<b>{label_b}</b><br>%{{x|%d %b %Y}}<br>%{{y:.2f}}<extra></extra>",
        )
    )
    fig.add_hline(y=100.0, line_color="#7E57C2", line_width=2.5)

    spread = float(a["Norm"].iloc[-1] - b["Norm"].iloc[-1])
    spread_color = "#00C853" if spread >= 0 else "#7E57C2"
    spread_sign = "+" if spread >= 0 else ""
    fig.add_annotation(
        x=a["Date"].iloc[-1],
        y=a["Norm"].iloc[-1],
        text=f"<b>Spread: {spread_sign}{spread:.1f} pp</b>",
        showarrow=False,
        xshift=-40,
        yshift=15,
        font=dict(size=11, color=spread_color),
    )

    fig.update_layout(
        height=380,
        xaxis_title="",
        yaxis_title="Rendimiento (base 100)",
        margin=dict(t=20, b=20, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)


def build_monte_carlo_fan(
    sim: dict,
    accent_color: str = "#7E57C2",
) -> go.Figure:
    """Fan chart de una simulación Monte Carlo: bandas P10-P90, P25-P75 y mediana.

    Recibe el dict devuelto por `services.analytics.simulate_monte_carlo`.
    """
    months = sim["months"]
    p = sim["percentiles"]

    # Convertir meses a "años decimales" para eje X más legible
    years_axis = months / 12.0

    # Banda externa P10-P90 (sombra más translúcida)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years_axis,
            y=p["p90"],
            mode="lines",
            line=dict(width=0, color=accent_color),
            hoverinfo="skip",
            showlegend=False,
            name="P90",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years_axis,
            y=p["p10"],
            mode="lines",
            line=dict(width=0, color=accent_color),
            fill="tonexty",
            fillcolor=_hex_to_rgba(accent_color, 0.12),
            hoverinfo="skip",
            showlegend=True,
            name="P10–P90 (rango amplio)",
        )
    )
    # Banda interna P25-P75 (más opaca)
    fig.add_trace(
        go.Scatter(
            x=years_axis,
            y=p["p75"],
            mode="lines",
            line=dict(width=0, color=accent_color),
            hoverinfo="skip",
            showlegend=False,
            name="P75",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years_axis,
            y=p["p25"],
            mode="lines",
            line=dict(width=0, color=accent_color),
            fill="tonexty",
            fillcolor=_hex_to_rgba(accent_color, 0.25),
            hoverinfo="skip",
            showlegend=True,
            name="P25–P75 (rango medio)",
        )
    )
    # Línea mediana
    fig.add_trace(
        go.Scatter(
            x=years_axis,
            y=p["p50"],
            mode="lines",
            line=dict(color=accent_color, width=2.5),
            name="Mediana (P50)",
            hovertemplate="<b>Año %{x:.1f}</b><br>Mediana: %{y:,.0f} €<extra></extra>",
        )
    )

    fig.update_layout(
        height=420,
        xaxis=dict(title="Años", showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(title="Patrimonio (€)", showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        margin=dict(t=20, b=20, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        **_LAYOUT_BASE,
    )
    return _apply_crystal_aesthetic(fig)
