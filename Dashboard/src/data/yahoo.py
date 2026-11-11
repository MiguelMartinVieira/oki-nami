"""
yahoo.py — Precios en vivo e históricos de Yahoo Finance.
"""

import logging
import os

import pandas as pd
import requests
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential

from constants import CACHE_DIR, TTL_YAHOO

log = logging.getLogger(__name__)

CACHE_DIR = str(CACHE_DIR)
os.makedirs(CACHE_DIR, exist_ok=True)


_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _fetch_yahoo_json(url: str) -> dict:
    headers = {
        "User-Agent": _DEFAULT_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_cached_price(ticker: str) -> float | None:
    """Intenta recuperar el último precio de cierre registrado en la caché local CSV."""
    cache_path = os.path.join(CACHE_DIR, f"yahoo_{ticker.replace('=', '_')}.csv")
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path)
            if not df.empty and "Price" in df.columns:
                valid = df["Price"].dropna()
                if not valid.empty:
                    last_val = float(valid.iloc[-1])
                    if last_val > 0:
                        return last_val
        except Exception as e:
            log.warning("No se pudo leer el último precio de caché para %s: %s", ticker, e)
    return None


@st.cache_data(ttl=TTL_YAHOO)
def get_yahoo_price(ticker: str) -> float | None:
    """
    Devuelve el precio de mercado actual para un ticker de Yahoo Finance.

    Si la llamada en vivo a Yahoo Finance falla (red, rate-limit o HTTP 403/429),
    recurre automáticamente al último precio en caché local para evitar
    mostrar 0.00 € o romper cálculos.
    """
    from services.demo_data import demo_price, is_demo_mode

    if is_demo_mode():
        return demo_price(ticker)

    urls = [
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d",
    ]
    for url in urls:
        try:
            data = _fetch_yahoo_json(url)
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            if price is not None and float(price) > 0:
                return float(price)
        except Exception as e:
            endpoint_name = url.split("/")[2] if "/" in url else url
            log.warning("Yahoo Finance endpoint (%s) falló para %s: %s", endpoint_name, ticker, e)

    # Fallback automático a caché local CSV
    cached = _get_cached_price(ticker)
    if cached is not None:
        log.warning(
            "Yahoo Finance caído para %s; usando fallback local en caché: %.2f", ticker, cached
        )
        return cached

    log.warning("Yahoo Finance: no se pudo obtener precio ni hay caché para %s", ticker)
    return None


@st.cache_data(ttl=TTL_YAHOO)
def get_yahoo_history(ticker: str, days: int = 90) -> pd.DataFrame:
    """
    Devuelve un DataFrame con columnas ['Date', 'Price']
    para los últimos N días de un ticker.
    Utiliza un caché local avanzado (CSV) para minimizar llamadas a la API.
    """
    from services.demo_data import demo_price_history, is_demo_mode

    if is_demo_mode():
        return demo_price_history(ticker, days)

    cache_path = os.path.join(CACHE_DIR, f"yahoo_{ticker.replace('=', '_')}.csv")

    df_cache = pd.DataFrame(columns=["Date", "Price"])
    if os.path.exists(cache_path):
        try:
            df_cache = pd.read_csv(cache_path)
            if not df_cache.empty and "Date" in df_cache.columns:
                df_cache["Date"] = pd.to_datetime(df_cache["Date"]).dt.date
            else:
                df_cache = pd.DataFrame(columns=["Date", "Price"])
        except Exception as e:
            log.warning("No se pudo leer el caché local de %s: %s", ticker, e)

    today = pd.Timestamp.today().date()
    cutoff_date = today - pd.Timedelta(days=days)

    missing_days = days
    if not df_cache.empty:
        max_date = df_cache["Date"].max()
        min_date = df_cache["Date"].min()
        missing_days = (today - max_date).days

        # Si el caché tiene menos días hacia atrás de los que pedimos, forzamos la descarga completa
        if min_date > cutoff_date:
            missing_days = days
            df_cache = pd.DataFrame(columns=["Date", "Price"])  # Reseteamos para evitar huecos

    if missing_days > 0:
        fetch_days = min(missing_days + 5, days) if not df_cache.empty else days
        endpoints = [
            f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={fetch_days}d",
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={fetch_days}d",
        ]
        data = None
        for u in endpoints:
            try:
                data = _fetch_yahoo_json(u)
                if (
                    data
                    and "chart" in data
                    and "result" in data["chart"]
                    and data["chart"]["result"]
                ):
                    break
            except Exception as e:
                endpoint_name = u.split("/")[2] if "/" in u else u
                log.warning(
                    "Yahoo Finance endpoint (%s) falló para historial de %s: %s",
                    endpoint_name,
                    ticker,
                    e,
                )

        if data:
            try:
                result = data["chart"]["result"][0]
                timestamps = result["timestamp"]
                prices = result["indicators"]["quote"][0]["close"]
                df_new = pd.DataFrame(
                    {
                        "Date": pd.to_datetime(timestamps, unit="s").date,
                        "Price": prices,
                    }
                )
                df_new = df_new.dropna()

                if not df_cache.empty:
                    df_cache = pd.concat([df_cache, df_new]).drop_duplicates(
                        subset=["Date"], keep="last"
                    )
                else:
                    df_cache = df_new

                df_cache = df_cache.sort_values("Date").reset_index(drop=True)
                df_cache.to_csv(cache_path, index=False)
            except Exception as e:
                log.warning("Error procesando historial de %s: %s", ticker, e)

    if df_cache.empty:
        return pd.DataFrame(columns=["Date", "Price"])

    return df_cache[df_cache["Date"] >= cutoff_date].copy()
