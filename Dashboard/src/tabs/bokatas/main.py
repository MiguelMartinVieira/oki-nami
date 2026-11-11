"""
tabs/bokatas/main.py — Tab "Bokatas (ONG)" (Cuenta 133).

Lógica contable:
  - Cuenta 133 es un PASIVO (Deudas a Cobrar): dinero de la ONG
    custodiado en el TR personal de Miguel.
  - Haber: entradas de la ONG → aumenta lo que Miguel "debe" a la ONG.
  - Debe:  pagos realizados  → reduce esa deuda.
  - Saldo disponible = Haber - Debe  (contable negativo → se muestra positivo).
  - NO se contabiliza en el Patrimonio Personal.
"""

import pandas as pd
import streamlit as st

from components.metric_card import render_metric_card
from components.tab_markers import render_tab_accent_marker
from constants import (
    BOKATAS_DRIVE_FOLDER_ID,
    BOKATAS_VERSION_SHEET_URL,
    COLOR_BOKATAS,
    CUENTA_BOKATAS,
    DATE_FORMAT,
    drive_folder_url,
)
from services.accounting import calc_bokatas_detalle, filter_cuenta
from services.auditor import identify_unregistered_tickets, match_expenses_with_files


def render(df_diario: pd.DataFrame) -> None:
    """Renderiza el tab completo de Bokatas ONG."""
    render_tab_accent_marker("bokatas-tab-marker", COLOR_BOKATAS)

    df_133 = filter_cuenta(df_diario, CUENTA_BOKATAS)

    if df_133.empty:
        st.info("No hay transacciones registradas en la cuenta 133 todavía.")
        return

    # ── Cálculos (centralizados en accounting.py) ──
    detalle = calc_bokatas_detalle(df_diario)
    total_recibido = detalle["total_recibido"]
    total_pagado = detalle["total_pagado"]
    saldo_disponible = detalle["saldo_disponible"]

    # ── Cards ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            render_metric_card(
                "Total Recibido de la ONG",
                f"+{total_recibido:,.2f} €",
                color=COLOR_BOKATAS,
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card(
                "Total Pagado en nombre de la ONG",
                f"-{total_pagado:,.2f} €",
                color=COLOR_BOKATAS,
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            render_metric_card(
                "Saldo Disponible para Facturas",
                f"{saldo_disponible:,.2f} €",
                bg_color=COLOR_BOKATAS,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 🪄 Procesamiento Unificado de Tickets ──
    from services.auditor import _get_files_from_drive
    from services.extraction import _ALREADY_RENAMED

    with st.spinner("Analizando Drive y Diario..."):
        all_files = _get_files_from_drive(BOKATAS_DRIVE_FOLDER_ID)

        try:
            from data.gsheets import _get_gspread_client

            gspread_client = _get_gspread_client()
            sheet = gspread_client.open_by_url(BOKATAS_VERSION_SHEET_URL).sheet1
            existing_ids = set(filter(None, sheet.col_values(6)))
        except Exception:
            existing_ids = set()

        pending_tickets = identify_unregistered_tickets(
            df_diario,
            folder_path_or_id=BOKATAS_DRIVE_FOLDER_ID,
            account_id=CUENTA_BOKATAS,
            is_drive=True,
            match_amount_only=True,
            only_renamed=True,
        )
        pending_paths = {t["path"] for t in pending_tickets}

        unprocessed_data = []
        for f in all_files:
            is_renamed = bool(_ALREADY_RENAMED.match(f["filename"]))
            is_in_sheet = f["path"] in existing_ids

            if not is_renamed and not is_in_sheet:
                unprocessed_data.append(
                    {
                        "Archivo": f["filename"],
                        "Nombre": "❌ Mal formato",
                        "Diario": "⏳ Tras renombrar",
                    }
                )
            elif not is_renamed and is_in_sheet:
                unprocessed_data.append(
                    {
                        "Archivo": f["filename"],
                        "Nombre": "⚠️ Renombrar a mano",
                        "Diario": "⏳ Tras renombrar",
                    }
                )
            elif is_renamed and f["path"] in pending_paths:
                unprocessed_data.append(
                    {
                        "Archivo": f["filename"],
                        "Nombre": "✅ Correcto",
                        "Diario": "❌ No registrado",
                    }
                )

    if unprocessed_data:
        st.info(
            f"Se han detectado {len(unprocessed_data)} archivo(s) pendientes de procesar o corregir."
        )
        st.dataframe(pd.DataFrame(unprocessed_data), hide_index=True, width="stretch")

        can_process = any(
            row["Nombre"] == "❌ Mal formato" or row["Diario"] == "❌ No registrado"
            for row in unprocessed_data
        )
        can_retry = any(row["Nombre"] == "⚠️ Renombrar a mano" for row in unprocessed_data)

        if can_process or can_retry:
            btn_label = (
                "🚀 Process All (Renombrar, ONG y Registrar)"
                if can_process
                else "🔄 Reintentar Renombrado en Drive"
            )
            if st.button(btn_label, key="bokatas_btn_registrar_tickets"):
                with st.spinner(
                    "Procesando tickets con Gemini, ONG GSheet y actualizando Diario..."
                ):
                    from services.automation import process_bokatas_tickets

                    res = process_bokatas_tickets(df_diario)
                    renamed_count = res["renamed"]
                    registered_count = res["registered"]
                    failed = res["failed"]

                if renamed_count > 0 or registered_count > 0:
                    st.markdown(
                        f'<div style="background-color: rgba(58,171,206,0.15); border: 1px solid rgba(58,171,206,0.3); '
                        f'padding: 1rem; border-radius: 8px; color: {COLOR_BOKATAS}; font-weight: 500; margin-bottom: 1rem;">'
                        f"✔️ ¡Éxito! Se procesaron en la ONG / renombraron {renamed_count} archivo(s) y se registraron "
                        f"{registered_count} movimiento(s) en el Diario personal.</div>",
                        unsafe_allow_html=True,
                    )

                if failed:
                    _items = "\n".join(
                        f"- `{r['original']}` — {r.get('error', 'Error')}" for r in failed
                    )
                    st.warning(
                        f"⚠️ Hubo problemas con {len(failed)} archivo(s). Puedes reintentar más tarde o renombrarlo a mano:\n\n{_items}"
                    )

                if renamed_count == 0 and registered_count == 0 and not failed:
                    st.info("No había archivos pendientes de procesar.")

                if registered_count > 0:
                    from data.gsheets import get_diario

                    get_diario.clear()
                if (renamed_count > 0 or registered_count > 0) and not failed:
                    st.balloons()
                    st.rerun()

    else:
        st.markdown(
            f'<div style="background-color: rgba(58,171,206,0.15); border: 1px solid rgba(58,171,206,0.3); '
            f'padding: 1rem; border-radius: 8px; color: {COLOR_BOKATAS}; font-weight: 500;">'
            f"🎉 Todos los tickets en Drive están correctamente nombrados, pasados por la ONG y registrados.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ── Cruce de Justificantes ──
    with st.spinner("Cruzando datos con Drive..."):
        df_matched = match_expenses_with_files(
            df_133,
            folder_path_or_id=BOKATAS_DRIVE_FOLDER_ID,
            is_drive=True,
            use_drive_doc=False,
            match_amount_only=True,
        )

        df_unified = (
            df_matched[
                ["Fecha", "Categoría", "Descripción", "Debe", "Haber", "Justificante", "Estado"]
            ]
            .copy()
            .sort_values(by="Fecha", ascending=False)
        )
        df_unified["Fecha"] = pd.to_datetime(df_unified["Fecha"], errors="coerce").dt.strftime(
            DATE_FORMAT
        )
        df_unified["Descripción"] = df_unified["Descripción"].fillna("").replace("None", "")
        # Reemplazar el emoji verde por defecto por uno neutro para que herede el color azul en CSS
        df_unified["Estado"] = df_unified["Estado"].str.replace("✅", "✔️")

        def _color_estado(val: str) -> str:
            # Pills dark coherentes con el tema Abyssal Monochrome.
            s = str(val)
            if "✔️" in s:
                # Color azul Bokatas en vez de verde
                return "color: #3AABCE; background-color: rgba(58,171,206,0.15); font-weight: 600; border: 1px solid rgba(58,171,206,0.3); border-radius: 4px;"
            if "📄" in s:
                return "color: #3AABCE; background-color: rgba(58,171,206,0.10); font-weight: 600"
            if "⚠️" in s:
                return "color: #F59E0B; background-color: rgba(245,158,11,0.10); font-weight: 600"
            if "❌" in s:
                return "color: #FF1744; background-color: rgba(255,23,68,0.10); font-weight: 600"
            if "➖" in s:
                return "color: #A1A1AA; background-color: rgba(255,255,255,0.04); font-weight: 500"
            return ""

        st.dataframe(
            df_unified.style.map(_color_estado, subset=["Estado"]).format(
                "{:,.2f}", subset=["Debe", "Haber"]
            ),
            width="stretch",
            hide_index=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    _link_btn_css = (
        "background-color: #18181B; color: #E4E4E7; "
        "border: 1px solid rgba(58,171,206,0.25); "
        "border-left: 3px solid #3AABCE; "
        "padding: 10px 18px; border-radius: 10px; cursor: pointer; width: 100%; "
        "font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 500; "
        "transition: border-color 0.2s ease, box-shadow 0.2s ease;"
    )
    ext_links = []
    if BOKATAS_VERSION_SHEET_URL:
        ext_links.append(("📄 Ver Google Sheet", BOKATAS_VERSION_SHEET_URL))
    if BOKATAS_DRIVE_FOLDER_ID:
        ext_links.append(("📁 Ver Carpeta Drive", drive_folder_url(BOKATAS_DRIVE_FOLDER_ID)))
    for col, (label, url) in zip(st.columns(max(len(ext_links), 1)), ext_links, strict=False):
        with col:
            st.markdown(
                f'<a href="{url}" target="_blank" style="text-decoration:none;">'
                f'<button style="{_link_btn_css}">{label}</button></a>',
                unsafe_allow_html=True,
            )
