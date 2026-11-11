"""
drive_doc.py — Gestión del Google Doc "Pagos Sin Ticket" (cuenta 131).

Flujo:
  1. Descarga el doc como texto plano (Drive API export)
  2. Parsea las líneas en entradas {date, store, amount, raw}
  3. Tras el matching, elimina las líneas justificadas y re-sube el doc (Docs API batchUpdate)

Formatos de entrada soportados:
  - DD/MM/YYYY - Tienda - XX,XX€
  - Tienda XX,XX€ - DD/MM/YYYY
"""

import datetime
import json
import logging
import re
import urllib.request

from constants import CREDENTIALS_FILE

log = logging.getLogger(__name__)

try:
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2.service_account import Credentials

    _OAUTH_AVAILABLE = True
except ImportError:
    _OAUTH_AVAILABLE = False


# ──────────────────────────────────────────────
# Autenticación
# ──────────────────────────────────────────────

_DRIVE_DOC_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def _get_access_token() -> str | None:
    """Obtiene un access token del service account con scopes de Drive + Docs."""
    if not _OAUTH_AVAILABLE:
        log.warning("google-auth no está instalado")
        return None
    try:
        import os

        if not os.path.exists(CREDENTIALS_FILE):
            log.warning("credentials.json no encontrado en: %s", CREDENTIALS_FILE)
            return None
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=_DRIVE_DOC_SCOPES)
        creds.refresh(GoogleAuthRequest())
        return creds.token
    except Exception as e:
        log.warning("No se pudo obtener access token: %s", e)
        return None


# ──────────────────────────────────────────────
# Lectura del doc
# ──────────────────────────────────────────────


def download_doc_as_text(doc_id: str) -> str | None:
    """
    Descarga el contenido de un Google Doc como texto plano.

    Retorna None si el doc no es accesible o hay error.
    IMPORTANTE: el service account debe tener acceso de Editor al doc.
    """
    token = _get_access_token()
    if not token:
        return None

    url = f"https://www.googleapis.com/drive/v3/files/{doc_id}/export?mimeType=text/plain"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        log.warning("Error descargando Google Doc %s: %s", doc_id, e)
        return None


# ──────────────────────────────────────────────
# Listado de Archivos en Carpeta Drive
# ──────────────────────────────────────────────

from cachetools import TTLCache, cached


@cached(cache=TTLCache(maxsize=128, ttl=3600))
def list_drive_files(folder_id: str) -> list[dict]:
    """
    Lista archivos dentro de una carpeta de Google Drive.
    Solo archivos que NO están en la papelera.

    Retorna lista de {id, name, mimeType, createdTime}
    """
    if not folder_id:
        return []
    token = _get_access_token()
    if not token:
        return []

    query = f"'{folder_id}'+in+parents+and+trashed=false"
    fields = "files(id,name,mimeType,createdTime)"
    url = f"https://www.googleapis.com/drive/v3/files?q={query}&fields={fields}"

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("files", [])
    except Exception as e:
        log.warning("Error listando archivos de carpeta Drive %s: %s", folder_id, e)
        return []


# ──────────────────────────────────────────────
# Parseo de entradas
# ──────────────────────────────────────────────


def parse_doc_entries(text: str) -> list[dict]:
    """
    Parsea el texto del doc y devuelve lista de entradas.

    Formatos soportados:
      - DD/MM/YYYY - Tienda - XX,XX€
      - Tienda XX,XX€ - DD/MM/YYYY
      - YYYYMMDD Tienda XX,XX €   (mismo estilo que el renombrado de tickets)

    Retorna lista de dicts: {date, store, amount, raw}
    """
    entries = []
    for line in text.splitlines():
        # .strip() + quitar BOM (el export a texto suele empezar con ﻿)
        line = line.strip().lstrip("﻿").strip()
        if not line:
            continue

        # Formato 1: DD/MM/YYYY - Tienda - XX,XX€
        m = re.match(
            r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(.+?)\s*[-–]\s*([\d.,]+)\s*€?",
            line,
            re.IGNORECASE,
        )
        if m:
            try:
                date = datetime.datetime.strptime(m.group(1), "%d/%m/%Y").date()
                store = m.group(2).strip()
                amount = _parse_amount(m.group(3))
                if amount is not None:
                    entries.append({"date": date, "store": store, "amount": amount, "raw": line})
                    continue
            except (ValueError, Exception):
                pass

        # Formato 2: Tienda XX,XX€ - DD/MM/YYYY
        m = re.match(
            r"(.+?)\s+([\d.,]+)\s*€\s*[-–]\s*(\d{2}/\d{2}/\d{4})",
            line,
            re.IGNORECASE,
        )
        if m:
            try:
                store = m.group(1).strip()
                amount = _parse_amount(m.group(2))
                date = datetime.datetime.strptime(m.group(3), "%d/%m/%Y").date()
                if amount is not None:
                    entries.append({"date": date, "store": store, "amount": amount, "raw": line})
                    continue
            except (ValueError, Exception):
                pass

        # Formato 3: YYYYMMDD Tienda XX,XX €  (igual que el renombrado de tickets)
        m = re.match(r"(\d{8})\s+(.+?)\s+([\d.,]+)\s*€?$", line)
        if m:
            try:
                date = datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
                store = m.group(2).strip()
                amount = _parse_amount(m.group(3))
                if amount is not None:
                    entries.append({"date": date, "store": store, "amount": amount, "raw": line})
                    continue
            except (ValueError, Exception):
                pass

        log.debug("Línea del doc sin parsear: %r", line)

    return entries


def _parse_amount(raw: str) -> float | None:
    """Convierte '26,52' o '26.52' o '3.80' a float."""
    try:
        cleaned = raw.strip()
        # Formato europeo con punto de miles: 1.234,56
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except ValueError:
        return None


# ──────────────────────────────────────────────
# Escritura del doc
# ──────────────────────────────────────────────


def update_doc_removing_lines(doc_id: str, lines_to_remove: list[str], full_text: str) -> bool:
    """
    Elimina las líneas indicadas del doc y sube el contenido actualizado.

    Hace una sola llamada a la API (batchUpdate) con todo el nuevo contenido,
    independientemente de cuántas líneas se eliminen.

    Args:
        doc_id: ID del Google Doc.
        lines_to_remove: Lista de líneas a eliminar (comparación por strip).
        full_text: El texto completo actual del doc (para no descargarlo de nuevo).

    Returns:
        True si la actualización fue exitosa.
    """
    if not lines_to_remove:
        return True

    # Calcular texto resultante
    to_remove_set = {line.strip() for line in lines_to_remove}
    new_lines = [line for line in full_text.splitlines() if line.strip() not in to_remove_set]
    new_text = "\n".join(new_lines).strip()

    token = _get_access_token()
    if not token:
        return False

    try:
        # 1. Obtener el índice final del contenido del doc
        url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            doc = json.loads(resp.read().decode())

        end_index = doc["body"]["content"][-1]["endIndex"] - 1

        # 2. Construir el batchUpdate: borrar todo + insertar nuevo texto
        requests_list = []
        if end_index > 1:
            requests_list.append(
                {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index}}}
            )
        if new_text:
            requests_list.append(
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": new_text,
                    }
                }
            )

        if not requests_list:
            return True

        # 3. Enviar
        body = json.dumps({"requests": requests_list}).encode()
        url = f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate"
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()

        log.info("Doc actualizado: %d línea(s) eliminada(s)", len(lines_to_remove))
        return True

    except Exception as e:
        log.error("Error actualizando Google Doc %s: %s", doc_id, e)
        return False
