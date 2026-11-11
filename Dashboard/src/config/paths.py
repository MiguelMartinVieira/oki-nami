"""
paths.py — Configuración de rutas y IDs de recursos externos.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# Rutas Base
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # Dashboard/src/
PROJECT_ROOT = BASE_DIR.parent.parent  # Oki-Nami/ (raíz del repo)
FINANZAS_ROOT = PROJECT_ROOT.parent  # Finanzas/ (carpeta padre, contiene PDFs_TR y Padres)
BACKUP_DIR = BASE_DIR / "data" / "backups"
CACHE_DIR = PROJECT_ROOT / ".cache"

# Asegurar que las carpetas de persistencia existen
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# Cargar .env explícitamente para que las variables estén disponibles
# antes de leer cualquier os.environ.get(...) en este módulo
# ──────────────────────────────────────────────
try:
    from dotenv import load_dotenv

    _env_path = PROJECT_ROOT / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
except ImportError:
    pass

# ──────────────────────────────────────────────
# Ficheros de Datos y Configuración
# ──────────────────────────────────────────────
CREDENTIALS_FILE = os.environ.get(
    "GSHEETS_CREDENTIALS_FILE",
    str(BASE_DIR / "config" / "credentials.json"),
)

# Fallbacks CSV (ahora en la carpeta de backups)
CSV_DIARIO = str(BACKUP_DIR / "Cuentas Miguel 2.0 - Diario.csv")
CSV_DIARIO_CRUDO = str(BACKUP_DIR / "Cuentas Miguel 2.0 - Diario Crudo.csv")
CSV_SALDOS = str(BACKUP_DIR / "Cuentas Miguel 2.0 - Saldos Cuentas.csv")
CSV_HISTORICO = str(BACKUP_DIR / "Cuentas Miguel 2.0 - Historico.csv")

# URL pública (CSV publicado en la web) del Diario Crudo, como fallback HTTP.
# Opcional: déjalo vacío si no publicas la hoja.
CSV_URL_DIARIO_CRUDO = os.environ.get("CSV_URL_DIARIO_CRUDO", "")

# Logs y Metadatos
PROCESSED_LOG_FILE = str(BACKUP_DIR / "_processed_log.json")
LIQUIDATED_PADRES_FILE = str(BACKUP_DIR / "_padres_liquidated.json")

# ──────────────────────────────────────────────
# Carpetas Externas
# ──────────────────────────────────────────────
_default_padres = str(FINANZAS_ROOT / "Padres")
_env_padres = os.environ.get("PADRES_FOLDER", "").split(";")
POSSIBLE_PADRES_FOLDERS = [p for p in _env_padres if p] + [_default_padres]

PADRES_FOLDER = next(
    (p for p in POSSIBLE_PADRES_FOLDERS if os.path.isdir(p)),
    POSSIBLE_PADRES_FOLDERS[0],
)

# ──────────────────────────────────────────────
# Google Resources (IDs)
# ──────────────────────────────────────────────
# Todos los recursos de Google se configuran por entorno (ver `.env.example`).
# Sin ellos la app funciona igual con el CSV local o con `DEMO_MODE=true`.

# Carpeta de Drive con los tickets de Padres y el Google Doc "Sin Ticket".
PADRES_DRIVE_FOLDER_ID = os.environ.get("PADRES_DRIVE_FOLDER_ID", "")

# ID del Google Doc "Sin Ticket". Si se deja vacío, se autodescubre el primer
# Google Doc dentro de PADRES_DRIVE_FOLDER_ID (robusto si se recrea el doc).
PADRES_DOC_ID = os.environ.get("PADRES_DOC_ID", "")

BOKATAS_DRIVE_FOLDER_ID = os.environ.get("BOKATAS_DRIVE_FOLDER_ID", "")

SHEET_URL = os.environ.get("GSHEETS_URL", "")

BOKATAS_VERSION_SHEET_URL = os.environ.get("BOKATAS_VERSION_SHEET_URL", "")

URL_CENTRO_CONTROL = os.environ.get("URL_CENTRO_CONTROL", "")

# Google Doc con las citas que se muestran en la cabecera (opcional).
QUOTES_DOC_ID = os.environ.get("QUOTES_DOC_ID", "")


def drive_folder_url(folder_id: str) -> str:
    """URL de una carpeta de Drive, o cadena vacía si no está configurada."""
    return f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else ""
