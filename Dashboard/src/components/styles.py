"""
styles.py — CSS global inyectable en Streamlit.

Estilo Fintech Dark Bento con tipografía Inter.
Referencia: AGENTS.md §6.
"""

import streamlit as st

from constants import (
    COLOR_GASTOS,
    COLOR_INGRESOS,
    COLOR_TEXTO_PRIMARIO,
    COLOR_TEXTO_SECUNDARIO,
)

GLOBAL_CSS = f"""
<style>
    /* ── Tipografía ── */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;500&display=swap');

    .stApp {{
        background-color: #09090B;
        background-image: linear-gradient(rgba(9,9,11,0.78), rgba(9,9,11,0.92)),
                          url("app/static/Background.png");
        background-size: cover;
        background-position: center center;
        background-attachment: fixed;
        background-repeat: no-repeat;
        color: {COLOR_TEXTO_PRIMARIO};
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}
    /* Header transparente para que el fondo respire detrás */
    header[data-testid="stHeader"] {{
        background: transparent !important;
    }}

    /* Reducir espacio superior del Dashboard */
    .block-container {{
        padding-top: 2.5rem !important;
        padding-bottom: 2rem !important;
    }}

    /* ── Fintech Dark Bento Cards ── */
    .metric-card {{
        padding: 24px;
        text-align: left;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        background-color: #18181B;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
        /* La card se declara contenedor inline-size para que el valor
           pueda escalar con SU ancho real (no con el del viewport). */
        container-type: inline-size;
    }}
    .metric-card:hover {{
        border-color: rgba(255, 255, 255, 0.12);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }}
    /* Cards de la cabecera (header) — altura uniforme y compacta */
    .header-card {{
        height: 136px;
        padding: 16px 20px !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    /* Estilos para tarjetas de alerta según gravedad */
    .alert-header-subcard {{
        padding: 4px 8px !important;
        box-sizing: border-box !important;
        border-radius: 10px !important;
        height: 78px !important;
        min-height: 78px !important;
        max-height: 78px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        overflow: hidden !important;
        margin: 0 !important;
    }}
    .alert-card-critical {{
        background-color: rgba(225, 29, 72, 0.18) !important;
        border: 1px solid rgba(225, 29, 72, 0.45) !important;
    }}
    .alert-card-warning {{
        background-color: rgba(245, 158, 11, 0.18) !important;
        border: 1px solid rgba(245, 158, 11, 0.45) !important;
    }}
    .alert-card-info {{
        background-color: rgba(0, 184, 217, 0.18) !important;
        border: 1px solid rgba(0, 184, 217, 0.45) !important;
    }}
    .alert-card-ok {{
        background-color: rgba(16, 185, 129, 0.12) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }}

    .alert-label-critical {{
        color: #E11D48 !important;
        font-weight: 600 !important;
    }}
    .alert-label-warning {{
        color: #F59E0B !important;
        font-weight: 600 !important;
    }}
    .alert-label-info {{
        color: #00B8D9 !important;
        font-weight: 600 !important;
    }}

    /* Asegurar texto blanco y secundario en tarjetas de alerta, inmune a sanitización inline */
    .alert-card-critical div:not([class]),
    .alert-card-warning div:not([class]),
    .alert-card-info div:not([class]) {{
        color: #FFFFFF !important;
    }}
    .alert-card-critical .metric-subtitle,
    .alert-card-warning .metric-subtitle,
    .alert-card-info .metric-subtitle {{
        color: #A1A1AA !important;
    }}
    /* Cards del Resumen General (tab_diario) — altura uniforme y compacta */
    .resumen-card {{
        height: 200px;
        padding: 16px 20px !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 4px;
    }}
    /* (la regla responsive de .resumen-card .metric-value está más abajo
        junto al resto de overrides de cifras) */
    .resumen-card .metric-label {{
        font-size: 0.78rem;
    }}
    .resumen-card hr {{
        margin: 6px 0 4px 0;
        border-color: rgba(255, 255, 255, 0.06);
    }}
    /* Cards superiores del Portfolio (Patrimonio · SP500 · BRK · TR · Efectivo · Te Deben) */
    .portfolio-card {{
        height: 170px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    /* Cards de Análisis (Berkshire / Vanguard / Inversiones globales) — altura uniforme */
    .brk-analysis-card,
    .vanguard-analysis-card,
    .portfolio-analysis-card {{
        height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    /* Cards del bloque "Pay Yourself First" (info tab) */
    .pay-analysis-card {{
        height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    /* Cards del Análisis Fiscal — altura uniforme */
    .fiscal-card {{
        height: 170px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}

    /* ── Premium Card ── */
    .premium-card {{
        border: 1px solid rgba(255, 255, 255, 0.15);
        background: linear-gradient(145deg, #18181B 0%, #09090B 100%);
    }}
    .premium-card .metric-value {{ color: #FFFFFF !important; font-weight: 600; }}
    .premium-card .metric-label {{ color: rgba(255, 255, 255, 0.8) !important; }}

    /* ── Tipografía de métricas ──
       `font-size` se calcula como porcentaje del ancho del CONTAINER
       (la propia card) mediante `cqi` (container query inline), con
       cota inferior y superior. Así la cifra nunca se sale de la fila
       por mucho que crezca el patrimonio. `white-space: nowrap` impide
       que ` €` salte de línea cuando hay espacio justo. */
    .metric-value {{
        font-family: 'Roboto Mono', monospace;
        font-size: clamp(1.3rem, 11cqi, 2.4rem);
        font-weight: 500;
        letter-spacing: -0.05em;
        color: {COLOR_TEXTO_PRIMARIO};
        margin: 8px 0;
        line-height: 1.1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: clip;
    }}
    /* Cards en filas estrechas (6 columnas — `portfolio-card`) usan
       una pendiente más agresiva: el ancho disponible es ~16 % del
       viewport en desktop, así que necesitamos bajar la cota máxima. */
    .portfolio-card .metric-value {{
        font-size: clamp(1.1rem, 16cqi, 2.3rem);
    }}
    /* Cards de análisis (5 columnas en BRK/Vanguard, 5 en Inversiones).
       Margen visual ligeramente más generoso. */
    .brk-analysis-card .metric-value,
    .vanguard-analysis-card .metric-value,
    .portfolio-analysis-card .metric-value {{
        font-size: clamp(1.15rem, 11cqi, 2.1rem);
    }}
    /* Cards del resumen general (3 columnas amplias). */
    .resumen-card .metric-value {{
        font-size: clamp(1.4rem, 9cqi, 2.1rem);
        margin: 2px 0;
    }}
    .metric-label {{
        font-size: clamp(0.65rem, 4.2cqi, 0.85rem);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: {COLOR_TEXTO_SECUNDARIO};
        font-weight: 400;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: clip;
    }}
    /* Subtítulo de la card (debajo del valor): mismo principio responsive
       que `metric-value` — escala con el ancho del container, jamás
       se sale de una línea. */
    .metric-subtitle {{
        font-family: 'Roboto Mono', monospace;
        font-size: clamp(0.62rem, 3.8cqi, 0.82rem);
        margin-top: 4px;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: clip;
    }}
    /* En filas estrechas (6 cards), permitimos que baje un punto más. */
    .portfolio-card .metric-subtitle {{
        font-size: clamp(0.55rem, 4.2cqi, 0.78rem);
    }}
    .brk-analysis-card .metric-subtitle,
    .vanguard-analysis-card .metric-subtitle,
    .portfolio-analysis-card .metric-subtitle {{
        font-size: clamp(0.58rem, 3.6cqi, 0.8rem);
    }}

    /* ── Pills (Neón Bento Style) ── */
    .positive-pill {{
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        background-color: rgba(5, 150, 105, 0.12); border: none; color: #059669;
        font-family: 'Roboto Mono', monospace; font-size: 0.85rem; font-weight: 600;
    }}
    .negative-pill {{
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        background-color: rgba(225, 29, 72, 0.12); border: none; color: #E11D48;
        font-family: 'Roboto Mono', monospace; font-size: 0.85rem; font-weight: 600;
    }}

    /* ── Headings ── */
    h1, h2, h3, h4, h5, h6 {{
        font-weight: 500 !important;
        color: #FFFFFF !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: -0.02em;
    }}
    hr {{ border-color: rgba(255, 255, 255, 0.06) !important; }}

    /* ── Transitions ── */
    .transition-text {{ transition: color 0.5s ease; font-weight: 500; }}

    /* ── Plotly text cleanup ── */
    .js-plotly-plot text, .plotly text {{ text-shadow: none !important; }}

    /* ── Sankey link gradient hack ── */
    .js-plotly-plot .sankey-link {{ stroke-width: 0 !important; }}
    .js-plotly-plot path[style*="1, 2, 3"],
    .js-plotly-plot .sankey-link[style*="1, 2, 3"] {{
        fill: url(#sankey-gradient) !important;
        fill-opacity: 0.4 !important;
    }}

    /* ── DataFrames & Tables ── */
    div[data-testid="stDataFrame"] {{
        background-color: transparent !important;
    }}
    div[data-testid="stDataFrame"] table {{
        color: #FFFFFF !important;
    }}


    /* ── Popovers minimalistas de menú hamburguesa (☰) ── */
    div[data-testid="stPopover"] {{
        display: inline-flex;
        align-items: center;
        justify-content: flex-end;
    }}
    div[data-testid="stPopover"] > button {{
        background: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 8px !important;
        color: #A1A1AA !important;
        padding: 2px 8px !important;
        min-height: 28px !important;
        height: 28px !important;
        font-size: 1.05rem !important;
        line-height: 1 !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stPopover"] > button:hover {{
        background: rgba(255, 255, 255, 0.12) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        color: #FFFFFF !important;
    }}
    div[data-testid="stPopover"] > button p {{
        margin: 0 !important;
        padding: 0 !important;
        font-size: 1.05rem !important;
        font-family: inherit !important;
    }}

    /* ── Contenedor absoluto para el popover ☰ en la esquina superior derecha de la tarjeta 4 ── */
    .header-card-popover-container {{
        position: absolute !important;
        top: 10px !important;
        right: 10px !important;
        z-index: 999999 !important;
    }}
    .header-card-popover-container div[data-testid="stPopover"] > button {{
        background: rgba(255, 255, 255, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 8px !important;
        color: #F4F4F5 !important;
        padding: 2px 8px !important;
        min-height: 28px !important;
        height: 28px !important;
        font-size: 1.05rem !important;
        line-height: 1 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        cursor: pointer !important;
    }}
    .header-card-popover-container div[data-testid="stPopover"] > button:hover {{
        background: rgba(255, 255, 255, 0.25) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        color: #FFFFFF !important;
    }}

    /* ══════════════════════════════════════════════
       Streamlit Widgets Dark Override
       ══════════════════════════════════════════════ */

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent;
        /* Sin línea de fondo estática: dejamos sólo el indicador activo,
           que es el que se mueve al cambiar de pestaña. */
        border-bottom: none;
        gap: 0;
        /* Espaciado extra para separar el menú de pestañas de las tarjetas superiores */
        margin-top: 2rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: #71717A;
        background-color: transparent;
        border: none;
        padding: 10px 20px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 500;
        font-size: 0.9rem;
        transition: color 0.2s ease;
    }}
    .stTabs [aria-selected="true"] {{
        color: #FFFFFF !important;
        /* Sin border-bottom propio: dejamos que el indicador nativo
           animado de BaseWeb (el `tab-highlight`) sea el único
           subrayado. Antes había doble línea por superposición. */
        border-bottom: none !important;
        background-color: transparent !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: #FFFFFF;
    }}
    /* Indicador animado de la pestaña activa: blanco puro. Solo el highlight,
       no el border-bottom estático (que se queda invisible/gris por defecto). */
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: #FFFFFF !important;
    }}

    /* Logo de Flechas (Ingresos/Gastos) inyectado en la 1ª pestaña principal */
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(1),
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(1) {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(1)::before,
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(1)::before {{
        content: "";
        display: block;
        width: 24px;
        height: 24px;
        background-image: url("app/static/logo_arrows.png?v=2");
        background-size: contain;
        background-repeat: no-repeat;
    }}

    /* Logo de Portfolio inyectado en la 2ª pestaña principal */
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(2),
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(2) {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(2)::before,
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(2)::before {{
        content: "";
        display: block;
        width: 24px;
        height: 24px;
        background-image: url("app/static/logo_portfolio.png?v=2");
        background-size: contain;
        background-repeat: no-repeat;
    }}

    /* Logo de Hábitos inyectado en la 3ª pestaña principal */
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(3),
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(3) {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(3)::before,
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(3)::before {{
        content: "";
        display: block;
        width: 24px;
        height: 24px;
        background-image: url("app/static/logo_habitos.png?v=4");
        background-size: contain;
        background-repeat: no-repeat;
    }}

    /* Logo de Padres inyectado en la 4ª pestaña principal */
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(4),
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(4) {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(4)::before,
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(4)::before {{
        content: "";
        display: block;
        width: 24px;
        height: 24px;
        background-image: url("app/static/logo_padres.png?v=3");
        background-size: contain;
        background-repeat: no-repeat;
    }}

    /* Logo de Bokatas inyectado en la 5ª pestaña principal */
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(5),
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(5) {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    div.element-container:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(5)::before,
    div[data-testid="stElementContainer"]:has(#main-tabs-marker) + div[data-testid="stTabs"] [data-baseweb="tab-list"]:not([data-baseweb="tab-panel"] *) > [data-baseweb="tab"]:nth-child(5)::before {{
        content: "";
        display: block;
        width: 24px;
        height: 24px;
        /* Usar el PNG estático proporcionado por el usuario */
        background-image: url("app/static/logo_bokatas.png");
        background-size: contain;
        background-repeat: no-repeat;
    }}

    /* ── Contenedor del popover general: anchura holgada para mostrar icono + texto ── */
    div[data-baseweb="popover"]:has(#main-nav-popover-marker),
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) > div,
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) {{
        min-width: 185px !important;
        width: max-content !important;
        max-width: 250px !important;
        padding: 6px 8px !important;
        box-sizing: border-box !important;
    }}

    /* Logos y anchura uniforme 100% para las opciones del menú popover general */
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"],
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"],
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"],
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] {{
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
    }}

    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label {{
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        padding: 6px 10px !important;
        border-radius: 6px !important;
        transition: background-color 0.2s ease !important;
        cursor: pointer !important;
        width: 100% !important;
        box-sizing: border-box !important;
        font-size: 0.85rem !important;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label > div[data-testid="stMarkdownContainer"],
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label > div[data-testid="stMarkdownContainer"],
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"],
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] {{
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        flex: 1 !important;
        white-space: nowrap !important;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label > div[data-testid="stMarkdownContainer"] p,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label > div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {{
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        font-size: 0.85rem !important;
        color: #F4F4F5 !important;
        white-space: nowrap !important;
        margin: 0 !important;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:hover,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:hover {{
        background-color: rgba(255, 255, 255, 0.08) !important;
    }}

    /* Ocultar ÚNICAMENTE el círculo / indicador de selección de radio por completo */
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label [data-testid="stRadioButtonCustomIcon"],
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label [data-testid="stRadioButtonCustomIcon"],
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div[data-baseweb="radio"],
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div[data-baseweb="radio"],
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div:has(input[type="radio"]),
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div:has(input[type="radio"]),
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div:first-child:not([data-testid="stMarkdownContainer"]):not(:has([data-testid="stMarkdownContainer"])),
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label div:first-child:not([data-testid="stMarkdownContainer"]):not(:has([data-testid="stMarkdownContainer"])),
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label input[type="radio"],
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label input[type="radio"],
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label svg,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label svg {{
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        visibility: hidden !important;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label:has(input:checked),
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] label:has(input:checked) {{
        background-color: rgba(255, 255, 255, 0.12) !important;
    }}

    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(1)::before,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(1)::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 22px;
        min-width: 22px;
        background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='15' fill='%23000'/%3E%3Cpath d='M22 41.5l22-5l12 5l22-5v13l-22 5l-12-5l-22 5zM22 58.5l22-5l12 5l22-5v13l-22 5l-12-5l-22 5z' fill='%23fff'/%3E%3C/svg%3E");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(2)::before,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(2)::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 22px;
        min-width: 22px;
        background-image: url("app/static/logo_arrows.png?v=2");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(3)::before,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(3)::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 22px;
        min-width: 22px;
        background-image: url("app/static/logo_portfolio.png?v=2");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(4)::before,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(4)::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 22px;
        min-width: 22px;
        background-image: url("app/static/logo_habitos.png?v=4");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(5)::before,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(5)::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 22px;
        min-width: 22px;
        background-image: url("app/static/logo_padres.png?v=3");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(6)::before,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(6)::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 22px;
        min-width: 22px;
        background-image: url("app/static/logo_bokatas.png");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    div[data-testid="stPopoverBody"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(7)::before,
    div[data-baseweb="popover"]:has(#main-nav-popover-marker) div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(7)::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 22px;
        min-width: 22px;
        background-image: url("app/static/logo_guitarra.png?v=1");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}

    /* Distancia uniforme entre la lista de pestañas y la primera sección
       de cualquier tab en TODO el dashboard. Cualquier `<br>`, `margin-top`
       o `st.markdown` vacío que metan los tabs individuales queda neutralizado
       por este padding fijo en el `tabpanel`. */
    .stTabs [data-baseweb="tab-panel"] {{
        padding-top: 1.5rem !important;
    }}
    .stTabs [data-baseweb="tab-panel"] > div:first-child {{
        margin-top: 0 !important;
    }}

    /* Colapsar element-containers cuyo único contenido sea un `<style>` o un
       marker `display:none` (CSS escopados / anchors). Sin esto, esos st.markdown
       invisibles añaden un gap vertical y los tabs que los usan al inicio
       (Hábitos, Padres) arrancan más abajo que los que no los tienen. */
    div[data-testid="stElementContainer"]:has(> div[data-testid="stMarkdown"] style),
    div[data-testid="stElementContainer"]:has(
        > div[data-testid="stMarkdown"]
        > div[data-testid="stMarkdownContainer"]
        > div[style*="display:none"]:only-child
    ) {{
        display: none !important;
    }}

    /* Selectboxes, multiselects, text inputs */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {{
        background-color: #18181B !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        color: #FFFFFF !important;
    }}
    div[data-baseweb="popover"] > div {{
        background-color: #18181B !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
    }}
    [data-baseweb="menu"] {{
        background-color: #18181B !important;
    }}
    [data-baseweb="menu"] li {{
        color: #FFFFFF !important;
    }}
    [data-baseweb="menu"] li:hover {{
        background-color: rgba(255, 255, 255, 0.06) !important;
    }}

    /* MultiSelect base tag styling (Streamlit 1.60+ data-tag and BaseWeb fallback) */
    div[data-testid="stMultiSelect"] span[data-tag],
    div[data-testid="stMultiSelectTagsContainer"] span[data-tag],
    div.stMultiSelect span[data-tag],
    [data-baseweb="tag"] {{
        background-color: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 6px !important;
        color: #FFFFFF !important;
    }}
    div[data-testid="stMultiSelect"] span[data-tag] > span,
    div[data-testid="stMultiSelectTagsContainer"] span[data-tag] > span,
    div.stMultiSelect span[data-tag] > span,
    [data-baseweb="tag"] > span {{
        color: #FFFFFF !important;
    }}
    div[data-testid="stMultiSelect"] span[data-tag] button,
    div[data-testid="stMultiSelect"] span[data-tag] svg,
    div[data-testid="stMultiSelectTagsContainer"] span[data-tag] svg,
    [data-baseweb="tag"] svg {{
        color: #A1A1AA !important;
        fill: #A1A1AA !important;
    }}
    div[data-testid="stMultiSelect"] span[data-tag] svg path,
    div[data-testid="stMultiSelectTagsContainer"] span[data-tag] svg path {{
        stroke: #A1A1AA !important;
    }}
    div[data-testid="stMultiSelect"] span[data-tag] button:hover svg,
    div[data-testid="stMultiSelect"] span[data-tag] button:hover svg path,
    [data-baseweb="tag"] svg:hover {{
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }}

    /* Expanders */
    details[data-testid="stExpander"] {{
        background-color: #18181B;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
    }}
    details[data-testid="stExpander"] summary {{
        color: #FFFFFF;
    }}

    /* Buttons */
    .stButton > button {{
        background-color: #18181B !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 500;
        transition: all 0.2s ease;
    }}
    .stButton > button:hover {{
        background-color: #27272A !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
    }}

    /* ── Botones Sidebar Unificados (Estética idéntica y texto alineado a la izquierda) ── */
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] .stLinkButton > a,
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button,
    section[data-testid="stSidebar"] div[data-testid="stLinkButton"] > a {{
        background-color: #18181B !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
        padding: 0 14px !important;
        height: 42px !important;
        min-height: 42px !important;
        width: 100% !important;
        box-sizing: border-box !important;
        text-decoration: none !important;
        box-shadow: none !important;
        cursor: pointer !important;
        pointer-events: auto !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover,
    section[data-testid="stSidebar"] .stLinkButton > a:hover,
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover,
    section[data-testid="stSidebar"] div[data-testid="stLinkButton"] > a:hover {{
        background-color: #27272A !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] .stButton > button p,
    section[data-testid="stSidebar"] .stLinkButton > a p,
    section[data-testid="stSidebar"] .stButton > button div,
    section[data-testid="stSidebar"] .stLinkButton > a div,
    section[data-testid="stSidebar"] .stButton > button span,
    section[data-testid="stSidebar"] .stLinkButton > a span {{
        text-align: left !important;
        justify-content: flex-start !important;
        display: flex !important;
        align-items: center !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        color: #FFFFFF !important;
        pointer-events: none !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: #0F0F11 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.04);
    }}
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span {{
        color: #A1A1AA !important;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: #FFFFFF !important;
    }}

    /* Sliders */
    div[data-testid="stSlider"] > div > div > div {{
        color: #A1A1AA !important;
    }}

    /* Toggle */
    div[data-testid="stToggle"] {{
        background: rgba(24, 24, 27, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease-in-out !important;
    }}
    div[data-testid="stToggle"]:hover {{
        border-color: rgba(255, 255, 255, 0.16) !important;
        background: rgba(39, 39, 42, 0.6) !important;
    }}
    div[data-testid="stToggle"] label p {{
        color: #F4F4F5 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }}

    /* Checked State for Streamlit Toggle Switch Track */
    div[data-testid="stToggle"] input[type="checkbox"]:checked ~ div,
    div[data-testid="stToggle"] [aria-checked="true"],
    div[data-testid="stToggle"] div[aria-checked="true"] > div:first-child,
    div[data-testid="stToggle"] span[data-testid="stToggleSwitch"][aria-checked="true"] {{
        background-color: #00B8D9 !important;
        border-color: #00B8D9 !important;
    }}

    /* Handle/Knob inside the toggle switch */
    div[data-testid="stToggle"] input[type="checkbox"]:checked ~ div > div,
    div[data-testid="stToggle"] [aria-checked="true"] span,
    div[data-testid="stToggle"] [aria-checked="true"] div > div {{
        background-color: #FFFFFF !important;
    }}

    /* Success/Warning/Error/Info banners */
    div[data-testid="stAlert"] {{
        background-color: rgba(24, 24, 27, 0.8) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
    }}

    /* Captions */
    .stCaption, small, .stMarkdown small {{
        color: #71717A !important;
    }}

    /* Metric native streamlit (fallback) */
    div[data-testid="stMetricValue"] {{
        color: #FFFFFF !important;
        font-family: 'Roboto Mono', monospace !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: #A1A1AA !important;
    }}

    /* Radio buttons */
    div[data-testid="stRadio"] label {{
        color: #A1A1AA !important;
    }}
    div[data-testid="stRadio"] label[data-checked="true"] {{
        color: #FFFFFF !important;
    }}

    /* Checkbox */
    div[data-testid="stCheckbox"] label span {{
        color: #A1A1AA !important;
    }}

    /* ── Cash Denomination Dialog ── */
    /* Dialog: inputs más compactos */
    div[data-testid="stDialog"] div[data-testid="stNumberInput"] input {{
        background-color: #18181B !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        font-family: 'Roboto Mono', monospace !important;
        font-size: 0.85rem !important;
        text-align: center !important;
        height: 32px !important;
        padding: 2px 6px !important;
    }}
    div[data-testid="stDialog"] div[data-testid="stNumberInput"] button {{
        background-color: #18181B !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        color: #A1A1AA !important;
        height: 32px !important;
    }}
    div[data-testid="stDialog"] div[data-testid="stNumberInput"] button:hover {{
        background-color: #27272A !important;
        color: #FFFFFF !important;
    }}

    /* ── Tamaños Tipográficos de la Tarjeta de Cita (Quote Card) ── */
    .quote-len-180 {{ font-size: 0.78rem !important; }}
    .quote-len-140 {{ font-size: 0.86rem !important; }}
    .quote-len-100 {{ font-size: 0.95rem !important; }}
    .quote-len-70 {{ font-size: 1.05rem !important; }}
    .quote-len-40 {{ font-size: 1.18rem !important; }}
    .quote-len-0 {{ font-size: 1.32rem !important; }}

    /* ── Tamaños Tipográficos de Inv. Obligatoria ── */
    .inv-oblig-details {{ font-size: 0.75rem !important; }}
    .inv-oblig-total {{ font-size: 1.8rem !important; }}

    /* ── Skeleton Loaders (Carga Progresiva / Shimmer Effect) ── */
    @keyframes skeleton-shimmer {{
        0% {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}

    .skeleton-box {{
        background: linear-gradient(90deg, #18181B 25%, #27272A 37%, #18181B 63%) !important;
        background-size: 400% 100% !important;
        animation: skeleton-shimmer 1.4s ease infinite !important;
        border-radius: 8px !important;
    }}

    .skeleton-card {{
        background: #18181B !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.3) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        box-sizing: border-box !important;
    }}

    .skeleton-line {{
        height: 12px;
        margin-bottom: 8px;
        border-radius: 4px;
    }}

    .skeleton-line-title {{
        width: 45%;
        height: 14px;
    }}

    .skeleton-line-value {{
        width: 70%;
        height: 28px;
        margin-top: 6px;
        margin-bottom: 6px;
    }}

    .skeleton-line-sub {{
        width: 60%;
        height: 10px;
    }}

    /* Rediseño elegante de st.spinner a Skeleton Loader en Streamlit */
    div[data-testid="stSpinner"] {{
        background: rgba(24, 24, 27, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 18px 24px !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35) !important;
    }}
    div[data-testid="stSpinner"] > div {{
        border-top-color: #00B8D9 !important;
    }}
    div[data-testid="stSpinner"] span {{
        color: #E4E4E7 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }}

    /* ══════════════════════════════════════════════
       Responsive: Portrait orientation
       ══════════════════════════════════════════════
       Detecta cuando height > width (monitor vertical, tablet portrait,
       móvil vertical). Reorganiza los layouts de Streamlit columns sin
       tocar Python — sobreescribe el flexbox nativo de st.columns con
       CSS Grid para redistribuir las cards.
    */

    @media (orientation: portrait) {{

        /* ── Padding general más compacto ── */
        .block-container {{
            padding-left: 1.2rem !important;
            padding-right: 1.2rem !important;
        }}

        /* ── Portfolio cards: 6 columnas → grid 3×2 ──
           Streamlit renderiza st.columns(6) como un div con
           data-testid="stHorizontalBlock" y 6 hijos flex.
           Lo convertimos a CSS Grid 3 columnas. */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-card) {{
            display: grid !important;
            grid-template-columns: repeat(3, 1fr) !important;
            gap: 10px !important;
        }}
        /* Eliminar el flex-basis/width fijo que Streamlit pone en cada hijo */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-card) > div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: none !important;
        }}

        /* ── Header cards: 3-4 columnas → grid 2×2 ── */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .header-card) {{
            display: grid !important;
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 10px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .header-card) > div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: none !important;
        }}

        /* ── Gráficos (donut + stacked area): lado a lado → apilados ──
           Cualquier HorizontalBlock que contenga un gráfico Plotly se
           convierte en flex-column para apilar verticalmente. */
        div[data-testid="stHorizontalBlock"]:has(.js-plotly-plot) {{
            flex-direction: column !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.js-plotly-plot) > div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: none !important;
        }}

        /* ── Tabs principales: scroll horizontal ──
           En portrait los 6 tabs con iconos no caben, los hacemos
           scrolleables con swipe. */
        .stTabs [data-baseweb="tab-list"] {{
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            flex-wrap: nowrap !important;
        }}
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {{
            display: none;
        }}
        .stTabs [data-baseweb="tab"] {{
            flex-shrink: 0 !important;
            padding: 8px 14px !important;
            font-size: 0.85rem !important;
        }}

        /* ── Cards de análisis (5 cols → grid 3+2) ── */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .brk-analysis-card),
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .vanguard-analysis-card),
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-analysis-card) {{
            display: grid !important;
            grid-template-columns: repeat(3, 1fr) !important;
            gap: 10px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .brk-analysis-card) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .vanguard-analysis-card) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-analysis-card) > div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: none !important;
        }}

        /* ── Cards Resumen Diario (3 cols) → stack 1×3 si < 900px,
              en portrait normal (1080px) mantener 3 cols ── */

        /* ── Fiscal cards (3-4 cols → 2×2) ── */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .fiscal-card) {{
            display: grid !important;
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 10px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .fiscal-card) > div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: none !important;
        }}

        /* ── Pay-analysis cards → 2 columnas ── */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .pay-analysis-card) {{
            display: grid !important;
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 10px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .pay-analysis-card) > div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: none !important;
        }}

        /* ── Tamaños Tipográficos de la Tarjeta de Cita (Quote Card) en Portrait ── */
        .quote-len-180 {{ font-size: 0.72rem !important; }}
        .quote-len-140 {{ font-size: 0.78rem !important; }}
        .quote-len-100 {{ font-size: 0.86rem !important; }}
        .quote-len-70 {{ font-size: 0.95rem !important; }}
        .quote-len-40 {{ font-size: 1.05rem !important; }}
        .quote-len-0 {{ font-size: 1.18rem !important; }}

        /* ── Tamaños Tipográficos de Inv. Obligatoria en Portrait ── */
        .inv-oblig-details {{ font-size: 0.65rem !important; line-height: 1.3 !important; }}
        .inv-oblig-total {{ font-size: 1.3rem !important; }}

        /* ── Alturas de cards reducidas para aprovechar espacio ── */
        .portfolio-card {{ height: 148px !important; }}
        .header-card {{ height: 130px !important; }}
        .brk-analysis-card,
        .vanguard-analysis-card,
        .portfolio-analysis-card {{ height: 158px !important; }}

        /* ── Botones externos del header: más compactos ── */
        .header-btn {{
            width: 160px !important;
            font-size: 0.75rem !important;
            padding: 0 10px !important;
            height: 36px !important;
        }}
    }}

    /* ── Breakpoint adicional: tablets y ventanas estrechas ── */
    @media (orientation: portrait) and (max-width: 768px) {{

        .block-container {{
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }}

        /* Portfolio: de 3×2 a 2×3 */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-card) {{
            grid-template-columns: repeat(2, 1fr) !important;
        }}

        /* Header: stack vertical */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .header-card) {{
            grid-template-columns: 1fr !important;
        }}

        /* Análisis: 2 columnas */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .brk-analysis-card),
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .vanguard-analysis-card),
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-analysis-card) {{
            grid-template-columns: repeat(2, 1fr) !important;
        }}

        /* Resumen diario: stack */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .resumen-card) {{
            display: grid !important;
            grid-template-columns: 1fr !important;
            gap: 10px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .resumen-card) > div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: none !important;
        }}

        /* ── Tamaños Tipográficos de la Tarjeta de Cita (Quote Card) en Portrait Mobile ── */
        .quote-len-180 {{ font-size: 0.68rem !important; }}
        .quote-len-140 {{ font-size: 0.72rem !important; }}
        .quote-len-100 {{ font-size: 0.78rem !important; }}
        .quote-len-70 {{ font-size: 0.86rem !important; }}
        .quote-len-40 {{ font-size: 0.95rem !important; }}
        .quote-len-0 {{ font-size: 1.05rem !important; }}

        /* ── Tamaños Tipográficos de Inv. Obligatoria en Portrait Mobile ── */
        .inv-oblig-details {{ font-size: 0.60rem !important; line-height: 1.2 !important; }}
        .inv-oblig-total {{ font-size: 1.2rem !important; }}

        .portfolio-card {{ height: 135px !important; }}
        .header-card {{ height: 120px !important; }}
    }}

    /* ── Breakpoint: móvil (<480px) ── */
    @media (orientation: portrait) and (max-width: 480px) {{

        .block-container {{
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }}

        /* Portfolio: stack 1 columna */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-card) {{
            grid-template-columns: 1fr !important;
        }}

        /* Análisis: stack 1 columna */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .brk-analysis-card),
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .vanguard-analysis-card),
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .portfolio-analysis-card) {{
            grid-template-columns: 1fr !important;
        }}

        /* Fiscal: stack */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > .fiscal-card) {{
            grid-template-columns: 1fr !important;
        }}

        .metric-card {{
            padding: 12px !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            padding: 6px 10px !important;
            font-size: 0.78rem !important;
        }}
    }}

</style>

<!-- SVG Gradient Definition for Sankey -->
<svg width="0" height="0" style="position: absolute;">
  <defs>
    <linearGradient id="sankey-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{COLOR_INGRESOS}" stop-opacity="1" />
      <stop offset="100%" stop-color="{COLOR_GASTOS}" stop-opacity="1" />
    </linearGradient>
  </defs>
</svg>
"""


def inject_multiselect_colors(selected_labels: list[str], color_map: dict[str, str]) -> None:
    """
    Inyecta CSS dinámico para colorear los tags de un st.multiselect.
    Soporta tanto Streamlit moderno (1.60+ con data-tag y aria-label)
    como versiones clásicas con BaseWeb (data-baseweb="tag").
    """
    if not color_map:
        return

    css_lines = []

    # 1. Reglas directas por aria-label para todas las series conocidas
    for label, color in color_map.items():
        if not color:
            continue
        r, g, b = 255, 255, 255
        if color.startswith("#") and len(color) == 7:
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

        sel_pill = (
            f'div[data-testid="stMultiSelect"] span[data-tag][aria-label="{label}"], '
            f'div[data-testid="stMultiSelectTagsContainer"] span[data-tag][aria-label="{label}"]'
        )
        css_lines.append(
            f"{sel_pill} {{ "
            f"background-color: rgba({r}, {g}, {b}, 0.16) !important; "
            f"border: 1px solid {color} !important; "
            f"border-radius: 6px !important; "
            f"color: {color} !important; }}"
        )
        sel_text = (
            f'div[data-testid="stMultiSelect"] span[data-tag][aria-label="{label}"] > span, '
            f'div[data-testid="stMultiSelectTagsContainer"] span[data-tag][aria-label="{label}"] > span'
        )
        css_lines.append(
            f"{sel_text} {{ color: {color} !important; font-weight: 500 !important; }}"
        )
        sel_icon = (
            f'div[data-testid="stMultiSelect"] span[data-tag][aria-label="{label}"] button, '
            f'div[data-testid="stMultiSelect"] span[data-tag][aria-label="{label}"] svg, '
            f'div[data-testid="stMultiSelectTagsContainer"] span[data-tag][aria-label="{label}"] svg'
        )
        css_lines.append(f"{sel_icon} {{ color: {color} !important; fill: {color} !important; }}")
        sel_icon_path = (
            f'div[data-testid="stMultiSelect"] span[data-tag][aria-label="{label}"] svg path, '
            f'div[data-testid="stMultiSelectTagsContainer"] span[data-tag][aria-label="{label}"] svg path'
        )
        css_lines.append(f"{sel_icon_path} {{ stroke: {color} !important; }}")

    # 2. Reglas posicionales (por índice) para etiquetas seleccionadas y BaseWeb
    for i, label in enumerate(selected_labels or []):
        color = color_map.get(label)
        if not color:
            continue
        r, g, b = 255, 255, 255
        if color.startswith("#") and len(color) == 7:
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

        sel_pill_idx = (
            f'div[data-testid="stMultiSelect"] span[data-tag-index="{i}"], '
            f'div[data-testid="stMultiSelectTagsContainer"] [role="group"] > span:nth-child({i + 1}), '
            f'[data-baseweb="tag"]:nth-child({i + 1})'
        )
        css_lines.append(
            f"{sel_pill_idx} {{ "
            f"background-color: rgba({r}, {g}, {b}, 0.16) !important; "
            f"border: 1px solid {color} !important; "
            f"border-radius: 6px !important; "
            f"color: {color} !important; }}"
        )
        sel_text_idx = (
            f'div[data-testid="stMultiSelect"] span[data-tag-index="{i}"] > span, '
            f'div[data-testid="stMultiSelectTagsContainer"] [role="group"] > span:nth-child({i + 1}) > span, '
            f'[data-baseweb="tag"]:nth-child({i + 1}) > span, '
            f'[data-baseweb="tag"]:nth-child({i + 1}) span[title="{label}"]'
        )
        css_lines.append(
            f"{sel_text_idx} {{ color: {color} !important; font-weight: 500 !important; }}"
        )
        sel_icon_idx = (
            f'div[data-testid="stMultiSelect"] span[data-tag-index="{i}"] svg, '
            f'div[data-testid="stMultiSelectTagsContainer"] [role="group"] > span:nth-child({i + 1}) svg, '
            f'[data-baseweb="tag"]:nth-child({i + 1}) svg'
        )
        css_lines.append(
            f"{sel_icon_idx} {{ color: {color} !important; fill: {color} !important; }}"
        )
        sel_icon_path_idx = (
            f'div[data-testid="stMultiSelect"] span[data-tag-index="{i}"] svg path, '
            f'div[data-testid="stMultiSelectTagsContainer"] [role="group"] > span:nth-child({i + 1}) svg path'
        )
        css_lines.append(f"{sel_icon_path_idx} {{ stroke: {color} !important; }}")

    # Hover para que la cruz se ilumine al pasar el ratón
    css_lines.append(
        'div[data-testid="stMultiSelect"] span[data-tag] button:hover svg path { stroke: #FFFFFF !important; }'
    )

    if css_lines:
        style_block = f"<style>{' '.join(css_lines)}</style>"
        st.markdown(style_block, unsafe_allow_html=True)


def inject_cipher_js() -> None:
    """Inyecta un script JavaScript para cifrar en tiempo real todos los números en pantalla (incluyendo gráficos SVG de Plotly y pestañas)."""
    try:
        from services.demo_data import is_cipher_mode

        if not is_cipher_mode():
            return
    except Exception:
        return

    js_code = """
    <script>
    (function() {
        const doc = (window.parent && window.parent.document) ? window.parent.document : document;
        const win = doc.defaultView || window;
        const pool = ['%', '$', '.', 'F', 'R', '/', 'X', 'T', 'Ø', 'Ɛ', 'ϛ', 'ㄥ', '§', 'Ψ', 'Ω', '⇂', '‡', '⌘', 'Ж', '¥'];

        function cipherString(str) {
            if (!str || typeof str !== 'string') return str;
            let digitIdx = 0;
            return str.replace(/\\d/g, function(d) {
                const num = parseInt(d, 10);
                const sym = pool[(num + digitIdx * 3) % pool.length];
                digitIdx++;
                return sym;
            });
        }

        function cipherElement(el) {
            if (!el) return;
            // 1. Cifrado de nodos de texto simples
            try {
                const walker = doc.createTreeWalker(
                    el,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            if (!node.nodeValue || !/\\d/.test(node.nodeValue)) return NodeFilter.FILTER_SKIP;
                            const p = node.parentElement;
                            if (!p) return NodeFilter.FILTER_SKIP;
                            const pName = p.tagName ? p.tagName.toUpperCase() : '';
                            if (['SCRIPT', 'STYLE', 'INPUT', 'TEXTAREA', 'A', 'BUTTON'].includes(pName)) return NodeFilter.FILTER_SKIP;
                            if (p.closest && (
                                p.closest('[data-testid="stToggle"]') ||
                                p.closest('[data-testid="stLinkButton"]') ||
                                p.closest('[data-testid="stButton"]') ||
                                p.closest('a') ||
                                p.closest('button')
                            )) return NodeFilter.FILTER_SKIP;
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                let n;
                while (n = walker.nextNode()) {
                    n.nodeValue = cipherString(n.nodeValue);
                }
            } catch(e) {}

            // 2. Cifrado explícito de elementos SVG (Plotly charts, Donut center, slices, ejes, tooltips)
            try {
                const svgNodes = el.querySelectorAll ? el.querySelectorAll('svg text, svg tspan, .js-plotly-plot text, .js-plotly-plot tspan, .annotation-text, .slicetext, .xtick text, .ytick text, g.xtick, g.ytick, .xtick, .ytick, .hovertext') : [];
                svgNodes.forEach(node => {
                    if (node.textContent && /\\d/.test(node.textContent)) {
                        let hasScrambled = false;
                        for (let child of node.childNodes) {
                            if (child.nodeType === 3 && child.nodeValue && /\\d/.test(child.nodeValue)) {
                                child.nodeValue = cipherString(child.nodeValue);
                                hasScrambled = true;
                            }
                        }
                        if (!hasScrambled && node.children.length === 0) {
                            node.textContent = cipherString(node.textContent);
                        }
                    }
                });
            } catch(e) {}

            // 3. Recorrido recursivo de iframes (st.plotly_chart y componentes personalizados)
            try {
                const iframes = el.querySelectorAll ? el.querySelectorAll('iframe') : [];
                iframes.forEach(iframe => {
                    try {
                        const iDoc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
                        if (iDoc && iDoc.body) {
                            // Cifrar contenido dentro del iframe
                            const iWalker = iDoc.createTreeWalker(
                                iDoc.body,
                                NodeFilter.SHOW_TEXT,
                                {
                                    acceptNode: function(n) {
                                        return (n.nodeValue && /\\d/.test(n.nodeValue)) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
                                    }
                                }
                            );
                            let inode;
                            while (inode = iWalker.nextNode()) {
                                inode.nodeValue = cipherString(inode.nodeValue);
                            }
                            const iSvg = iDoc.querySelectorAll('svg text, svg tspan, .js-plotly-plot text, .js-plotly-plot tspan, .annotation-text, .slicetext, .xtick text, .ytick text, g.xtick, g.ytick, .xtick, .ytick, .hovertext');
                            iSvg.forEach(node => {
                                if (node.textContent && /\\d/.test(node.textContent)) {
                                    let hasScrambled = false;
                                    for (let child of node.childNodes) {
                                        if (child.nodeType === 3 && child.nodeValue && /\\d/.test(child.nodeValue)) {
                                            child.nodeValue = cipherString(child.nodeValue);
                                            hasScrambled = true;
                                        }
                                    }
                                    if (!hasScrambled && node.children.length === 0) {
                                        node.textContent = cipherString(node.textContent);
                                    }
                                }
                            });
                        }
                    } catch(err) {}
                });
            } catch(e) {}
        }

        // Ejecutar barrido inmediato en todo el cuerpo del documento principal
        cipherElement(doc.body);

        // Observer persistente de mutaciones del DOM principal
        if (!win._globalCipherObserver) {
            win._globalCipherObserver = new MutationObserver(mutations => {
                for (let mut of mutations) {
                    for (let added of mut.addedNodes) {
                        if (added.nodeType === 1 || added.nodeType === 3) {
                            cipherElement(added);
                        }
                    }
                    if (mut.type === 'characterData') {
                        cipherElement(mut.target.parentElement || doc.body);
                    }
                }
            });
            win._globalCipherObserver.observe(doc.body, { childList: true, subtree: true, characterData: true });
        }

        // Re-barrido periódico ultrasrápido (100ms) sobre doc.body
        if (!win._globalCipherInterval) {
            win._globalCipherInterval = setInterval(() => {
                cipherElement(doc.body);
            }, 100);
        }
    })();
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)
