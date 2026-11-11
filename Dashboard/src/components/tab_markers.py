"""
tab_markers.py — Helper para inyectar markers DOM + CSS scoped por-tab.

PATRÓN: cada tab con identidad de color (Padres lavanda, Bokatas azul,
Hábitos burdeos, etc.) repite la misma estructura CSS:

    <div id="X-tab-marker" style="display:none;"></div>
    <style>
        div.element-container:has(#X-tab-marker) ~ div button[kind=...] {
            border: 1px solid rgba(R,G,B,0.25);
            border-left: 3px solid <accent>;
            ...
        }
        :hover { border-color: rgba(R,G,B,0.55); ... }
    </style>

Este módulo centraliza esa plantilla en `render_tab_accent_marker(...)` y
`tab_accent_marker_css(...)` para que añadir un nuevo tab con color propio
sea una sola línea, no 30 líneas de HTML repetidas.

NOTA: el helper devuelve el HTML como string. Para inyectarlo en la UI
hay que envolverlo con `st.markdown(..., unsafe_allow_html=True)`.
"""

from __future__ import annotations


def _hex_to_rgb_tuple(hex_color: str) -> tuple[int, int, int]:
    """Convierte '#RRGGBB' (o 'RRGGBB') a tupla (R, G, B). Lanza ValueError si inválido."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Hex inválido: {hex_color!r} (se esperaba '#RRGGBB')")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def tab_accent_marker_css(
    marker_id: str,
    accent_hex: str,
    *,
    border_width_left: int = 3,
    alpha_idle: float = 0.25,
    alpha_hover: float = 0.55,
    alpha_glow: float = 0.30,
) -> str:
    """Devuelve el bloque `<div>+<style>` listo para inyectar en st.markdown.

    Args:
        marker_id: ID único del marker DOM (sin '#'). Ej: ``'padres-tab-marker'``.
        accent_hex: Color de acento en formato ``'#RRGGBB'``.
        border_width_left: Grosor del border-left de acento en px (default 3).
        alpha_idle: Opacidad del borde general en estado idle (default 0.25).
        alpha_hover: Opacidad del borde general al hover (default 0.55).
        alpha_glow: Opacidad del box-shadow ring al hover (default 0.30).

    Returns:
        HTML completo (`<div>` marker + `<style>` scoped) como string.
    """
    if marker_id.startswith("#"):
        marker_id = marker_id[1:]
    r, g, b = _hex_to_rgb_tuple(accent_hex)

    # Selectores soportados: botones secondary, primary, link buttons, download buttons.
    # `:has()` requiere navegador moderno (Chrome 105+, Safari 15.4+, Firefox 121+).
    selectors_base = (
        f'div.element-container:has(#{marker_id}) ~ div button[kind="secondary"],\n'
        f'div.element-container:has(#{marker_id}) ~ div button[kind="primary"],\n'
        f'div.element-container:has(#{marker_id}) ~ div a[data-testid="stBaseLinkButton-secondary"],\n'
        f'div.element-container:has(#{marker_id}) ~ div a[data-testid="stBaseLinkButton-primary"],\n'
        f'div.element-container:has(#{marker_id}) ~ div div[data-testid="stDownloadButton"] button'
    )
    selectors_hover = (
        f'div.element-container:has(#{marker_id}) ~ div button[kind="secondary"]:hover,\n'
        f'div.element-container:has(#{marker_id}) ~ div button[kind="primary"]:hover,\n'
        f'div.element-container:has(#{marker_id}) ~ div a[data-testid="stBaseLinkButton-secondary"]:hover,\n'
        f'div.element-container:has(#{marker_id}) ~ div a[data-testid="stBaseLinkButton-primary"]:hover,\n'
        f'div.element-container:has(#{marker_id}) ~ div div[data-testid="stDownloadButton"] button:hover'
    )

    return (
        f'<div id="{marker_id}" style="display:none;"></div>\n'
        f"<style>\n"
        f"    {selectors_base} {{\n"
        f"        border: 1px solid rgba({r}, {g}, {b}, {alpha_idle}) !important;\n"
        f"        border-left: {border_width_left}px solid {accent_hex} !important;\n"
        f"        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;\n"
        f"    }}\n"
        f"    {selectors_hover} {{\n"
        f"        border-color: rgba({r}, {g}, {b}, {alpha_hover}) !important;\n"
        f"        border-left-color: {accent_hex} !important;\n"
        f"        box-shadow: 0 0 0 1px rgba({r}, {g}, {b}, {alpha_glow}), "
        f"0 2px 10px rgba(0,0,0,0.35) !important;\n"
        f"    }}\n"
        f"</style>"
    )


def render_tab_accent_marker(marker_id: str, accent_hex: str, **kwargs) -> None:
    """Versión opinionada: inyecta el marker + CSS vía st.markdown en una llamada.

    Uso típico al inicio de un render():

        from components.tab_markers import render_tab_accent_marker
        from constants import COLOR_PADRES

        def render(df_diario):
            render_tab_accent_marker("padres-tab-marker", COLOR_PADRES)
            ...

    Equivalente a:

        st.markdown(
            tab_accent_marker_css("padres-tab-marker", COLOR_PADRES),
            unsafe_allow_html=True,
        )
    """
    import streamlit as st

    st.markdown(tab_accent_marker_css(marker_id, accent_hex, **kwargs), unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Helper auxiliar: caja de notice con acento de tab
# ──────────────────────────────────────────────


def render_accent_notice(
    message: str,
    accent_hex: str,
    *,
    fill_alpha: float = 0.15,
    border_alpha: float = 0.30,
    icon: str = "",
) -> str:
    """Caja inline con fondo translúcido del acento del tab. Devuelve HTML.

    Útil para notices "todo OK" coherentes con el color del tab (en lugar
    del `st.info` azul Streamlit que rompe la unidad visual dark).

    Uso:

        st.markdown(
            render_accent_notice("Todo correcto.", COLOR_PADRES, icon="🎉"),
            unsafe_allow_html=True,
        )
    """
    from config.theme import FONT_PRIMARY

    r, g, b = _hex_to_rgb_tuple(accent_hex)
    icon_html = f"{icon} " if icon else ""
    return (
        f'<div style="background:rgba({r},{g},{b},{fill_alpha}); '
        f"border:1px solid rgba({r},{g},{b},{border_alpha}); "
        f"border-radius:8px; padding:12px 16px; "
        f"color:{accent_hex}; font-family:{FONT_PRIMARY}; "
        f'font-size:0.9rem; font-weight:500; margin:8px 0;">'
        f"{icon_html}{message}"
        f"</div>"
    )
