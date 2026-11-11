"""
app.py — Orquestador principal del Dashboard de Finanzas 2.0.

Responsabilidades:
  1. Configuración de página Streamlit
  2. Inyección de CSS global
  3. Carga y preprocesamiento de datos (paralela cuando es posible)
  4. Sidebar: formulario manual + sincronización PDF (Modularizado)
  5. Delegación a tabs
"""

import datetime
import os

# ── Importante: añadir src/ al path para imports relativos ──
import sys
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuración de Logging centralizada
from services.logger_config import setup_logging

setup_logging()

# ──────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────
from PIL import Image

from components.header import render_header, sync_inversion_obligatoria_js
from components.sidebar import render_sidebar
from components.styles import GLOBAL_CSS, inject_cipher_js
from constants import TICKER_BRK, TICKER_EURUSD, TICKER_VANGUARD
from data.gsheets import clean_cuenta_col, get_diario, get_historico, get_saldos
from data.ipc import get_ipc_series
from data.yahoo import get_yahoo_price
from services.accounting import calc_metalico_fisico, calc_portfolio_summary

_logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "Logo.png")
try:
    _logo_img = Image.open(_logo_path)
except Exception:
    _logo_img = "💸"

st.set_page_config(page_title="Proyecto Oki-Nami", page_icon=_logo_img, layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
inject_cipher_js()


# ──────────────────────────────────────────────
# Auto-Shutdown Monitor
# ──────────────────────────────────────────────
@st.cache_resource
def _start_session_monitor():
    import os
    import threading
    import time

    from streamlit.runtime import Runtime

    def monitor():
        time.sleep(10)  # Espera inicial
        while True:
            time.sleep(3)
            try:
                if Runtime.exists():
                    sessions = Runtime.instance()._session_mgr.list_active_sessions()
                    if not sessions:
                        print("💤 No quedan pestañas activas. Apagando servidor Streamlit...")
                        os._exit(0)
            except Exception:
                pass

    t = threading.Thread(target=monitor, daemon=True)
    t.start()
    return t


_start_session_monitor()


# ──────────────────────────────────────────────
# Carga de Datos (paralela)
# ──────────────────────────────────────────────
with ThreadPoolExecutor(max_workers=7) as pool:
    fut_diario = pool.submit(get_diario)
    fut_saldos = pool.submit(get_saldos)
    fut_historico = pool.submit(get_historico)

    pool.submit(get_yahoo_price, TICKER_BRK)
    pool.submit(get_yahoo_price, TICKER_VANGUARD)
    pool.submit(get_yahoo_price, TICKER_EURUSD)
    pool.submit(get_ipc_series)

    df_diario = fut_diario.result()
    df_saldos = fut_saldos.result()
    try:
        _df_hist_header = fut_historico.result()
    except Exception:
        _df_hist_header = None

if df_diario.empty or df_saldos.empty:
    st.info(
        "👋 Buscando datos en Google Sheets o CSVs locales. Asegúrate de configurar credentials.json."
    )
    st.stop()

# ──────────────────────────────────────────────
# Sincronización Automática de Tickets en Drive
# ──────────────────────────────────────────────
if "auto_sync_tickets_done" not in st.session_state:
    st.session_state["auto_sync_tickets_done"] = True
    try:
        from services.automation import auto_sync_drive_tickets

        with st.spinner("🔍 Revisando carpetas de Drive y tickets pendientes..."):
            sync_res = auto_sync_drive_tickets(df_diario)

        if sync_res.get("executed"):
            st.session_state["auto_sync_notice"] = sync_res
            if sync_res.get("total_registered", 0) > 0:
                get_diario.clear()
                st.rerun()
    except Exception as e:
        import logging

        logging.getLogger(__name__).error("Error en auto-sync inicial de tickets: %s", e)

# Notificación al usuario tras procesar tickets
if "auto_sync_notice" in st.session_state:
    notice = st.session_state.pop("auto_sync_notice")
    total_reg = notice.get("total_registered", 0)
    total_ren = notice.get("total_renamed", 0)
    failed = notice.get("failed", [])
    if total_reg > 0 or total_ren > 0:
        st.toast(
            f"🤖 Auto-procesado completado: {total_ren} ticket(s) procesado(s) y {total_reg} registrado(s) en el Diario.",
            icon="✅",
        )
    if failed:
        st.warning(
            f"⚠️ Auto-procesado: {len(failed)} archivo(s) no se pudieron procesar automáticamente con Gemini. Revisa las pestañas de Padres/Bokatas para gestionarlos manualmente."
        )

# Registro de sincronización para el sidebar
from services.session_state import session_state

session_state.last_sync = datetime.datetime.now().strftime("%H:%M:%S")

# Preprocesamiento básico
df_diario = clean_cuenta_col(df_diario)
df_diario = df_diario.dropna(subset=["Fecha"])

# Cálculo global
metalico_fisico = calc_metalico_fisico(df_diario)
_portfolio_header = calc_portfolio_summary(df_diario, metalico_fisico)

# Renderizar Cabecera
render_header(
    df_diario=df_diario,
    df_historico=_df_hist_header,
    header_metrics={
        "tr_cash": _portfolio_header.get("tr_cash", 0.0),
        "metalico_fisico": metalico_fisico,
        "total_patrimonio": _portfolio_header.get("total_patrimonio", 0.0),
    },
)

# Actualizar JSON estático para widgets móviles
from services.accounting import calc_ahorro_ytd
from services.widget_api import update_widget_metrics_file
from tabs.guitarra.storage import get_practice_stats

try:
    _ahorro_ytd_val = calc_ahorro_ytd(df_diario)
    _guitar_stats = get_practice_stats()
    update_widget_metrics_file(
        total_patrimonio=_portfolio_header.get("total_patrimonio", 0.0),
        ahorro_ytd=_ahorro_ytd_val,
        tr_cash=_portfolio_header.get("tr_cash", 0.0),
        metalico_fisico=metalico_fisico,
        guitar_streak=_guitar_stats.get("streak", 0),
    )
except Exception:
    pass


render_sidebar(
    df_diario=df_diario,
    df_historico=_df_hist_header,
    header_metrics={
        "tr_cash": _portfolio_header.get("tr_cash", 0.0),
        "metalico_fisico": metalico_fisico,
        "total_patrimonio": _portfolio_header.get("total_patrimonio", 0.0),
    },
)

# ──────────────────────────────────────────────
# Render de Navegación Dinámica (vía menú hamburguesa ☰)
# ──────────────────────────────────────────────


def _frag_diario():
    from services.roundup import get_pending_roundups
    from tabs.diario import render as render_diario
    from tabs.diario.roundup import _load_done

    render_diario(df_diario, df_saldos, metalico_fisico)

    done = _load_done()
    df_pending = get_pending_roundups(df_diario, already_done_fingerprints=done)
    roundup_val = float(df_pending["Céntimos"].sum()) if not df_pending.empty else 0.0
    sync_inversion_obligatoria_js(roundup_val=roundup_val)


def _frag_inversiones():
    from tabs.inversiones import render as render_inversiones

    render_inversiones(df_diario, metalico_fisico)


def _frag_habitos():
    from tabs.habitos.main import load_data
    from tabs.habitos.main import render as render_habitos

    render_habitos()

    habitos_data = load_data()
    bote_val = float(habitos_data.get("current_month_total", 0.0))
    sync_inversion_obligatoria_js(bote_val=bote_val)


def _frag_resumen():
    from tabs.resumen import render as render_resumen

    render_resumen(df_diario, df_saldos, metalico_fisico)


def _frag_padres():
    from tabs.padres import render as render_padres

    render_padres(df_diario)


def _frag_bokatas():
    from tabs.bokatas import render as render_bokatas

    render_bokatas(df_diario)


def _frag_guitarra():
    from tabs.guitarra import render as render_guitarra

    render_guitarra()


# Selección activa del menú hamburguesa
active_tab = st.session_state.get("nav_main_tab", "Resumen")

# Contenedor dinámico con key único por pestaña para forzar la destrucción y desmontado completo del DOM (Plotly charts, DataFrames) al cambiar de sección
with st.container(key=f"tab_main_view_{active_tab.lower().replace(' ', '_')}"):
    if active_tab == "Resumen":
        _frag_resumen()
    elif active_tab == "Portfolio":
        _frag_inversiones()
    elif active_tab == "Hábitos y Ahorros":
        _frag_habitos()
    elif active_tab == "Padres":
        _frag_padres()
    elif active_tab == "Bokatas":
        _frag_bokatas()
    elif active_tab == "Guitarra":
        _frag_guitarra()
    else:
        _frag_diario()
