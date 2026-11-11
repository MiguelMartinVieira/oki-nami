"""
test_automation.py — Tests para `services/automation.py`.

Cubre la generación de pares de partida doble desde tickets de Padres/bokatas
y el flujo `register_tickets_in_diario` con apend mockeado.
"""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from constants import CUENTA_BOKATAS, CUENTA_PADRES, CUENTA_TR
from services.automation import (
    auto_sync_drive_tickets,
    check_pending_tickets,
    create_journal_rows_for_ticket,
    process_bokatas_tickets,
    process_padres_tickets,
    register_tickets_in_diario,
)


# ─────────────────────────────────────────────────────────
# create_journal_rows_for_ticket
# ─────────────────────────────────────────────────────────
class TestCreateJournalRows:
    def test_returns_two_rows(self):
        ticket = {
            "date": "2026-05-23",
            "amount": 15.50,
            "store": "Mercadona",
            "filename": "ticket1.jpg",
        }
        rows = create_journal_rows_for_ticket(ticket)
        assert len(rows) == 2

    def test_double_entry_balance(self):
        """Debe + Haber del par debe sumar 0 (partida doble)."""
        ticket = {"date": "2026-05-23", "amount": 25.0, "store": "Carrefour", "filename": "x.jpg"}
        row1, row2 = create_journal_rows_for_ticket(ticket)
        # row[4] = Debe, row[5] = Haber (índices según contrato del diario)
        debe1, haber1 = row1[4], row1[5]
        debe2, haber2 = row2[4], row2[5]
        assert debe1 == 25.0 and haber1 is None
        assert haber2 == 25.0 and debe2 is None

    def test_default_accounts(self):
        ticket = {"date": "2026-05-23", "amount": 10.0, "store": "X", "filename": "x.jpg"}
        row1, row2 = create_journal_rows_for_ticket(ticket)
        assert row1[1] == CUENTA_PADRES  # Debe target = Padres (131)
        assert row2[1] == CUENTA_TR  # Haber payment = TR (121)

    def test_custom_accounts_for_bokatas(self):
        ticket = {"date": "2026-05-23", "amount": 10.0, "store": "X", "filename": "x.jpg"}
        row1, row2 = create_journal_rows_for_ticket(
            ticket,
            target_account=CUENTA_BOKATAS,
            payment_account=CUENTA_TR,
        )
        assert row1[1] == CUENTA_BOKATAS
        assert row2[1] == CUENTA_TR

    def test_date_as_datetime(self):
        ticket = {"date": datetime(2026, 5, 23), "amount": 5.0, "store": "X", "filename": "x.jpg"}
        row1, _ = create_journal_rows_for_ticket(ticket)
        assert row1[0] == "2026-05-23"

    def test_missing_amount_defaults_to_zero(self):
        ticket = {"date": "2026-05-23", "amount": None, "store": "X", "filename": "x.jpg"}
        rows = create_journal_rows_for_ticket(ticket)
        # Aún devuelve filas; el filtrado de importes inválidos es trabajo
        # de register_tickets_in_diario, no de este helper puro.
        assert rows[0][4] == 0.0

    def test_categoria_uses_store(self):
        ticket = {"date": "2026-05-23", "amount": 5.0, "store": "Mercadona", "filename": "x.jpg"}
        row1, row2 = create_journal_rows_for_ticket(ticket)
        # row[3] = Categoría
        assert row1[3] == "Mercadona"
        assert row2[3] == "Mercadona"


# ─────────────────────────────────────────────────────────
# register_tickets_in_diario
# ─────────────────────────────────────────────────────────


class TestRegisterTickets:
    def test_empty_list_returns_zero(self):
        assert register_tickets_in_diario([]) == 0

    @patch("services.automation.append_to_diario", return_value=True)
    def test_valid_tickets_appended(self, mock_append):
        tickets = [
            {"date": "2026-05-23", "amount": 10.0, "store": "A", "filename": "1.jpg"},
            {"date": "2026-05-24", "amount": 20.0, "store": "B", "filename": "2.jpg"},
        ]
        count = register_tickets_in_diario(tickets)
        assert count == 2
        # Se llamó UNA vez con 4 filas (2 por ticket)
        assert mock_append.call_count == 1
        args = mock_append.call_args.args[0]
        assert len(args) == 4

    @patch("services.automation.append_to_diario", return_value=True)
    def test_skips_invalid_amounts(self, mock_append):
        tickets = [
            {"date": "2026-05-23", "amount": None, "store": "A", "filename": "1.jpg"},
            {"date": "2026-05-24", "amount": -5.0, "store": "B", "filename": "2.jpg"},
            {"date": "2026-05-25", "amount": 10.0, "store": "C", "filename": "3.jpg"},
        ]
        count = register_tickets_in_diario(tickets)
        # Solo el tercer ticket es válido
        assert count == 1
        args = mock_append.call_args.args[0]
        assert len(args) == 2  # solo 1 par

    @patch("services.automation.append_to_diario", return_value=False)
    def test_append_failure_returns_zero(self, _mock_append):
        tickets = [
            {"date": "2026-05-23", "amount": 10.0, "store": "A", "filename": "1.jpg"},
        ]
        assert register_tickets_in_diario(tickets) == 0

    @patch("services.automation.append_to_diario", return_value=True)
    def test_all_invalid_no_call(self, mock_append):
        tickets = [
            {"date": "2026-05-23", "amount": 0.0, "store": "A", "filename": "1.jpg"},
        ]
        assert register_tickets_in_diario(tickets) == 0
        mock_append.assert_not_called()


# ─────────────────────────────────────────────────────────
# check_pending_tickets & processing flows
# ─────────────────────────────────────────────────────────
class TestCheckPendingTickets:
    @patch("services.auditor._get_padres_files", return_value=[])
    @patch("services.auditor._get_files_from_drive", return_value=[])
    @patch("services.auditor.identify_unregistered_tickets", return_value=[])
    @patch("data.gsheets._get_gspread_client")
    def test_no_pending_tickets(self, mock_client, mock_ident, mock_drive, mock_padres):
        mock_sheet = mock_client.return_value.open_by_url.return_value.sheet1
        mock_sheet.col_values.return_value = []
        df_diario = pd.DataFrame()

        res = check_pending_tickets(df_diario)
        assert res["padres"]["has_pending"] is False
        assert res["bokatas"]["has_pending"] is False
        assert res["total_pending"] == 0

    @patch("services.auditor._get_padres_files")
    @patch("services.auditor._get_files_from_drive", return_value=[])
    @patch("services.auditor.identify_unregistered_tickets", return_value=[])
    @patch("data.gsheets._get_gspread_client")
    def test_padres_unrenamed_detected(self, mock_client, mock_ident, mock_drive, mock_padres):
        mock_sheet = mock_client.return_value.open_by_url.return_value.sheet1
        mock_sheet.col_values.return_value = []
        mock_padres.return_value = [{"filename": "IMG_1234.jpg", "path": "/path/IMG_1234.jpg"}]
        df_diario = pd.DataFrame()

        res = check_pending_tickets(df_diario)
        assert res["padres"]["has_pending"] is True
        assert len(res["padres"]["unrenamed"]) == 1
        assert res["total_pending"] == 1


class TestProcessTickets:
    @patch("services.extraction.process_padres_folder")
    @patch("services.auditor.identify_unregistered_tickets")
    @patch("services.automation.register_tickets_in_diario")
    def test_process_padres_tickets(self, mock_register, mock_identify, mock_process):
        mock_process.return_value = [
            {
                "original": "raw.jpg",
                "renamed": "20260523 Mercadona 15,50 €.jpg",
                "data": type("D", (), {"efectivo": True})(),
            }
        ]
        mock_identify.return_value = [
            {
                "filename": "20260523 Mercadona 15,50 €.jpg",
                "amount": 15.50,
                "date": "2026-05-23",
                "store": "Mercadona",
            }
        ]
        mock_register.return_value = 1
        df_diario = pd.DataFrame()

        res = process_padres_tickets(df_diario)
        assert res["renamed"] == 1
        assert res["registered"] == 1
        assert res["cash_count"] == 1
        assert len(res["failed"]) == 0
        assert mock_identify.return_value[0]["efectivo"] is True

    @patch("services.auditor._get_files_from_drive")
    @patch("data.gsheets._get_gspread_client")
    @patch("services.extraction.process_and_update_sheet")
    @patch("services.extraction.retry_failed_renames")
    @patch("services.auditor.identify_unregistered_tickets")
    @patch("services.automation.register_tickets_in_diario")
    def test_process_bokatas_tickets(
        self, mock_register, mock_ident, mock_retry, mock_process, mock_client, mock_drive
    ):
        mock_drive.return_value = [
            {
                "id": "file123",
                "path": "file123",
                "name": "IMG_001.jpg",
                "filename": "IMG_001.jpg",
                "mimeType": "image/jpeg",
            }
        ]
        mock_sheet = mock_client.return_value.open_by_url.return_value.sheet1
        mock_sheet.col_values.return_value = []
        mock_process.return_value = [
            {"original": "IMG_001.jpg", "renamed": "20260523 - 10.00€", "data": None}
        ]
        mock_ident.return_value = [
            {
                "filename": "20260523 - 10.00€",
                "amount": 10.00,
                "date": "2026-05-23",
                "store": "Establecimiento",
            }
        ]
        mock_register.return_value = 1
        df_diario = pd.DataFrame()

        res = process_bokatas_tickets(df_diario)
        assert res["renamed"] == 1
        assert res["registered"] == 1
        assert mock_process.called


class TestAutoSyncDriveTickets:
    @patch("services.automation.check_pending_tickets")
    @patch("services.automation.process_padres_tickets")
    @patch("services.automation.process_bokatas_tickets")
    def test_auto_sync_no_pending(self, mock_bokatas, mock_padres, mock_check):
        mock_check.return_value = {
            "padres": {"has_pending": False, "unrenamed": [], "unregistered": []},
            "bokatas": {
                "has_pending": False,
                "unprocessed": [],
                "can_retry": False,
                "unregistered": [],
            },
            "total_pending": 0,
        }
        res = auto_sync_drive_tickets(pd.DataFrame())
        assert res["executed"] is False
        assert res["total_registered"] == 0
        assert not mock_padres.called
        assert not mock_bokatas.called

    @patch("services.automation.check_pending_tickets")
    @patch("services.automation.process_padres_tickets")
    @patch("services.automation.process_bokatas_tickets")
    def test_auto_sync_triggers_when_pending(self, mock_bokatas, mock_padres, mock_check):
        mock_check.return_value = {
            "padres": {"has_pending": True, "unrenamed": [1], "unregistered": []},
            "bokatas": {
                "has_pending": True,
                "unprocessed": [1],
                "can_retry": False,
                "unregistered": [],
            },
            "total_pending": 2,
        }
        mock_padres.return_value = {"renamed": 1, "registered": 1, "cash_count": 0, "failed": []}
        mock_bokatas.return_value = {"renamed": 1, "registered": 1, "failed": []}

        res = auto_sync_drive_tickets(pd.DataFrame())
        assert res["executed"] is True
        assert res["total_registered"] == 2
        assert res["total_renamed"] == 2
        assert mock_padres.called
        assert mock_bokatas.called
