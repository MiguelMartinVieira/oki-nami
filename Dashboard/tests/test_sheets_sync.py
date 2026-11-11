"""
test_sheets_sync.py — Tests para el sync bidireccional con GSheets.

Cubre `check_and_refresh_if_remote_changed`:
  - Primera vez: registra el modifiedTime sin invalidar caches.
  - modifiedTime sin cambios: no invalida.
  - modifiedTime distinto: invalida + actualiza el sentinel.
  - modifiedTime None (GSheets inaccesible): no invalida ni registra.
"""

from unittest.mock import MagicMock, patch

import pytest


class _FakeSessionState:
    """Stub mínimo del AppSessionState — solo sheet_modified_time."""

    def __init__(self, initial: str | None = None):
        self.sheet_modified_time = initial


# ──────────────────────────────────────────────
# check_and_refresh_if_remote_changed
# ──────────────────────────────────────────────


@patch("data.gsheets.get_sheet_modified_time", return_value=None)
@patch("data.gsheets.invalidate_data_caches")
def test_returns_false_when_modified_time_none(mock_inval, _mock_mt):
    from data.gsheets import check_and_refresh_if_remote_changed

    sst = _FakeSessionState(initial=None)
    assert check_and_refresh_if_remote_changed(sst) is False
    mock_inval.assert_not_called()
    assert sst.sheet_modified_time is None


@patch("data.gsheets.get_sheet_modified_time", return_value="2026-05-23T12:00:00Z")
@patch("data.gsheets.invalidate_data_caches")
def test_first_run_records_without_invalidating(mock_inval, _mock_mt):
    from data.gsheets import check_and_refresh_if_remote_changed

    sst = _FakeSessionState(initial=None)
    result = check_and_refresh_if_remote_changed(sst)
    assert result is False
    mock_inval.assert_not_called()
    assert sst.sheet_modified_time == "2026-05-23T12:00:00Z"


@patch("data.gsheets.get_sheet_modified_time", return_value="2026-05-23T12:00:00Z")
@patch("data.gsheets.invalidate_data_caches")
def test_same_modified_time_does_not_invalidate(mock_inval, _mock_mt):
    from data.gsheets import check_and_refresh_if_remote_changed

    sst = _FakeSessionState(initial="2026-05-23T12:00:00Z")
    assert check_and_refresh_if_remote_changed(sst) is False
    mock_inval.assert_not_called()


@patch("data.gsheets.get_sheet_modified_time", return_value="2026-05-23T13:30:00Z")
@patch("data.gsheets.invalidate_data_caches")
def test_changed_modified_time_invalidates_caches(mock_inval, _mock_mt):
    from data.gsheets import check_and_refresh_if_remote_changed

    sst = _FakeSessionState(initial="2026-05-23T12:00:00Z")
    result = check_and_refresh_if_remote_changed(sst)
    assert result is True
    mock_inval.assert_called_once()
    assert sst.sheet_modified_time == "2026-05-23T13:30:00Z"


# ──────────────────────────────────────────────
# get_sheet_modified_time fallback (sin gsheets disponible)
# ──────────────────────────────────────────────


@patch("data.gsheets._can_use_gsheets", return_value=False)
def test_get_sheet_modified_time_returns_none_when_gsheets_unavailable(_mock_cu):
    from data.gsheets import get_sheet_modified_time

    get_sheet_modified_time.clear()
    assert get_sheet_modified_time() is None


@patch("data.gsheets._can_use_gsheets", return_value=True)
@patch("data.gsheets._get_gspread_client")
def test_get_sheet_modified_time_handles_exception(mock_client, _mock_cu):
    mock_client.side_effect = Exception("Network down")
    from data.gsheets import get_sheet_modified_time

    get_sheet_modified_time.clear()
    assert get_sheet_modified_time() is None


@patch("data.gsheets._can_use_gsheets", return_value=True)
@patch("data.gsheets._get_gspread_client")
def test_get_sheet_modified_time_returns_value_when_available(mock_client, _mock_cu):
    fake_sheet = MagicMock()
    # gspread ≥ 6 expone `get_lastUpdateTime()`; configuramos ese path
    fake_sheet.get_lastUpdateTime = MagicMock(return_value="2026-05-23T15:00:00Z")
    fake_client = MagicMock()
    fake_client.open_by_url.return_value = fake_sheet
    mock_client.return_value = fake_client

    from data.gsheets import get_sheet_modified_time

    get_sheet_modified_time.clear()
    assert get_sheet_modified_time() == "2026-05-23T15:00:00Z"
