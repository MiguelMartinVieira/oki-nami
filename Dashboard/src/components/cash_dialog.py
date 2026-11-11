"""
cash_dialog.py — Dialog modal para el desglose de efectivo por denominación.

Se abre desde el botón en la tarjeta de Efectivo del Portfolio.
Permite ver y editar la cantidad de cada billete/moneda en Cartera y Hucha.
"""

from __future__ import annotations

import datetime

import streamlit as st

from constants import (
    COLOR_BILL,
    COLOR_COIN,
    COLOR_POSITIVO,
    DENOMINATIONS_BILLS,
    DENOMINATIONS_COINS,
)
from services.cash_tracker import (
    calc_total,
    format_denomination,
    get_empty_template,
)


def _render_denomination_inputs(
    location: str,
    current_counts: dict[float, int],
) -> dict[float, int]:
    """Renderiza los inputs de denominación para una ubicación (cartera/hucha).

    Returns:
        dict actualizado con las cantidades editadas por el usuario.
    """
    updated = {}

    # ── Billetes ──
    st.markdown(
        f'<div style="color:{COLOR_BILL}; font-size:0.75rem; font-weight:600; '
        f"text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px; "
        f"font-family:'Plus Jakarta Sans', sans-serif;\">"
        f"💵 Billetes</div>",
        unsafe_allow_html=True,
    )

    subtotal_bills = 0.0
    for denom in DENOMINATIONS_BILLS:
        col_label, col_input, col_sub = st.columns([2, 2, 2])
        qty = current_counts.get(denom, 0)
        with col_label:
            pill_color = COLOR_BILL
            st.markdown(
                f'<div style="background:rgba(133,77,14,0.15); color:{pill_color}; '
                f"padding:4px 10px; border-radius:6px; font-family:'Roboto Mono', monospace; "
                f'font-size:0.85rem; font-weight:600; display:inline-block; margin-top:6px;">'
                f"{format_denomination(denom)}</div>",
                unsafe_allow_html=True,
            )
        with col_input:
            new_qty = st.number_input(
                f"{denom}",
                min_value=0,
                value=int(qty),
                step=1,
                key=f"denom_{location}_{denom}",
                label_visibility="collapsed",
            )
            updated[denom] = new_qty
        with col_sub:
            sub = denom * new_qty
            subtotal_bills += sub
            color = "#71717A" if new_qty == 0 else "#E4E4E7"
            st.markdown(
                f"<div style=\"font-family:'Roboto Mono', monospace; "
                f'font-size:0.82rem; color:{color}; margin-top:8px; text-align:right;">'
                f"{sub:,.2f}€</div>",
                unsafe_allow_html=True,
            )

    # Subtotal billetes
    st.markdown(
        f"<div style=\"text-align:right; font-family:'Roboto Mono', monospace; "
        f"font-size:0.78rem; color:{COLOR_BILL}; padding:4px 0; "
        f'border-top:1px solid rgba(255,255,255,0.06); margin-top:4px;">'
        f"Subtotal: {subtotal_bills:,.2f}€</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div style="margin:12px 0;"></div>', unsafe_allow_html=True)

    # ── Monedas ──
    st.markdown(
        f'<div style="color:{COLOR_COIN}; font-size:0.75rem; font-weight:600; '
        f"text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px; "
        f"font-family:'Plus Jakarta Sans', sans-serif;\">"
        f"🪙 Monedas</div>",
        unsafe_allow_html=True,
    )

    subtotal_coins = 0.0
    for denom in DENOMINATIONS_COINS:
        col_label, col_input, col_sub = st.columns([2, 2, 2])
        qty = current_counts.get(denom, 0)
        with col_label:
            st.markdown(
                f'<div style="background:rgba(148,163,184,0.12); color:{COLOR_COIN}; '
                f"padding:4px 10px; border-radius:6px; font-family:'Roboto Mono', monospace; "
                f'font-size:0.85rem; font-weight:600; display:inline-block; margin-top:6px;">'
                f"{format_denomination(denom)}</div>",
                unsafe_allow_html=True,
            )
        with col_input:
            new_qty = st.number_input(
                f"{denom}",
                min_value=0,
                value=int(qty),
                step=1,
                key=f"denom_{location}_{denom}",
                label_visibility="collapsed",
            )
            updated[denom] = new_qty
        with col_sub:
            sub = denom * new_qty
            subtotal_coins += sub
            color = "#71717A" if new_qty == 0 else "#E4E4E7"
            st.markdown(
                f"<div style=\"font-family:'Roboto Mono', monospace; "
                f'font-size:0.82rem; color:{color}; margin-top:8px; text-align:right;">'
                f"{sub:,.2f}€</div>",
                unsafe_allow_html=True,
            )

    # Subtotal monedas
    st.markdown(
        f"<div style=\"text-align:right; font-family:'Roboto Mono', monospace; "
        f"font-size:0.78rem; color:{COLOR_COIN}; padding:4px 0; "
        f'border-top:1px solid rgba(255,255,255,0.06); margin-top:4px;">'
        f"Subtotal: {subtotal_coins:,.2f}€</div>",
        unsafe_allow_html=True,
    )

    # Total ubicación
    total_loc = subtotal_bills + subtotal_coins
    st.markdown(
        f"<div style=\"text-align:right; font-family:'Roboto Mono', monospace; "
        f"font-size:1rem; font-weight:600; color:#FFFFFF; padding:8px 0; "
        f'border-top:1px solid rgba(255,255,255,0.10); margin-top:8px;">'
        f"Total: {total_loc:,.2f}€</div>",
        unsafe_allow_html=True,
    )

    return updated


@st.dialog("💶 Desglose de Efectivo", width="large")
def render_cash_dialog(
    metalico_fisico: float,
    saldo_cartera: float,
    saldo_hucha: float,
) -> None:
    """Modal con el desglose de billetes y monedas en Cartera y Hucha."""
    from data.gsheets import get_denominaciones, save_denominaciones

    data = get_denominaciones()

    # Verificación cruzada: comparar denominaciones actuales vs saldo contable
    total_denom_cartera = calc_total(data.get("cartera", {}))
    total_denom_hucha = calc_total(data.get("hucha", {}))
    total_denom = total_denom_cartera + total_denom_hucha
    diff = total_denom - metalico_fisico

    # Header con cross-check
    if abs(diff) < 0.01:
        st.markdown(
            f'<div style="background:rgba(0,230,118,0.08); border:1px solid rgba(0,230,118,0.25); '
            f"border-radius:10px; padding:10px 16px; margin-bottom:16px; "
            f"font-family:'Plus Jakarta Sans', sans-serif; font-size:0.85rem; color:{COLOR_POSITIVO};\">"
            f"✅ El desglose coincide con el saldo contable ({metalico_fisico:,.2f}€)</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); '
            f"border-radius:10px; padding:10px 16px; margin-bottom:16px; "
            f"font-family:'Plus Jakarta Sans', sans-serif; font-size:0.85rem; color:#F59E0B;\">"
            f"⚠️ Diferencia de <b>{diff:+,.2f}€</b> con el saldo contable ({metalico_fisico:,.2f}€).<br>"
            f'<span style="font-size:0.75rem; color:#71717A;">'
            f"Desglose: {total_denom:,.2f}€ · Cartera contable: {saldo_cartera:,.2f}€ · "
            f"Hucha contable: {saldo_hucha:,.2f}€</span></div>",
            unsafe_allow_html=True,
        )

    # Última actualización
    last_updated = data.get("last_updated", "")
    if last_updated:
        st.markdown(
            f'<div style="font-size:0.7rem; color:#71717A; margin-bottom:12px; '
            f"font-family:'Plus Jakarta Sans', sans-serif;\">"
            f"🕐 Última actualización: {last_updated}</div>",
            unsafe_allow_html=True,
        )

    # Dos columnas: Cartera | Hucha
    col_cartera, col_hucha = st.columns(2)

    template = get_empty_template()
    cartera_counts = data.get("cartera", template["cartera"])
    hucha_counts = data.get("hucha", template["hucha"])

    with col_cartera:
        st.markdown(
            "<div style=\"font-family:'Plus Jakarta Sans', sans-serif; "
            'font-size:1.1rem; font-weight:600; color:#FFFFFF; margin-bottom:4px;">'
            "👛 Cartera</div>"
            f'<div style="font-size:0.72rem; color:#71717A; margin-bottom:12px; '
            f"font-family:'Roboto Mono', monospace;\">"
            f"Saldo contable: {saldo_cartera:,.2f}€</div>",
            unsafe_allow_html=True,
        )
        updated_cartera = _render_denomination_inputs("cartera", cartera_counts)

    with col_hucha:
        st.markdown(
            "<div style=\"font-family:'Plus Jakarta Sans', sans-serif; "
            'font-size:1.1rem; font-weight:600; color:#FFFFFF; margin-bottom:4px;">'
            "🐷 Hucha</div>"
            f'<div style="font-size:0.72rem; color:#71717A; margin-bottom:12px; '
            f"font-family:'Roboto Mono', monospace;\">"
            f"Saldo contable: {saldo_hucha:,.2f}€</div>",
            unsafe_allow_html=True,
        )
        updated_hucha = _render_denomination_inputs("hucha", hucha_counts)

    # ── Grand Total + Save ──
    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
    grand_total = calc_total(updated_cartera) + calc_total(updated_hucha)
    new_diff = grand_total - metalico_fisico

    col_total, col_save = st.columns([3, 1])
    with col_total:
        diff_html = ""
        if abs(new_diff) >= 0.01:
            diff_html = (
                f' <span style="font-size:0.8rem; color:#F59E0B;">(dif: {new_diff:+,.2f}€)</span>'
            )
        st.markdown(
            f"<div style=\"font-family:'Roboto Mono', monospace; "
            f'font-size:1.3rem; font-weight:700; color:#FFFFFF; padding:8px 0;">'
            f"💶 Total: {grand_total:,.2f}€{diff_html}</div>",
            unsafe_allow_html=True,
        )
    with col_save:
        if st.button(
            "💾 Guardar", key="btn_save_denominations", type="primary", use_container_width=True
        ):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            save_denominaciones(updated_cartera, updated_hucha, now)
            st.toast("✅ Desglose guardado correctamente")
            st.rerun()
