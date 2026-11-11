"""
gsheets.py — Capa de datos: Google Sheets con fallback a CSV local.

Funciones:
  - get_diario()       → pd.DataFrame del Libro Diario
  - get_saldos()       → pd.DataFrame de Saldos de Cuentas
  - get_historico()    → pd.DataFrame de Histórico de Saldos
  - append_to_diario() → Inserta filas (partida doble) en el Diario
  - append_to_historico() → Inserta filas en el Historial

Cache en disco:
  Cada función guarda el DataFrame procesado en un parquet local
  (`BACKUP_DIR/_cache_<name>.parquet`). En el siguiente arranque, si
  el parquet es más reciente que TTL_SHEETS, se devuelve directamente
  sin tocar Google Sheets (cold start ≈ instant).
"""

import logging
import os
import time

import pandas as pd
import streamlit as st
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from constants import (
    ALL_DENOMINATIONS,
    BACKUP_DIR,
    CREDENTIALS_FILE,
    CSV_DIARIO,
    CSV_DIARIO_CRUDO,
    CSV_HISTORICO,
    CSV_SALDOS,
    CSV_URL_DIARIO_CRUDO,
    SHEET_DENOMINACIONES,
    SHEET_DIARIO,
    SHEET_DIARIO_CRUDO,
    SHEET_HISTORICO,
    SHEET_SALDOS,
    SHEET_URL,
    TTL_SHEETS,
)

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Cache en disco (parquet) — acelera el cold start
# ──────────────────────────────────────────────
_PARQUET_DIARIO = os.path.join(str(BACKUP_DIR), "_cache_diario.parquet")
_PARQUET_DIARIO_CRUDO = os.path.join(str(BACKUP_DIR), "_cache_diario_crudo.parquet")
_PARQUET_SALDOS = os.path.join(str(BACKUP_DIR), "_cache_saldos.parquet")
_PARQUET_HISTORICO = os.path.join(str(BACKUP_DIR), "_cache_historico.parquet")
_PARQUET_DENOM = os.path.join(str(BACKUP_DIR), "_cache_denominaciones.parquet")


def _load_parquet_if_fresh(path: str, ttl_seconds: int) -> pd.DataFrame | None:
    """Devuelve el DataFrame del parquet si existe y es más reciente que TTL.
    En caso contrario, devuelve None."""
    if not os.path.exists(path):
        return None
    try:
        age = time.time() - os.path.getmtime(path)
        if age >= ttl_seconds:
            return None
        df = pd.read_parquet(path)
        if df.empty:
            return None
        return df
    except Exception as e:
        log.debug("No se pudo leer parquet %s: %s", path, e)
        return None


def _save_parquet(df: pd.DataFrame, path: str) -> None:
    """Guarda el DataFrame en parquet silenciosamente."""
    if df is None or df.empty:
        return
    try:
        df.to_parquet(path, compression="snappy", index=False)
    except Exception as e:
        log.debug("No se pudo escribir parquet %s: %s", path, e)


def _invalidate_parquet(path: str) -> None:
    """Borra un parquet cache para forzar releer de Sheets en la próxima llamada."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        log.debug("No se pudo borrar parquet %s: %s", path, e)


def invalidate_all_parquet_caches() -> None:
    """Borra todos los parquet caches (usar desde el botón 'Forzar Recarga')."""
    for p in (
        _PARQUET_DIARIO,
        _PARQUET_DIARIO_CRUDO,
        _PARQUET_SALDOS,
        _PARQUET_HISTORICO,
        _PARQUET_DENOM,
    ):
        _invalidate_parquet(p)


GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Intentar importar gspread (puede no estar instalado)
try:
    import gspread
    from google.oauth2.service_account import Credentials

    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False


# ──────────────────────────────────────────────
# Limpieza numérica
# ──────────────────────────────────────────────


def _clean_numeric(val) -> float:
    """
    Convierte un valor de Google Sheets a float.

    Reglas:
      - Valores numéricos (int, float) se retornan directamente como float sin alteración.
      - Coma europea (,) se convierte a punto (.)
      - Punto miles se elimina si hay coma (7.856,69 → 7856.69)
      - Contabilidad: (valor) se asume como valor negativo
      - Div 100: Si no tiene divisas, comas ni puntos y length >= 3, se divide (ej: 97064 → 970.64)
    """
    if pd.isna(val) or val == "":
        return 0.0

    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)

    original_str = str(val).strip()
    clean_val = original_str.replace("€", "").replace("$", "").replace("EUR", "").replace(" ", "")

    # "-" solo → 0
    if clean_val in ("-", ""):
        return 0.0

    is_negative = False
    if clean_val.startswith("(") and clean_val.endswith(")"):
        clean_val = clean_val[1:-1]
        is_negative = True
    elif clean_val.startswith("-"):
        clean_val = clean_val[1:]
        is_negative = True

    # Convertir formato europeo (coma decimal) a formato estándar (punto decimal)
    if "," in clean_val:
        if "." in clean_val:
            # Formato 7.856,69 → 7856.69 (elimina punto de miles)
            clean_val = clean_val.replace(".", "").replace(",", ".")
        else:
            # Formato 9,38 → 9.38 (simple conversión)
            clean_val = clean_val.replace(",", ".")

    try:
        num = float(clean_val)

        has_currency = any(s in original_str for s in ("€", "$", "EUR"))
        if not has_currency and "." not in original_str and "," not in original_str:
            digits_orig = "".join(c for c in original_str if c.isdigit())
            if len(digits_orig) >= 3:
                num = num / 100.0

        if is_negative:
            num = -num

        return num
    except ValueError:
        log.warning("_clean_numeric: no se pudo convertir %r", val)
        return 0.0


# ──────────────────────────────────────────────
# Helpers de conexión
# ──────────────────────────────────────────────


@st.cache_resource
def _get_gspread_client():
    """Crea y devuelve un cliente gspread autenticado (cacheado por sesión)."""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=GSHEETS_SCOPES)
    return gspread.authorize(creds)


# ──────────────────────────────────────────────
# Retry helpers (errores transitorios de la API de GSheets)
# ──────────────────────────────────────────────


def _is_transient_gspread_error(exc: BaseException) -> bool:
    """Reintenta sólo errores transitorios (red, 5xx, rate limit)."""
    try:
        from gspread.exceptions import APIError
    except Exception:
        APIError = ()  # type: ignore

    if isinstance(exc, APIError):
        # Errores de servidor (5xx) o rate-limit (429) son retriables.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status and (status >= 500 or status == 429):
            return True
        return False
    # Errores de red genéricos
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


_retry_gspread = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    reraise=True,
)


def _can_use_gsheets() -> bool:
    """Comprueba si GSheets está disponible y configurado."""
    return GSHEETS_AVAILABLE and os.path.exists(CREDENTIALS_FILE) and bool(SHEET_URL)


# ──────────────────────────────────────────────
# Sync bidireccional — modifiedTime polling
# ──────────────────────────────────────────────


@st.cache_data(ttl=30, show_spinner=False)
def get_sheet_modified_time() -> str | None:
    """Devuelve el `modifiedTime` ISO 8601 del Spreadsheet (cacheado 30 s).

    Usa `gspread.Spreadsheet.lastUpdateTime`, que es una llamada barata a Drive
    metadata (≈50 ms). Cachear 30 s evita golpear la API en cada rerun de
    Streamlit y mantiene granularidad suficiente para "edits en vivo".
    """
    if not _can_use_gsheets():
        return None
    try:
        client = _get_gspread_client()
        sheet = client.open_by_url(SHEET_URL)
        # gspread ≥ 6 expone get_lastUpdateTime(); el atributo .lastUpdateTime
        # sigue funcionando pero está deprecated.
        getter = getattr(sheet, "get_lastUpdateTime", None)
        return getter() if callable(getter) else sheet.lastUpdateTime
    except Exception as e:
        log.debug("get_sheet_modified_time falló: %s", e)
        return None


def invalidate_data_caches() -> None:
    """Limpia los caches de get_diario / get_diario_crudo / get_saldos / get_historico / get_denominaciones y elimina los parquets en disco."""
    try:
        get_diario.clear()
        get_diario_crudo.clear()
        get_saldos.clear()
        get_historico.clear()
        get_denominaciones.clear()
        invalidate_all_parquet_caches()
    except Exception as e:
        log.debug("invalidate_data_caches: %s", e)


def check_and_refresh_if_remote_changed(session_state_obj) -> bool:
    """Si el Spreadsheet ha sido modificado desde fuera, invalida los caches.

    Compara el `modifiedTime` actual contra el último visto en
    `session_state.sheet_modified_time`. Si difiere, llama a
    `invalidate_data_caches()` y actualiza el sentinel.

    Returns True si hubo cambio detectado (caches invalidados), False en otro caso.
    """
    current = get_sheet_modified_time()
    if current is None:
        return False
    last_seen = getattr(session_state_obj, "sheet_modified_time", None)
    if last_seen is None:
        # Primera vez en esta sesión: registramos sin invalidar
        session_state_obj.sheet_modified_time = current
        return False
    if current != last_seen:
        invalidate_data_caches()
        session_state_obj.sheet_modified_time = current
        log.info("GSheets remote-edit detectado (%s → %s); caches invalidados.", last_seen, current)
        return True
    return False


# ──────────────────────────────────────────────
# Limpieza de columna Nº Cuenta (reutilizable)
# ──────────────────────────────────────────────


def clean_cuenta_col(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia y normaliza la columna 'Nº Cuenta' a string sin espacios."""
    if "Nº Cuenta" in df.columns:
        df["Nº Cuenta"] = df["Nº Cuenta"].astype(str).str.strip()
    return df


# ──────────────────────────────────────────────
# Lectura de datos
# ──────────────────────────────────────────────


@st.cache_data(ttl=TTL_SHEETS)
def get_diario() -> pd.DataFrame:
    """Lee el Libro Diario de Google Sheets o CSV local.

    En modo `DEMO_MODE` devuelve un Libro sintético determinista en lugar
    de tocar GSheets o el CSV (cf. `services/demo_data.generate_demo_diario`).
    """
    # ── DEMO MODE: datos sintéticos, sin tocar GSheets ni CSV ──
    try:
        from services.demo_data import generate_demo_diario, is_demo_mode

        if is_demo_mode():
            return generate_demo_diario()
    except Exception as _e:
        log.debug("demo_mode bypass falló (diario): %s", _e)

    # ── Cache en disco (parquet) — cold start instantáneo ──
    cached = _load_parquet_if_fresh(_PARQUET_DIARIO, TTL_SHEETS)
    if cached is not None:
        log.info("Diario servido desde parquet cache (%d filas)", len(cached))
        return cached

    df = pd.DataFrame()
    use_csv = True

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            sp = client.open_by_url(SHEET_URL)
            sheet = None
            for candidate in [SHEET_DIARIO, "Diario Limpio", "Diario", "Diario Crudo"]:
                try:
                    sheet = sp.worksheet(candidate)
                    break
                except Exception:
                    pass
            if sheet is None:
                raise ValueError(
                    f"No se encontró ninguna pestaña del Diario (probadas: {SHEET_DIARIO}, Diario Limpio, Diario, Diario Crudo)"
                )
            # UNFORMATTED_VALUE devuelve números como floats reales, evitando
            # que gspread malinterprete el formato europeo (9,38 → 938)
            raw = _retry_gspread(sheet.get)("A1:Z10000", value_render_option="UNFORMATTED_VALUE")
            if raw and len(raw) > 1:
                # Columnas útiles del Diario (ignorar columnas extra de comprobación)
                useful_cols = [
                    "Fecha",
                    "Nº Cuenta",
                    "Cuenta",
                    "Categoría",
                    "Debe",
                    "Haber",
                    "Descripción",
                ]
                n_cols = len(useful_cols)
                # Pad/truncate cada fila a n_cols columnas
                rows = [row[:n_cols] + [""] * (n_cols - len(row)) for row in raw[1:]]
                df = pd.DataFrame(rows, columns=useful_cols)

                # El espejo CSV se sincronizará tras limpiar y normalizar los datos
            use_csv = False
        except Exception as e:
            log.warning("Error conectando con Google Sheets (Diario): %s", e)
            st.warning(f"⚠️ Error conectando con Google Sheets: {e}. Usando CSV local.")

    if use_csv and os.path.exists(CSV_DIARIO):
        df = pd.read_csv(CSV_DIARIO, dtype=str)

    if not df.empty:
        df.columns = [c.strip() for c in df.columns]
        # Con UNFORMATTED_VALUE los números ya vienen como floats correctos
        if "Debe" in df.columns:
            df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0)
        if "Haber" in df.columns:
            df["Haber"] = pd.to_numeric(df["Haber"], errors="coerce").fillna(0)
        if "Fecha" in df.columns:

            def parse_fecha(v):
                if pd.isna(v) or v == "":
                    return pd.NaT
                s = str(v).strip()
                if "-" in s or "/" in s:
                    return pd.to_datetime(s, errors="coerce")
                try:
                    n = float(s)
                    if 30000 <= n <= 60000:
                        return pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
                    return pd.to_datetime(s, errors="coerce")
                except (ValueError, TypeError):
                    return pd.to_datetime(s, errors="coerce")

            df["Fecha"] = df["Fecha"].apply(parse_fecha)

        # Sincronizar espejo CSV con datos procesados y limpios
        try:
            df.to_csv(CSV_DIARIO, index=False, encoding="utf-8")
        except Exception as e_csv:
            log.warning("No se pudo sobrescribir CSV de fallback (Diario): %s", e_csv)

    # Persistir cache parquet para acelerar el próximo cold start
    _save_parquet(df, _PARQUET_DIARIO)

    return df


@st.cache_data(ttl=TTL_SHEETS)
def get_diario_crudo() -> pd.DataFrame:
    """Lee el Diario Crudo de Google Sheets, CSV local, o CSV público.

    El Diario Crudo contiene los datos brutos tal como ocurrieron en Trade
    Republic.  Se usa exclusivamente para la reconciliación PDF ↔ Diario.

    Cascade de lectura:
      1. Parquet cache en disco (_cache_diario_crudo.parquet)
      2. Google Sheets API (hoja ``SHEET_DIARIO_CRUDO``)
      3. CSV local (CSV_DIARIO_CRUDO)
      4. CSV público via HTTP (CSV_URL_DIARIO_CRUDO)
    """
    # ── Cache en disco (parquet) — cold start instantáneo ──
    cached = _load_parquet_if_fresh(_PARQUET_DIARIO_CRUDO, TTL_SHEETS)
    if cached is not None:
        log.info("Diario Crudo servido desde parquet cache (%d filas)", len(cached))
        return cached

    df = pd.DataFrame()
    use_csv = True

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            sp = client.open_by_url(SHEET_URL)
            sheet = None
            for candidate in [SHEET_DIARIO_CRUDO, "Diario Crudo"]:
                try:
                    sheet = sp.worksheet(candidate)
                    break
                except Exception:
                    pass
            if sheet is None:
                raise ValueError(
                    f"No se encontró la pestaña del Diario Crudo "
                    f"(probadas: {SHEET_DIARIO_CRUDO}, Diario Crudo)"
                )
            raw = _retry_gspread(sheet.get)("A1:Z10000", value_render_option="UNFORMATTED_VALUE")
            if raw and len(raw) > 1:
                useful_cols = [
                    "Fecha",
                    "Nº Cuenta",
                    "Cuenta",
                    "Categoría",
                    "Debe",
                    "Haber",
                    "Descripción",
                ]
                n_cols = len(useful_cols)
                rows = [row[:n_cols] + [""] * (n_cols - len(row)) for row in raw[1:]]
                df = pd.DataFrame(rows, columns=useful_cols)
            use_csv = False
        except Exception as e:
            log.warning("Error conectando con Google Sheets (Diario Crudo): %s", e)
            try:
                st.warning(f"⚠️ Error conectando con Google Sheets (Crudo): {e}. Usando CSV local.")
            except Exception:
                pass  # Sin runtime Streamlit (CLI)

    # Fallback 1: CSV local
    if use_csv and os.path.exists(CSV_DIARIO_CRUDO):
        df = pd.read_csv(CSV_DIARIO_CRUDO, dtype=str)

    # Fallback 2: CSV público vía HTTP
    if df.empty and CSV_URL_DIARIO_CRUDO:
        try:
            df = pd.read_csv(CSV_URL_DIARIO_CRUDO, dtype=str)
            log.info("Diario Crudo descargado desde CSV público (%d filas)", len(df))
        except Exception as e_http:
            log.warning("No se pudo descargar Diario Crudo vía HTTP: %s", e_http)

    if not df.empty:
        df.columns = [c.strip() for c in df.columns]
        if "Debe" in df.columns:
            df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0)
        if "Haber" in df.columns:
            df["Haber"] = pd.to_numeric(df["Haber"], errors="coerce").fillna(0)
        if "Fecha" in df.columns:

            def parse_fecha(v):
                if pd.isna(v) or v == "":
                    return pd.NaT
                s = str(v).strip()
                if "-" in s or "/" in s:
                    return pd.to_datetime(s, errors="coerce")
                try:
                    n = float(s)
                    if 30000 <= n <= 60000:
                        return pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
                    return pd.to_datetime(s, errors="coerce")
                except (ValueError, TypeError):
                    return pd.to_datetime(s, errors="coerce")

            df["Fecha"] = df["Fecha"].apply(parse_fecha)

        # Sincronizar espejo CSV con datos procesados
        try:
            df.to_csv(CSV_DIARIO_CRUDO, index=False, encoding="utf-8")
        except Exception as e_csv:
            log.warning("No se pudo sobrescribir CSV de fallback (Diario Crudo): %s", e_csv)

    # Persistir cache parquet
    _save_parquet(df, _PARQUET_DIARIO_CRUDO)

    return df


@st.cache_data(ttl=TTL_SHEETS)
def get_saldos() -> pd.DataFrame:
    """Lee los Saldos de Cuentas de Google Sheets o CSV local.

    En modo `DEMO_MODE` devuelve saldos sintéticos coherentes con el
    Libro Diario demo.
    """
    try:
        from services.demo_data import generate_demo_saldos, is_demo_mode

        if is_demo_mode():
            return generate_demo_saldos()
    except Exception as _e:
        log.debug("demo_mode bypass falló (saldos): %s", _e)

    # ── Cache en disco (parquet) — cold start instantáneo ──
    cached = _load_parquet_if_fresh(_PARQUET_SALDOS, TTL_SHEETS)
    if cached is not None:
        log.info("Saldos servidos desde parquet cache (%d filas)", len(cached))
        return cached

    df = pd.DataFrame()
    use_csv = True

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_SALDOS)
            # get_all_values() evita el error de cabeceras duplicadas/vacías
            raw = _retry_gspread(sheet.get_all_values)()
            if raw and len(raw) > 1:
                headers = raw[0]
                # Deduplicar cabeceras vacías añadiendo sufijo numérico
                seen: dict[str, int] = {}
                clean_headers = []
                for h in headers:
                    h = h.strip()
                    if h == "" or h in seen:
                        seen[h] = seen.get(h, 0) + 1
                        h = f"_col_{seen[h]}" if h == "" else f"{h}_{seen[h]}"
                    else:
                        seen[h] = 0
                    clean_headers.append(h)
                df = pd.DataFrame(raw[1:], columns=clean_headers)

                # Sincronizar espejo CSV
                try:
                    df.to_csv(CSV_SALDOS, index=False, encoding="utf-8")
                except Exception as e_csv:
                    log.warning("No se pudo sobrescribir CSV de fallaback (Saldos): %s", e_csv)
            use_csv = False
        except Exception as e:
            log.warning("Error conectando con Google Sheets (Saldos): %s", e)

    if use_csv and os.path.exists(CSV_SALDOS):
        df = pd.read_csv(CSV_SALDOS, dtype=str)

    if not df.empty:
        df.columns = [c.strip() for c in df.columns]
        numeric_cols = [
            "SUMAS DEBE",
            "SUMAS HABER",
            "SALDO DEUDOR",
            "SALDO ACREEDOR",
            "Saldo para resumen",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(_clean_numeric)

    # Persistir cache parquet para acelerar el próximo cold start
    _save_parquet(df, _PARQUET_SALDOS)

    return df


@st.cache_data(ttl=TTL_SHEETS)
def get_centro_control_data() -> dict[str, float]:
    """Lee datos específicos de la hoja Centro Control para las métricas."""
    data = {"H4": 0.0, "L2": 0.0, "F7": 0.0, "J7": 0.0}
    from constants import URL_CENTRO_CONTROL

    if _can_use_gsheets() and URL_CENTRO_CONTROL:
        try:
            from constants import SHEET_CENTRO_CONTROL

            client = _get_gspread_client()
            sheet = client.open_by_url(URL_CENTRO_CONTROL).worksheet(SHEET_CENTRO_CONTROL)
            raw = _retry_gspread(sheet.get)("A1:Z50", value_render_option="UNFORMATTED_VALUE")
            if raw:

                def get_val(r: int, c: int) -> float:
                    try:
                        return _clean_numeric(raw[r][c])
                    except IndexError:
                        return 0.0

                data["H4"] = get_val(3, 7)  # Row 4, Col H (Total Por Cobrar)
                val_l2 = get_val(1, 11)  # Row 2, Col L (Deducción configurada o vacía)
                val_l6 = get_val(5, 11)  # Row 6, Col L (Bizum David)
                val_l7 = get_val(6, 11)  # Row 7, Col L (Efectivo David)
                # Si L2 está vacía, deduce automáticamente la parte de David (L6 + L7)
                data["L2"] = val_l2 if val_l2 != 0.0 else (val_l6 + val_l7)
                data["F7"] = get_val(6, 5)  # Row 7, Col F (Bizum Mike: Debe / Se debe)
                data["J7"] = get_val(6, 9)  # Row 7, Col J (Efectivo Miguel cobrado)
        except Exception as e:
            log.warning("Error conectando con Google Sheets (Centro Control): %s", e)
    return data


@st.cache_data(ttl=TTL_SHEETS)
def get_historico() -> pd.DataFrame:
    """
    Lee el Historial de Saldos de Google Sheets o CSV local.

    IMPORTANTE: usa UNFORMATTED_VALUE para evitar que Google Sheets devuelva
    números con formato europeo (9,38) que gspread convertiría erróneamente a 938.
    """
    # ── DEMO MODE: histórico reconstruido desde el Diario demo ──
    try:
        from services.demo_data import generate_demo_historico, is_demo_mode

        if is_demo_mode():
            return generate_demo_historico()
    except Exception as _e:
        log.debug("demo_mode bypass falló (histórico): %s", _e)

    # ── Cache en disco (parquet) — cold start instantáneo ──
    cached = _load_parquet_if_fresh(_PARQUET_HISTORICO, TTL_SHEETS)
    if cached is not None:
        log.info("Histórico servido desde parquet cache (%d filas)", len(cached))
        return cached

    df = pd.DataFrame()
    use_csv = True

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_HISTORICO)
            # UNFORMATTED_VALUE devuelve los valores numéricos sin formato de locale
            raw = _retry_gspread(sheet.get)("A1:Z10000", value_render_option="UNFORMATTED_VALUE")
            if raw and len(raw) > 1:
                headers = raw[0]
                rows = raw[1:]
                df = pd.DataFrame(rows, columns=headers)

                # Sincronizar espejo CSV
                try:
                    df.to_csv(CSV_HISTORICO, index=False, encoding="utf-8")
                except Exception as e_csv:
                    log.warning(
                        "No se pudo sobrescribir CSV de fallaback (Historico): %s",
                        e_csv,
                    )
            use_csv = False
        except Exception as e:
            log.warning("Error conectando con Google Sheets (Historico): %s", e)

    if use_csv and os.path.exists(CSV_HISTORICO):
        df = pd.read_csv(CSV_HISTORICO)

    if not df.empty and "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        # Convertir columnas numéricas a float
        numeric_cols = [
            "Efectivo Fisico",
            "Efectivo TR",
            "BRK Value",
            "Vanguard Value",
            "Total",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    # Persistir cache parquet para acelerar el próximo cold start
    _save_parquet(df, _PARQUET_HISTORICO)

    return df


# ──────────────────────────────────────────────
# Denominaciones (rastreador de efectivo)
# ──────────────────────────────────────────────


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def get_denominaciones() -> dict:
    """Lee el desglose de denominaciones de la hoja 'Denominaciones'.

    Returns:
        {"cartera": {100: 0, 50: 2, ...}, "hucha": {...}, "last_updated": "..."}
        Si la hoja no existe, devuelve un template vacío.
    """
    from services.cash_tracker import get_empty_template

    # Cache parquet
    cached = _load_parquet_if_fresh(_PARQUET_DENOM, TTL_SHEETS)
    if cached is not None and not cached.empty:
        return _df_to_denom_dict(cached)

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            spreadsheet = client.open_by_url(SHEET_URL)
            try:
                sheet = spreadsheet.worksheet(SHEET_DENOMINACIONES)
            except Exception:
                # La hoja no existe todavía → crearla con valores por defecto
                log.info("Hoja '%s' no encontrada, creando...", SHEET_DENOMINACIONES)
                sheet = spreadsheet.add_worksheet(title=SHEET_DENOMINACIONES, rows=20, cols=5)
                # Escribir cabeceras + filas por defecto
                header = ["Denominación", "Cartera", "Hucha"]
                rows = [[_denom_to_sheet(d), 0, 0] for d in ALL_DENOMINATIONS]
                sheet.update(
                    values=[header] + rows,
                    range_name=f"A1:C{len(rows) + 1}",
                )
                # Guardar timestamp
                sheet.update(
                    values=[["Última Actualización", ""]],
                    range_name="E1:F1",
                )

            raw = _retry_gspread(sheet.get)("A1:F50", value_render_option="UNFORMATTED_VALUE")
            if raw and len(raw) > 1:
                df = _parse_denom_raw(raw)
                _save_parquet(df, _PARQUET_DENOM)
                return _df_to_denom_dict(df)
        except Exception as e:
            log.warning("Error leyendo denominaciones de GSheets: %s", e)

    return get_empty_template()


def save_denominaciones(
    cartera: dict[float, int],
    hucha: dict[float, int],
    timestamp: str = "",
) -> bool:
    """Escribe el desglose de denominaciones en la hoja 'Denominaciones'."""
    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            spreadsheet = client.open_by_url(SHEET_URL)
            try:
                sheet = spreadsheet.worksheet(SHEET_DENOMINACIONES)
            except Exception:
                sheet = spreadsheet.add_worksheet(title=SHEET_DENOMINACIONES, rows=20, cols=5)

            header = ["Denominación", "Cartera", "Hucha"]
            rows = []
            for d in ALL_DENOMINATIONS:
                rows.append(
                    [
                        _denom_to_sheet(d),
                        int(cartera.get(d, 0)),
                        int(hucha.get(d, 0)),
                    ]
                )

            # Actualizar datos + timestamp
            sheet.update(
                values=[header] + rows,
                range_name=f"A1:C{len(rows) + 1}",
            )
            if timestamp:
                sheet.update(
                    values=[["Última Actualización", timestamp]],
                    range_name="E1:F1",
                )

            # Invalidar caches
            get_denominaciones.clear()
            _invalidate_parquet(_PARQUET_DENOM)
            return True
        except Exception as e:
            log.error("Error escribiendo denominaciones en GSheets: %s", e)
    return False


def _denom_to_sheet(d: float) -> str:
    """Convierte denominación float a string para la hoja: 100 → '100', 0.5 → '0.50'."""
    if d >= 1 and d == int(d):
        return str(int(d))
    return f"{d:.2f}"


def _parse_denom_raw(raw: list[list]) -> pd.DataFrame:
    """Parsea los datos crudos de la hoja Denominaciones a un DataFrame."""
    headers = ["Denominación", "Cartera", "Hucha"]
    rows = []
    for row in raw[1:]:
        if not row or not row[0]:
            continue
        padded = row[:3] + [0] * (3 - len(row[:3]))
        rows.append(padded)
    if not rows:
        return pd.DataFrame(columns=headers)
    df = pd.DataFrame(rows, columns=headers)
    df["Cartera"] = pd.to_numeric(df["Cartera"], errors="coerce").fillna(0).astype(int)
    df["Hucha"] = pd.to_numeric(df["Hucha"], errors="coerce").fillna(0).astype(int)
    return df


def _df_to_denom_dict(df: pd.DataFrame) -> dict:
    """Convierte un DataFrame de denominaciones al dict estándar."""
    from services.cash_tracker import get_empty_template

    result = get_empty_template()
    # Buscar timestamp en columnas extra (E1:F1) — puede no estar
    last_updated = ""

    for _, row in df.iterrows():
        denom_str = str(row.get("Denominación", "")).strip()
        if denom_str == "Última Actualización":
            last_updated = str(row.get("Cartera", ""))
            continue
        try:
            denom = float(denom_str)
        except (ValueError, TypeError):
            continue
        cartera_val = int(row.get("Cartera", 0) or 0)
        hucha_val = int(row.get("Hucha", 0) or 0)
        if denom in result["cartera"]:
            result["cartera"][denom] = cartera_val
            result["hucha"][denom] = hucha_val

    result["last_updated"] = last_updated
    return result


# ──────────────────────────────────────────────
# Escritura de datos
# ──────────────────────────────────────────────


def append_to_diario(rows_data: list[list]) -> bool:
    """
    Inserta filas en el Diario (siempre en pares — partida doble).

    Args:
        rows_data: Lista de listas [Fecha, CuentaID, Nombre, Cat, Debe, Haber, Desc].

    Returns:
        True si la inserción fue exitosa.
    """
    # ── DEMO MODE: bloquear escrituras ──
    try:
        from services.demo_data import block_writes_in_demo

        if block_writes_in_demo("append_to_diario"):
            return False
    except Exception:
        pass

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_DIARIO)

            col_dates = sheet.col_values(1)
            first_empty_row = len(col_dates) + 1

            if rows_data:
                end_col = chr(65 + len(rows_data[0]) - 1)
                rango = f"A{first_empty_row}:{end_col}{first_empty_row + len(rows_data) - 1}"
                try:
                    sheet.update(values=rows_data, range_name=rango)
                except TypeError:
                    sheet.update(rango, rows_data)

            get_diario.clear()
            _invalidate_parquet(_PARQUET_DIARIO)
            try:
                import csv

                with open(CSV_DIARIO, "a", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows(rows_data)
            except Exception as e_csv:
                log.warning("No se pudo actualizar CSV espejo en append_to_diario: %s", e_csv)
            return True
        except Exception as e:
            log.error("Error escribiendo en Google Sheets (Diario): %s", e)
            st.error(f"Error escribiendo en Google Sheets: {e}. Intentando CSV local.")

    # Fallback: CSV local
    import csv

    with open(CSV_DIARIO, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows_data)
    get_diario.clear()
    _invalidate_parquet(_PARQUET_DIARIO)
    return True


def append_to_diario_crudo(rows_data: list[list]) -> bool:
    """
    Inserta filas en el Diario Crudo (siempre en pares — partida doble).
    Esta función es usada principalmente por el importador de PDFs para guardar
    los datos "en bruto" de Trade Republic antes de cualquier limpieza manual.

    Args:
        rows_data: Lista de listas [Fecha, CuentaID, Nombre, Cat, Debe, Haber, Desc].

    Returns:
        True si la inserción fue exitosa.
    """
    # ── DEMO MODE: bloquear escrituras ──
    try:
        from services.demo_data import block_writes_in_demo

        if block_writes_in_demo("append_to_diario_crudo"):
            return False
    except Exception:
        pass

    # TODO(futuro): Aquí se podría añadir lógica de limpieza automática.
    # Si la transacción cumple ciertas reglas (ej: un Saveback conocido, un
    # redondeo trivial), podemos llamar a append_to_diario(rows_data_limpios)
    # desde aquí para que se auto-propague al Diario Limpio sin intervención manual.

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_DIARIO_CRUDO)

            col_dates = sheet.col_values(1)
            first_empty_row = len(col_dates) + 1

            if rows_data:
                end_col = chr(65 + len(rows_data[0]) - 1)
                rango = f"A{first_empty_row}:{end_col}{first_empty_row + len(rows_data) - 1}"
                try:
                    sheet.update(values=rows_data, range_name=rango)
                except TypeError:
                    sheet.update(rango, rows_data)

            get_diario_crudo.clear()
            _invalidate_parquet(_PARQUET_DIARIO_CRUDO)
            try:
                import csv

                with open(CSV_DIARIO_CRUDO, "a", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows(rows_data)
            except Exception as e_csv:
                log.warning("No se pudo actualizar CSV espejo en append_to_diario_crudo: %s", e_csv)
            return True
        except Exception as e:
            log.error("Error escribiendo en Google Sheets (Diario Crudo): %s", e)
            try:
                st.error(f"Error escribiendo en GSheets Crudo: {e}. Intentando CSV local.")
            except Exception:
                pass

    # Fallback: CSV local
    import csv

    with open(CSV_DIARIO_CRUDO, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows_data)
    get_diario_crudo.clear()
    _invalidate_parquet(_PARQUET_DIARIO_CRUDO)
    return True


def append_to_historico(rows_data: list[list]) -> bool:
    """
    Inserta filas en el Historial.
    """
    if not rows_data:
        return True

    from services.demo_data import block_writes_in_demo

    if block_writes_in_demo("append_to_historico"):
        return False

    if _can_use_gsheets():
        try:
            client = _get_gspread_client()
            sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_HISTORICO)

            # Formatear fechas a string para GSheets
            formatted_rows = []
            for row in rows_data:
                new_row = list(row)
                if hasattr(new_row[0], "strftime"):
                    new_row[0] = new_row[0].strftime("%Y-%m-%d")
                formatted_rows.append(new_row)

            sheet.append_rows(formatted_rows)
            get_historico.clear()
            _invalidate_parquet(_PARQUET_HISTORICO)
            return True
        except Exception as e:
            log.error("Error actualizando Histórico en GSheets: %s", e)
            st.error(f"Error actualizando Histórico en GSheets: {e}")

    # Fallback: CSV local
    import csv

    file_exists = os.path.exists(CSV_HISTORICO)
    with open(CSV_HISTORICO, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                [
                    "Fecha",
                    "Efectivo Fisico",
                    "Efectivo TR",
                    "BRK Value",
                    "Vanguard Value",
                    "Te Deben",
                    "Total",
                ]
            )
        writer.writerows(rows_data)
    get_historico.clear()
    return True
