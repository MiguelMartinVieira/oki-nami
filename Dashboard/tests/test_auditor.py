import datetime
import os
import sys

import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from services.auditor import match_expenses_with_files


def test_match_amount_only_bokatas_logic():
    """
    Tests the match_amount_only flag uses only amount for matching and
    ignores dates completely. This is crucial for Bokatas ONG reconciliation.
    """
    # Create mock DataFrame representing Diario (Cuenta 133)
    df_acc = pd.DataFrame(
        [
            {
                "Fecha": "2026-03-01",
                "Categoría": "Bokatas Pago",
                "Descripción": "Pago a voluntario",
                "Debe": 33.47,
            },
        ]
    )

    # Mock files coming from Drive
    # Notice the date of the file is more than 7 days apart from the Diario date (2026-03-01 vs 2026-03-26)
    import services.auditor

    original_get_files = services.auditor._get_files_from_drive

    try:

        def mock_get_files(folder_id):
            return [
                {
                    "filename": "20260326 - 33.47€",
                    "path": "test_id_123",
                    "type": "drive",
                    "date": datetime.date(2026, 3, 26),
                    "amount": 33.47,
                    "store": "Mercadona",
                }
            ]

        services.auditor._get_files_from_drive = mock_get_files

        # Test 1: With match_amount_only=False (should fail to match because date is > 7 days)
        df_failed = match_expenses_with_files(
            df_acc,
            folder_path_or_id="mock",
            is_drive=True,
            use_drive_doc=False,
            match_amount_only=False,
        )
        assert df_failed.iloc[0]["Estado"] == "❌ Faltante", (
            "Should not match if date is checked and > 7 days"
        )

        # Test 2: With match_amount_only=True (should match purely based on amount)
        df_matched = match_expenses_with_files(
            df_acc,
            folder_path_or_id="mock",
            is_drive=True,
            use_drive_doc=False,
            match_amount_only=True,
        )
        assert df_matched.iloc[0]["Estado"] == "✅ Match Drive", (
            "Should match because amounts are equal and match_amount_only=True"
        )
        assert df_matched.iloc[0]["Justificante"] == "20260326 - 33.47€"

    finally:
        services.auditor._get_files_from_drive = original_get_files


def test_identify_unregistered_tickets_amount_only():
    """
    Tests that identify_unregistered_tickets correctly skips matching
    against the Diario if only the amount matches but match_amount_only=True.
    """
    # Diario has a 23.48 entry on 2026-03-25
    df_diario = pd.DataFrame(
        [
            {
                "Fecha": "2026-03-25",
                "Nº Cuenta": "133",
                "Categoría": "Bokatas Teresa",
                "Debe": 23.48,
                "Haber": 0.0,
            },
        ]
    )

    import services.auditor

    original_get_files = services.auditor._get_files_from_drive

    try:
        # File in Drive has date 2026-03-16 (9 days difference, > 7)
        def mock_get_files(folder_id):
            return [
                {
                    "filename": "20260316 - 23.48€",
                    "path": "id_2348",
                    "type": "drive",
                    "date": datetime.date(2026, 3, 16),
                    "amount": 23.48,
                    "store": "Desconocido",
                }
            ]

        services.auditor._get_files_from_drive = mock_get_files

        # Test 1: With match_amount_only=False (should be UNREGISTERED because date > 7 days)
        from services.auditor import identify_unregistered_tickets

        unreg_false = identify_unregistered_tickets(
            df_diario, "mock", account_id="133", is_drive=True, match_amount_only=False
        )
        assert len(unreg_false) == 1, "Should be unregistered if date check is active and > 7 days"

        # Test 2: With match_amount_only=True (should be REGISTERED / not in the list)
        unreg_true = identify_unregistered_tickets(
            df_diario, "mock", account_id="133", is_drive=True, match_amount_only=True
        )
        assert len(unreg_true) == 0, (
            "Should NOT be in the unregistered list because amounts match and match_amount_only=True"
        )

    finally:
        services.auditor._get_files_from_drive = original_get_files


if __name__ == "__main__":
    pytest.main([__file__])
