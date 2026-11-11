"""Tests para config/theme.py — resolución de colores."""

import pytest

from config.theme import CATEGORY_COLORS_GASTOS, CATEGORY_COLORS_INGRESOS, get_category_color


class TestGetCategoryColor:
    def test_exact_match_gasto(self):
        assert get_category_color("Gastos Comida", True) == CATEGORY_COLORS_GASTOS["Gastos Comida"]

    def test_partial_match_gasto(self):
        # "Comida" debe encontrar "Gastos Comida"
        assert get_category_color("Comida", True) == CATEGORY_COLORS_GASTOS["Gastos Comida"]

    def test_exact_match_ingreso(self):
        assert (
            get_category_color("Ingresos Sueldo", False)
            == CATEGORY_COLORS_INGRESOS["Ingresos Sueldo"]
        )

    def test_fallback_gasto(self):
        # Algo que no matchea ninguna paleta — devuelve el catchall crimson base.
        from config.theme import _GASTOS_CATCHALL_COLOR

        assert get_category_color("Gasto Desconocido", True) == _GASTOS_CATCHALL_COLOR

    def test_fallback_ingreso(self):
        from config.theme import _INGRESOS_CATCHALL_COLOR

        assert get_category_color("Ingreso Raro", False) == _INGRESOS_CATCHALL_COLOR

    def test_case_insensitive(self):
        assert get_category_color("comida", True) == CATEGORY_COLORS_GASTOS["Gastos Comida"]
