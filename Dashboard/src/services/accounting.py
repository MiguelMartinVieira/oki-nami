"""
accounting.py — Cálculos contables reutilizables.

Todas las funciones reciben DataFrames ya cargados y devuelven
valores calculados — sin acceso a datos externos.

Las funciones marcadas con @st.cache_data se cachean automáticamente
por Streamlit usando el contenido del DataFrame como clave (hash interno).
TTL = TTL_SHEETS para alinear el ciclo de invalidación con el de
get_diario() en data/gsheets.py.
"""

import pandas as pd
import streamlit as st

from constants import (
    BASE_ACCIONES_BRK,
    BRK_CHECKPOINT_DATE,
    CUENTA_BERKSHIRE,
    CUENTA_BOKATAS,
    CUENTA_CARTERA,
    CUENTA_HUCHA,
    CUENTA_PADRES,
    CUENTA_SP500,
    CUENTA_TR,
    HISTORY_START_DATE,
    PREFIX_GASTOS,
    PREFIX_INGRESOS,
    TTL_SHEETS,
)
from data.gsheets import clean_cuenta_col
from services.utils import extract_signed_quantity


def _ensure_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Copia el DataFrame y normaliza Nº Cuenta."""
    df = df.copy()
    return clean_cuenta_col(df)


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_metalico_fisico(df_diario: pd.DataFrame) -> float:
    """Saldo de efectivo físico: Cartera (111) + Hucha (112)."""
    if df_diario.empty:
        return 0.0
    df = _ensure_clean(df_diario)
    mask = df["Nº Cuenta"].str.startswith((CUENTA_CARTERA, CUENTA_HUCHA))
    df = df[mask]
    if df.empty:
        return 0.0
    value = pd.to_numeric(df["Debe"], errors="coerce").fillna(0) - pd.to_numeric(
        df["Haber"], errors="coerce"
    ).fillna(0)
    return float(value.sum())


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_metalico_desglose(df_diario: pd.DataFrame) -> dict:
    """Saldo individual de Cartera (111) y Hucha (112).

    Returns:
        {"cartera": float, "hucha": float}
    """
    if df_diario.empty:
        return {"cartera": 0.0, "hucha": 0.0}
    df = _ensure_clean(df_diario)
    result = {}
    for cuenta, nombre in [(CUENTA_CARTERA, "cartera"), (CUENTA_HUCHA, "hucha")]:
        mask = df["Nº Cuenta"].str.startswith(cuenta)
        subset = df[mask]
        if subset.empty:
            result[nombre] = 0.0
        else:
            debe = pd.to_numeric(subset["Debe"], errors="coerce").fillna(0)
            haber = pd.to_numeric(subset["Haber"], errors="coerce").fillna(0)
            result[nombre] = float((debe - haber).sum())
    return result


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_bokatas_saldo(df_diario: pd.DataFrame) -> float:
    """
    Saldo disponible de la ONG Bokatas en TR (cuenta 133).

    La cuenta 133 es un PASIVO: Haber = entradas de la ONG,
    Debe = pagos realizados. El saldo disponible = Haber - Debe.
    Este importe está físicamente dentro del saldo de la cuenta 121.
    """
    if df_diario.empty:
        return 0.0
    df = _ensure_clean(df_diario)
    df = df[df["Nº Cuenta"] == CUENTA_BOKATAS]
    if df.empty:
        return 0.0
    haber = pd.to_numeric(df["Haber"], errors="coerce").fillna(0).sum()
    debe = pd.to_numeric(df["Debe"], errors="coerce").fillna(0).sum()
    return max(haber - debe, 0.0)  # nunca negativo por seguridad


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_bokatas_detalle(df_diario: pd.DataFrame) -> dict:
    """
    Devuelve total_recibido, total_pagado y saldo_disponible para la ONG.
    Centraliza la lógica que antes estaba en tab_bokatas.
    """
    if df_diario.empty:
        return {"total_recibido": 0.0, "total_pagado": 0.0, "saldo_disponible": 0.0}
    df = _ensure_clean(df_diario)
    df = df[df["Nº Cuenta"] == CUENTA_BOKATAS]
    if df.empty:
        return {"total_recibido": 0.0, "total_pagado": 0.0, "saldo_disponible": 0.0}
    total_recibido = pd.to_numeric(df["Haber"], errors="coerce").fillna(0).sum()
    total_pagado = pd.to_numeric(df["Debe"], errors="coerce").fillna(0).sum()
    return {
        "total_recibido": total_recibido,
        "total_pagado": total_pagado,
        "saldo_disponible": max(total_recibido - total_pagado, 0.0),
    }


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_padres_saldo(df_diario: pd.DataFrame) -> dict:
    """
    Devuelve total_debe, total_haber y saldo_pendiente para cuenta 131.
    """
    if df_diario.empty:
        return {"total_debe": 0.0, "total_haber": 0.0, "saldo_pendiente": 0.0}
    df = _ensure_clean(df_diario)
    df = df[df["Nº Cuenta"] == CUENTA_PADRES]
    if df.empty:
        return {"total_debe": 0.0, "total_haber": 0.0, "saldo_pendiente": 0.0}
    total_debe = pd.to_numeric(df["Debe"], errors="coerce").fillna(0).sum()
    total_haber = pd.to_numeric(df["Haber"], errors="coerce").fillna(0).sum()
    return {
        "total_debe": total_debe,
        "total_haber": total_haber,
        "saldo_pendiente": total_debe - total_haber,
    }


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_padres_total(df_diario: pd.DataFrame, as_of_date=None) -> float:
    """
    Saldo neto pendiente que me deben (cuentas 131, 132 y 134 — excluye 133 Bokatas).

    Cuentas de deudas a cobrar:
      - Debe  = dinero que adelanté / me deben
      - Haber = dinero que ya me han devuelto

    El saldo neto = Debe − Haber (lo que aún queda por cobrar).

    Si as_of_date se proporciona, calcula el saldo solo hasta esa fecha.
    """
    if df_diario.empty:
        return 0.0
    df = _ensure_clean(df_diario)

    # Filtrar por fecha si se proporciona
    if as_of_date is not None:
        df = df[df["Fecha"].dt.date <= as_of_date]

    df = df[df["Nº Cuenta"].astype(str).str.startswith("13") & (df["Nº Cuenta"] != CUENTA_BOKATAS)]
    if df.empty:
        return 0.0
    debe = pd.to_numeric(df["Debe"], errors="coerce").fillna(0).sum()
    haber = pd.to_numeric(df["Haber"], errors="coerce").fillna(0).sum()
    return float(max(debe - haber, 0.0))  # nunca negativo


def filter_cuenta(df_diario: pd.DataFrame, cuenta: str) -> pd.DataFrame:
    """Filtra el diario por una cuenta concreta, devolviendo copia limpia."""
    df = _ensure_clean(df_diario)
    return df[df["Nº Cuenta"] == cuenta].copy()


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_tr_cash(df_diario: pd.DataFrame) -> float:
    """
    Saldo personal de liquidez en Trade Republic (cuenta 121).

    Se descuenta el saldo de la cuenta 133 (Bokatas ONG) porque ese
    dinero está físicamente en TR pero NO pertenece a Miguel.
    """
    if df_diario.empty:
        return 0.0
    df = _ensure_clean(df_diario)
    mask = df["Nº Cuenta"].str.startswith(CUENTA_TR)
    df_tr = df[mask]
    if df_tr.empty:
        return 0.0
    value = pd.to_numeric(df_tr["Debe"], errors="coerce").fillna(0) - pd.to_numeric(
        df_tr["Haber"], errors="coerce"
    ).fillna(0)
    saldo_121 = float(value.sum())
    saldo_bokatas = calc_bokatas_saldo(df_diario)
    return saldo_121 - saldo_bokatas


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_brk_shares(df_diario: pd.DataFrame) -> float:
    """
    Calcula el número total de acciones de Berkshire.
    Base (checkpoint) + compras/ventas del Diario (campo Descripción: 'quantity: X.XXXXXX').
    Las ventas (Haber > Debe o categoría Venta) restan acciones.
    """
    extra = 0.0
    if not df_diario.empty:
        df = _ensure_clean(df_diario)
        df_141 = df[df["Nº Cuenta"] == CUENTA_BERKSHIRE]
        if not df_141.empty:
            fechas = pd.to_datetime(df_141["Fecha"])
            checkpoint = pd.to_datetime(BRK_CHECKPOINT_DATE)
            mask = fechas > checkpoint
            df_filtered = df_141[mask]
            if not df_filtered.empty:
                extra = df_filtered.apply(extract_signed_quantity, axis=1).sum()

    return BASE_ACCIONES_BRK + extra


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_vanguard_shares(df_diario: pd.DataFrame) -> float:
    """
    Calcula el número total de participaciones de Vanguard SP500.
    Extrae la cantidad del campo Descripción: 'quantity: X.XXXXXX' de la cuenta 142.
    Las ventas (Haber > Debe o categoría Venta) restan participaciones.
    """
    total = 0.0
    if not df_diario.empty:
        df = _ensure_clean(df_diario)
        df_142 = df[df["Nº Cuenta"] == CUENTA_SP500]
        if not df_142.empty:
            total = df_142.apply(extract_signed_quantity, axis=1).sum()

    return total


def filter_df_by_date_range(
    df: pd.DataFrame,
    start_date: pd.Timestamp | str | None = None,
    end_date: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Filtra un DataFrame contable por rango de fechas [start_date, end_date]."""
    if df.empty or "Fecha" not in df.columns:
        return df.copy() if hasattr(df, "copy") else df
    df_filtered = df.copy()
    if start_date is not None and not pd.isna(start_date):
        df_filtered = df_filtered[df_filtered["Fecha"] >= pd.to_datetime(start_date)]
    if end_date is not None and not pd.isna(end_date):
        end_ts = (
            pd.to_datetime(end_date).normalize()
            + pd.Timedelta(days=1)
            - pd.Timedelta(nanoseconds=1)
        )
        df_filtered = df_filtered[df_filtered["Fecha"] <= end_ts]
    return df_filtered


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_gastos_ingresos(df_diario: pd.DataFrame) -> dict:
    """
    Calcula totales mensuales e históricos de gastos e ingresos.

    Returns:
        dict con claves:
            df_gastos, df_ingresos, current_month,
            cm_gastos, pm_gastos, cm_ingresos, pm_ingresos,
            total_hist_gastos, total_hist_ingresos,
            cat_expenses (Series), cat_incomes (Series),
            df_gastos_cm, df_ingresos_cm,
            cat_expenses_cm (Series), cat_incomes_cm (Series)
    """
    df = _ensure_clean(df_diario)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    # Excluir movimientos anteriores al inicio del dashboard
    df = df[df["Fecha"] >= pd.to_datetime(HISTORY_START_DATE)]

    df["Mes"] = df["Fecha"].dt.to_period("M")
    current_month = df["Fecha"].dt.to_period("M").max()

    df_gastos = df[df["Nº Cuenta"].str.startswith(PREFIX_GASTOS)].copy()
    df_ingresos = df[df["Nº Cuenta"].str.startswith(PREFIX_INGRESOS)].copy()

    total_hist_gastos = df_gastos["Debe"].sum()
    total_hist_ingresos = df_ingresos["Haber"].sum()

    if pd.isna(current_month):
        cm_gastos = 0.0
        pm_gastos = 0.0
        cm_ingresos = 0.0
        pm_ingresos = 0.0
    else:
        cm_gastos = df_gastos[df_gastos["Mes"] == current_month]["Debe"].sum()
        pm_gastos = df_gastos[df_gastos["Mes"] == current_month - 1]["Debe"].sum()
        cm_ingresos = df_ingresos[df_ingresos["Mes"] == current_month]["Haber"].sum()
        pm_ingresos = df_ingresos[df_ingresos["Mes"] == current_month - 1]["Haber"].sum()

    # Histórico
    cat_expenses = df_gastos.groupby("Cuenta")["Debe"].sum()
    cat_expenses = cat_expenses[cat_expenses > 0]
    cat_incomes = df_ingresos.groupby("Cuenta")["Haber"].sum()
    cat_incomes = cat_incomes[cat_incomes > 0]

    # Mes Actual (cm)
    df_gastos_cm = df_gastos[df_gastos["Mes"] == current_month]
    df_ingresos_cm = df_ingresos[df_ingresos["Mes"] == current_month]

    cat_expenses_cm = df_gastos_cm.groupby("Cuenta")["Debe"].sum()
    cat_expenses_cm = cat_expenses_cm[cat_expenses_cm > 0]
    cat_incomes_cm = df_ingresos_cm.groupby("Cuenta")["Haber"].sum()
    cat_incomes_cm = cat_incomes_cm[cat_incomes_cm > 0]

    # Inversiones (cuentas 141 y 142 — Berkshire y Vanguard)
    df_inversiones = df[df["Nº Cuenta"].isin([CUENTA_BERKSHIRE, CUENTA_SP500])].copy()
    debe_inv = pd.to_numeric(df_inversiones["Debe"], errors="coerce").fillna(0).sum()
    haber_inv = pd.to_numeric(df_inversiones["Haber"], errors="coerce").fillna(0).sum()
    total_inversiones = float(debe_inv - haber_inv)

    df_inversiones_cm = df_inversiones[df_inversiones["Mes"] == current_month]
    debe_inv_cm = pd.to_numeric(df_inversiones_cm["Debe"], errors="coerce").fillna(0).sum()
    haber_inv_cm = pd.to_numeric(df_inversiones_cm["Haber"], errors="coerce").fillna(0).sum()
    total_inversiones_cm = float(debe_inv_cm - haber_inv_cm)

    return {
        "df_gastos": df_gastos,
        "df_ingresos": df_ingresos,
        "current_month": current_month,
        "cm_gastos": cm_gastos,
        "pm_gastos": pm_gastos,
        "cm_ingresos": cm_ingresos,
        "pm_ingresos": pm_ingresos,
        "total_hist_gastos": total_hist_gastos,
        "total_hist_ingresos": total_hist_ingresos,
        "cat_expenses": cat_expenses,
        "cat_incomes": cat_incomes,
        "df_gastos_cm": df_gastos_cm,
        "df_ingresos_cm": df_ingresos_cm,
        "cat_expenses_cm": cat_expenses_cm,
        "cat_incomes_cm": cat_incomes_cm,
        "df_inversiones": df_inversiones,
        "df_inversiones_cm": df_inversiones_cm,
        "total_inversiones": total_inversiones,
        "total_inversiones_cm": total_inversiones_cm,
    }


def calc_ahorro(ingresos: float, gastos: float) -> tuple[float, float]:
    """Devuelve (ahorro_mes, tasa_ahorro_pct)."""
    ahorro = ingresos - gastos
    tasa = (ahorro / ingresos * 100) if ingresos > 0 else 0.0
    return ahorro, tasa


def get_color_smooth(percent: float) -> str:
    """
    Color HSL que transiciona de rojo (-20%) a verde (50%)
    según la tasa de ahorro.
    """
    normalized = max(-20, min(50, percent))
    hue = (normalized + 20) * (140 / 70)
    return f"hsl({hue}, 75%, 45%)"


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_portfolio_summary(df_diario: pd.DataFrame, metalico_fisico: float) -> dict:
    """
    Calcula el resumen de patrimonio de forma DRY para ser usado en tab_diario y tab_inversiones.
    """
    from config.logic import TICKER_BRK, TICKER_EURUSD, TICKER_VANGUARD
    from data.yahoo import get_yahoo_price

    precio_fondo = get_yahoo_price(TICKER_VANGUARD) or 0.0
    precio_brk_usd = get_yahoo_price(TICKER_BRK) or 0.0
    usd_to_eur = get_yahoo_price(TICKER_EURUSD) or 1.0

    acciones_brk = calc_brk_shares(df_diario)
    acciones_vanguard = calc_vanguard_shares(df_diario)
    tr_cash = calc_tr_cash(df_diario)
    bokatas_saldo = calc_bokatas_saldo(df_diario)
    padres_total = calc_padres_total(df_diario)

    valor_fondo_eur = acciones_vanguard * precio_fondo
    valor_brk_eur = acciones_brk * precio_brk_usd * usd_to_eur
    total_patrimonio = valor_fondo_eur + valor_brk_eur + tr_cash + metalico_fisico + padres_total

    return {
        "precio_fondo": precio_fondo,
        "precio_brk_usd": precio_brk_usd,
        "usd_to_eur": usd_to_eur,
        "acciones_brk": acciones_brk,
        "acciones_vanguard": acciones_vanguard,
        "tr_cash": tr_cash,
        "bokatas_saldo": bokatas_saldo,
        "padres_total": padres_total,
        "valor_fondo_eur": valor_fondo_eur,
        "valor_brk_eur": valor_brk_eur,
        "total_patrimonio": total_patrimonio,
    }


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_ahorro_ytd(df_diario: pd.DataFrame) -> float:
    """Calcula el ahorro acumulado basado en las inversiones netas (cuentas 14x: Debe - Haber) para el año actual."""
    if df_diario.empty:
        return 0.0
    df = _ensure_clean(df_diario)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    # Filtro del año actual a partir de HISTORY_START_DATE (19 de Marzo)
    year_start = max(
        pd.to_datetime(f"{pd.Timestamp.today().year}-01-01"),
        pd.to_datetime(HISTORY_START_DATE),
    )
    df_ytd = df[df["Fecha"] >= year_start]
    if df_ytd.empty:
        return 0.0

    inversiones_mask = df_ytd["Nº Cuenta"].astype(str).str.startswith("14")
    debe = pd.to_numeric(df_ytd[inversiones_mask]["Debe"], errors="coerce").fillna(0).sum()
    haber = pd.to_numeric(df_ytd[inversiones_mask]["Haber"], errors="coerce").fillna(0).sum()

    return float(debe - haber)
