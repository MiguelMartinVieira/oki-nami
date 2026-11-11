"""Tests para _clean_numeric() — la función más crítica del proyecto."""

import pytest

from data.gsheets import _clean_numeric


class TestCleanNumeric:
    """Conversión de formatos numéricos de Google Sheets a float."""

    # ── Valores vacíos / nulos ──
    def test_empty_string(self):
        assert _clean_numeric("") == 0.0

    def test_none(self):
        assert _clean_numeric(None) == 0.0

    def test_dash(self):
        assert _clean_numeric("-") == 0.0

    # ── Formato europeo con coma decimal ──
    def test_european_comma(self):
        assert _clean_numeric("9,38") == pytest.approx(9.38)

    def test_european_comma_large(self):
        assert _clean_numeric("126,50") == pytest.approx(126.50)

    # ── Formato contable con paréntesis (negativos) ──
    def test_parentheses_negative(self):
        assert _clean_numeric("  (419,54)  ") == pytest.approx(-419.54)
        assert _clean_numeric("(1.234,56)") == pytest.approx(-1234.56)

    # ── Formato europeo con punto de miles + coma decimal ──
    def test_european_thousands(self):
        assert _clean_numeric("7.856,69") == pytest.approx(7856.69)

    def test_european_thousands_small(self):
        assert _clean_numeric("1.234,56") == pytest.approx(1234.56)

    # ── Formato sin decimales → /100 (solo si >2 dígitos) ──
    def test_no_decimals_divide_100(self):
        assert _clean_numeric("97064") == pytest.approx(970.64)

    def test_no_decimals_three_digits(self):
        assert _clean_numeric("150") == pytest.approx(1.50)

    # ── Números pequeños sin decimales NO se dividen ──
    def test_small_integer_not_divided(self):
        """'10' debe ser 10.0, no 0.1"""
        assert _clean_numeric("10") == pytest.approx(10.0)

    def test_two_digit_integer(self):
        assert _clean_numeric("50") == pytest.approx(50.0)

    def test_single_digit(self):
        assert _clean_numeric("5") == pytest.approx(5.0)

    def test_zero(self):
        assert _clean_numeric("0") == pytest.approx(0.0)

    # ── Con símbolo de moneda ──
    def test_euro_symbol(self):
        assert _clean_numeric("9,38 €") == pytest.approx(9.38)

    def test_dollar_symbol(self):
        assert _clean_numeric("$100.50") == pytest.approx(100.50)

    # ── Formato americano con punto decimal ──
    def test_american_decimal(self):
        assert _clean_numeric("100.50") == pytest.approx(100.50)

    def test_american_no_cents(self):
        assert _clean_numeric("100.00") == pytest.approx(100.00)

    # ── Espacios ──
    def test_spaces(self):
        assert _clean_numeric("  9,38  ") == pytest.approx(9.38)

    # ── Números ya float / int (passthrough directo sin dividir entre 100) ──
    def test_float_passthrough(self):
        assert _clean_numeric(9.38) == pytest.approx(9.38)

    def test_int_passthrough_small(self):
        assert _clean_numeric(10) == pytest.approx(10.0)

    def test_int_passthrough_large(self):
        assert _clean_numeric(169) == pytest.approx(169.0)
        assert _clean_numeric(150) == pytest.approx(150.0)
        assert _clean_numeric(1000) == pytest.approx(1000.0)

    def test_currency_whole_number_not_divided(self):
        assert _clean_numeric("169 €") == pytest.approx(169.0)
        assert _clean_numeric("150 €") == pytest.approx(150.0)
        assert _clean_numeric("$200") == pytest.approx(200.0)

    # ── Valores no parseables ──
    def test_garbage(self):
        assert _clean_numeric("abc") == 0.0
