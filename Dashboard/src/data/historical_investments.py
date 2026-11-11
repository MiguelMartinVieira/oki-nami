"""
historical_investments.py — Operaciones de inversión anteriores a la
contabilidad por partida doble (brókers antiguos, posiciones ya cerradas).

Los datos reales se leen de `data/backups/historical_investments.json`, que
está fuera de git. Si no existe (clon limpio, CI, DEMO_MODE) se usa un
historial de ejemplo con la misma forma.

Formato de cada registro:
    {"Fecha": "dd/mm/aaaa", "Activo": str, "Operación": str,
     "Importe (€)": float, "Estado": "Completada" | "Activa"}
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

HISTORY_FILE = Path(__file__).resolve().parent / "backups" / "historical_investments.json"

EXAMPLE_HISTORY: list[dict] = [
    {
        "Fecha": "15/01/2019",
        "Activo": "Fondo indexado S&P 500 (bróker A)",
        "Operación": "Compra",
        "Importe (€)": 300.00,
        "Estado": "Completada",
    },
    {
        "Fecha": "10/09/2019",
        "Activo": "Fondo indexado S&P 500 (bróker A)",
        "Operación": "Compra",
        "Importe (€)": 250.00,
        "Estado": "Completada",
    },
    {
        "Fecha": "02/03/2021",
        "Activo": "Fondo indexado S&P 500 (bróker A)",
        "Operación": "Compra",
        "Importe (€)": 500.00,
        "Estado": "Completada",
    },
    {
        "Fecha": "20/05/2024",
        "Activo": "Fondo indexado S&P 500 (bróker A)",
        "Operación": "Traspaso de salida",
        "Importe (€)": 1450.00,
        "Estado": "Completada",
    },
    {
        "Fecha": "20/05/2024",
        "Activo": "Fondo indexado S&P 500 (bróker B)",
        "Operación": "Traspaso de entrada",
        "Importe (€)": 1450.00,
        "Estado": "Completada",
    },
    {
        "Fecha": "03/09/2024",
        "Activo": "Monetario EUR",
        "Operación": "Compra",
        "Importe (€)": 800.00,
        "Estado": "Completada",
    },
    {
        "Fecha": "25/02/2026",
        "Activo": "Monetario EUR",
        "Operación": "Venta",
        "Importe (€)": 835.20,
        "Estado": "Completada",
    },
    {
        "Fecha": "25/02/2026",
        "Activo": "Vanguard SP500",
        "Operación": "Traspaso de entrada",
        "Importe (€)": 2100.00,
        "Estado": "Activa",
    },
]


def _load_records() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            log.warning("No se pudo leer %s (%s); usando historial de ejemplo.", HISTORY_FILE, e)
    return EXAMPLE_HISTORY


def get_historical_investments() -> pd.DataFrame:
    """Devuelve el historial de operaciones antiguas como DataFrame."""
    df = pd.DataFrame(_load_records())
    df["Fecha"] = pd.to_datetime(df["Fecha"], format="%d/%m/%Y")
    return df
