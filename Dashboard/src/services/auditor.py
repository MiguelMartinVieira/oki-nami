"""
auditor.py — Matching de justificantes para la Cuenta 131 (Padres).

Flujo:
  1. Filtra del Diario todos los asientos de la Cuenta 131.
  2. Escanea Padres/ en busca de justificantes (PDF, imagen, sin extensión).
  3. Matching en tres pasadas:
       1ª Exacto     — importe ±0.05 € + fecha ≤7 días (ticket físico)
       2ª Fuzzy      — solo fecha ≤5 días               (ticket físico)
       3ª Doc Drive  — cruce con Google Doc "Pagos Sin Ticket"
                       Si hay match → elimina la línea del doc y re-sube
"""

import datetime
import json
import logging
import os
import re

import pandas as pd

from constants import (
    CUENTA_PADRES,
    LIQUIDATED_PADRES_FILE,
    PADRES_DOC_ID,
    PADRES_DRIVE_FOLDER_ID,
    PADRES_FOLDER,
    POSSIBLE_PADRES_FOLDERS,
)

log = logging.getLogger(__name__)


# ───────────────────────────────────────────
# Persistencia de Liquidaciones de Padres
# ───────────────────────────────────────────


def load_liquidated_padres() -> set[str]:
    """Carga las claves de transacciones de Padres que han sido liquidadas."""
    if not os.path.exists(LIQUIDATED_PADRES_FILE):
        return set()
    try:
        with open(LIQUIDATED_PADRES_FILE, encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return set()
            data = json.loads(content)
            return set(data)
    except Exception as e:
        log.warning("Error leyendo _padres_liquidated.json: %s", e)
        return set()


def _clean_key_str(val) -> str:
    if pd.isna(val) or str(val).strip().lower() in ("none", "nan"):
        return ""
    return str(val).replace("", "").strip()


def save_liquidated_padres(keys: list[str]) -> None:
    """Guarda claves de transacciones liquidadas."""
    if not keys:
        return
    current = load_liquidated_padres()
    current.update(k for k in keys if k)
    try:
        os.makedirs(os.path.dirname(LIQUIDATED_PADRES_FILE), exist_ok=True)
        with open(LIQUIDATED_PADRES_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(current)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("Error guardando _padres_liquidated.json: %s", e)


def get_txn_key(row) -> str:
    """Genera una clave única representativa de una transacción para seguimiento de liquidación."""
    raw_fecha = row.get("Fecha")
    try:
        dt = pd.to_datetime(raw_fecha)
        fecha_str = dt.strftime("%Y-%m-%d") if not pd.isna(dt) else ""
    except Exception:
        fecha_str = str(raw_fecha or "").split()[0].replace("/", "-")

    cat_str = _clean_key_str(row.get("Categoría"))
    desc_str = _clean_key_str(row.get("Descripción"))

    try:
        val_debe = float(row.get("Debe", 0) or 0)
    except (ValueError, TypeError):
        val_debe = 0.0

    try:
        val_haber = float(row.get("Haber", 0) or 0)
    except (ValueError, TypeError):
        val_haber = 0.0

    return f"{fecha_str}_{cat_str}_{desc_str}_{val_debe:.2f}_{val_haber:.2f}"


# ───────────────────────────────────────────
# PDF helpers
# ───────────────────────────────────────────


def _extract_amount_from_filename(filename: str) -> float | None:
    """Extrae importe de forma robusta eliminando la fecha primero."""
    s_clean = re.sub(r"\d{8}", "", filename)

    m = re.search(r"(\d+[.,]\d{1,2})", s_clean)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except Exception:
            pass

    m_int = re.search(r"(\d+)", s_clean)
    if m_int:
        try:
            return float(m_int.group(1))
        except Exception:
            pass

    return None


def _extract_date_amount_from_pdf(pdf_path: str) -> tuple:
    """Extrae fecha y cantidad de un recibo PDF (basado en nombre de fichero y fecha de fichero)."""
    basename = os.path.basename(pdf_path)
    amount = _extract_amount_from_filename(basename)

    date_obj = _extract_date_from_filename(basename)
    if date_obj is None:
        date_obj = datetime.datetime.fromtimestamp(os.path.getmtime(pdf_path)).date()

    return date_obj, amount


# ───────────────────────────────────────────
# Filename date parser
# ───────────────────────────────────────────


def _extract_date_from_filename(filename: str) -> datetime.date | None:
    """
    Parsea fecha en nombre de fichero.
    Soporta:
      - DDMMYYYY (sufijo)
      - YYYYMMDD (prefijo o sufijo)
      - DDMMYY (prefijo, común en fotos de Drive)
    """
    # 1. DDMMYYYY al final
    m = re.search(r"(\d{2})(\d{2})(\d{4})\s*(?:\.[^.]+)?$", filename)
    if m:
        try:
            return datetime.datetime.strptime(
                f"{m.group(1)}{m.group(2)}{m.group(3)}", "%d%m%Y"
            ).date()
        except Exception:
            pass

    # 2. YYYYMMDD en cualquier posición
    m = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if m:
        try:
            return datetime.datetime.strptime(m.group(0), "%Y%m%d").date()
        except Exception:
            pass

    # 3. DDMMYY al principio (ej: 050326)
    m = re.match(r"(\d{2})(\d{2})(\d{2})", filename)
    if m:
        try:
            # Asumimos siglo 21 (20XX)
            return datetime.datetime.strptime(
                f"{m.group(1)}{m.group(2)}20{m.group(3)}", "%d%m%Y"
            ).date()
        except Exception:
            pass

    return None


def _extract_store_from_filename(filename: str) -> str:
    """Extrae el nombre del establecimiento del nombre del fichero."""
    # Eliminar fecha (8 dígitos seguidos o con guiones)
    s = re.sub(r"\d{4}[-]?\d{2}[-]?\d{2}", "", filename)
    s = re.sub(r"\d{2}[-]?\d{2}[-]?\d{4}", "", s)

    # Eliminar importes (dígitos con coma/punto)
    s = re.sub(r"\d+[.,]\d{1,2}", "", s)
    s = re.sub(r"\d+", "", s)

    # Eliminar símbolos de moneda y extensiones
    s = s.replace("€", "").replace("$", "")
    s = re.sub(r"\.[^.]+$", "", s)

    # Limpiar espacios y guiones sobrantes
    s = s.replace("-", " ").replace("_", " ")

    # Eliminar palabras ruidosas comunes
    noise = ["ticket", "recibo", "comprobante", "pago", "scan", "foto"]
    words = [w.strip() for w in s.split() if w.strip() and w.lower() not in noise]

    if not words:
        return "Establecimiento Desconocido"

    # Capitalizar cada palabra
    return " ".join(words).title()


# ───────────────────────────────────────────
# File discovery
# ───────────────────────────────────────────


def _get_padres_files(folder_path: str = PADRES_FOLDER) -> list[dict]:
    """Escanea la carpeta local Padres/ — prueba todas las rutas configuradas."""
    for path in POSSIBLE_PADRES_FOLDERS:
        if os.path.isdir(path):
            return _get_files_from_local(path)
    return _get_files_from_local(folder_path)


def _get_files_from_local(folder_path: str) -> list[dict]:
    """Escanea una carpeta local y extrae metadatos de los justificantes."""
    if not os.path.exists(folder_path):
        return []

    records: list[dict] = []
    for f in sorted(os.listdir(folder_path)):
        # Ignorar archivos del sistema y de Google Drive
        if f.lower() in ("desktop.ini", "icon\r"):
            continue
        if f.lower().endswith((".gdoc", ".gsheet", ".gslides")):
            continue

        full_path = os.path.join(folder_path, f)
        if os.path.isdir(full_path):
            continue

        if f.lower().endswith(".pdf"):
            d, amt = _extract_date_amount_from_pdf(full_path)
            records.append(
                {
                    "filename": f,
                    "path": full_path,
                    "type": "pdf",
                    "date": d
                    or datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).date(),
                    "amount": amt,
                    "store": _extract_store_from_filename(f),
                }
            )

        elif f.lower().endswith((".jpg", ".jpeg", ".png")):
            d = _extract_date_from_filename(f)
            if d is None:
                d = datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).date()
            # Sin importe en el nombre queda en None: el OCR de imágenes se hace
            # con Gemini Vision en services/extraction.py, no aquí.
            amt = _extract_amount_from_filename(f)
            records.append(
                {
                    "filename": f,
                    "path": full_path,
                    "type": "img",
                    "date": d,
                    "amount": amt,
                    "store": _extract_store_from_filename(f),
                }
            )

        else:
            # Caso genérico sin extensión
            d = _extract_date_from_filename(f)
            if d is None:
                d = datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).date()
            # Sin importe en el nombre queda en None: el OCR de imágenes se hace
            # con Gemini Vision en services/extraction.py, no aquí.
            amt = _extract_amount_from_filename(f)
            records.append(
                {
                    "filename": f,
                    "path": full_path,
                    "type": "img",
                    "date": d,
                    "amount": amt,
                    "store": _extract_store_from_filename(f),
                }
            )

    return records


def _get_files_from_drive(folder_id: str) -> list[dict]:
    """
    Lista archivos de Drive y extrae metadatos del nombre.

    Usa el mimeType devuelto por la API para identificar imágenes/PDFs.
    Esto es robusto ante renombrados del tipo 'YYYYMMDD - importe€' que
    eliminan la extensión original (.jpg) y confundirían un filtro basado
    solo en el nombre.
    """
    from services.drive_doc import list_drive_files

    drive_files = list_drive_files(folder_id)
    records: list[dict] = []

    for f in drive_files:
        name = f["name"]
        mime_type = f.get("mimeType", "")

        # Filtrar: solo imágenes o PDFs.
        # Prioridad al mimeType (no cambia aunque se renombre el archivo).
        # Fallback a la extensión del nombre como segunda opción.
        is_supported = "image" in mime_type.lower() or "pdf" in mime_type.lower()
        if not is_supported:
            is_supported = name.lower().endswith((".jpg", ".jpeg", ".png", ".pdf"))
        if not is_supported:
            continue

        d = _extract_date_from_filename(name)
        if d is None:
            try:
                d = datetime.datetime.fromisoformat(f["createdTime"].replace("Z", "+00:00")).date()
            except Exception:
                d = datetime.date.today()

        amt = _extract_amount_from_filename(name)

        records.append(
            {
                "filename": name,
                "path": f["id"],  # ID de Drive (sin descarga)
                "type": "drive",
                "date": d,
                "amount": amt,
                "store": _extract_store_from_filename(name),
            }
        )

    return records


def identify_unregistered_tickets(
    df_diario: pd.DataFrame,
    folder_path_or_id: str = PADRES_FOLDER,
    account_id: str = CUENTA_PADRES,
    is_drive: bool = False,
    match_amount_only: bool = False,
    only_renamed: bool = False,
) -> list[dict]:
    """
    Identifica tickets que NO tienen un asiento correspondiente en el Diario.
    Soporta tanto carpetas locales como IDs de Drive.

    Args:
        only_renamed: Si True, ignora los archivos que aún no están en el
            formato canónico (YYYYMMDD …). Para Padres esto es imprescindible:
            el importe/fecha/establecimiento de esos archivos se "adivinaría"
            del nombre o por OCR (no fiable), por lo que registrarlos metería
            datos inventados en el Diario. Solo deben registrarse los archivos
            ya validados por Gemini (renombrados) o correctos de origen.
    """
    from services.accounting import filter_cuenta

    if only_renamed:
        from services.extraction import _is_already_renamed

    df_acc = filter_cuenta(df_diario, account_id)

    if is_drive:
        files = _get_files_from_drive(folder_path_or_id)
    else:
        files = _get_files_from_local(folder_path_or_id)

    if not files:
        return []

    unregistered = []

    # Pre-calcular gastos existentes en el Diario (Debe > 0)
    # Usamos una lista de dicts para poder marcar los ya "usados" en el matching
    existing_expenses = []
    for _, row in df_acc.iterrows():
        try:
            amt = float(row.get("Debe", 0))
            if amt > 0:
                dt = pd.to_datetime(row["Fecha"]).date()
                existing_expenses.append({"amount": amt, "date": dt, "matched": False})
        except Exception:
            continue

    for f in files:
        # Padres: descartar archivos que aún no están en formato canónico.
        # Para esos, importe/fecha se deducirían del nombre/OCR (no fiable);
        # primero tienen que pasar por Gemini. Sin esto, un archivo cuya
        # extracción de Gemini falló se registraría con datos inventados.
        if only_renamed and not _is_already_renamed(f["filename"]):
            continue

        # Solo procesar si tiene un importe válido mayor que cero
        if f["amount"] is None or f["amount"] <= 0:
            continue

        found = False
        # Para evitar que un asiento del Diario "satisfaga" a dos ficheros distintos,
        # deberíamos llevar cuenta de cuáles han sido usados.
        for exp in existing_expenses:
            if exp["matched"]:
                continue

            # Match por importe (±0.05€)
            amount_match = abs(f["amount"] - exp["amount"]) < 0.05

            if amount_match:
                if match_amount_only:
                    # En Bokatas, si coincide el importe ya lo damos por registrado
                    found = True
                    exp["matched"] = True
                    break
                else:
                    # En Padres (o por defecto), requerimos fecha exacta (±1 día)
                    if abs((f["date"] - exp["date"]).days) <= 1:
                        found = True
                        exp["matched"] = True
                        break

        if not found:
            unregistered.append(f)

    return unregistered


# ───────────────────────────────────────────
# Matching principal
# ───────────────────────────────────────────


def match_expenses_with_files(
    df_acc: pd.DataFrame,
    folder_path_or_id: str = PADRES_FOLDER,
    is_drive: bool = False,
    use_drive_doc: bool = True,
    match_amount_only: bool = False,
) -> pd.DataFrame:
    """
    Cruza asientos de una cuenta con justificantes.

    Pasadas:
      1ª Exacto    — importe ±0.05€ (+ fecha ≤7 días si match_amount_only=False)
      2ª Fuzzy     — solo fecha ≤5 días (omitida si match_amount_only=True)
      3ª Doc Drive — Solo si use_drive_doc=True (típico de Padres 131)

    Args:
        match_amount_only: Si True, ignora la fecha en el matching.
            Usar para Bokatas (133): el voluntario paga el ticket un día,
            pero el reembolso desde la cuenta de Miguel puede llegar semanas
            más tarde, por lo que la fecha no es criterio válido.
    """
    df_result = df_acc.copy()
    if df_result.empty:
        df_result["Estado"] = []
        df_result["Justificante"] = []
        return df_result

    if is_drive:
        files = _get_files_from_drive(folder_path_or_id)
    else:
        files = _get_files_from_local(folder_path_or_id)

    df_result["Estado"] = "❌ Faltante"
    df_result["Justificante"] = ""

    used_files: set[int] = set()
    matched_rows: set[int] = set()

    # Pre-calcular datos de las filas
    row_data = []
    for idx, row in df_result.iterrows():
        try:
            amt = float(row.get("Debe", 0))
        except (ValueError, TypeError):
            amt = 0.0

        rd_dt = pd.to_datetime(row["Fecha"])
        rd = rd_dt.date() if not pd.isnull(rd_dt) else datetime.date.today()
        row_data.append({"idx": idx, "amount": amt, "date": rd})

    # Resolver carpeta: primera que exista de las rutas configuradas
    if not is_drive:
        resolved_folder = next(
            (p for p in POSSIBLE_PADRES_FOLDERS if os.path.isdir(p)), folder_path_or_id
        )
        files = _get_files_from_local(resolved_folder)
        pagado_dir = os.path.join(resolved_folder, "Pagado")
        pagado_files = _get_files_from_local(pagado_dir) if os.path.isdir(pagado_dir) else []
    else:
        pagado_files = []

    liquidated_keys = load_liquidated_padres()
    used_pagado_files: set[int] = set()

    # ── 0ª PASADA: Movimientos ya liquidados o con justificante en /Pagado ──
    for r in row_data:
        row_obj = df_result.loc[r["idx"]]
        t_key = get_txn_key(row_obj)
        if t_key in liquidated_keys:
            df_result.at[r["idx"], "Estado"] = "✅ Pagado"
            matched_rows.add(r["idx"])
            continue

        if r["amount"] > 0 and pagado_files:
            for i, pf in enumerate(pagado_files):
                if i in used_pagado_files or pf["amount"] is None:
                    continue
                amount_ok = abs(pf["amount"] - r["amount"]) < 0.05
                date_ok = abs((pf["date"] - r["date"]).days) <= 7
                if amount_ok and date_ok:
                    df_result.at[r["idx"], "Estado"] = "✅ Pagado"
                    df_result.at[r["idx"], "Justificante"] = pf["filename"]
                    used_pagado_files.add(i)
                    matched_rows.add(r["idx"])
                    break

    # ── 1ª PASADA: Match EXACTO (Importe ±0.05€ y Fecha ±1 día) ──
    for r in row_data:
        if r["idx"] in matched_rows:
            continue

        if r["amount"] <= 0:
            df_result.at[r["idx"], "Estado"] = "➖ N/A (Ingreso)"
            matched_rows.add(r["idx"])
            continue

        for i, f in enumerate(files):
            if i in used_files or f["amount"] is None:
                continue

            amount_ok = abs(f["amount"] - r["amount"]) < 0.05
            date_ok = abs((f["date"] - r["date"]).days) <= 1

            if amount_ok and date_ok:
                label = (
                    "✅ Match Drive"
                    if f["type"] == "drive"
                    else "✅ Match PDF"
                    if f["type"] == "pdf"
                    else "✅ Match Imagen"
                )
                df_result.at[r["idx"], "Estado"] = label
                df_result.at[r["idx"], "Justificante"] = f["filename"]
                used_files.add(i)
                matched_rows.add(r["idx"])
                break

    # ── 2ª PASADA: Match AMPLIO (Importe ±0.05€ y Fecha ±7 días) ──
    for r in row_data:
        if r["idx"] in matched_rows:
            continue

        for i, f in enumerate(files):
            if i in used_files or f["amount"] is None:
                continue

            amount_ok = abs(f["amount"] - r["amount"]) < 0.05
            if not amount_ok:
                continue

            # Comprobar fecha según modo
            if match_amount_only:
                date_ok = True
            else:
                date_ok = abs((f["date"] - r["date"]).days) <= 7

            if date_ok:
                label = (
                    "✅ Match Drive"
                    if f["type"] == "drive"
                    else "✅ Match PDF"
                    if f["type"] == "pdf"
                    else "✅ Match Imagen"
                )
                df_result.at[r["idx"], "Estado"] = label
                df_result.at[r["idx"], "Justificante"] = f["filename"]
                used_files.add(i)
                matched_rows.add(r["idx"])
                break

    # ── 3ª PASADA: Matches Fuzzy por Fecha (omitida en modo solo-importe) ──
    if not match_amount_only:
        for r in row_data:
            if r["idx"] in matched_rows:
                continue

            for i, f in enumerate(files):
                if i in used_files:
                    continue
                if abs((f["date"] - r["date"]).days) <= 5:
                    label = (
                        "⚠️ Fecha Drive"
                        if f["type"] == "drive"
                        else "⚠️ Fecha PDF"
                        if f["type"] == "pdf"
                        else "⚠️ Fecha Imagen"
                    )
                    df_result.at[r["idx"], "Estado"] = label
                    df_result.at[r["idx"], "Justificante"] = f["filename"]
                    used_files.add(i)
                    matched_rows.add(r["idx"])
                    break

    # ── 4ª PASADA: Google Doc "Pagos Sin Ticket" (opcional) ──
    if use_drive_doc:
        df_result = _match_with_drive_doc(df_result, row_data, matched_rows)

    return df_result


def _discover_padres_doc_id() -> str | None:
    """
    Autodescubre el Google Doc dentro de la carpeta Drive de Padres.

    Prefiere uno cuyo nombre contenga "ticket". Robusto a que el doc se
    recree o cambie de ID.
    """
    try:
        from services.drive_doc import list_drive_files
    except ImportError:
        return None

    docs = [
        f
        for f in list_drive_files(PADRES_DRIVE_FOLDER_ID)
        if "document" in f.get("mimeType", "").lower()
    ]
    if not docs:
        return None
    for f in docs:
        if "ticket" in f.get("name", "").lower():
            return f["id"]
    return docs[0]["id"]


def _load_padres_doc_text() -> str | None:
    """
    Descarga el texto del Google Doc "Sin Ticket".

    Intenta primero el ID configurado (PADRES_DOC_ID, override por env) y, si
    no es accesible (p.ej. el doc se recreó y el ID quedó obsoleto), autodescubre
    el doc dentro de la carpeta Drive de Padres. Así nunca se queda "atascado"
    en un ID muerto.
    """
    try:
        from services.drive_doc import download_doc_as_text
    except ImportError:
        log.warning("drive_doc no disponible")
        return None

    tried: set[str] = set()
    for cid in (PADRES_DOC_ID, _discover_padres_doc_id()):
        if not cid or cid in tried:
            continue
        tried.add(cid)
        text = download_doc_as_text(cid)
        if text and text.strip():
            return text
    return None


def _match_with_drive_doc(
    df_result: pd.DataFrame,
    row_data: list[dict],
    matched_rows: set[int],
) -> pd.DataFrame:
    """
    Cuarta pasada: cruza los ❌ Faltante contra el Google Doc "Sin Ticket".

    Si el pago aparece en el doc, se marca como "✅ Match Docs" (mismo color que
    el resto de matches). NO se elimina la línea del doc: el doc es el registro
    persistente de los pagos sin ticket, por lo que el match se mantiene en
    sucesivas reconciliaciones mientras la línea siga ahí.
    """
    doc_text = _load_padres_doc_text()
    if not doc_text or not doc_text.strip():
        return df_result

    # Importar aquí para evitar dependencia circular
    try:
        from services.drive_doc import parse_doc_entries
    except ImportError:
        log.warning("drive_doc no disponible")
        return df_result

    doc_entries = parse_doc_entries(doc_text)
    if not doc_entries:
        return df_result

    used_doc: set[int] = set()

    for r in row_data:
        if r["idx"] in matched_rows or r["amount"] <= 0:
            continue

        for i, e in enumerate(doc_entries):
            if i in used_doc:
                continue
            if abs(e["amount"] - r["amount"]) < 0.05 and abs((e["date"] - r["date"]).days) <= 7:
                df_result.at[r["idx"], "Estado"] = "✅ Match Docs"
                df_result.at[r["idx"], "Justificante"] = f"{e['store']} — Doc Sin Ticket"
                matched_rows.add(r["idx"])
                used_doc.add(i)
                break

    return df_result


def archive_padres_tickets(
    filenames: list[str],
    tx_keys: list[str] | None = None,
    folder_path: str = PADRES_FOLDER,
) -> tuple[int, list[str]]:
    """
    Mueve los justificantes indicados de la carpeta Padres/ a Padres/Pagado/
    y guarda las claves de las transacciones como liquidadas.

    Args:
        filenames: Lista de nombres de archivos a mover.
        tx_keys: Opcional. Claves de transacciones a guardar en _padres_liquidated.json.
        folder_path: Ruta base de la carpeta Padres/.

    Returns:
        tuple[int, list[str]]: (número de archivos movidos, lista de mensajes de error)
    """
    import shutil

    if tx_keys:
        save_liquidated_padres(tx_keys)

    resolved_folder = next((p for p in POSSIBLE_PADRES_FOLDERS if os.path.isdir(p)), folder_path)
    pagado_folder = os.path.join(resolved_folder, "Pagado")
    os.makedirs(pagado_folder, exist_ok=True)

    moved_count = 0
    errors = []

    for fname in filenames:
        if not fname:
            continue
        # Limpiar si el nombre viene con sufijo de auditoría (ej: " — Doc Sin Ticket")
        clean_fname = str(fname).split(" —")[0].strip()

        if clean_fname in ("Pagado", "desktop.ini", "Sin Ticket.gdoc"):
            continue

        src_path = os.path.join(resolved_folder, clean_fname)

        if os.path.exists(src_path) and os.path.isfile(src_path):
            dst_path = os.path.join(pagado_folder, clean_fname)
            try:
                shutil.move(src_path, dst_path)
                moved_count += 1
            except Exception as e:
                errors.append(f"Error al mover {clean_fname}: {e}")
        else:
            # Comprobar si ya existe en /Pagado
            if os.path.exists(os.path.join(pagado_folder, clean_fname)):
                moved_count += 1
            else:
                log.info("No se encontró el archivo físico %s en %s", clean_fname, resolved_folder)

    return moved_count, errors
