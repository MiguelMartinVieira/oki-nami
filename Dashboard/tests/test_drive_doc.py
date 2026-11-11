"""Tests para services/drive_doc.py — parseo del Google Doc de pagos sin ticket."""

import datetime

import pytest

from services.drive_doc import _parse_amount, parse_doc_entries


class TestParseAmount:
    def test_european_comma(self):
        assert _parse_amount("26,52") == pytest.approx(26.52)

    def test_decimal_point(self):
        assert _parse_amount("3.80") == pytest.approx(3.80)

    def test_integer(self):
        assert _parse_amount("10") == pytest.approx(10.0)

    def test_thousands(self):
        assert _parse_amount("1.234,56") == pytest.approx(1234.56)

    def test_invalid(self):
        assert _parse_amount("abc") is None


class TestParseDocEntries:
    def test_formato_fecha_primero(self):
        text = "24/03/2026 - Mercadona - 26,52€"
        entries = parse_doc_entries(text)
        assert len(entries) == 1
        assert entries[0]["date"] == datetime.date(2026, 3, 24)
        assert entries[0]["store"] == "Mercadona"
        assert entries[0]["amount"] == pytest.approx(26.52)
        assert entries[0]["raw"] == "24/03/2026 - Mercadona - 26,52€"

    def test_formato_tienda_primero(self):
        text = "Primaprix 3.80€ - 25/03/2026"
        entries = parse_doc_entries(text)
        assert len(entries) == 1
        assert entries[0]["date"] == datetime.date(2026, 3, 25)
        assert entries[0]["store"] == "Primaprix"
        assert entries[0]["amount"] == pytest.approx(3.80)

    def test_multiple_entries(self):
        text = (
            "24/03/2026 - Mercadona - 26,52€\n"
            "Primaprix 3.80€ - 25/03/2026\n"
            "25/03/2026 - Primaprix - 8,45€\n"
        )
        entries = parse_doc_entries(text)
        assert len(entries) == 3

    def test_empty_lines_ignored(self):
        text = "\n\n24/03/2026 - Mercadona - 26,52€\n\n"
        entries = parse_doc_entries(text)
        assert len(entries) == 1

    def test_empty_text(self):
        assert parse_doc_entries("") == []

    def test_unparseable_line_ignored(self):
        text = "esto no tiene formato valido\n24/03/2026 - Mercadona - 26,52€"
        entries = parse_doc_entries(text)
        assert len(entries) == 1

    def test_dash_separator_variants(self):
        """Acepta tanto guion normal como guion largo (–)."""
        text = "24/03/2026 – Mercadona – 26,52€"
        entries = parse_doc_entries(text)
        assert len(entries) == 1
        assert entries[0]["amount"] == pytest.approx(26.52)

    def test_amount_without_euro_symbol(self):
        text = "24/03/2026 - Mercadona - 26,52"
        entries = parse_doc_entries(text)
        assert len(entries) == 1
        assert entries[0]["amount"] == pytest.approx(26.52)

    def test_store_with_spaces(self):
        text = "24/03/2026 - El Corte Inglés - 15,00€"
        entries = parse_doc_entries(text)
        assert len(entries) == 1
        assert entries[0]["store"] == "El Corte Inglés"
