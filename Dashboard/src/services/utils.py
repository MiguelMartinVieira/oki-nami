"""
utils.py — Utilidades compartidas para el procesamiento de datos.
"""

import logging
import re

log = logging.getLogger(__name__)


def extract_quantity(description: str) -> float:
    """
    Extrae la cantidad (quantity) del campo Descripción usando regex.
    Soporta formatos como 'quantity: 0.123456', 'quantity: -1.5' o 'quantity: 1,23'.
    """
    if not description or not isinstance(description, str):
        return 0.0

    # Regex mejorada para capturar decimales con punto o coma, opcionalmente con signo
    match = re.search(r"quantity[:\s]+([-+]?[0-9.,]+)", description, re.IGNORECASE)
    if match:
        try:
            # Normalizar coma a punto
            val_str = match.group(1).replace(",", ".")
            return float(val_str)
        except ValueError:
            log.warning("No se pudo convertir cantidad a float: %s", match.group(1))

    return 0.0


def extract_signed_quantity(row) -> float:
    """
    Extrae la cantidad de acciones/participaciones firmada de una fila del diario contable.
    Si la fila corresponde a una venta o desinversión (Haber > Debe o categoría/concepto que indica venta),
    la cantidad se devuelve negativa (-qty). Si es una compra/inversión, positiva (+qty).
    """
    if row is None:
        return 0.0

    desc = str(row.get("Descripción", "") if hasattr(row, "get") else "")
    qty = extract_quantity(desc)
    if qty == 0.0:
        return 0.0

    haber = 0.0
    debe = 0.0
    if hasattr(row, "get"):
        try:
            h_val = row.get("Haber", 0.0)
            haber = float(h_val) if (h_val is not None and h_val == h_val) else 0.0
        except (ValueError, TypeError):
            haber = 0.0

        try:
            d_val = row.get("Debe", 0.0)
            debe = float(d_val) if (d_val is not None and d_val == d_val) else 0.0
        except (ValueError, TypeError):
            debe = 0.0

    text_fields = " ".join(
        [
            str(row.get("Categoría", "") if hasattr(row, "get") else ""),
            str(row.get("Subcategoría", "") if hasattr(row, "get") else ""),
            str(row.get("Concepto", "") if hasattr(row, "get") else ""),
            desc,
        ]
    ).lower()

    keywords = ["venta", "reembolso", "sell"]
    is_sale = (haber > debe) or any(k in text_fields for k in keywords)

    return -abs(qty) if (is_sale or qty < 0) else abs(qty)


def clean_cat_name(name) -> str:
    """Sanitiza nombres de categoría provenientes de GSheets/DataFrames (elimina 0, #N/A, nan...)."""
    if name is None:
        return "Sin Categorizar"
    name_str = str(name).strip()
    if not name_str or name_str in (
        "0",
        "0.0",
        "0.00",
        "0,0",
        "0,00",
        "nan",
        "None",
        "null",
        "#N/A",
        "N/A",
    ):
        return "Sin Categorizar"
    if name_str.startswith("#N/A") or "VLOOKUP" in name_str or "ERROR" in name_str.upper():
        m = re.search(r"'(\d+)'", name_str)
        if m:
            return f"Cuenta {m.group(1)}"
        return "Sin Categorizar"
    return name_str
