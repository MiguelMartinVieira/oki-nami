"""
header.py — Componente visual para la cabecera del Dashboard.
"""

import streamlit as st
import streamlit.components.v1 as components


def render_header(df_diario=None, df_historico=None, header_metrics: dict | None = None) -> None:
    """
    Renderiza la cabecera: YTD savings, active alerts (with dynamic centering if empty) and external links.
    """
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

    # Inyección de alerta de demostración si no hay alertas reales y st.session_state.show_demo_alert es True
    if not alerts and st.session_state.get("show_demo_alert", True):
        alerts = [
            {
                "level": "critical",
                "icon": "🛡️",
                "title": "Fondo de emergencia bajo",
                "detail": "Sólo 1.0 meses cubiertos (objetivo: ≥ 3).",
            }
        ]

    # Cards en 4 columnas: 3 de métricas + la 4ª tarjeta de menú rellenando el espacio restante (136px de alto)
    c1, c2, c3, c4 = st.columns([2.8, 2.8, 2.8, 1.6])
    if df_diario is not None and not df_diario.empty:
        _render_progress_bars(df_diario, cols=(c1, c2, c3))
    with c4:
        st.markdown(
            """
            <style>
            div[data-testid="stColumn"]:has(div.menu-card-marker) {
                padding-top: 8px !important;
            }
            div[data-testid="stColumn"]:has(div.menu-card-marker) > div[data-testid="stElementContainer"] {
                margin-bottom: 0 !important;
                padding-top: 0 !important;
                padding-bottom: 0 !important;
            }
            div[data-testid="stColumn"]:has(div.menu-card-marker) div[data-testid="stPopover"] {
                width: 100% !important;
                display: block !important;
                margin-bottom: 3px !important;
            }
            div[data-testid="stColumn"]:has(div.menu-card-marker) div[data-testid="stPopover"] > button {
                width: 100% !important;
                height: 34px !important;
                min-height: 34px !important;
                max-height: 34px !important;
                background: rgba(255, 255, 255, 0.04) !important;
                backdrop-filter: blur(12px) !important;
                -webkit-backdrop-filter: blur(12px) !important;
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 10px !important;
                color: #F4F4F5 !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
                font-size: 0.88rem !important;
                font-weight: 700 !important;
                letter-spacing: 0.04em !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.15) !important;
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 8px !important;
                margin: 0 !important;
                padding: 0 12px !important;
                transition: all 0.25s ease !important;
            }
            div[data-testid="stColumn"]:has(div.menu-card-marker) div[data-testid="stPopover"] > button:hover {
                background: rgba(255, 255, 255, 0.08) !important;
                border-color: rgba(255, 255, 255, 0.25) !important;
                box-shadow: 0 8px 25px rgba(0,0,0,0.3) !important;
                transform: translateY(-1px) !important;
                color: #FFFFFF !important;
            }
            </style>
            <div class="menu-card-marker" style="display:none;"></div>
            """,
            unsafe_allow_html=True,
        )
        _render_header_navigation_menu()
        st.markdown(_build_alerts_metric_card(alerts), unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)


def _render_header_navigation_menu() -> None:
    """Renderiza el menú hamburguesa desplegable estilizado como la 4ª tarjeta del header."""
    main_options = [
        "Resumen",
        "Ingresos/Gastos",
        "Portfolio",
        "Hábitos y Ahorros",
        "Padres",
        "Bokatas",
        "Guitarra",
    ]

    current_main_clean = st.session_state.get("nav_main_tab", "Resumen")
    if current_main_clean not in main_options:
        current_main_clean = "Resumen"

    with st.popover("☰  MENÚ", use_container_width=True, help="Navegación Principal"):
        st.markdown(
            '<div id="main-nav-popover-marker" style="display:none;"></div>', unsafe_allow_html=True
        )
        sel_main = st.radio(
            "Sección Principal",
            options=main_options,
            index=main_options.index(current_main_clean),
            key="popover_nav_main",
            label_visibility="collapsed",
        )
        if sel_main != st.session_state.get("nav_main_tab"):
            st.session_state["nav_main_tab"] = sel_main
            st.rerun()

        st.markdown(
            "<hr style='margin:12px 0; border-color:rgba(255,255,255,0.1);'>",
            unsafe_allow_html=True,
        )
        _render_external_links()


# ──────────────────────────────────────────────
# Barra YTD anual + sub-barra mensual con catch-up
# ──────────────────────────────────────────────


def _render_progress_bars(df_diario, cols=None) -> None:
    from config.logic import META_AHORRO_ANUAL
    from services.accounting import calc_ahorro_ytd
    from services.analytics import calc_meta_mensual

    ahorro_ytd = calc_ahorro_ytd(df_diario)
    pct = (ahorro_ytd / META_AHORRO_ANUAL) * 100 if META_AHORRO_ANUAL > 0 else 0.0
    pct_clamped = max(0.0, min(100.0, pct))

    if ahorro_ytd < 0:
        bar_color = "linear-gradient(90deg, #F43F5E 0%, #E11D48 100%)"
        glow_color = "rgba(244, 63, 94, 0.4)"
    else:
        bar_color = "linear-gradient(90deg, #10B981 0%, #3B82F6 100%)"
        glow_color = "rgba(59, 130, 246, 0.4)"

    # ── Sub-barra mensual: meta + catch-up ──
    meta_mes = calc_meta_mensual(df_diario, META_AHORRO_ANUAL)
    meta_obj = meta_mes["meta_mes_objetivo"]
    ahorro_mes = meta_mes["ahorro_mes"]
    pct_mes = meta_mes["pct_mes"]
    pct_mes_clamped = max(0.0, min(100.0, pct_mes))
    catchup_delta = meta_obj - meta_mes["meta_mes_base"]

    if ahorro_mes < 0:
        bar_color_mes = "linear-gradient(90deg, #F43F5E 0%, #E11D48 100%)"
        glow_mes = "rgba(244, 63, 94, 0.3)"
    elif pct_mes >= 100:
        bar_color_mes = "linear-gradient(90deg, #10B981 0%, #059669 100%)"
        glow_mes = "rgba(16, 185, 129, 0.3)"
    else:
        bar_color_mes = "linear-gradient(90deg, #F59E0B 0%, #10B981 100%)"
        glow_mes = "rgba(245, 158, 11, 0.3)"

    # Etiqueta mensual compacta
    if catchup_delta > 1.0:
        mes_tag = f"catch-up +{catchup_delta:,.0f}€"
    elif catchup_delta < -1.0:
        mes_tag = "adelantado"
    else:
        mes_tag = ""
    mes_tag_html = (
        f' <span style="color:#71717A; font-size:0.6rem;">({mes_tag})</span>' if mes_tag else ""
    )

    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode():
            meta_anual_str = scramble_numbers(f"{META_AHORRO_ANUAL:,.0f}")
            ahorro_ytd_str = scramble_numbers(f"{ahorro_ytd:,.2f}")
            pct_str = scramble_numbers(f"{pct:.1f}")
            ahorro_mes_str = scramble_numbers(f"{ahorro_mes:,.0f}")
            meta_obj_str = scramble_numbers(f"{meta_obj:,.0f}")
            pct_mes_str = scramble_numbers(f"{pct_mes:.0f}")
        else:
            meta_anual_str = f"{META_AHORRO_ANUAL:,.0f}"
            ahorro_ytd_str = f"{ahorro_ytd:,.2f}"
            pct_str = f"{pct:.1f}"
            ahorro_mes_str = f"{ahorro_mes:,.0f}"
            meta_obj_str = f"{meta_obj:,.0f}"
            pct_mes_str = f"{pct_mes:.0f}"
    except Exception:
        meta_anual_str = f"{META_AHORRO_ANUAL:,.0f}"
        ahorro_ytd_str = f"{ahorro_ytd:,.2f}"
        pct_str = f"{pct:.1f}"
        ahorro_mes_str = f"{ahorro_mes:,.0f}"
        meta_obj_str = f"{meta_obj:,.0f}"
        pct_mes_str = f"{pct_mes:.0f}"

    # ── Tarjeta combinada ──
    html_combined = f"""
    <div class="metric-card header-card" style="padding:12px 16px; height:136px !important; display:flex; flex-direction:column; justify-content:space-between;">
        <!-- YTD row -->
        <div style="display:flex; align-items:baseline; justify-content:space-between;">
            <div class="metric-label" style="font-size:0.7rem;">🎯 AHORRO YTD</div>
            <div style="font-family:'Roboto Mono',monospace; font-size:0.65rem; color:#71717A;">Meta: {meta_anual_str}€</div>
        </div>
        <div style="display:flex; align-items:baseline; gap:8px;">
            <div style="font-family:'Roboto Mono',monospace; font-size:1.45rem; font-weight:500; color:#FFFFFF; letter-spacing:-0.04em; line-height:1;">{ahorro_ytd_str} €</div>
            <div style="font-family:'Roboto Mono',monospace; font-size:0.75rem; color:#71717A;">{pct_str}%</div>
        </div>
        <div style="width:100%; height:6px; background:rgba(255,255,255,0.06); border-radius:3px; overflow:hidden;">
            <div style="width:{pct_clamped:.1f}%; height:100%; background:{bar_color}; border-radius:3px; box-shadow:0 0 8px {glow_color}; transition:width 0.8s cubic-bezier(0.4,0,0.2,1);"></div>
        </div>
        <!-- Mes row -->
        <div style="display:flex; align-items:baseline; justify-content:space-between; margin-top:4px;">
            <div style="font-size:0.65rem; color:#A1A1AA; font-weight:500; text-transform:uppercase; letter-spacing:0.08em;">📅 Mes: {ahorro_mes_str}€ / {meta_obj_str}€{mes_tag_html}</div>
            <div style="font-family:'Roboto Mono',monospace; font-size:0.72rem; font-weight:600; color:#FFFFFF;">{pct_mes_str}%</div>
        </div>
        <div style="width:100%; height:6px; background:rgba(255,255,255,0.06); border-radius:3px; overflow:hidden;">
            <div style="width:{pct_mes_clamped:.1f}%; height:100%; background:{bar_color_mes}; border-radius:3px; box-shadow:0 0 6px {glow_mes}; transition:width 0.8s cubic-bezier(0.4,0,0.2,1);"></div>
        </div>
    </div>
    """

    col1, col2, col3 = cols if cols is not None else st.columns(3)
    with col1:
        st.markdown(f'<div style="padding-top: 8px;">{html_combined}</div>', unsafe_allow_html=True)
    with col2:
        _render_quote_card()
    with col3:
        _render_inversion_obligatoria(df_diario)


# ──────────────────────────────────────────────
# Quote Card (cita motivacional aleatoria)
# ──────────────────────────────────────────────


def _render_quote_card() -> None:
    from data.quotes import get_random_quote, safe_html

    if "current_quote" not in st.session_state:
        st.session_state["current_quote"] = get_random_quote()

    q = st.session_state["current_quote"]
    quote_text = safe_html(q["quote"])
    author = q.get("author")

    length = len(q["quote"])
    if length > 180:
        font_class = "quote-len-180"
    elif length > 140:
        font_class = "quote-len-140"
    elif length > 100:
        font_class = "quote-len-100"
    elif length > 70:
        font_class = "quote-len-70"
    elif length > 40:
        font_class = "quote-len-40"
    else:
        font_class = "quote-len-0"

    author_block = ""
    if author:
        author_safe = safe_html(author)
        author_block = (
            '<div style="flex:0 0 22px; text-align:right; '
            "font-family:'Plus Jakarta Sans', sans-serif; "
            "font-size:0.7rem; font-weight:700; color:#A1A1AA; "
            "font-style:normal; display:flex; align-items:center; "
            'justify-content:flex-end;">'
            f"{author_safe}</div>"
        )

    card = (
        '<div class="metric-card header-card" '
        'style="padding:12px 12px; height:136px !important; '
        "display:flex; flex-direction:column; "
        'position:relative; overflow:hidden;">'
        '<div style="flex:1; min-height:0; display:flex; '
        'align-items:center; justify-content:center;">'
        '<div style="text-align:center; width:100%;">'
        f'<div class="quote-text {font_class}" style="font-family:\'Plus Jakarta Sans\', sans-serif; '
        "font-style:italic; font-weight:400; "
        "color:#E4E4E7; line-height:1.4; letter-spacing:0.01em; "
        "overflow:hidden; display:-webkit-box; "
        '-webkit-line-clamp:4; -webkit-box-orient:vertical;">'
        f"\u201c{quote_text}\u201d</div>"
        "</div></div>"
        f"{author_block}"
        "</div>"
    )

    st.markdown(
        f'<div style="padding-top: 8px;">{card}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        [class*="st-key-btn_refresh_quote"] {
            margin-top: -140px !important;
            align-self: flex-end !important;
            margin-right: 4px !important;
            width: 30px !important;
            height: 30px !important;
            z-index: 10 !important;
        }
        [class*="st-key-btn_refresh_quote"] button {
            background-color: transparent !important;
            border: none !important;
            border-radius: 6px !important;
            width: 30px !important;
            height: 30px !important;
            min-height: 30px !important;
            padding: 0 !important;
            box-shadow: none !important;
            cursor: pointer !important;
            opacity: 0 !important;
            transition: opacity 0.2s ease !important;
        }
        [class*="st-key-btn_refresh_quote"] button:hover {
            opacity: 0.5 !important;
            background-color: rgba(255,255,255,0.04) !important;
        }
        [class*="st-key-btn_refresh_quote"] button p {
            font-size: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button(" ", key="btn_refresh_quote", help="Nueva cita"):
        st.session_state["current_quote"] = get_random_quote()
        st.rerun()


# ──────────────────────────────────────────────
# Inversión Obligatoria (Tarjeta interactiva)
# ──────────────────────────────────────────────


def _render_inversion_obligatoria(df_diario) -> None:
    from datetime import datetime

    from constants import COLOR_BERKSHIRE, CUENTA_BERKSHIRE, CUENTA_TR
    from data.gsheets import append_to_diario, get_diario
    from services.roundup import get_pending_roundups
    from tabs.diario.roundup import _get_brk_price_eur, _load_done, _save_done
    from tabs.habitos.main import archive_and_reset, load_data
    from tabs.inversiones.montecarlo import _load_mc_contrib

    aportacion = _load_mc_contrib()

    done = _load_done()
    df_pending = get_pending_roundups(df_diario, already_done_fingerprints=done)
    roundup_val = float(df_pending["Céntimos"].sum()) if not df_pending.empty else 0.0

    habitos_data = load_data()
    bote_val = float(habitos_data.get("current_month_total", 0.0))

    total = aportacion + roundup_val + bote_val

    bg_color = "rgba(30, 58, 138, 0.12)"
    border_color = COLOR_BERKSHIRE

    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode():
            str_aportacion = scramble_numbers(f"{aportacion:,.2f}")
            str_roundup = scramble_numbers(f"{roundup_val:,.2f}")
            str_bote = scramble_numbers(f"{bote_val:,.2f}")
            str_total = scramble_numbers(f"{total:,.2f}")
        else:
            str_aportacion = f"{aportacion:,.2f}"
            str_roundup = f"{roundup_val:,.2f}"
            str_bote = f"{bote_val:,.2f}"
            str_total = f"{total:,.2f}"
    except Exception:
        str_aportacion = f"{aportacion:,.2f}"
        str_roundup = f"{roundup_val:,.2f}"
        str_bote = f"{bote_val:,.2f}"
        str_total = f"{total:,.2f}"

    card_html = f"""
    <div class="metric-card header-card" style="display:flex; flex-direction:column; padding: 10px 14px; background:{bg_color}; border:1px solid {border_color}; margin-top:8px; border-radius: 12px; position: relative;">
        <div class="metric-label" style="color:{COLOR_BERKSHIRE}; text-transform:uppercase; font-size:0.75rem; font-weight:700; margin-bottom:8px;">📈 INV. OBLIGATORIA</div>
        <div style="display:flex; align-items:center; justify-content:space-between; flex:1; gap:8px;">
            <div class="inv-oblig-details" style="color:#A1A1AA; line-height:1.5; white-space:nowrap;">
                Savings Plan: <span id="header-aportacion">{str_aportacion}</span> €<br>
                Round Up: <span id="header-roundup">{str_roundup}</span> €<br>
                Bote: <span id="header-bote">{str_bote}</span> €
            </div>
            <div class="inv-oblig-total" style="color:#FFFFFF !important; font-family:'Plus Jakarta Sans', sans-serif; font-weight:700; line-height:1; white-space:nowrap; text-align:right;"><span id="header-total">{str_total}</span> €</div>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    if total > 0:
        st.markdown(
            """
            <style>
            [class*="st-key-btn_exec_inv_oblig"] {
                margin-top: -128px !important;
                align-self: flex-end !important;
                margin-right: 12px !important;
                width: 32px !important;
                height: 32px !important;
                z-index: 10 !important;
            }
            [class*="st-key-btn_exec_inv_oblig"] button[kind="primary"] {
                background-color: transparent !important;
                border: 1px solid transparent !important;
                border-radius: 6px !important;
                width: 32px !important;
                height: 32px !important;
                min-height: 32px !important;
                padding: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: none !important;
                color: initial !important;
            }
            [class*="st-key-btn_exec_inv_oblig"] button[kind="primary"]:hover {
                background-color: rgba(30, 58, 138, 0.1) !important;
                border-color: rgba(30, 58, 138, 0.25) !important;
            }
            [class*="st-key-btn_exec_inv_oblig"] button[kind="primary"] p {
                font-size: 1.2rem !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🤝",
            type="primary",
            key="btn_exec_inv_oblig",
            help="Ejecutar inversión automáticamente",
        ):
            brk_price = _get_brk_price_eur()
            rows = []
            fecha_str = datetime.now().strftime("%Y-%m-%d")

            def _build_row(amount: float, cat: str) -> list[list]:
                final_desc = ""
                if brk_price and brk_price > 0:
                    qty = round(amount / brk_price, 6)
                    if qty > 0:
                        final_desc = f"quantity: {qty:.6f}"
                r_debe = [fecha_str, CUENTA_BERKSHIRE, None, cat, amount, None, final_desc]
                r_haber = [fecha_str, CUENTA_TR, None, cat, None, amount, final_desc]
                return [r_debe, r_haber]

            if aportacion > 0:
                rows.extend(_build_row(aportacion, "Savings Plan"))
            if roundup_val > 0:
                rows.extend(_build_row(roundup_val, "Round Up Efectivo"))
            if bote_val > 0:
                rows.extend(_build_row(bote_val, "Bote"))

            if append_to_diario(rows):
                if not df_pending.empty:
                    new_done = set(done)
                    for _, r in df_pending.iterrows():
                        new_done.add(str(r["Fingerprint"]))
                    _save_done(new_done)
                if bote_val > 0:
                    archive_and_reset()
                get_diario.clear()
                st.success("¡Inversión ejecutada con éxito!")
                st.rerun()
            else:
                st.error("Error al ejecutar la inversión.")


# ──────────────────────────────────────────────
# Alertas (banner colapsable solo si hay alguna)
# ──────────────────────────────────────────────


def _build_alerts_metric_card(alerts: list[dict]) -> str:
    _LEVEL_FG = {
        "critical": "#E11D48",
        "warning": "#F59E0B",
        "info": "#00B8D9",
    }

    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode() and alerts:
            alerts = [
                {
                    **a,
                    "title": scramble_numbers(a.get("title", "")),
                    "detail": scramble_numbers(a.get("detail", "")),
                }
                for a in alerts
            ]
    except Exception:
        pass

    if not alerts:
        return (
            '<div class="alert-header-subcard alert-card-ok">'
            '<div class="metric-label" style="text-transform:uppercase; font-size:0.65rem; color:#10B981 !important; font-weight:700; letter-spacing:0.05em; line-height:1; margin-bottom:2px;">✅ SISTEMA OK</div>'
            "<div style=\"color:#FFFFFF !important; font-family:'Plus Jakarta Sans', sans-serif; font-size:0.82rem; font-weight:700; line-height:1.1; margin-bottom:2px;\">Sin alertas activas</div>"
            '<div class="metric-subtitle" style="color:#A1A1AA !important; font-size:0.65rem; font-weight:500; margin:0; line-height:1;">Todo en orden en tu patrimonio</div>'
            "</div>"
        )

    if len(alerts) == 1:
        a = alerts[0]
        lbl = (
            "CRÍTICO"
            if a["level"] == "critical"
            else "ADVERTENCIA"
            if a["level"] == "warning"
            else "INFO"
        )
        return (
            f'<div class="alert-header-subcard alert-card-{a["level"]}">'
            f'<div class="metric-label alert-label-{a["level"]}" style="text-transform:uppercase; font-size:0.65rem; font-weight:700; letter-spacing:0.05em; line-height:1; margin-bottom:2px;">{a["icon"]} {lbl}</div>'
            f"<div style=\"color:#FFFFFF !important; font-family:'Plus Jakarta Sans', sans-serif; font-size:0.82rem; font-weight:700; line-height:1.1; margin-bottom:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;\">{a['title']}</div>"
            f'<div class="metric-subtitle" style="color:#A1A1AA !important; font-size:0.65rem; font-weight:500; margin:0; line-height:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{a["detail"]}</div>'
            f"</div>"
        )
    else:
        has_critical = any(x["level"] == "critical" for x in alerts)
        has_warning = any(x["level"] == "warning" for x in alerts)
        top_level = "critical" if has_critical else "warning" if has_warning else "info"

        scroll_items = []
        for a in alerts:
            scroll_items.append(
                f"<div style=\"margin-top:3px; padding:3px 6px; background:rgba(0,0,0,0.35); color:#FFFFFF; border-radius:4px; font-size:0.65rem; border-left:2px solid {_LEVEL_FG[a['level']]}; font-weight:500; font-family:'Plus Jakarta Sans',sans-serif; line-height:1.25; white-space:normal; word-break:break-word;\">"
                f'<strong>{a["icon"]} {a["title"]}</strong>: <span style="color:#D4D4D8;">{a["detail"]}</span>'
                f"</div>"
            )
        alerts_list_html = "".join(scroll_items)
        extra_html = f'<div class="alerts-scroll-container" style="max-height: 52px; overflow-y: auto; padding-right: 2px;">{alerts_list_html}</div>'

        lbl = "CRÍTICAS" if has_critical else "ADVERTENCIAS" if has_warning else "INFO"
        val_text = f"{len(alerts)} Activas"

        return (
            f'<div class="alert-header-subcard alert-card-{top_level}">'
            f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:2px; flex-shrink:0;">'
            f'<div class="metric-label alert-label-{top_level}" style="text-transform:uppercase; font-size:0.65rem; font-weight:700; letter-spacing:0.04em;">⚠️ {lbl}</div>'
            f"<div style=\"color:#FFFFFF !important; font-family:'Plus Jakarta Sans', sans-serif; font-size:0.7rem; font-weight:700;\">{val_text}</div>"
            f"</div>"
            f"{extra_html}"
            f"</div>"
        )


# ──────────────────────────────────────────────
# Botones externos (Sheets + Drive)
# ──────────────────────────────────────────────


def _render_external_links() -> None:
    from constants import PADRES_DRIVE_FOLDER_ID, SHEET_URL, drive_folder_url

    links = []
    if SHEET_URL:
        links.append(
            f"""<a href="{SHEET_URL}" target="_blank" style="text-decoration: none; display: block; width: 100%;">
                <div class="header-btn header-btn-gsheets">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/3/30/Google_Sheets_logo_%282014-2020%29.svg" width="18">
                    Ir al Libro Diario
                </div>
            </a>"""
        )
    padres_url = drive_folder_url(PADRES_DRIVE_FOLDER_ID)
    if padres_url:
        links.append(
            f"""<a href="{padres_url}" target="_blank" style="text-decoration: none; display: block; width: 100%;">
                <div class="header-btn header-btn-drive">
                    <span style="font-size: 1.2rem;">📂</span>
                    Ir a /Padres
                </div>
            </a>"""
        )
    if not links:
        return
    st.markdown(
        """
        <div style="display: flex; flex-direction: column; align-items: stretch; gap: 8px; padding-top: 5px; width: 100%;">
            """
        + "\n".join(links)
        + """
        </div>
        <style>
            .header-btn {
                background: rgba(255, 255, 255, 0.06);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 0 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                font-weight: 600;
                font-size: 0.85rem;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                transition: all 0.3s ease;
                cursor: pointer;
                width: 100%;
                box-sizing: border-box;
                height: 38px;
                margin: 0;
            }
            .header-btn-gsheets { color: #00E676; }
            .header-btn-drive { color: #475569; }
            .header-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1) !important;
                background: rgba(255, 255, 255, 0.9) !important;
                border-color: rgba(255, 255, 255, 0.8) !important;
            }
            .header-btn-gsheets:hover { color: #059669; }
            .header-btn-drive:hover { color: #0F172A; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sync_inversion_obligatoria_js(bote_val: float = None, roundup_val: float = None):

    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode():
            js_code = "<script>const doc = window.parent.document;"
            if bote_val is not None:
                b_str = scramble_numbers(f"{bote_val:,.2f}")
                js_code += f'{{ const el = doc.getElementById("header-bote"); if (el) el.innerText = "{b_str}"; }}'
            if roundup_val is not None:
                r_str = scramble_numbers(f"{roundup_val:,.2f}")
                js_code += f'{{ const el = doc.getElementById("header-roundup"); if (el) el.innerText = "{r_str}"; }}'
            js_code += "</script>"
            components.html(js_code, height=0, width=0)
            return
    except Exception:
        pass

    js_code = "<script>const doc = window.parent.document;"
    if bote_val is not None:
        js_code += (
            "{"
            f'const el = doc.getElementById("header-bote"); if (el) el.innerText = "{bote_val:,.2f}";'
            "}"
        )
    if roundup_val is not None:
        js_code += (
            "{"
            f'const el = doc.getElementById("header-roundup"); if (el) el.innerText = "{roundup_val:,.2f}";'
            "}"
        )

    js_code += """
    {
        const aEl = doc.getElementById("header-aportacion");
        const rEl = doc.getElementById("header-roundup");
        const bEl = doc.getElementById("header-bote");
        const tEl = doc.getElementById("header-total");

        if (aEl && rEl && bEl && tEl) {
            const a = parseFloat(aEl.innerText.replace(/,/g, '')) || 0;
            const r = parseFloat(rEl.innerText.replace(/,/g, '')) || 0;
            const b = parseFloat(bEl.innerText.replace(/,/g, '')) || 0;
            const tot = a + r + b;
            if (!isNaN(tot)) {
                tEl.innerText = tot.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            }
        }
    }
    </script>
    """
    components.html(js_code, height=0, width=0)
