"""
cost_per_day.py — Traduce el gasto mensual por categoría a unidades
emocionales: € al día, horas de trabajo al sueldo/hora.

Convierte un "gasto bajo el radar" como Cafeína en algo accionable:
en vez de "120 € al mes en cafés", muestra "4 € al día · 12 horas
trabajadas al mes para pagarlos".

Reglas:
  - Se calcula sobre los últimos `months_lookback` meses (default 3).
  - Solo cuentas del grupo 5 (gastos), excluyendo filas pasivas TR
    (Saveback/RoundUp/Cashback/Interest/Bonificación).
  - El sueldo/hora es un parámetro (no se intenta derivarlo).
  - Las cuentas sin gasto en el periodo no aparecen.
"""

from __future__ import annotations

import pandas as pd

from constants import PREFIX_GASTOS
from data.gsheets import clean_cuenta_col
from services.analytics import _PASIVE_CATEGORIES_RE

# Constante razonable: una jornada laboral media son ~8h
HORAS_JORNADA = 8.0
DIAS_MES = 30.0


def compute_cost_per_day(
    df_diario: pd.DataFrame,
    *,
    sueldo_hora_eur: float,
    months_lookback: int = 3,
) -> pd.DataFrame:
    """
    Devuelve un DataFrame con el coste-por-día/hora/jornada por categoría.

    Args:
        df_diario: Libro Diario completo.
        sueldo_hora_eur: tu tarifa horaria efectiva (€/h).
        months_lookback: ventana hacia atrás para promediar el gasto mensual.

    Returns:
        DataFrame ordenado descendentemente por `€/mes`, con columnas:
            Categoría       — nombre de cuenta
            €/mes           — gasto medio mensual en la ventana
            €/día           — €/mes ÷ 30
            Horas/día       — €/día ÷ sueldo_hora
            Horas/mes       — €/mes ÷ sueldo_hora
            Jornadas/mes    — Horas/mes ÷ 8 (jornadas laborales completas)
    """
    cols = ["Categoría", "€/mes", "€/día", "Horas/día", "Horas/mes", "Jornadas/mes"]
    if df_diario is None or df_diario.empty or sueldo_hora_eur <= 0:
        return pd.DataFrame(columns=cols)

    df = clean_cuenta_col(df_diario.copy())
    df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])

    # Solo gastos con Debe > 0
    df = df[df["Nº Cuenta"].str.startswith(PREFIX_GASTOS, na=False) & (df["Debe"] > 0)]

    # Excluir pasivas TR
    blob = df.get("Categoría", "").astype(str) + " " + df.get("Descripción", "").astype(str)
    mask_active = ~blob.str.contains(
        _PASIVE_CATEGORIES_RE.pattern, regex=True, case=False, na=False
    )
    df = df[mask_active]

    # Filtrar a la ventana
    if months_lookback > 0:
        cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(months=months_lookback)
        df = df[df["Fecha"] >= cutoff]

    if df.empty:
        return pd.DataFrame(columns=cols)

    # Agregar por categoría: gasto total en la ventana → mensualizar
    grouped = df.groupby("Cuenta")["Debe"].sum()
    eur_mes = grouped / max(months_lookback, 1)
    eur_dia = eur_mes / DIAS_MES
    horas_dia = eur_dia / sueldo_hora_eur
    horas_mes = eur_mes / sueldo_hora_eur
    jornadas_mes = horas_mes / HORAS_JORNADA

    result = pd.DataFrame(
        {
            "Categoría": eur_mes.index,
            "€/mes": eur_mes.values.round(2),
            "€/día": eur_dia.values.round(2),
            "Horas/día": horas_dia.values.round(2),
            "Horas/mes": horas_mes.values.round(1),
            "Jornadas/mes": jornadas_mes.values.round(2),
        }
    )
    return result.sort_values("€/mes", ascending=False).reset_index(drop=True)


def estimate_sueldo_hora_from_ingresos(
    df_diario: pd.DataFrame,
    *,
    horas_mes_referencia: float = 160.0,
    months_lookback: int = 3,
) -> float:
    """Estimación opcional del sueldo/hora derivada de los ingresos del
    Diario. NO se usa por defecto (el slider de la UI prevalece), pero
    sirve como valor sugerido al usuario.

    Suma los ingresos de cuentas 44 (Sueldo) y 43 (Ítaca) de los últimos
    `months_lookback` meses, divide entre meses para obtener mensual, y
    luego entre `horas_mes_referencia` (default 160 = 40h × 4 semanas).

    Devuelve 0.0 si no hay datos.
    """
    if df_diario is None or df_diario.empty:
        return 0.0
    df = clean_cuenta_col(df_diario.copy())
    df["Haber"] = pd.to_numeric(df["Haber"], errors="coerce").fillna(0.0)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])

    cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(months=months_lookback)
    df = df[df["Fecha"] >= cutoff]
    df = df[df["Nº Cuenta"].isin(["43", "44"]) & (df["Haber"] > 0)]
    if df.empty:
        return 0.0
    ingresos_mes = float(df["Haber"].sum()) / max(months_lookback, 1)
    if ingresos_mes <= 0 or horas_mes_referencia <= 0:
        return 0.0
    return round(ingresos_mes / horas_mes_referencia, 2)
