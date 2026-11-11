import math

import pandas as pd
import plotly.graph_objects as go

from .base import _LAYOUT_BASE


def log_normalize(value, median, threshold):
    """Mapea valor a [0, 1] usando escala logarítmica."""
    if median <= 0 or threshold <= median:
        return min(1.0, max(0.0, value / max(threshold, 1.0)))
    ratio = value / median if value > 0 else 0.0
    threshold_ratio = threshold / median
    if ratio <= 0:
        return 0.0
    result = math.log(ratio + 1) / math.log(threshold_ratio + 1)
    return min(1.0, max(0.0, result))


def _prepare_heatmap_data(df_diario: pd.DataFrame, year: int, metric: str):
    df = df_diario.copy()
    df["Nº Cuenta"] = df["Nº Cuenta"].astype(str).str.strip()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df = df[df["Fecha"].dt.year == year]
    if df.empty:
        return None, None, None

    ingresos = df[df["Nº Cuenta"].str.startswith("4")].groupby(df["Fecha"].dt.date)["Haber"].sum()
    gastos = df[df["Nº Cuenta"].str.startswith("5")].groupby(df["Fecha"].dt.date)["Debe"].sum()
    diario = pd.DataFrame({"ingresos": ingresos, "gastos": gastos}).fillna(0.0)
    diario["ahorro"] = diario["ingresos"] - diario["gastos"]

    all_dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    diario = diario.reindex(all_dates.date, fill_value=0.0)

    diario.index = pd.to_datetime(diario.index)
    diario["dow"] = diario.index.dayofweek
    iso = diario.index.isocalendar()
    diario["week"] = iso.week
    diario["year_iso"] = iso.year
    diario.loc[diario["year_iso"] < year, "week"] = 0
    diario.loc[(diario["year_iso"] > year) & (diario["week"] < 5), "week"] = 53

    value_col = {"ingresos": "ingresos", "gastos": "gastos", "mixto": "ahorro"}[metric]

    if metric == "gastos":
        diario["__activity"] = diario["gastos"].abs() > 1e-9
    elif metric == "ingresos":
        diario["__activity"] = diario["ingresos"].abs() > 1e-9
    else:
        diario["__activity"] = (diario["ingresos"].abs() > 1e-9) | (diario["gastos"].abs() > 1e-9)

    pivot = diario.pivot_table(index="dow", columns="week", values=value_col, aggfunc="sum")
    pivot = pivot.reindex(sorted(pivot.columns), axis=1).reindex([0, 1, 2, 3, 4, 5, 6])

    activity_pivot = diario.pivot_table(
        index="dow", columns="week", values="__activity", aggfunc="max"
    )
    activity_pivot = activity_pivot.reindex(sorted(activity_pivot.columns), axis=1).reindex(
        [0, 1, 2, 3, 4, 5, 6]
    )

    return diario, pivot, activity_pivot


def _calculate_dow_stats(z):
    stats_by_dow = {}
    for dow in range(7):
        dow_values = [
            v
            for row_idx, row in enumerate(z)
            if row_idx == dow
            for v in row
            if v is not None and not (isinstance(v, float) and math.isnan(v))
        ]
        if dow_values:
            median = float(pd.Series(dow_values).median())
            std = float(pd.Series(dow_values).std())
            stats_by_dow[dow] = {"median": median, "std": std}
        else:
            stats_by_dow[dow] = {"median": 0.0, "std": 1.0}
    return stats_by_dow


def build_annual_savings_heatmap(
    df_diario: pd.DataFrame,
    year: int | None = None,
    metric: str = "mixto",
    recent_weeks: int | None = None,
) -> go.Figure | None:
    if df_diario is None or df_diario.empty:
        return None

    metric = metric.lower().strip()
    if metric not in ("ingresos", "gastos", "mixto"):
        metric = "mixto"

    if year is None:
        year = pd.Timestamp.today().year

    diario, pivot, activity_pivot = _prepare_heatmap_data(df_diario, year, metric)
    if diario is None:
        return None

    if recent_weeks and recent_weeks > 0 and pivot is not None:
        today_wk = int(pd.Timestamp.today().week)
        valid_cols = [c for c in pivot.columns if int(c) <= today_wk]
        if not valid_cols:
            valid_cols = list(pivot.columns)
        sel_cols = valid_cols[-recent_weeks:] if len(valid_cols) > recent_weeks else valid_cols
        pivot = pivot[sel_cols]
        if activity_pivot is not None:
            activity_pivot = activity_pivot[sel_cols]

    semana_a_mes: dict[int, str] = {}
    for d, w in zip(diario.index, diario["week"], strict=False):
        if int(w) not in semana_a_mes:
            semana_a_mes[int(w)] = d.strftime("%b")

    x_labels = [semana_a_mes.get(int(w), "") for w in pivot.columns]
    seen: set[str] = set()
    x_text = []
    for lbl in x_labels:
        if lbl and lbl not in seen:
            x_text.append(lbl)
            seen.add(lbl)
        else:
            x_text.append("")

    raw_vals = pivot.values
    activity_mask = activity_pivot.values.astype(bool)
    z = [
        [
            (
                None
                if not bool(activity_mask[i][j])
                else (
                    None
                    if (
                        raw_vals[i][j] is None
                        or (isinstance(raw_vals[i][j], float) and math.isnan(raw_vals[i][j]))
                    )
                    else float(raw_vals[i][j])
                )
            )
            for j in range(raw_vals.shape[1])
        ]
        for i in range(raw_vals.shape[0])
    ]
    flat = [
        v
        for row in z
        for v in row
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    ]

    stats_by_dow = _calculate_dow_stats(z)

    diario_by_dow_week = {
        (d.dayofweek, int(w)): d for d, w in zip(diario.index, diario["week"], strict=False)
    }
    fechas_matrix = [
        [
            (
                diario_by_dow_week.get((dow, int(w))).strftime("%a %d %b %Y")
                if diario_by_dow_week.get((dow, int(w))) is not None
                else "—"
            )
            for w in pivot.columns
        ]
        for dow in range(7)
    ]

    hover_label = {"ingresos": "Ingresos", "gastos": "Gastos", "mixto": "Ahorro"}[metric]

    if metric == "mixto":
        active = [abs(v) for v in flat if abs(v) > 1.0]
        cap = float(pd.Series(active).quantile(0.95)) if active else 1.0
        if cap < 1.0:
            cap = max(active) if active else 1.0
        colorscale = [
            [0.0, "#FF1744"],
            [0.499, "#B91C1C"],
            [0.5, "#52525B"],
            [0.501, "#047857"],
            [1.0, "#00E676"],
        ]
        heatmap_kwargs = dict(
            z=z,
            x=list(pivot.columns),
            y=list(range(7)),
            colorscale=colorscale,
            zmin=-cap,
            zmax=cap,
            zmid=0.0,
            customdata=fechas_matrix,
            hovertemplate="<b>%{customdata}</b><br>" + hover_label + ": %{z:,.2f} €<extra></extra>",
            xgap=2,
            ygap=2,
            hoverongaps=False,
            colorbar=dict(title="€", thickness=10, len=0.8, tickformat=",.0f"),
        )
    else:
        colorscale = (
            [[0.0, "#7F1D1D"], [0.35, "#B91C1C"], [0.70, "#DC2626"], [1.0, "#FF1744"]]
            if metric == "gastos"
            else [
                [0.0, "#065F46"],
                [0.35, "#047857"],
                [0.70, "#00C853"],
                [1.0, "#00E676"],
            ]
        )

        z_normalized, custom_display = [], []
        for row_idx in range(len(z)):
            median, std = stats_by_dow[row_idx]["median"], stats_by_dow[row_idx]["std"]
            threshold = median + 2 * std if std > 0 else median
            if threshold <= median or threshold <= 0:
                threshold = max(median * 1.5, 1.0)

            fila, custom_fila = [], []
            for col_idx, v in enumerate(z[row_idx]):
                fecha = fechas_matrix[row_idx][col_idx]
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    fila.append(None)
                    custom_fila.append([fecha, 0.0, ""])
                else:
                    normalized = log_normalize(v, median, threshold)
                    fila.append(normalized)
                    annotation = "⚡ Saturado" if v > threshold else ""
                    custom_fila.append([fecha, v, annotation])
            z_normalized.append(fila)
            custom_display.append(custom_fila)

        hover_template_str = (
            "<b>%{customdata[0]}</b><br>"
            + hover_label
            + ": %{customdata[1]:,.2f} €<br>%{customdata[2]}<extra></extra>"
        )
        heatmap_kwargs = dict(
            z=z_normalized,
            x=list(pivot.columns),
            y=list(range(7)),
            colorscale=colorscale,
            zmin=0.0,
            zmax=1.0,
            customdata=custom_display,
            hovertemplate=hover_template_str,
            xgap=2,
            ygap=2,
            hoverongaps=False,
            colorbar=dict(title="Saturación", thickness=10, len=0.8, tickformat=".0%"),
        )

    heatmap_kwargs_interior = heatmap_kwargs.copy()
    heatmap_kwargs_interior.update(
        {
            "xgap": 6,
            "ygap": 6,
            "showscale": False,
            "hoverinfo": "skip",
            "hovertemplate": None,
            "colorscale": [
                [0.0, "rgba(15, 15, 17, 0.75)"],
                [1.0, "rgba(15, 15, 17, 0.75)"],
            ],
        }
    )
    if "colorbar" in heatmap_kwargs_interior:
        del heatmap_kwargs_interior["colorbar"]

    fig = go.Figure()
    fig.add_trace(go.Heatmap(**heatmap_kwargs))
    fig.add_trace(go.Heatmap(**heatmap_kwargs_interior))

    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=list(pivot.columns),
            ticktext=x_text,
            side="top",
            showgrid=False,
            constrain="domain",
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            autorange="reversed",
            showgrid=False,
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
        ),
        height=260,
        margin=dict(t=20, b=10, l=40, r=10),
        **_LAYOUT_BASE,
    )
    fig.update_layout(plot_bgcolor="#0F0F11")
    return fig
