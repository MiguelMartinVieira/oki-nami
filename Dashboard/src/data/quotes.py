"""
quotes.py — Carga de citas motivacionales desde un Google Doc.

Lee el documento de texto plano exportado desde Google Docs,
parsea líneas con formato `N. "texto" - Autor` y devuelve una lista.
"""

import html as html_mod
import logging
import random
import re

import streamlit as st

log = logging.getLogger(__name__)


# Regex: captura opcional "N. " al inicio, luego el texto entre comillas, luego " - Autor"
# Soporta: comillas rectas "", tipográficas \u201c\u201d, angulares \u00ab\u00bb, o sin comillas
_NUM_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)*\.\s*")
_QUOTE_AUTHOR_RE = re.compile(
    r'^["\u201c\u201d\u00ab\u00bb](.+?)["\u201c\u201d\u00ab\u00bb]\s*[-\u2013\u2014]\s*(.+)$'
)
_QUOTE_ONLY_RE = re.compile(r'^["\u201c\u201d\u00ab\u00bb](.+?)["\u201c\u201d\u00ab\u00bb]\s*$')

# Fallback quotes
_FALLBACK = [
    {
        "quote": "The best time to plant a tree was 20 years ago. The second best time is now.",
        "author": "Proverbio chino",
    },
    {"quote": "Compound interest is the eighth wonder of the world.", "author": "Albert Einstein"},
    {
        "quote": "Do not save what is left after spending, but spend what is left after saving.",
        "author": "Warren Buffett",
    },
]


def _parse_line(line: str) -> dict | None:
    """Parsea una línea del Google Doc a {quote, author}."""
    line = line.replace("\ufeff", "").strip()
    if not line or len(line) < 5:
        return None

    # Quitar prefijo numérico: "8. " o "297. "
    line = _NUM_PREFIX_RE.sub("", line).strip()
    if not line:
        return None

    # Intentar: "texto" - Autor
    m = _QUOTE_AUTHOR_RE.match(line)
    if m:
        return {"quote": m.group(1).strip(), "author": m.group(2).strip()}

    # Intentar: "texto" (sin autor)
    m = _QUOTE_ONLY_RE.match(line)
    if m:
        return {"quote": m.group(1).strip(), "author": None}

    # Intentar split por " - " sin comillas
    if " - " in line:
        parts = line.rsplit(" - ", 1)
        quote = parts[0].strip().strip('"\u201c\u201d\u00ab\u00bb')
        author = parts[1].strip() if len(parts) > 1 else None
        if len(quote) > 5:
            return {"quote": quote, "author": author}

    # Línea suelta (sin autor, sin comillas)
    clean = line.strip('"\u201c\u201d\u00ab\u00bb')
    if len(clean) > 10:
        return {"quote": clean, "author": None}

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_quotes() -> list[dict]:
    """Descarga y parsea las citas del Google Doc.

    Returns:
        Lista de {"quote": str, "author": str | None}
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials

        from constants import CREDENTIALS_FILE, QUOTES_DOC_ID

        if not QUOTES_DOC_ID:
            return list(_FALLBACK)

        creds = Credentials.from_service_account_file(
            str(CREDENTIALS_FILE),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        creds.refresh(Request())

        import requests

        url = f"https://docs.google.com/document/d/{QUOTES_DOC_ID}/export?format=txt"
        resp = requests.get(url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=10)
        resp.raise_for_status()

        quotes = []
        for line in resp.text.splitlines():
            parsed = _parse_line(line)
            if parsed:
                quotes.append(parsed)

        if quotes:
            log.info("Quotes cargadas: %d citas desde Google Doc", len(quotes))
            return quotes
    except Exception as e:
        log.warning("Error cargando quotes de Google Doc: %s", e)

    return list(_FALLBACK)


def get_random_quote() -> dict:
    """Devuelve una cita aleatoria."""
    quotes = get_quotes()
    return random.choice(quotes)


def safe_html(text: str) -> str:
    """Escapa texto para insertar de forma segura en HTML."""
    return html_mod.escape(text, quote=True)
