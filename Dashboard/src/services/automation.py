"""
automation.py — Lógica para la inserción automática de asientos desde tickets.
"""

import logging
from datetime import datetime

import pandas as pd

from constants import (
    BOKATAS_DRIVE_FOLDER_ID,
    BOKATAS_VERSION_SHEET_URL,
    CUENTA_BOKATAS,
    CUENTA_CARTERA,
    CUENTA_PADRES,
    CUENTA_TR,
)
from data.gsheets import append_to_diario

log = logging.getLogger(__name__)


def create_journal_rows_for_ticket(
    ticket: dict, target_account: str = CUENTA_PADRES, payment_account: str = CUENTA_TR
) -> list[list]:
    """
    Crea el par de filas (partida doble) para un ticket.
    Estructura Diario: [Fecha, Nº Cuenta, Cuenta, Categoría, Debe, Haber, Descripción]
    """
    fecha = ticket["date"]
    if isinstance(fecha, datetime):
        fecha_str = fecha.strftime("%Y-%m-%d")
    else:
        fecha_str = str(fecha)

    importe = ticket.get("amount") or 0.0
    store = ticket.get("store", "Establecimiento")

    # NOTA: la columna "Cuenta" del Diario se rellena con fórmula en GSheets
    # (lookup por Nº Cuenta), así que las filas devuelven `None` ahí. Antes
    # se intentaba resolver el nombre desde `df_saldos` pero el valor nunca
    # se usaba — bloque eliminado para simplificar.

    # Método de pago: si el ticket es en efectivo, el dinero sale de Cartera
    # (111); en caso contrario (tarjeta, el ~90%) sale de la cuenta de pago
    # indicada (TR / 121 por defecto).
    pay_account = CUENTA_CARTERA if ticket.get("efectivo") else payment_account

    desc = "Script"

    if str(target_account) == str(CUENTA_BOKATAS):
        categoria = "Bokatas"
    else:
        categoria = store

    # Fila 1: Debe Target (Activo aumenta o Pasivo disminuye)
    row1 = [fecha_str, target_account, None, categoria, importe, None, desc]
    # Fila 2: Haber Payment (Banco/Cartera disminuye)
    row2 = [fecha_str, pay_account, None, categoria, None, importe, desc]

    return [row1, row2]


def register_tickets_in_diario(
    tickets: list[dict],
    target_account: str = CUENTA_PADRES,
    payment_account: str = CUENTA_TR,
) -> int:
    """
    Procesa una lista de tickets y los inserta en el Diario.
    Retorna el número de tickets (pares de filas) insertados con éxito.
    """
    if not tickets:
        return 0

    # ── DEMO MODE: bloquear escrituras ──
    try:
        from services.demo_data import block_writes_in_demo

        if block_writes_in_demo("register_tickets_in_diario"):
            return 0
    except Exception:
        pass

    all_rows = []
    for t in tickets:
        if t.get("amount") is None or t["amount"] <= 0:
            log.warning("Saltando ticket %s: importe no válido", t["filename"])
            continue
        all_rows.extend(create_journal_rows_for_ticket(t, target_account, payment_account))

    if not all_rows:
        return 0

    success = append_to_diario(all_rows)
    if success:
        log.info("Insertadas %d filas (%d tickets) en el Diario", len(all_rows), len(tickets))
        return len(all_rows) // 2
    else:
        log.error("Error al insertar tickets en el Diario")
        return 0


def check_pending_tickets(df_diario: pd.DataFrame) -> dict:
    """
    Inspecciona las carpetas de Drive (Padres y Bokatas) para determinar si existen
    tickets pendientes de procesar con Gemini o pendientes de registrar en el Diario.

    Retorna un diccionario estructurado con el estado de ambas fuentes:
      {
        "padres": {"has_pending": bool, "unrenamed": list, "unregistered": list},
        "bokatas": {"has_pending": bool, "unprocessed": list, "can_retry": bool, "unregistered": list},
        "total_pending": int
      }
    """
    from services.auditor import (
        _get_files_from_drive,
        _get_padres_files,
        identify_unregistered_tickets,
    )
    from services.extraction import _ALREADY_RENAMED, _is_already_renamed

    result = {
        "padres": {
            "has_pending": False,
            "unrenamed": [],
            "unregistered": [],
        },
        "bokatas": {
            "has_pending": False,
            "unprocessed": [],
            "can_retry": False,
            "unregistered": [],
        },
        "total_pending": 0,
    }

    from services.demo_data import is_demo_mode

    if is_demo_mode():
        return result

    # 1. Comprobar Padres (local Drive folder)
    try:
        padres_files = _get_padres_files()
        padres_unrenamed = [f for f in padres_files if not _is_already_renamed(f["filename"])]
        padres_unregistered = identify_unregistered_tickets(df_diario, only_renamed=True)

        result["padres"]["unrenamed"] = padres_unrenamed
        result["padres"]["unregistered"] = padres_unregistered
        result["padres"]["has_pending"] = bool(padres_unrenamed or padres_unregistered)
    except Exception as e:
        log.warning("Error comprobando tickets pendientes de Padres: %s", e)

    # 2. Comprobar Bokatas (Drive folder ID)
    try:
        try:
            from services.drive_doc import list_drive_files

            if hasattr(list_drive_files, "cache"):
                list_drive_files.cache.clear()
        except Exception:
            pass

        bokatas_files = _get_files_from_drive(BOKATAS_DRIVE_FOLDER_ID)
        existing_ids = set()
        if BOKATAS_VERSION_SHEET_URL:
            try:
                from data.gsheets import _get_gspread_client

                client = _get_gspread_client()
                sheet = client.open_by_url(BOKATAS_VERSION_SHEET_URL).sheet1
                existing_ids = set(filter(None, sheet.col_values(6)))
            except Exception as e:
                log.warning("No se pudieron leer IDs del Sheet de Bokatas: %s", e)

        bokatas_unregistered = identify_unregistered_tickets(
            df_diario,
            folder_path_or_id=BOKATAS_DRIVE_FOLDER_ID,
            account_id=CUENTA_BOKATAS,
            is_drive=True,
            match_amount_only=True,
            only_renamed=True,
        )

        unprocessed = [
            f
            for f in bokatas_files
            if not bool(_ALREADY_RENAMED.match(f["filename"])) and f["path"] not in existing_ids
        ]
        can_retry = any(
            not bool(_ALREADY_RENAMED.match(f["filename"])) and f["path"] in existing_ids
            for f in bokatas_files
        )

        result["bokatas"]["unprocessed"] = unprocessed
        result["bokatas"]["can_retry"] = can_retry
        result["bokatas"]["unregistered"] = bokatas_unregistered
        result["bokatas"]["has_pending"] = bool(unprocessed or can_retry or bokatas_unregistered)
    except Exception as e:
        log.warning("Error comprobando tickets pendientes de Bokatas: %s", e)

    padres_count = len(result["padres"]["unrenamed"]) + len(result["padres"]["unregistered"])
    bokatas_count = (
        len(result["bokatas"]["unprocessed"])
        + (1 if result["bokatas"]["can_retry"] else 0)
        + len(result["bokatas"]["unregistered"])
    )
    result["total_pending"] = padres_count + bokatas_count

    return result


def process_padres_tickets(df_diario: pd.DataFrame) -> dict:
    """
    Ejecuta el procesamiento de tickets de Padres:
      1. Extrae datos con Gemini y renombra archivos locales en Padres/.
      2. Mapea el método de pago detectado (efectivo -> Cartera 111, tarjeta -> TR 121).
      3. Registra asientos de partida doble en el Diario (Cuenta 131).
    """
    from services.auditor import identify_unregistered_tickets
    from services.extraction import process_padres_folder

    rename_results = process_padres_folder()
    renamed_count = sum(1 for r in rename_results if r.get("renamed"))
    failed = [r for r in rename_results if not r.get("renamed")]

    efectivo_por_archivo = {
        r["renamed"]: bool(getattr(r.get("data"), "efectivo", False))
        for r in rename_results
        if r.get("renamed")
    }

    tickets_to_register = identify_unregistered_tickets(df_diario, only_renamed=True)
    for t in tickets_to_register:
        t["efectivo"] = efectivo_por_archivo.get(t["filename"], False)

    registered_count = register_tickets_in_diario(
        tickets_to_register, target_account=CUENTA_PADRES, payment_account=CUENTA_TR
    )
    cash_count = sum(
        1 for t in tickets_to_register if t.get("efectivo") and (t.get("amount") or 0) > 0
    )

    return {
        "renamed": renamed_count,
        "registered": registered_count,
        "cash_count": cash_count,
        "failed": failed,
    }


def process_bokatas_tickets(df_diario: pd.DataFrame) -> dict:
    """
    Ejecuta el procesamiento de tickets de Bokatas:
      1. Reintenta renombrar en Drive archivos que ya están en el Sheet si aplica.
      2. Procesa archivos nuevos con Gemini, renombra en Drive y añade al GSheet de la ONG.
      3. Registra los asientos correspondientes en el Diario personal (Cuenta 133).
    """
    from data.gsheets import _get_gspread_client
    from services.auditor import _get_files_from_drive, identify_unregistered_tickets
    from services.extraction import (
        _ALREADY_RENAMED,
        process_and_update_sheet,
        retry_failed_renames,
    )

    all_files = _get_files_from_drive(BOKATAS_DRIVE_FOLDER_ID)
    try:
        gspread_client = _get_gspread_client()
        sheet = gspread_client.open_by_url(BOKATAS_VERSION_SHEET_URL).sheet1
        existing_ids = set(filter(None, sheet.col_values(6)))
    except Exception as e:
        log.warning("No se pudo leer sheet de Bokatas: %s", e)
        existing_ids = set()

    can_retry = any(
        not bool(_ALREADY_RENAMED.match(f["filename"])) and f["path"] in existing_ids
        for f in all_files
    )
    can_process = any(
        not bool(_ALREADY_RENAMED.match(f["filename"])) and f["path"] not in existing_ids
        for f in all_files
    )

    rename_results = []
    if can_retry:
        rename_results.extend(retry_failed_renames())
    if can_process:
        rename_results.extend(process_and_update_sheet())

    renamed_count = sum(1 for r in rename_results if r.get("renamed"))
    failed = [r for r in rename_results if not r.get("renamed")]

    tickets_to_register = identify_unregistered_tickets(
        df_diario,
        folder_path_or_id=BOKATAS_DRIVE_FOLDER_ID,
        account_id=CUENTA_BOKATAS,
        is_drive=True,
        match_amount_only=True,
        only_renamed=True,
    )

    registered_count = register_tickets_in_diario(
        tickets_to_register, target_account=CUENTA_BOKATAS, payment_account=CUENTA_TR
    )

    return {
        "renamed": renamed_count,
        "registered": registered_count,
        "failed": failed,
    }


def auto_sync_drive_tickets(df_diario: pd.DataFrame) -> dict:
    """
    Revisa automáticamente las carpetas de Drive (Padres y Bokatas).
    Si detecta tickets no procesados o no registrados:
      - Extrae los datos con Gemini AI.
      - Renombra los archivos en Drive / local.
      - Inserta los asientos correspondientes en el Libro Diario.

    Retorna un resumen del resultado para feedback visual en la UI.
    """
    from services.demo_data import is_demo_mode

    if is_demo_mode():
        status = None
        padres_pending = bokatas_pending = False
    else:
        status = check_pending_tickets(df_diario)
        padres_pending = status["padres"]["has_pending"]
        bokatas_pending = status["bokatas"]["has_pending"]

    if not padres_pending and not bokatas_pending:
        return {
            "executed": False,
            "padres": {"renamed": 0, "registered": 0, "cash_count": 0, "failed": []},
            "bokatas": {"renamed": 0, "registered": 0, "failed": []},
            "total_registered": 0,
            "total_renamed": 0,
            "failed": [],
        }

    log.info(
        "Auto-sync activado: detectados tickets pendientes (Padres: %s, Bokatas: %s)",
        padres_pending,
        bokatas_pending,
    )

    padres_res = {"renamed": 0, "registered": 0, "cash_count": 0, "failed": []}
    bokatas_res = {"renamed": 0, "registered": 0, "failed": []}

    if padres_pending:
        try:
            padres_res = process_padres_tickets(df_diario)
        except Exception as e:
            log.error("Error en auto-sync Padres: %s", e)
            padres_res["failed"].append({"original": "Padres", "error": str(e)})

    if bokatas_pending:
        try:
            bokatas_res = process_bokatas_tickets(df_diario)
        except Exception as e:
            log.error("Error en auto-sync Bokatas: %s", e)
            bokatas_res["failed"].append({"original": "Bokatas", "error": str(e)})

    total_registered = padres_res["registered"] + bokatas_res["registered"]
    total_renamed = padres_res["renamed"] + bokatas_res["renamed"]
    all_failed = padres_res["failed"] + bokatas_res["failed"]

    return {
        "executed": True,
        "padres": padres_res,
        "bokatas": bokatas_res,
        "total_registered": total_registered,
        "total_renamed": total_renamed,
        "failed": all_failed,
    }
