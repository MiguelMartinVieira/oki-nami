"""
test_history.py — Pruebas unitarias para services/history.py (sincronización incremental del histórico).
"""

import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from services.history import _clear_historico_storage, update_historico


class TestHistoryService:
    @patch("services.history.get_historico")
    def test_update_historico_already_up_to_date(self, mock_get_historico):
        """Si el histórico ya está actualizado hasta el día de ayer, no hace nada y retorna False."""
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        mock_df = pd.DataFrame(
            [
                {
                    "Fecha": pd.to_datetime(yesterday),
                    "Efectivo Fisico": 100.0,
                    "Efectivo TR": 500.0,
                    "BRK Value": 1000.0,
                    "Vanguard Value": 2000.0,
                    "Te Deben": 50.0,
                    "Total": 3650.0,
                }
            ]
        )
        mock_get_historico.return_value = mock_df

        df_diario = pd.DataFrame()

        # Ejecutar
        updated = update_historico(df_diario, force=False)

        # Comprobar
        assert updated is False

    @patch("services.history._clear_historico_storage")
    @patch("services.history.get_historico")
    def test_update_historico_force_clears_storage(self, mock_get_historico, mock_clear_storage):
        """Con force=True se fuerza la limpieza del histórico y se inicializa."""
        mock_get_historico.return_value = pd.DataFrame()

        df_diario = pd.DataFrame()

        # Ejecutar (esto retornará False si df_diario está vacío, pero verificamos que llame a _clear_historico_storage)
        try:
            update_historico(df_diario, force=True)
        except Exception:
            pass

        assert mock_clear_storage.called

    @patch("services.history.get_historico")
    @patch("services.history.get_yahoo_history")
    @patch("services.history.append_to_historico")
    @patch("services.history.calc_metalico_fisico", return_value=150.0)
    @patch("services.history.calc_tr_cash", return_value=850.0)
    @patch("services.history.calc_brk_shares", return_value=2.0)
    @patch("services.history.calc_vanguard_shares", return_value=10.0)
    @patch("services.history.calc_padres_total", return_value=300.0)
    def test_update_historico_incremental_sync(
        self,
        _mock_padres,
        _mock_vanguard_shares,
        _mock_brk_shares,
        _mock_tr_cash,
        _mock_metalico,
        mock_append,
        mock_yahoo,
        mock_get_historico,
    ):
        """Verifica la sincronización incremental de días pendientes y el cálculo correcto del patrimonio."""
        today = datetime.date.today()
        two_days_ago = today - datetime.timedelta(days=2)
        yesterday = today - datetime.timedelta(days=1)

        # Histórico existente llega hasta hace dos días
        mock_df = pd.DataFrame(
            [
                {
                    "Fecha": pd.to_datetime(two_days_ago),
                    "Efectivo Fisico": 100.0,
                    "Efectivo TR": 500.0,
                    "BRK Value": 1000.0,
                    "Vanguard Value": 2000.0,
                    "Te Deben": 50.0,
                    "Total": 3650.0,
                }
            ]
        )
        mock_get_historico.return_value = mock_df

        # Mock de histórico de Yahoo (Date e Price) para ayer
        # get_price_at busca el último precio <= fecha buscada
        mock_yahoo_history = pd.DataFrame(
            [
                {
                    "Date": pd.to_datetime(yesterday),
                    "Price": 350.0,
                }  # precio genérico para todos los tickers
            ]
        )
        mock_yahoo.return_value = mock_yahoo_history

        # df_diario simulado
        df_diario = pd.DataFrame(
            [
                {
                    "Fecha": pd.to_datetime(yesterday),
                    "Nº Cuenta": "121",
                    "Debe": 100.0,
                    "Haber": 0.0,
                    "Descripción": "Dummy",
                }
            ]
        )

        # Ejecutar
        updated = update_historico(df_diario, force=False)

        assert updated is True
        assert mock_append.called

        # Recuperar filas insertadas
        new_rows = mock_append.call_args[0][0]
        assert len(new_rows) == 1

        row = new_rows[0]
        # Estructura: [d, efectivo_fisico, tr_cash_neto, brk_value_eur, van_value, padres_total, total]
        assert row[0] == yesterday
        assert row[1] == 150.0  # Efectivo Fisico
        assert row[2] == 850.0  # Efectivo TR (neto)

        # BRK Value = 2.0 (shares) * 350 (price_brk_usd) * 350 (eur_usd rate mockeado por el mismo df) = 245000.0
        assert row[3] == 2.0 * 350.0 * 350.0

        # Vanguard Value = 10.0 (shares) * 350 (price_vanguard_proxy) * 1.0 (ratio daily 350 / 350) = 3500.0
        assert row[4] == 10.0 * 350.0

        assert row[5] == 300.0  # Te Deben

        # Total = 150 + 850 + 245000 + 3500 + 300 = 249800.0
        assert row[6] == 150.0 + 850.0 + (2.0 * 350.0 * 350.0) + (10.0 * 350.0) + 300.0

    @patch("services.history._get_gspread_client")
    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    def test_clear_historico_storage(self, mock_remove, mock_exists, mock_gspread):
        """Verifica la limpieza del CSV local de histórico y la recreación de la cabecera en GSheets."""
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_gspread.return_value = mock_client
        mock_client.open_by_url.return_value.worksheet.return_value = mock_sheet

        # Inyectar disponibilidad de GSheets temporalmente
        with (
            patch("data.gsheets.GSHEETS_AVAILABLE", True),
            patch("data.gsheets.CREDENTIALS_FILE", "dummy_cred.json"),
        ):
            _clear_historico_storage()

            assert mock_remove.called
            assert mock_sheet.clear.called
            assert mock_sheet.update.called
