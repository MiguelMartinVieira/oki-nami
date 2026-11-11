"""
session_state.py — Gestor centralizado y tipado para Streamlit session_state.

Este módulo encapsula todo el acceso a st.session_state a través de una interfaz
bien definida y con anotaciones de tipo, evitando KeyErrors, colisiones de claves,
y asegurando inicializaciones seguras.
"""

import logging
from typing import Any

import streamlit as st

log = logging.getLogger(__name__)


class AppSessionState:
    """
    Boundary de gestión de estado para la aplicación Streamlit.
    """

    _INIT_SENTINEL = "_app_session_state_initialized"
    _DEFAULTS: dict[str, Any] = {
        "last_sync": "--:--:--",
        "tl_playing": False,
        "tl_slider_w": 0,
        "_tl_advance": False,
        "sheet_modified_time": None,
        "sankey_period": "Histórico",
        "sankey_mode_label": "Desglose Detallado",
        "sankey_granularity_mode": "detailed",
    }

    @classmethod
    def init_defaults(cls) -> None:
        """Inicializa los valores por defecto una sola vez por sesión.

        Tras la primera llamada en una sesión Streamlit, futuras invocaciones
        son no-op (chequeo O(1) de un sentinela).
        """
        if st.session_state.get(cls._INIT_SENTINEL):
            return
        for key, value in cls._DEFAULTS.items():
            st.session_state.setdefault(key, value)
        st.session_state[cls._INIT_SENTINEL] = True

    @property
    def last_sync(self) -> str:
        self.init_defaults()
        return st.session_state["last_sync"]

    @last_sync.setter
    def last_sync(self, value: str) -> None:
        st.session_state["last_sync"] = value

    # ── Time Lapse (Portfolio) ──
    @property
    def tl_playing(self) -> bool:
        self.init_defaults()
        return st.session_state["tl_playing"]

    @tl_playing.setter
    def tl_playing(self, value: bool) -> None:
        st.session_state["tl_playing"] = value

    @property
    def tl_slider_w(self) -> int:
        self.init_defaults()
        return st.session_state["tl_slider_w"]

    @tl_slider_w.setter
    def tl_slider_w(self, value: int) -> None:
        st.session_state["tl_slider_w"] = value

    @property
    def tl_advance(self) -> bool:
        self.init_defaults()
        return st.session_state["_tl_advance"]

    @tl_advance.setter
    def tl_advance(self, value: bool) -> None:
        st.session_state["_tl_advance"] = value

    # ── Sync bidireccional GSheets ──
    @property
    def sheet_modified_time(self) -> str | None:
        self.init_defaults()
        return st.session_state.get("sheet_modified_time")

    @sheet_modified_time.setter
    def sheet_modified_time(self, value: str | None) -> None:
        st.session_state["sheet_modified_time"] = value


# Instancia central global para importar
session_state = AppSessionState()
