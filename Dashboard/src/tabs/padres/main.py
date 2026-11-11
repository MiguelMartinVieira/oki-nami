"""
tabs/padres/main.py — Tab "Auditoría Padres" (Cuenta 131).

Muestra: 3 metric cards + tabla de cruce de justificantes.
"""

import pandas as pd
import streamlit as st

from components.metric_card import render_metric_card
from components.tab_markers import render_tab_accent_marker
from constants import (
    COLOR_PADRES,
    CUENTA_PADRES,
    DATE_FORMAT,
    PADRES_DRIVE_FOLDER_ID,
    drive_folder_url,
)
from services.accounting import filter_cuenta
from services.auditor import (
    _get_padres_files,
    identify_unregistered_tickets,
    match_expenses_with_files,
)
from services.extraction import _is_already_renamed

# Alias local (legacy): el resto del archivo usa _COLOR_PADRES en notices inline.
# Se mantiene apuntando a la constante centralizada para que un único cambio
# en config/theme.py propage a TODO el tab.
_COLOR_PADRES = COLOR_PADRES


def render(df_diario: pd.DataFrame) -> None:
    """Renderiza el tab completo de Auditoría Padres."""
    # ── Identidad visual lavanda en los botones del tab ──
    # (CSS marker + scoped styling centralizado en components/tab_markers.py)
    render_tab_accent_marker("padres-tab-marker", COLOR_PADRES)

    df_131 = filter_cuenta(df_diario, CUENTA_PADRES)

    if df_131.empty:
        st.info("No hay transacciones registradas en la cuenta 131.")
        return

    # Pre-calcular cruce para obtener métricas exactas de lo PENDIENTE
    df_matched = match_expenses_with_files(df_131)
    df_pending_metrics = df_matched[~df_matched["Estado"].astype(str).str.contains("Pagado")].copy()

    total_debe = df_pending_metrics["Debe"].fillna(0).sum()
    total_haber = df_pending_metrics["Haber"].fillna(0).sum()
    saldo_pendiente = total_debe - total_haber

    # ── Cards (Métricas solo de lo PENDIENTE) ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            render_metric_card("Total Gastado", f"-{total_debe:,.2f} €", color=_COLOR_PADRES),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card("Total Devuelto", f"+{total_haber:,.2f} €", color=_COLOR_PADRES),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            render_metric_card(
                "Saldo Pendiente", f"{saldo_pendiente:,.2f} €", bg_color=_COLOR_PADRES
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 🪄 Procesamiento Unificado de Tickets ──
    with st.spinner("Analizando carpeta Padres/ y Diario..."):
        all_files = _get_padres_files()
        # Solo los archivos ya en formato canónico (renombrados por Gemini o
        # correctos de origen) se cruzan con el Diario. Los demás primero deben
        # pasar por Gemini; registrarlos antes metería importes/fechas inventados.
        pending_tickets = identify_unregistered_tickets(df_diario, only_renamed=True)
        pending_paths = {t["path"] for t in pending_tickets}

        unprocessed_data = []
        for f in all_files:
            if not _is_already_renamed(f["filename"]):
                # Pendiente de Gemini: no se puede registrar hasta tener el
                # nombre correcto (importe/fecha fiables).
                unprocessed_data.append(
                    {
                        "Archivo": f["filename"],
                        "Nombre": "❌ Mal formato",
                        "Diario": "⏳ Tras renombrar",
                    }
                )
            elif f["path"] in pending_paths:
                unprocessed_data.append(
                    {
                        "Archivo": f["filename"],
                        "Nombre": "✅ Correcto",
                        "Diario": "❌ No registrado",
                    }
                )

    if unprocessed_data:
        st.info(f"Se han detectado {len(unprocessed_data)} archivo(s) pendientes de procesar.")
        st.dataframe(pd.DataFrame(unprocessed_data), hide_index=True, width="stretch")

        if st.button("🚀 Process All (Renombrar y Registrar)"):
            with st.spinner("Procesando tickets con Gemini y actualizando Diario..."):
                from services.automation import process_padres_tickets

                res = process_padres_tickets(df_diario)
                renamed_count = res["renamed"]
                registered_count = res["registered"]
                cash_count = res["cash_count"]
                failed = res["failed"]

            # ── Reporte final ──
            if renamed_count > 0 or registered_count > 0:
                _cash_note = f" ({cash_count} en efectivo → Cartera 111)" if cash_count else ""
                st.markdown(
                    f'<div style="background-color: rgba(167,139,250,0.15); border: 1px solid rgba(167,139,250,0.3); '
                    f'padding: 1rem; border-radius: 8px; color: {_COLOR_PADRES}; font-weight: 500; margin-bottom: 1rem;">'
                    f"✔️ ¡Éxito! Se renombraron {renamed_count} archivo(s) y se registraron "
                    f"{registered_count} movimiento(s) en el Diario{_cash_note}.</div>",
                    unsafe_allow_html=True,
                )

            if failed:
                _items = "\n".join(
                    f"- `{r['original']}` — {r.get('error', 'Gemini no pudo extraer datos')}"
                    for r in failed
                )
                st.warning(
                    f"⚠️ Gemini no pudo leer {len(failed)} archivo(s). Se han dejado SIN "
                    f"registrar para que los revises manualmente (vuelve a intentarlo o "
                    f"renómbralos a `YYYYMMDD Establecimiento Importe €`):\n\n{_items}"
                )

            # Refrescar datos solo si se registró algo. Si hubo fallos NO hacemos
            # rerun, para que el aviso siga visible; la tabla se refresca al
            # siguiente clic.
            if registered_count > 0:
                from data.gsheets import get_diario

                get_diario.clear()
            if (renamed_count > 0 or registered_count > 0) and not failed:
                st.balloons()
                st.rerun()
    else:
        st.markdown(
            f'<div style="background-color: rgba(167,139,250,0.15); border: 1px solid rgba(167,139,250,0.3); '
            f'padding: 1rem; border-radius: 8px; color: {_COLOR_PADRES}; font-weight: 500;">'
            f"🎉 Todos los tickets en la carpeta Padres/ están correctamente nombrados y registrados.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ── Cruce de Justificantes & Liquidación ──
    with st.spinner("Analizando carpeta Padres, doc Drive y emparejando recibos..."):
        df_matched = match_expenses_with_files(df_131)
        df_display = (
            df_matched[
                ["Fecha", "Categoría", "Descripción", "Debe", "Haber", "Justificante", "Estado"]
            ]
            .copy()
            .sort_values(by="Fecha", ascending=False)
            .reset_index(drop=True)
        )
        # Formatear fecha con el formato universal del dashboard
        df_display["Fecha"] = pd.to_datetime(df_display["Fecha"], errors="coerce").dt.strftime(
            DATE_FORMAT
        )
        # Limpiar None en Descripción
        df_display["Descripción"] = df_display["Descripción"].fillna("").replace("None", "")
        # Limpiar emojis del estado para coincidir con el tema Abyssal Monochrome
        df_display["Estado"] = (
            df_display["Estado"]
            .astype(str)
            .str.replace("✅ ", "", regex=False)
            .str.replace("✅", "", regex=False)
            .str.strip()
        )

        def _color_estado(val: str) -> str:
            s = str(val)
            if "Pagado" in s:
                return "color: #10B981; background-color: rgba(16,185,129,0.12); font-weight: 600"
            if "Match" in s:
                return f"color: {_COLOR_PADRES}; background-color: rgba(167,139,250,0.12); font-weight: 600"
            if "📄" in s:
                return "color: #3AABCE; background-color: rgba(58,171,206,0.10); font-weight: 600"
            if "⚠️" in s:
                return "color: #F59E0B; background-color: rgba(245,158,11,0.10); font-weight: 600"
            if "❌" in s:
                return "color: #FF1744; background-color: rgba(255,23,68,0.10); font-weight: 600"
            if "➖" in s:
                return "color: #A1A1AA; background-color: rgba(255,255,255,0.04); font-weight: 500"
            return ""

        v_col1, v_col2 = st.columns([2, 3])
        with v_col1:
            st.subheader("📋 Cruce de Justificantes")
        with v_col2:
            view_mode = st.radio(
                "Vista de tabla:",
                ["📌 Solo Pendientes", "✅ Solo Pagados", "📋 Todos"],
                horizontal=True,
                key="padres_view_mode",
            )

        if view_mode == "📌 Solo Pendientes":
            df_filtered = df_display[df_display["Estado"] != "Pagado"].copy()
        elif view_mode == "✅ Solo Pagados":
            df_filtered = df_display[df_display["Estado"] == "Pagado"].copy()
        else:
            df_filtered = df_display.copy()

        df_filtered = df_filtered.reset_index(drop=True)

        st.caption(
            "Selecciona filas si deseas liquidar partidas específicas, o liquida directamente los gastos pendientes visibles."
        )

        # Tabla interactiva con multiselección
        event = st.dataframe(
            df_filtered.style.map(_color_estado, subset=["Estado"]).format(
                "{:,.2f}", subset=["Debe", "Haber"]
            ),
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="padres_df_selection",
        )

        raw_selected_indices = event.get("selection", {}).get("rows", [])
        selected_indices = [i for i in raw_selected_indices if 0 <= i < len(df_filtered)]

        if selected_indices:
            df_selected = df_filtered.iloc[selected_indices].copy()
        else:
            # Por defecto, si no hay selección manual, todas las filas de la vista filtrada actual
            df_selected = df_filtered.copy()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 💳 Panel de Liquidación (Marcar como Pagado & Mover a /Pagado) ──
    from services.auditor import archive_padres_tickets, get_txn_key
    from services.pdf_generator import generate_padres_pdf
    from services.report import (
        generate_padres_csv,
        generate_padres_excel,
    )

    liq_col1, liq_col2, liq_col3, liq_col4 = st.columns(4)

    # Generación de Excel, CSV y PDF para la liquidación actual
    today_str = pd.Timestamp.now().strftime("%Y%m%d")
    liq_excel_bytes = generate_padres_excel(df_matched, df_subset=df_selected)
    liq_csv_bytes = generate_padres_csv(df_matched, df_subset=df_selected)
    liq_pdf_bytes = generate_padres_pdf(
        df_131,
        df_subset=df_selected,
        title_suffix=f"Liquidación {pd.Timestamp.now().strftime('%d/%m/%Y')}",
    )

    with liq_col1:
        st.download_button(
            label="📊 Descargar CSV Liquidación",
            data=liq_csv_bytes,
            file_name=f"Informe_Padres_Liquidacion_{today_str}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with liq_col2:
        st.download_button(
            label="📄 Descargar Excel Liquidación",
            data=liq_excel_bytes,
            file_name=f"Informe_Padres_Liquidacion_{today_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with liq_col3:
        st.download_button(
            label="📄 Descargar PDF Liquidación",
            data=liq_pdf_bytes,
            file_name=f"Informe_Padres_Liquidacion_{today_str}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with liq_col4:
        if st.button("🚀 Liquidar y Mover a /Pagado", use_container_width=True, type="primary"):
            with st.spinner("Archivando justificantes en /Pagado..."):
                filenames_to_move = df_selected["Justificante"].dropna().unique().tolist()
                tx_keys_to_save = [get_txn_key(row) for _, row in df_selected.iterrows()]
                moved_count, errors = archive_padres_tickets(
                    filenames_to_move, tx_keys=tx_keys_to_save
                )

                if moved_count > 0:
                    st.toast(
                        f"✅ ¡{moved_count} justificante(s) movidos a /Pagado y partidas marcadas como pagadas!",
                        icon="🎉",
                    )
                else:
                    st.toast("✅ ¡Partidas marcadas como pagadas!", icon="🎉")

                if errors:
                    st.warning("Avisos al mover algunos justificantes:\n" + "\n".join(errors))

                st.balloons()
                st.rerun()

    padres_url = drive_folder_url(PADRES_DRIVE_FOLDER_ID)
    if padres_url:
        st.link_button(
            "📂 Ir a Carpeta Drive /Padres",
            url=padres_url,
            use_container_width=True,
        )
