"""tabs.diario.roundup — Sección "Round-up pendiente".

Lista los últimos gastos pagados FUERA de TR (121) que tienen céntimos
sin redondear, y permite simular el Round-Up automático de TR enviando
esos céntimos desde TR (121) a Berkshire Hathaway (141). Persiste los
fingerprints ya redondeados en `Dashboard/src/data/backups/_roundup_done.json`
para evitar duplicados entre sesiones.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import streamlit as st

from components.metric_card import render_metric_card
from constants import COLOR_BERKSHIRE, COLOR_TEXTO_SECUNDARIO, TICKER_BRK, TICKER_EURUSD
from data.gsheets import append_to_diario, get_diario
from data.yahoo import get_yahoo_price
from services.roundup import (
    build_roundup_journal_rows,
    get_pending_roundups,
)

from .context import DiarioContext

log = logging.getLogger(__name__)

_DONE_FILE = (
    Path(__file__).resolve().parent.parent.parent / "data" / "backups" / "_roundup_done.json"
)


def _load_done() -> set[str]:
    try:
        if _DONE_FILE.exists():
            return set(json.loads(_DONE_FILE.read_text(encoding="utf-8")))
    except Exception as e:
        log.warning("No se pudo leer %s: %s", _DONE_FILE, e)
    return set()


def _save_done(done: set[str]) -> None:
    try:
        _DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DONE_FILE.write_text(json.dumps(sorted(done)), encoding="utf-8")
    except Exception as e:
        log.warning("No se pudo escribir %s: %s", _DONE_FILE, e)


def _get_brk_price_eur() -> float | None:
    """Precio actual de BRK en EUR (USD × usd_to_eur). None si Yahoo falla."""
    try:
        usd = get_yahoo_price(TICKER_BRK)
        fx = get_yahoo_price(TICKER_EURUSD)
        if not usd or not fx:
            return None
        return float(usd) * float(fx)
    except Exception as e:
        log.debug("No se pudo obtener precio BRK EUR: %s", e)
        return None


def render_roundup(ctx: DiarioContext) -> None:
    """Sección "Round-up pendiente"."""
    done = _load_done()
    df_pending = get_pending_roundups(ctx.df_diario, already_done_fingerprints=done)

    total_potencial = float(df_pending["Céntimos"].sum()) if not df_pending.empty else 0.0
    n_pendientes = len(df_pending)
    brk_price_eur = _get_brk_price_eur()

    # ── Card hero compacta: ocupa solo 1/3 del ancho ──
    subtitle = (
        f"{n_pendientes} gasto{'s' if n_pendientes != 1 else ''} fuera de TR · → 141 BRK"
        if n_pendientes > 0
        else "¡Al día!"
    )
    col_hero, _spacer = st.columns([1, 2])
    with col_hero:
        st.markdown(
            render_metric_card(
                "ROUND-UP PENDIENTE",
                f"{total_potencial:,.2f} €",
                color=COLOR_BERKSHIRE,
                bg_color=COLOR_BERKSHIRE,
                subtitle=subtitle,
            ),
            unsafe_allow_html=True,
        )

    if n_pendientes == 0:
        return

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

    # ── Botón "Redondear TODOS" ──
    bulk_col, _ = st.columns([1, 3])
    with bulk_col:
        if st.button(
            f"🔁 Redondear los {n_pendientes} ({total_potencial:,.2f} €) → BRK",
            use_container_width=True,
            key="btn_roundup_all",
        ):
            all_rows = []
            new_done = set(done)
            for _, r in df_pending.iterrows():
                all_rows.extend(
                    build_roundup_journal_rows(
                        float(r["Céntimos"]),
                        str(r.get("Descripción") or ""),
                        brk_price_eur=brk_price_eur,
                    )
                )
                new_done.add(str(r["Fingerprint"]))
            if append_to_diario(all_rows):
                _save_done(new_done)
                get_diario.clear()
                st.success(
                    f"✅ {n_pendientes} round-ups insertados — "
                    f"{total_potencial:,.2f} € a Berkshire Hathaway."
                )
                st.rerun()
            else:
                st.error("No se pudo insertar en el Diario.")

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

    # ── Tabla de pendientes con botón por fila ──
    header_cols = st.columns([1.5, 2.5, 4, 1, 1, 1.2])
    for col, label in zip(
        header_cols, ["Fecha", "Categoría", "Descripción", "Importe", "Céntimos", ""], strict=False
    ):
        col.markdown(
            f"<div style='font-size:0.72rem; text-transform:uppercase; "
            f"letter-spacing:0.08em; color:{COLOR_TEXTO_SECUNDARIO}; "
            f"font-weight:500;'>{label}</div>",
            unsafe_allow_html=True,
        )

    for idx, r in df_pending.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2.5, 4, 1, 1, 1.2])
        fecha_str = (
            r["Fecha"].strftime("%d %b") if hasattr(r["Fecha"], "strftime") else str(r["Fecha"])
        )
        c1.markdown(
            f"<div style='font-family:Roboto Mono,monospace; color:#E4E4E7; padding-top:8px;'>"
            f"{fecha_str}</div>",
            unsafe_allow_html=True,
        )
        c2.markdown(
            f"<div style='color:#A1A1AA; padding-top:8px;'>{r['Cuenta']}</div>",
            unsafe_allow_html=True,
        )
        desc = str(r.get("Descripción") or "")[:50]
        c3.markdown(
            f"<div style='color:#E4E4E7; padding-top:8px;'>{desc}</div>",
            unsafe_allow_html=True,
        )
        c4.markdown(
            f"<div style='font-family:Roboto Mono,monospace; color:#FFFFFF; "
            f"padding-top:8px; text-align:right;'>{r['Debe']:,.2f}</div>",
            unsafe_allow_html=True,
        )
        c5.markdown(
            f"<div style='font-family:Roboto Mono,monospace; "
            f"color:{COLOR_BERKSHIRE}; padding-top:8px; text-align:right; "
            f"font-weight:600;'>+{r['Céntimos']:,.2f}</div>",
            unsafe_allow_html=True,
        )
        with c6:
            # idx + fingerprint para evitar colisiones cuando hay 2 gastos
            # idénticos el mismo día (fingerprint repetido).
            if st.button(
                "🔁",
                key=f"btn_roundup_{idx}_{r['Fingerprint']}",
                help="Redondear a Berkshire Hathaway (141)",
            ):
                rows = build_roundup_journal_rows(
                    float(r["Céntimos"]),
                    str(r.get("Descripción") or ""),
                    brk_price_eur=brk_price_eur,
                )
                if append_to_diario(rows):
                    new_done = set(done)
                    new_done.add(str(r["Fingerprint"]))
                    _save_done(new_done)
                    get_diario.clear()
                    st.success(f"+{r['Céntimos']:,.2f} € → BRK")
                    st.rerun()
                else:
                    st.error("Error insertando en el Diario.")
