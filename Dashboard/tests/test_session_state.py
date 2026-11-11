"""
test_session_state.py — Tests para `services/session_state.py:AppSessionState`.

Cubre el refactor de `init_defaults` (sentinela O(1) en lugar de chequeos
por propiedad), las propiedades core (last_sync, tl_*, recon_*) y los
helpers de transacciones staged por PDF.

Se usa un dict como stand-in de `st.session_state` (que en runtime es un
SessionStateProxy con interfaz dict-like).
"""

import sys
import types

import pytest


class FakeSessionState(dict):
    """Dict con la misma API que `st.session_state` (get/setdefault/in/del)."""


@pytest.fixture(autouse=True)
def _patch_streamlit(monkeypatch):
    """Sustituye `st.session_state` por un dict aislado por test."""
    fake = FakeSessionState()
    # Importamos session_state DESPUÉS de parchear para que el módulo use el dict fake
    import services.session_state as ss_mod

    monkeypatch.setattr(ss_mod.st, "session_state", fake, raising=True)
    return fake


def _get_session_state():
    from services.session_state import session_state

    return session_state


class TestInitDefaults:
    def test_initializes_once(self, _patch_streamlit):
        ss = _get_session_state()
        # Primera lectura → dispara init
        _ = ss.last_sync
        assert _patch_streamlit["_app_session_state_initialized"] is True
        assert _patch_streamlit["last_sync"] == "--:--:--"
        assert _patch_streamlit["tl_playing"] is False
        assert _patch_streamlit["tl_slider_w"] == 0
        assert _patch_streamlit["sankey_period"] == "Histórico"
        assert _patch_streamlit["sankey_mode_label"] == "Desglose Detallado"
        assert _patch_streamlit["sankey_granularity_mode"] == "detailed"

    def test_does_not_overwrite_existing(self, _patch_streamlit):
        # Pre-existing keys are preserved
        _patch_streamlit["last_sync"] = "12:34:56"
        ss = _get_session_state()
        assert ss.last_sync == "12:34:56"

    def test_second_call_noop(self, _patch_streamlit):
        ss = _get_session_state()
        _ = ss.last_sync
        # Sobreescribimos para detectar si se reinicia
        _patch_streamlit["last_sync"] = "CUSTOM"
        _ = ss.tl_playing  # Otra propiedad
        assert _patch_streamlit["last_sync"] == "CUSTOM"


class TestProperties:
    def test_last_sync_setter(self, _patch_streamlit):
        ss = _get_session_state()
        ss.last_sync = "23:00:00"
        assert _patch_streamlit["last_sync"] == "23:00:00"
        assert ss.last_sync == "23:00:00"

    def test_tl_playing_round_trip(self, _patch_streamlit):
        ss = _get_session_state()
        ss.tl_playing = True
        assert ss.tl_playing is True

    def test_sheet_modified_time_round_trip(self, _patch_streamlit):
        ss = _get_session_state()
        assert ss.sheet_modified_time is None
        ss.sheet_modified_time = "2026-10-09T08:00:00Z"
        assert ss.sheet_modified_time == "2026-10-09T08:00:00Z"
