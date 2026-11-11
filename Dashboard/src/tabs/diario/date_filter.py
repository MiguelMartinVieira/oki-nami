"""
date_filter.py — Servicio y componentes visuales para el filtrado temporal del análisis.
"""

import pandas as pd


def get_date_range_from_mode(
    df_diario: pd.DataFrame,
    mode: str,
    year_val: int | None = None,
    month_val: str | None = None,
    range_val: tuple | list | None = None,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None, str]:
    """
    Devuelve (start_date, end_date, date_label) según el modo de periodo seleccionado.
    """
    if df_diario.empty or "Fecha" not in df_diario.columns:
        return None, None, "Histórico Completo"

    dates = df_diario["Fecha"].dropna()
    if dates.empty:
        return None, None, "Histórico Completo"

    max_date = dates.max()
    min_date = dates.min()

    if mode == "📅 Año Actual":
        start_date = pd.Timestamp(year=max_date.year, month=1, day=1)
        end_date = pd.Timestamp(year=max_date.year, month=12, day=31, hour=23, minute=59, second=59)
        return start_date, end_date, f"Año {max_date.year}"

    elif mode == "📆 Últimos 12 Meses":
        end_date = max_date
        start_date = max_date - pd.DateOffset(years=1)
        label = f"{start_date.strftime('%d/%m/%Y')} — {end_date.strftime('%d/%m/%Y')}"
        return start_date, end_date, f"Últimos 12 meses ({label})"

    elif mode == "🗓️ Mes Actual":
        start_date = pd.Timestamp(year=max_date.year, month=max_date.month, day=1)
        end_date = (start_date + pd.offsets.MonthEnd(1)).replace(hour=23, minute=59, second=59)
        return start_date, end_date, f"Mes {max_date.strftime('%Y-%m')}"

    elif mode == "🎯 Año Concreto" and year_val is not None:
        y = int(year_val)
        start_date = pd.Timestamp(year=y, month=1, day=1)
        end_date = pd.Timestamp(year=y, month=12, day=31, hour=23, minute=59, second=59)
        return start_date, end_date, f"Año {y}"

    elif mode == "📆 Mes Concreto" and month_val is not None:
        try:
            period = pd.Period(month_val, freq="M")
            start_date = period.start_time
            end_date = period.end_time
            return start_date, end_date, f"Mes {month_val}"
        except Exception:
            return None, None, "Histórico Completo"

    elif mode == "⚙️ Rango Personalizado" and range_val and len(range_val) == 2:
        start_d, end_d = range_val[0], range_val[1]
        start_date = pd.Timestamp(start_d)
        end_date = pd.Timestamp(end_d).replace(hour=23, minute=59, second=59)
        label = f"{start_date.strftime('%d/%m/%Y')} — {end_date.strftime('%d/%m/%Y')}"
        return start_date, end_date, f"Rango ({label})"

    # Default "🌐 Histórico Completo"
    label = (
        f"Histórico Completo ({min_date.strftime('%d/%m/%Y')} — {max_date.strftime('%d/%m/%Y')})"
    )
    return None, None, label


def get_available_period_options(df_diario: pd.DataFrame) -> dict:
    """Extrae años, meses y límites de fechas para selectores."""
    if df_diario.empty or "Fecha" not in df_diario.columns:
        today = pd.Timestamp.today().date()
        return {
            "min_date": today,
            "max_date": today,
            "years": [today.year],
            "months": [today.strftime("%Y-%m")],
        }

    dates_valid = df_diario["Fecha"].dropna()
    min_date = dates_valid.min().date()
    max_date = dates_valid.max().date()

    years = sorted(df_diario["Fecha"].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
    months = sorted(
        df_diario["Fecha"].dt.to_period("M").dropna().unique().astype(str).tolist(), reverse=True
    )

    return {
        "min_date": min_date,
        "max_date": max_date,
        "years": years if years else [max_date.year],
        "months": months if months else [max_date.strftime("%Y-%m")],
    }
