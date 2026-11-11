"""
history.py — Lógica de sincronización incremental del histórico.
"""

import logging
from datetime import date, timedelta

import pandas as pd

from constants import (
    HISTORY_START_DATE,
    TICKER_BRK,
    TICKER_EURUSD,
    TICKER_VANGUARD,
    TICKER_VWRL_PROXY,
)
from data.gsheets import (
    SHEET_HISTORICO,
    SHEET_URL,
    _get_gspread_client,
    append_to_historico,
    get_historico,
)
from data.yahoo import get_yahoo_history
from services.accounting import (
    calc_brk_shares,
    calc_metalico_fisico,
    calc_padres_total,
    calc_tr_cash,
    calc_vanguard_shares,
)

log = logging.getLogger(__name__)


def update_historico(df_diario: pd.DataFrame, force: bool = False) -> bool:
    """
    Sincroniza el histórico de saldos día a día.
    """
    from services.demo_data import block_writes_in_demo

    if block_writes_in_demo("update_historico"):
        return False

    if force:
        _clear_historico_storage()
        df_hist = pd.DataFrame()
    else:
        df_hist = get_historico()

    # 1. Determinar fecha de inicio
    if df_hist.empty or "Fecha" not in df_hist.columns:
        last_date = pd.to_datetime(HISTORY_START_DATE).date() - timedelta(days=1)
    else:
        last_date = df_hist["Fecha"].max().date()

    target_end = date.today() - timedelta(days=1)

    if last_date >= target_end:
        return False  # Ya está al día

    # 2. Preparar rango de fechas
    missing_dates = pd.date_range(start=last_date + timedelta(days=1), end=target_end).date.tolist()

    if not missing_dates:
        return False

    msg = f"Sincronizando {len(missing_dates)} días de histórico..."
    log.info(msg)

    # 3. Obtener precios históricos (Yahoo) para todo el rango necesario
    days_back = (date.today() - (last_date + timedelta(days=1))).days + 15
    hist_brk = get_yahoo_history(TICKER_BRK, days=max(days_back, 30))
    hist_van = get_yahoo_history(TICKER_VWRL_PROXY, days=max(days_back, 30))
    hist_van_direct = get_yahoo_history(TICKER_VANGUARD, days=max(days_back, 30))
    hist_fx = get_yahoo_history(TICKER_EURUSD, days=max(days_back, 30))

    # Pre-procesar dataframes de Yahoo en un solo dataframe indexado por fecha (ffill)
    dfs = []
    for df, name in [
        (hist_brk, "brk"),
        (hist_van, "proxy_van"),
        (hist_van_direct, "van_direct"),
        (hist_fx, "fx"),
    ]:
        if not df.empty and "Date" in df.columns and "Price" in df.columns:
            df_temp = df[["Date", "Price"]].rename(columns={"Price": name})
            df_temp["Date"] = pd.to_datetime(df_temp["Date"]).dt.date
            # Agrupar por si hay múltiples precios en el mismo día
            df_temp = df_temp.groupby("Date").last()
            dfs.append(df_temp)

    if not dfs:
        # Fallback if Yahoo returned nothing at all
        df_prices = pd.DataFrame(index=missing_dates)
    else:
        min_date = min([df.index.min() for df in dfs] + [min(missing_dates)])
        max_date = max(missing_dates)
        df_prices = pd.DataFrame(index=pd.date_range(start=min_date, end=max_date).date)
        for df in dfs:
            df_prices = df_prices.join(df, how="left")
        df_prices = df_prices.ffill().bfill()

    new_rows = []

    for d in missing_dates:
        # Filtramos diario hasta ese día EOD
        df_d = df_diario[df_diario["Fecha"].dt.date <= d].copy()

        # Calcular balances
        efectivo_fisico = calc_metalico_fisico(df_d)
        tr_cash_neto = calc_tr_cash(df_d)
        brk_shares = calc_brk_shares(df_d)
        padres_total = calc_padres_total(df_d, as_of_date=d)

        # Precios
        try:
            row_p = df_prices.loc[d]
            p_brk_usd = row_p.get("brk")
            p_proxy_van = row_p.get("proxy_van")
            p_van_direct = row_p.get("van_direct")
            fx = row_p.get("fx")
        except KeyError:
            p_brk_usd = p_proxy_van = p_van_direct = fx = None

        if pd.isna(p_brk_usd) or pd.isna(fx):
            log.info("Sin datos de precio para %s, saltando día", d)
            continue

        van_shares = calc_vanguard_shares(df_d)

        if not pd.isna(p_proxy_van) and not pd.isna(p_van_direct):
            van_ratio_daily = p_van_direct / p_proxy_van
        else:
            van_ratio_daily = 1.0
            if pd.isna(p_proxy_van) or pd.isna(p_van_direct):
                log.debug("Sin datos de precio Vanguard para %s, usando ratio 1.0", d)

        van_value = van_shares * (p_proxy_van if not pd.isna(p_proxy_van) else 0) * van_ratio_daily
        brk_value_eur = brk_shares * p_brk_usd * fx

        total = efectivo_fisico + tr_cash_neto + van_value + brk_value_eur + padres_total

        new_rows.append(
            [
                d,
                round(efectivo_fisico, 2),
                round(tr_cash_neto, 2),
                round(brk_value_eur, 2),
                round(van_value, 2),
                round(padres_total, 2),
                round(total, 2),
            ]
        )

    if new_rows:
        append_to_historico(new_rows)
        return True

    return False


def _clear_historico_storage():
    """Limpia el histórico para forzar recalculado."""
    try:
        import os

        from data.gsheets import CREDENTIALS_FILE, CSV_HISTORICO, GSHEETS_AVAILABLE

        if os.path.exists(CSV_HISTORICO):
            os.remove(CSV_HISTORICO)

        # En GSheets vaciar pero mantener cabecera
        if GSHEETS_AVAILABLE and os.path.exists(CREDENTIALS_FILE):
            client = _get_gspread_client()
            sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_HISTORICO)
            sheet.clear()
            sheet.update(
                range_name="A1",
                values=[
                    [
                        "Fecha",
                        "Efectivo Fisico",
                        "Efectivo TR",
                        "BRK Value",
                        "Vanguard Value",
                        "Te Deben",
                        "Total",
                    ]
                ],
            )
        get_historico.clear()
    except Exception as e:
        log.error("Error al limpiar histórico: %s", e)
