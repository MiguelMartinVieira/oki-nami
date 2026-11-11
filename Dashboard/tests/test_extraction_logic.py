"""Tests para services/extraction.py — lógica de renombrado y validación."""

import pytest

from services.extraction import (
    _build_drive_name,
    _build_padres_name,
    _get_mime_type,
    _is_already_renamed,
)


class TestExtractionLogic:
    def test_build_drive_name(self):
        # Caso con fecha válida
        assert _build_drive_name("2026-03-24", 15.50) == "20260324 - 15.50€"
        # Caso sin fecha
        assert _build_drive_name("N/A", 10.00) == "SINfecha - 10.00€"
        assert _build_drive_name("", 5.25) == "SINfecha - 5.25€"

    def test_build_padres_name(self):
        # Formato: YYYYMMDD SUPERMERCADO COSTE €.ext
        name = _build_padres_name("2026-03-24", "Mercadona", 26.52, ".pdf")
        assert name == "20260324 Mercadona 26,52 €.pdf"

        # Con caracteres raros en el nombre del super
        name = _build_padres_name("2026-03-24", "Burger/King*", 12.00, ".jpg")
        assert "BurgerKing" in name
        assert "/" not in name
        assert "*" not in name
        assert "12,00 €" in name

    def test_is_already_renamed(self):
        assert _is_already_renamed("20260323 Mercadona 26,52 €.pdf") is True
        assert _is_already_renamed("20260323_Mercadona_26.52.jpg") is True
        assert _is_already_renamed("Mercadona_20260323.pdf") is False
        assert _is_already_renamed("IMG_20260101.jpg") is False
        assert _is_already_renamed("SINfecha - 15.50.jpg") is True  # Ahora es True (Drive)

    def test_get_mime_type(self):
        assert _get_mime_type(".pdf") == "application/pdf"
        assert _get_mime_type(".jpg") == "image/jpeg"
        assert _get_mime_type(".png") == "image/png"
        assert _get_mime_type("") == "image/jpeg"  # Default
