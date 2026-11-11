"""
sidebar.py — Componente visual para la barra lateral (configuración y carga).
"""

import streamlit as st

from data.gsheets import _can_use_gsheets, get_diario, get_saldos
from data.yahoo import get_yahoo_history, get_yahoo_price


def render_sidebar(df_diario=None, df_historico=None, header_metrics: dict | None = None):
    """
    Renderiza la barra lateral con info de conexión, alertas críticas del sistema,
    formulario manual y sincronización automática.
    """
    from components.header import _build_alerts_metric_card
    from services.analytics import detect_header_alerts

    header_metrics = header_metrics or {}
    alerts = []
    if df_diario is not None and not df_diario.empty:
        alerts = detect_header_alerts(
            df_diario=df_diario,
            df_historico=df_historico,
            tr_cash=float(header_metrics.get("tr_cash", 0.0) or 0.0),
            metalico_fisico=float(header_metrics.get("metalico_fisico", 0.0) or 0.0),
            total_patrimonio=float(header_metrics.get("total_patrimonio", 0.0) or 0.0),
        )

    if not alerts and st.session_state.get("show_demo_alert", True):
        alerts = [
            {
                "level": "critical",
                "icon": "🛡️",
                "title": "Fondo de emergencia bajo",
                "detail": "Sólo 1.0 meses cubiertos (objetivo: ≥ 3).",
            }
        ]

    with st.sidebar:
        # ── Logo e Identidad Visual de Oki-Nami ──
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.06);">
                <img src="app/static/Logo.png" style="width: 38px; height: 38px; border-radius: 50%; object-fit: cover; border: 1px solid rgba(255,255,255,0.1);">
                <span style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.15rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.02em;">Proyecto Oki-Nami</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Alertas Críticas ──
        if alerts:
            html_alerts = _build_alerts_metric_card(alerts)
            st.markdown(html_alerts, unsafe_allow_html=True)

        st.header("⚙️ Configuración & API")
        from services.demo_data import is_demo_mode

        if is_demo_mode():
            st.info("🧪 Modo demo: datos sintéticos, sin conexión a Sheets ni Drive.")
        elif _can_use_gsheets():
            st.success("✅ Conectado a Google Sheets")
            from constants import SHEET_URL

            st.link_button(
                "🟢 Abrir Libro Diario en GSheets",
                url=SHEET_URL,
                use_container_width=True,
            )
        else:
            st.warning("⚠️ Usando CSVs locales.")

        if st.button(
            "💶 Desglose de Efectivo", use_container_width=True, key="sidebar_btn_cash_breakdown"
        ):
            if df_diario is not None and not df_diario.empty:
                from components.cash_dialog import render_cash_dialog
                from services.accounting import calc_metalico_desglose, calc_metalico_fisico

                metalico_val = float(
                    header_metrics.get("metalico_fisico", 0.0)
                    if header_metrics
                    else calc_metalico_fisico(df_diario)
                )
                desglose = calc_metalico_desglose(df_diario)
                render_cash_dialog(
                    metalico_val,
                    desglose["cartera"],
                    desglose["hucha"],
                )

        if st.button("🔄 Forzar Recarga Completa", use_container_width=True):
            st.session_state.pop("auto_sync_tickets_done", None)
            get_diario.clear()
            get_saldos.clear()
            get_yahoo_price.clear()
            get_yahoo_history.clear()
            try:
                from data.ipc import get_ipc_series

                get_ipc_series.clear()
            except ImportError:
                pass
            # También invalidar los parquet caches en disco
            try:
                from data.gsheets import get_historico, invalidate_all_parquet_caches

                get_historico.clear()
                invalidate_all_parquet_caches()
            except ImportError:
                pass
            st.rerun()

        if st.button(
            "🤖 Sincronizar Tickets de Drive",
            use_container_width=True,
            key="sidebar_btn_sync_drive",
        ):
            st.session_state.pop("auto_sync_tickets_done", None)
            st.rerun()

        if st.button("🔄 Forzar Recalculado Histórico", use_container_width=True):
            with st.spinner("Recalculando todo el historial..."):
                from services.history import update_historico

                update_historico(df_diario, force=True)
                st.toast("Historial reiniciado y sincronizado ✅")
                st.rerun()

        from services.session_state import session_state

        st.caption(f"Última sincronización: {session_state.last_sync}")

        # ── Toggle Modo Cifrado ──
        st.markdown("---")
        try:
            from services.demo_data import is_cipher_mode

            current = is_cipher_mode()
            new_state = st.toggle(
                "🔐 Modo Cifrado",
                value=current,
                key="toggle_demo_mode",
                help="Oculta todas las cifras y cantidades numéricas en el dashboard.",
            )
            st.session_state["cipher_mode_active"] = new_state
            if new_state != current:
                # Solo cambia la presentación: los datos no se recargan.
                st.rerun()
        except Exception as e:
            st.caption(f"No se pudo cargar toggle cifrado: {e}")
