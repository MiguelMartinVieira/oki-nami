"""
test_utils.py — Tests para `services/utils.py`.

`extract_quantity` es el helper canónico de extracción de cantidad
desde la columna Descripción. Antes existían 3 variantes locales
(analytics.py, charts/line.py) — todas consolidadas en este utility.
"""

from services.utils import extract_quantity


class TestExtractQuantity:
    def test_decimal_with_dot(self):
        assert extract_quantity("Compra BRK quantity: 0.123456") == 0.123456

    def test_decimal_with_comma(self):
        # Formato europeo: la coma se normaliza a punto
        assert extract_quantity("Aporte Vanguard quantity: 1,5") == 1.5

    def test_integer(self):
        assert extract_quantity("quantity: 12") == 12.0

    def test_uppercase(self):
        # La regex es case-insensitive
        assert extract_quantity("Saveback QUANTITY: 0.01") == 0.01

    def test_with_extra_spaces(self):
        assert extract_quantity("Compra  quantity:   3.7  extra texto") == 3.7

    def test_no_match_returns_zero(self):
        assert extract_quantity("Sin metadata cantidad") == 0.0

    def test_empty_string(self):
        assert extract_quantity("") == 0.0

    def test_none(self):
        assert extract_quantity(None) == 0.0  # type: ignore[arg-type]

    def test_non_string(self):
        assert extract_quantity(12345) == 0.0  # type: ignore[arg-type]

    def test_malformed_number_falls_back_to_zero(self):
        # La regex captura algo, pero el cast falla → 0.0 (log warning)
        # Formato 1.2.3 → la regex captura "1.2.3", float() falla
        assert extract_quantity("quantity: 1.2.3") == 0.0

    def test_negative_quantity(self):
        assert extract_quantity("quantity: -2.5") == -2.5


from services.utils import extract_signed_quantity


class TestExtractSignedQuantity:
    def test_normal_purchase(self):
        row = {
            "Debe": 100.0,
            "Haber": 0.0,
            "Categoría": "Compra BRK",
            "Descripción": "quantity: 0.25",
        }
        assert extract_signed_quantity(row) == 0.25

    def test_sale_via_haber(self):
        row = {
            "Debe": 0.0,
            "Haber": 1399.0,
            "Categoría": "Venta Berkshire",
            "Descripción": "quantity: 3.111111",
        }
        assert extract_signed_quantity(row) == -3.111111

    def test_sale_via_keyword_even_if_haber_zero(self):
        row = {
            "Debe": 0.0,
            "Haber": 0.0,
            "Categoría": "Reembolso Participaciones",
            "Descripción": "quantity: 1.5",
        }
        assert extract_signed_quantity(row) == -1.5

    def test_row_with_no_quantity(self):
        row = {"Debe": 0.0, "Haber": 1.0, "Categoría": "Comisiones Venta", "Descripción": ""}
        assert extract_signed_quantity(row) == 0.0

    def test_empty_or_none(self):
        assert extract_signed_quantity(None) == 0.0
        assert extract_signed_quantity({}) == 0.0


from services.utils import clean_cat_name


class TestCleanCatName:
    def test_valid_category(self):
        assert clean_cat_name("Gastos Comida") == "Gastos Comida"

    def test_numeric_zero_or_string_zero(self):
        assert clean_cat_name("0") == "Sin Categorizar"
        assert clean_cat_name(0) == "Sin Categorizar"
        assert clean_cat_name("0.0") == "Sin Categorizar"
        assert clean_cat_name("0.00") == "Sin Categorizar"

    def test_na_and_vlookup_errors(self):
        assert clean_cat_name("#N/A") == "Sin Categorizar"
        assert clean_cat_name("#N/A (Did not find value '45' in VLOOKUP)") == "Cuenta 45"

    def test_none_and_empty(self):
        assert clean_cat_name(None) == "Sin Categorizar"
        assert clean_cat_name("") == "Sin Categorizar"
        assert clean_cat_name("   ") == "Sin Categorizar"
