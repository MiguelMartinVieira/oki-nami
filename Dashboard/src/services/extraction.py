"""
extraction.py — Extracción de datos de tickets con Gemini AI.

Dos flujos:
  A) Bokatas ONG (Cuenta 133) — archivos en Google Drive.
  B) Padres (Cuenta 131)      — archivos locales en carpeta Padres/.

Flujo Bokatas:
  1. Lista imágenes en la carpeta de Drive (BOKATAS_DRIVE_FOLDER_ID).
  2. Filtra las ya procesadas mediante el Drive File ID (columna F del GSheet).
  3. Descarga los bytes de cada imagen en memoria (sin escribir a disco).
  4. Envía los bytes directamente a Gemini AI (gemini-flash-latest) para
     extracción estructurada: Importe, Supermercado, Fecha, Nº Factura.
     Si Gemini falla → se omite el archivo (gestión manual).
  5. Renombra el archivo en Drive: YYYYMMDD - importe€
     (o SINfecha - importe€ si Gemini no detecta fecha).
  6. Añade una fila al Google Sheet:
       [Concepto, Importe, Supermercado, Fecha, Nº Factura, Drive File ID]
  Anti-duplicados: Drive File ID en columna F (no cambia al renombar el archivo).

Flujo Padres:
  1. Escanea archivos locales (imágenes y PDFs) en PADRES_FOLDER.
  2. Detecta cuáles ya están en el formato objetivo (YYYYMMDD …) y los salta.
  3. Lee los bytes del archivo y los envía a Gemini AI.
  4. Renombra el archivo local: YYYYMMDD SUPERMERCADO COSTE €.ext
"""

import json
import logging
import mimetypes
import re
import time
import urllib.request
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from constants import (
    BOKATAS_DRIVE_FOLDER_ID,
    BOKATAS_VERSION_SHEET_URL,
    GEMINI_API_KEY,
    GEMINI_VISION_MODELS,
    PADRES_FOLDER,
    POSSIBLE_PADRES_FOLDERS,
)
from data.gsheets import _get_gspread_client
from services.drive_doc import _get_access_token, list_drive_files

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Drive: Descarga en Memoria y Renombrado
# ──────────────────────────────────────────────


def _get_drive_image_bytes(
    file_id: str, mime_type: str, file_name: str = ""
) -> tuple[bytes, str] | None:
    """
    Descarga un archivo de Drive directamente a memoria (sin escribir a disco).

    Args:
        file_id:   ID del archivo en Drive.
        mime_type: MIME type reportado por Drive (ej. 'image/jpeg').
        file_name: Nombre del archivo (opcional).

    Returns:
        Tupla (bytes_del_archivo, mime_type_efectivo) o None si falla.
    """
    token = _get_access_token()
    if not token:
        log.error("No se pudo obtener access token para descargar %s", file_id)
        return None

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if (
            "pdf" in mime_type.lower()
            or file_name.lower().endswith(".pdf")
            or file_name.lower().endswith("-pdf")
        ):
            effective_mime = "application/pdf"
        elif mime_type.startswith("image/"):
            effective_mime = mime_type
        else:
            effective_mime = "image/jpeg"
        log.debug("Descargado en memoria: %s (%d bytes, %s)", file_id, len(data), effective_mime)
        return data, effective_mime
    except Exception as e:
        log.error("Error descargando %s de Drive: %s", file_id, e)
        return None


def _rename_drive_file(file_id: str, new_name: str) -> bool:
    """
    Renombra un archivo en Google Drive (REST API PATCH).

    Args:
        file_id:  ID del archivo en Drive.
        new_name: Nuevo nombre del archivo.

    Returns:
        True si el renombrado fue exitoso.
    """
    token = _get_access_token()
    if not token:
        return False

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    body = json.dumps({"name": new_name}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()

        # Limpiar caché para que la UI refleje el nuevo nombre inmediatamente
        try:
            from services.drive_doc import list_drive_files

            if hasattr(list_drive_files, "cache"):
                list_drive_files.cache.clear()
        except Exception as e:
            log.warning("No se pudo limpiar la caché de list_drive_files: %s", e)

        return True
    except Exception as e:
        log.error("Error renombrando %s en Drive: %s", file_id, e)
        return False


def _build_drive_name(fecha_iso: str, importe: float) -> str:
    """
    Genera el nuevo nombre del archivo en Drive.

    Formato:
      - Con fecha detectada:  YYYYMMDD - 33.47€
      - Sin fecha legible:    SINfecha - 33.47€
    """
    if fecha_iso and fecha_iso != "N/A" and len(fecha_iso) == 10:
        date_part = fecha_iso.replace("-", "")  # YYYY-MM-DD → YYYYMMDD
    else:
        date_part = "SINfecha"
    return f"{date_part} - {importe:.2f}\u20ac"


# ──────────────────────────────────────────────
# Gemini AI — Extracción Estructurada
# ──────────────────────────────────────────────


class TicketData(BaseModel):
    """Datos estructurados extraídos de un ticket/factura."""

    importe: float = Field(description="Importe TOTAL en euros (numérico, sin símbolo €)")
    supermercado: str = Field(
        description="Nombre del establecimiento (ej. Mercadona, Burger King). IMPORTANTE: Si es Mercadona (incluso 'MERCADONA S.A.'), usa exactamente 'Mercadona'."
    )
    fecha: str = Field(description="Fecha de la transacción en formato ISO YYYY-MM-DD")
    factura: str = Field(description="Número de ticket o factura. 'N/A' si no es legible.")
    efectivo: bool = Field(
        default=False,
        description=(
            "True SOLO si el ticket indica claramente pago en EFECTIVO/metálico "
            "(p.ej. 'EFECTIVO', 'CONTADO', 'CAMBIO', 'ENTREGADO', 'DEVUELTO'). "
            "False si se pagó con tarjeta (VISA, Mastercard, contactless, 'TARJETA') "
            "o si no se puede determinar."
        ),
    )


_GEMINI_PROMPT = """
Analiza este ticket o factura de compra y extrae los siguientes datos:

- importe: El importe TOTAL a pagar en euros (número, sin símbolo €). Usa el total, no subtotales.
- supermercado: Nombre legible del establecimiento. IMPORTANTE: Si es de Mercadona (independientemente de que ponga "MERCADONA S.A.", "MERCADONA", etc.), debes devolver SIEMPRE exactamente "Mercadona" (con la M inicial en mayúscula y el resto en minúsculas). Para el resto, usa el nombre comercial (ej. Burger King, Primaprix).
- fecha: La fecha de compra en formato ISO YYYY-MM-DD. IMPORTANTE: En España los tickets usan formato DD/MM/YY o DD/MM/YYYY. Por ejemplo, "07/08/26" significa 7 de agosto de 2026 (2026-08-07), NO el año 2007. Si el año es de 2 dígitos (ej. 26), corresponde al siglo XXI (2026).
- factura: El número de ticket, factura o ID de transacción. Pon "N/A" si no es legible.
- efectivo: true SOLO si el ticket indica pago en EFECTIVO/metálico (busca "EFECTIVO",
  "CONTADO", "CAMBIO", "ENTREGADO", "DEVUELTO", "Importe entregado/recibido"). Si se pagó
  con tarjeta ("TARJETA", "VISA", "Mastercard", "Contactless", "Tarj.") o no estás seguro,
  devuelve false.
"""


# Códigos HTTP transitorios: el modelo está saturado o sin cuota → reintentar
# o pasar al siguiente modelo de la cadena (NO es un problema del ticket).
_TRANSIENT_API_CODES = {429, 500, 503}


def _extract_with_gemini(file_bytes: bytes, mime_type: str) -> TicketData | None:
    """
    Envía un archivo (imagen o PDF) a Gemini AI y extrae los datos del ticket.

    Prueba la cadena GEMINI_VISION_MODELS en orden: si un modelo está saturado
    (503) o sin cuota (429), pasa al siguiente (tienen pools de capacidad
    distintos). Así un pico de demanda en un modelo no bloquea el procesado.

    Usa response_schema con Pydantic para garantizar JSON tipado. Retorna None
    solo si TODOS los modelos fallan o ninguno puede leer el ticket (entonces el
    archivo se omite para gestión manual).

    Args:
        file_bytes: Contenido binario del archivo (imagen o PDF).
        mime_type:  MIME type ('image/jpeg', 'application/pdf', etc.).
    """
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY no configurada. Imposible procesar con IA.")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        image_part = genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
    except Exception as e:
        log.error("Error inicializando cliente Gemini: %s", e)
        return None

    last_error: Exception | None = None
    for model in GEMINI_VISION_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[image_part, _GEMINI_PROMPT],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": TicketData,
                },
            )
        except genai_errors.APIError as e:
            last_error = e
            code = getattr(e, "code", None)
            if code in _TRANSIENT_API_CODES:
                log.warning("Modelo '%s' no disponible (code=%s). Probando siguiente…", model, code)
                time.sleep(1.0)  # breve respiro antes del siguiente modelo
            else:
                log.warning("Error de API con '%s': %s. Probando siguiente…", model, e)
            continue
        except Exception as e:
            last_error = e
            log.warning("Fallo inesperado con '%s': %s. Probando siguiente…", model, e)
            continue

        if response.parsed:
            result: TicketData = response.parsed
            log.info(
                "Gemini[%s]: importe=%.2f | supermercado=%s | fecha=%s | factura=%s",
                model,
                result.importe,
                result.supermercado,
                result.fecha,
                result.factura,
            )
            return result

        log.warning("Gemini[%s] no devolvió datos parseados. Probando siguiente…", model)

    log.error("Todos los modelos Gemini fallaron. Último error: %s", last_error)
    return None


# ──────────────────────────────────────────────
# Orquestación Principal
# ──────────────────────────────────────────────


def process_and_update_sheet() -> list[dict]:
    """
    Procesa todos los archivos de imagen nuevos en la carpeta de Drive de Bokatas.

    Para cada imagen nueva (no presente en el Sheet por su File ID):
      1. Descarga los bytes en memoria desde Drive.
      2. Envía a Gemini AI para extracción estructurada.
         Si Gemini falla → el archivo se omite (gestión manual).
      3. Renombra el archivo en Drive: YYYYMMDD - importe€
      4. Añade fila al Google Sheet (col F = Drive File ID).

    Returns:
        Lista de dicts con los resultados de cada archivo procesado:
        [{"original": str, "renamed": str, "data": TicketData}, ...]
    """
    files = list_drive_files(BOKATAS_DRIVE_FOLDER_ID)
    if not files:
        log.info("No se encontraron archivos en la carpeta de Drive.")
        return []

    # Filtra: solo imágenes soportadas y que NO estén ya renombradas
    from services.extraction import _ALREADY_RENAMED, _SUPPORTED_EXTS

    files = [
        f
        for f in files
        if (
            any(f["name"].lower().endswith(ext) for ext in _SUPPORTED_EXTS)
            or "image" in f.get("mimeType", "").lower()
            or "pdf" in f.get("mimeType", "").lower()
            or f["name"].lower().endswith("-pdf")
        )
        and not _ALREADY_RENAMED.match(f["name"])
    ]

    gspread_client = _get_gspread_client()
    sheet = gspread_client.open_by_url(BOKATAS_VERSION_SHEET_URL).sheet1

    # Anti-duplicados: Drive File ID en columna F (no cambia al renombrar)
    existing_ids: set[str] = set(filter(None, sheet.col_values(6)))
    log.info("Archivos ya procesados en Sheet: %d", len(existing_ids))

    new_rows: list[list] = []
    results: list[dict] = []

    for f in files:
        file_id: str = f["id"]
        file_name: str = f["name"]
        mime_type: str = f.get("mimeType", "")

        # Saltar si ya procesado
        if file_id in existing_ids:
            log.debug("Ya procesado, saltando: %s", file_name)
            continue

        # Soportar imágenes y PDFs
        is_supported = (
            any(file_name.lower().endswith(ext) for ext in _SUPPORTED_EXTS)
            or "image" in mime_type.lower()
            or "pdf" in mime_type.lower()
            or file_name.lower().endswith("-pdf")
        )
        if not is_supported:
            log.debug("No es archivo soportado, saltando: %s", file_name)
            continue

        log.info("Procesando: %s (ID: %s)", file_name, file_id)

        # 1. Descargar bytes en memoria
        result = _get_drive_image_bytes(file_id, mime_type, file_name)
        if result is None:
            log.warning("No se pudo descargar %s — omitido.", file_name)
            results.append(
                {"original": file_name, "renamed": None, "error": "No se pudo descargar de Drive"}
            )
            continue
        image_bytes, effective_mime = result

        # 2. Extraer datos con Gemini AI
        ticket = _extract_with_gemini(image_bytes, effective_mime)
        if ticket is None:
            log.warning("Gemini no pudo procesar '%s' — omitido para gestion manual.", file_name)
            results.append(
                {
                    "original": file_name,
                    "renamed": None,
                    "error": "Gemini no disponible o ticket ilegible",
                }
            )
            continue

        # 3. Renombrar en Drive
        new_drive_name = _build_drive_name(ticket.fecha, ticket.importe)
        renamed = _rename_drive_file(file_id, new_drive_name)
        if renamed:
            log.info("Drive renombrado: '%s' → '%s'", file_name, new_drive_name)
            results.append({"original": file_name, "renamed": new_drive_name, "data": ticket})
        else:
            log.warning(
                "No se pudo renombrar '%s' en Drive (datos guardados igualmente).", file_name
            )
            results.append(
                {"original": file_name, "renamed": None, "error": "Fallo al renombrar en Drive"}
            )

        # 4. Preparar fila para el Sheet
        importe_sheet = f"{ticket.importe:.2f}".replace(".", ",")  # Formato europeo
        new_rows.append(
            [
                "Compra para la ruta",  # A: Concepto (fijo por política ONG)
                importe_sheet,  # B: Importe
                ticket.supermercado,  # C: Supermercado
                ticket.fecha,  # D: Fecha (ISO YYYY-MM-DD)
                ticket.factura,  # E: Nº Factura
                file_id,  # F: Drive File ID (anti-duplicado)
            ]
        )

    if new_rows:
        sheet.append_rows(new_rows)
        log.info("Nuevas filas anadidas al Google Sheet: %d", len(new_rows))
    else:
        log.info("No hay imagenes nuevas para procesar.")

    return results


def retry_failed_renames() -> list[dict]:
    """
    Intenta renombrar en Drive los archivos que ya están en el Sheet
    pero cuyo nombre en Drive sigue sin estar en el formato correcto.
    """
    files = list_drive_files(BOKATAS_DRIVE_FOLDER_ID)
    if not files:
        return []

    from services.extraction import _ALREADY_RENAMED

    unrenamed_files = [f for f in files if not _ALREADY_RENAMED.match(f["name"])]
    if not unrenamed_files:
        return []

    gspread_client = _get_gspread_client()
    sheet = gspread_client.open_by_url(BOKATAS_VERSION_SHEET_URL).sheet1
    all_rows = sheet.get_all_values()

    # Mapa Drive File ID -> (Fecha, Importe)
    file_info = {}
    for row in all_rows:
        if len(row) >= 6:
            fid = row[5]
            if fid and fid != "ID Drive":  # Ignorar cabecera
                try:
                    fecha = row[3]
                    importe_str = row[1]
                    importe_str = importe_str.replace("€", "").replace("$", "").replace(" ", "")
                    if "," in importe_str and "." in importe_str:
                        importe_str = importe_str.replace(".", "").replace(",", ".")
                    elif "," in importe_str:
                        importe_str = importe_str.replace(",", ".")
                    importe = float(importe_str)
                    file_info[fid] = (fecha, importe)
                except Exception:
                    pass

    results = []
    for f in unrenamed_files:
        file_id = f["id"]
        file_name = f["name"]

        if file_id in file_info:
            fecha, importe = file_info[file_id]
            new_drive_name = _build_drive_name(fecha, importe)
            renamed = _rename_drive_file(file_id, new_drive_name)
            if renamed:
                log.info("Drive renombrado (retry): '%s' → '%s'", file_name, new_drive_name)
                results.append({"original": file_name, "renamed": new_drive_name, "data": None})
            else:
                log.warning("Sigue fallando el renombrado de '%s' en Drive.", file_name)
                results.append(
                    {"original": file_name, "renamed": None, "error": "Fallo al renombrar en Drive"}
                )

    return results


# ══════════════════════════════════════════════
# Padres (Cuenta 131) — Archivos Locales
# ══════════════════════════════════════════════

# Extensiones aceptadas para procesamiento
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
_PDF_EXTS = {".pdf"}
_SUPPORTED_EXTS = _IMAGE_EXTS | _PDF_EXTS

# Patrón: archivo que ya comienza con YYYYMMDD o SINfecha seguido de espacio o guion bajo
_ALREADY_RENAMED = re.compile(r"^(?:\d{8}|SINfecha)[\s_]+\S+.*\d")

# Archivos a ignorar
_IGNORE_FILES = {"desktop.ini", "thumbs.db", ".ds_store"}


def _is_already_renamed(filename: str) -> bool:
    """Devuelve True si el nombre ya sigue el formato YYYYMMDD CONCEPTO COSTE."""
    return bool(_ALREADY_RENAMED.match(filename))


def _build_padres_name(fecha_iso: str, supermercado: str, importe: float, ext: str) -> str:
    """
    Genera el nombre del archivo en formato Padres.

    Formato: YYYYMMDD SUPERMERCADO COSTE €.ext
    Ejemplo: 20260323 Mercadona 26,52 €.pdf
    """
    if fecha_iso and fecha_iso != "N/A" and len(fecha_iso) == 10:
        date_part = fecha_iso.replace("-", "")
    else:
        date_part = "SINfecha"

    # Limpiar nombre del supermercado: quitar caracteres problemáticos para el FS
    store = re.sub(r'[<>:"/\\|?*]', "", supermercado).strip()

    # Formatear importe con coma decimal (estilo europeo)
    importe_str = f"{importe:,.2f}".replace(",", "X").replace(".", ",").replace("X", "")
    # Si no tiene decimales significativos distintos de 00, simplificar
    # Mantener siempre 2 decimales para consistencia

    return f"{date_part} {store} {importe_str} €{ext}"


def _get_mime_type(ext: str) -> str:
    """Infiere el MIME type a partir de la extensión normalizada."""
    if ext in _PDF_EXTS:
        return "application/pdf"
    if ext in _IMAGE_EXTS:
        mime, _ = mimetypes.guess_type(f"file{ext}")
        return mime or "image/jpeg"
    # Sin extensión o extensión desconocida → asumir imagen JPEG
    return "image/jpeg"


def process_padres_folder() -> list[dict]:
    """
    Procesa archivos de la carpeta Padres con Gemini AI y los renombra.

    Para cada archivo (imagen o PDF) que no esté ya renombrado:
      1. Lee los bytes del archivo local.
      2. Envía a Gemini AI para extracción: supermercado, importe, fecha.
      3. Renombra el archivo: YYYYMMDD SUPERMERCADO COSTE €.ext

    Returns:
        Lista de dicts con los resultados de cada archivo procesado:
        [{"original": str, "renamed": str, "data": TicketData}, ...]
    """
    _padres_path = next((p for p in POSSIBLE_PADRES_FOLDERS if Path(p).is_dir()), PADRES_FOLDER)
    folder = Path(_padres_path)
    if not folder.exists():
        log.error("Carpeta Padres no encontrada en ninguna ruta: %s", POSSIBLE_PADRES_FOLDERS)
        return []

    results: list[dict] = []

    for file_path in sorted(folder.iterdir()):
        if not file_path.is_file():
            continue

        filename = file_path.name
        if filename.lower() in _IGNORE_FILES:
            continue

        raw_suffix = file_path.suffix.lower()
        # Si el "suffix" contiene espacios, no es una extensión real
        # (ej. "Primaprix 3.80€ 20260324" → suffix=".80€ 20260324")
        ext = raw_suffix if " " not in raw_suffix else ""

        # Si tiene extensión conocida, usarla; si no tiene, intentar como imagen
        if ext not in _SUPPORTED_EXTS and ext != "":
            log.debug("Extensión no soportada, saltando: %s", filename)
            continue

        # Detectar si ya está renombrado
        if _is_already_renamed(filename):
            log.debug("Ya renombrado, saltando: %s", filename)
            continue

        log.info("Procesando (Padres): %s", filename)

        # 1. Leer bytes del archivo local
        try:
            file_bytes = file_path.read_bytes()
        except Exception as e:
            log.error("Error leyendo %s: %s", filename, e)
            continue

        mime_type = _get_mime_type(ext)

        # 2. Extraer datos con Gemini AI
        ticket = _extract_with_gemini(file_bytes, mime_type)
        if ticket is None:
            log.warning("Gemini no pudo procesar '%s' — omitido.", filename)
            results.append(
                {
                    "original": filename,
                    "renamed": None,
                    "error": "Gemini no disponible (modelos saturados) o ticket ilegible",
                }
            )
            continue

        # 3. Renombrar archivo local
        new_name = _build_padres_name(ticket.fecha, ticket.supermercado, ticket.importe, ext)
        new_path = file_path.parent / new_name

        # Evitar sobreescribir un archivo existente
        if new_path.exists() and new_path != file_path:
            # Añadir sufijo numérico
            base = new_path.stem
            i = 2
            while new_path.exists():
                new_path = file_path.parent / f"{base} ({i}){ext}"
                i += 1
            new_name = new_path.name

        try:
            file_path.rename(new_path)
            log.info("Renombrado: '%s' → '%s'", filename, new_name)
            results.append({"original": filename, "renamed": new_name, "data": ticket})
        except Exception as e:
            log.error("Error renombrando '%s': %s", filename, e)
            results.append({"original": filename, "renamed": None, "error": str(e)})

    return results
