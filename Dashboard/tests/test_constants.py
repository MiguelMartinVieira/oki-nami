"""Tests para constants.py — integridad de la configuración."""

import constants


def test_essential_constants_exist():
    # Cuentas
    assert hasattr(constants, "CUENTA_TR")
    assert hasattr(constants, "CUENTA_BERKSHIRE")
    assert hasattr(constants, "CUENTA_SP500")
    assert hasattr(constants, "CUENTA_BOKATAS")
    assert hasattr(constants, "CUENTA_PADRES")

    # Tickers
    assert hasattr(constants, "TICKER_BRK")
    assert hasattr(constants, "TICKER_VANGUARD")
    assert hasattr(constants, "TICKER_EURUSD")

    # Fechas
    assert hasattr(constants, "HISTORY_START_DATE")
    assert hasattr(constants, "BRK_CHECKPOINT_DATE")


def test_sheet_url_is_optional_and_valid_when_set():
    # Sin .env queda vacío (la app cae a CSV / DEMO_MODE); si está, debe ser de Sheets.
    assert constants.SHEET_URL == "" or constants.SHEET_URL.startswith(
        "https://docs.google.com/spreadsheets"
    )


def test_base_shares():
    assert isinstance(constants.BASE_ACCIONES_BRK, (int, float))
    assert constants.BASE_ACCIONES_BRK >= 0
