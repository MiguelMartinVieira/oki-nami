"""
ipc.py — IPC España desde la API pública del INE.

Endpoint: https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/IPC251856?nult=36
Serie IPC251856 = Índice General IPC España (base 2021=100), datos mensuales.
No requiere clave de API. Se cachea 24h porque el INE actualiza mensualmente.
"""

import pandas as pd
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import requests

    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

_INE_URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/IPC251856?nult=48"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _fetch_ipc_json() -> list:
    resp = requests.get(_INE_URL, timeout=10)
    resp.raise_for_status()
    return resp.json().get("Data", [])


@st.cache_data(ttl=86_400, show_spinner=False)  # 24h
def get_ipc_series() -> pd.DataFrame | None:
    """
    Descarga la serie del IPC General España del INE.

    Returns:
        DataFrame con columnas ['Fecha', 'Valor'] ordenado ascendente,
        o None si no hay conexión.
    """
    if not _REQUESTS_OK:
        return None
    try:
        data = _fetch_ipc_json()
        if not data:
            return None
        df = pd.DataFrame(data)[["Fecha", "Valor"]].dropna()
        # Fecha viene en milisegundos Unix
        df["Fecha"] = pd.to_datetime(df["Fecha"], unit="ms")
        df = df.sort_values("Fecha").reset_index(drop=True)
        return df
    except Exception:
        return None
