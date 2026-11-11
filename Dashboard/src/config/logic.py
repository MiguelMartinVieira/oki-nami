"""
logic.py — Constantes de negocio, tickers y configuraciones de servicios.
"""

import os
from pathlib import Path

# Cargar .env explícitamente ANTES de leer cualquier os.environ.get(...).
# constants.py importa logic ANTES que paths (que también carga el .env), así
# que sin esto variables como GEMINI_API_KEY se leerían con el .env aún sin
# cargar → None. override=False respeta variables ya presentes en el entorno.
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parents[3] / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except ImportError:
    pass

# ──────────────────────────────────────────────
# Yahoo Finance — Tickers
# ──────────────────────────────────────────────
TICKER_VANGUARD = "0P00012SJB.F"
TICKER_BRK = "BRK-B"
TICKER_EURUSD = "EUR=X"
TICKER_VWRL_PROXY = "VWRL.AS"

# ──────────────────────────────────────────────
# Posiciones de inversión
# ──────────────────────────────────────────────
# Las posiciones reales van en el .env; los valores por defecto son de ejemplo.
# En DEMO_MODE se ignora el .env para no mezclar posiciones reales con datos sintéticos.
_DEMO = os.environ.get("DEMO_MODE", "").strip().lower() in ("true", "1", "yes", "on")


def _position(name: str, default: str) -> str:
    return default if _DEMO else os.environ.get(name, default)


PARTICIPACIONES_VANGUARD = float(_position("PARTICIPACIONES_VANGUARD", "6.5"))
BASE_ACCIONES_BRK = float(_position("BASE_ACCIONES_BRK", "0.0"))
BRK_CHECKPOINT_DATE = _position("BRK_CHECKPOINT_DATE", "2026-03-23")
# Plusvalía acumulada antes del checkpoint (se descuenta del coste de Vanguard).
VANGUARD_HISTORICAL_GAIN = float(_position("VANGUARD_HISTORICAL_GAIN", "0.0"))

# ──────────────────────────────────────────────
# Cuentas fijas (Grupo 1-3)
# ──────────────────────────────────────────────
CUENTA_CARTERA = "111"
CUENTA_HUCHA = "112"
CUENTA_TR = "121"
CUENTA_BOKATAS = "133"
CUENTA_PADRES = "131"
CUENTA_DEUDAS_PUNTUALES = "132"
CUENTA_DEUDAS_OTRAS = "134"
CUENTA_BERKSHIRE = "141"
CUENTA_SP500 = "142"
CUENTA_CAPITAL_INICIAL = "31"

PREFIX_INGRESOS = "4"
PREFIX_GASTOS = "5"

# Denominaciones Euro (rastreador de efectivo)
DENOMINATIONS_BILLS = [100, 50, 20, 10, 5]
DENOMINATIONS_COINS = [2, 1, 0.50, 0.20, 0.10, 0.05, 0.02, 0.01]
ALL_DENOMINATIONS = DENOMINATIONS_BILLS + DENOMINATIONS_COINS

# ──────────────────────────────────────────────
# Umbrales y Tiempos
# ──────────────────────────────────────────────
HISTORY_START_DATE = "2026-03-19"
TTL_SHEETS = 600  # 10 min — usar el botón "Forzar Recarga" del sidebar para refrescar manualmente
TTL_YAHOO = 3600
META_AHORRO_ANUAL = 12000.0

# ──────────────────────────────────────────────
# Formato de fecha (visualización)
# ──────────────────────────────────────────────
# Formato universal para mostrar fechas en TODO el dashboard (tablas, reports,
# paneles). Cambiar aquí propaga a toda la app. NO afecta a las fechas que se
# escriben en Google Sheets / JSON (esas se mantienen en ISO para no romper el
# parseo y el matching).
DATE_FORMAT = "%Y/%m/%d"

# ──────────────────────────────────────────────
# Google Sheets — Nombres de Hojas
# ──────────────────────────────────────────────
SHEET_DIARIO = "Diario Limpio"
SHEET_DIARIO_CRUDO = "Diario Crudo"
SHEET_SALDOS = "Saldos Cuentas"
SHEET_HISTORICO = "Historico"
SHEET_CENTRO_CONTROL = "Centro Control"
SHEET_DENOMINACIONES = "Denominaciones"

# ──────────────────────────────────────────────
# Gemini AI
# ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-flash-latest"

# Cadena de modelos de VISIÓN para extraer datos de tickets. Se prueban en
# orden: si uno está saturado (503) o sin cuota (429), se pasa al siguiente.
# El alias "-latest" puede saturarse; por eso el primario es una versión fija
# (la más precisa) y dejamos alternativas con pools de capacidad distintos.
GEMINI_VISION_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

# ──────────────────────────────────────────────
# Meses en Español
# ──────────────────────────────────────────────
MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}
