"""components.skeleton — Componentes reutilizables de Skeleton Loaders (Carga Progresiva)."""

from __future__ import annotations

import streamlit as st


def render_skeleton_cards(count: int = 3, height: int = 136) -> str:
    """Devuelve el HTML animado de N tarjetas Bento esqueleto con efecto Shimmer."""
    cards_html = []
    for _ in range(count):
        cards_html.append(
            f"""
            <div class="skeleton-card" style="height:{height}px;">
                <div class="skeleton-box skeleton-line skeleton-line-title"></div>
                <div class="skeleton-box skeleton-line skeleton-line-value"></div>
                <div class="skeleton-box skeleton-line skeleton-line-sub"></div>
            </div>
            """
        )
    return "".join(cards_html)


def render_skeleton_header() -> None:
    """Renderiza el esqueleto de la cabecera (3 columnas superiores)."""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(render_skeleton_cards(count=1, height=136), unsafe_allow_html=True)
    with c2:
        st.markdown(render_skeleton_cards(count=1, height=136), unsafe_allow_html=True)
    with c3:
        st.markdown(render_skeleton_cards(count=1, height=136), unsafe_allow_html=True)


def render_skeleton_chart(height: int = 420) -> None:
    """Renderiza un bloque esqueleto animado para gráficos de Plotly."""
    chart_html = f"""
    <div class="skeleton-card" style="height:{height}px; justify-content:space-between; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div class="skeleton-box" style="width:30%; height:16px;"></div>
            <div class="skeleton-box" style="width:15%; height:14px;"></div>
        </div>
        <div style="display:flex; align-items:flex-end; gap:12px; height:{height - 90}px; margin-top:20px;">
            <div class="skeleton-box" style="width:14%; height:45%;"></div>
            <div class="skeleton-box" style="width:14%; height:70%;"></div>
            <div class="skeleton-box" style="width:14%; height:55%;"></div>
            <div class="skeleton-box" style="width:14%; height:85%;"></div>
            <div class="skeleton-box" style="width:14%; height:60%;"></div>
            <div class="skeleton-box" style="width:14%; height:90%;"></div>
            <div class="skeleton-box" style="width:14%; height:75%;"></div>
        </div>
    </div>
    """
    st.markdown(chart_html, unsafe_allow_html=True)
