"""Tests para services/auditor.py — parsing de ficheros y matching de tickets."""

import datetime

import pytest

from services.auditor import (
    _extract_amount_from_filename,
    _extract_date_from_filename,
    _extract_store_from_filename,
)


class TestAuditorParsing:
    def test_extract_amount_standard(self):
        assert _extract_amount_from_filename("20260315 - Lidl - 15,50.jpg") == 15.50
        assert _extract_amount_from_filename("Ticket 5.25€ - 01022026.pdf") == 5.25
        assert _extract_amount_from_filename("100_Amazon_compra.png") == 100.0

    def test_extract_amount_complex(self):
        # El parser debe ignorar la fecha 20260315 y pillar el 15.50
        assert _extract_amount_from_filename("20260315_Lidl_15.50") == 15.50
        assert _extract_amount_from_filename("Compra 99 20260101") == 99.0

    def test_extract_date_formats(self):
        # DDMMYYYY al final
        assert _extract_date_from_filename("Ticket 15032026.pdf") == datetime.date(2026, 3, 15)
        # YYYYMMDD prefijo
        assert _extract_date_from_filename("20260401 - Gasolinera.jpg") == datetime.date(2026, 4, 1)
        # DDMMYY prefijo (fotos de Drive)
        assert _extract_date_from_filename("050326_ticket.jpg") == datetime.date(2026, 3, 5)

    def test_extract_store_name(self):
        assert _extract_store_from_filename("20260315 - Mercadona - 12.50.jpg") == "Mercadona"
        assert _extract_store_from_filename("Ticket_Amazon_Prime_9.99") == "Amazon Prime"
        assert _extract_store_from_filename("050326_Lidl_Compra") == "Lidl Compra"

    def test_extract_store_garbage(self):
        assert _extract_store_from_filename("20260315_12,50.pdf") == "Establecimiento Desconocido"


class TestAuditorMatchingLogic:
    # Estos tests requerirían mockear el sistema de archivos o usar archivos temporales
    # Se omiten por simplicidad en este script o se pueden añadir con pyfakefs
    pass
