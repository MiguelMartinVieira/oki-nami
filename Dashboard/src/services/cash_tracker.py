"""
cash_tracker.py — Servicio de rastreo de efectivo por denominación.

Gestiona el desglose de billetes y monedas en Cartera (111) y Hucha (112),
persistido en la hoja "Denominaciones" de Google Sheets.
"""

import logging

from constants import ALL_DENOMINATIONS, DENOMINATIONS_BILLS

log = logging.getLogger(__name__)


def get_empty_template() -> dict:
    """Devuelve una estructura vacía con todas las denominaciones a 0.

    Returns:
        {"cartera": {100: 0, 50: 0, ...}, "hucha": {100: 0, 50: 0, ...}}
    """
    empty = {d: 0 for d in ALL_DENOMINATIONS}
    return {"cartera": dict(empty), "hucha": dict(empty)}


def calc_total(counts: dict[float, int]) -> float:
    """Calcula el valor total de un conjunto de denominaciones.

    Args:
        counts: {denominación: cantidad} e.g. {50: 2, 20: 3} = 160€
    """
    return sum(denom * qty for denom, qty in counts.items())


def calc_breakdown(counts: dict[float, int]) -> dict[float, float]:
    """Calcula el subtotal por denominación.

    Returns:
        {denominación: subtotal_euros}
    """
    return {denom: denom * qty for denom, qty in counts.items()}


def is_bill(denomination: float) -> bool:
    """True si la denominación es un billete."""
    return denomination in DENOMINATIONS_BILLS


def format_denomination(d: float) -> str:
    """Formatea una denominación para mostrar: 100€, 0.50€, etc."""
    if d >= 1 and d == int(d):
        return f"{int(d)}€"
    return f"{d:.2f}€"
