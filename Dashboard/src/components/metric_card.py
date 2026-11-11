"""
metric_card.py — Componente reutilizable de tarjeta de métricas.

Genera HTML para cards Fintech Dark Bento y premium.
"""

from __future__ import annotations


def render_metric_card(
    label: str,
    value: str,
    *,
    color: str = "#FFFFFF",
    subtitle: str = "",
    premium: bool = False,
    bg_color: str | None = None,
    extra_html: str = "",
    extra_html_top: str = "",
    lbl_color: str | None = None,
    extra_class: str = "",
) -> str:
    """
    Genera el HTML de una metric card Fintech Dark Bento.
    """
    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode():
            value = scramble_numbers(value)
            if subtitle:
                subtitle = scramble_numbers(subtitle)
            if extra_html:
                extra_html = scramble_numbers(extra_html)
            if extra_html_top:
                extra_html_top = scramble_numbers(extra_html_top)
    except Exception:
        pass

    base = "metric-card premium-card" if premium else "metric-card"
    card_class = f"{base} {extra_class}".strip()

    # bg_color tints the left border for accent
    if bg_color:
        style_attr = f'style="border-color: {bg_color}; border-left: 3px solid {bg_color};"'
    else:
        style_attr = ""

    val_color = color if color else "#FFFFFF"
    if lbl_color is None:
        lbl_color = "#A1A1AA"
    else:
        lbl_color = f"{lbl_color} !important"
    sub_color = "#71717A"

    # El subtítulo lleva la clase `metric-subtitle` para que CSS responsive
    # (container queries en styles.py) controle el font-size y aplique
    # `white-space: nowrap`. Así el texto del subtítulo nunca se sale de
    # una línea por mucho que sea largo. Sólo el `color` sigue inline porque
    # depende del estilo `sub_color` calculado dinámicamente.
    subtitle_html = (
        f'<div class="metric-subtitle" style="color:{sub_color};">{subtitle}</div>'
        if subtitle
        else ""
    )

    return (
        f'<div class="{card_class}" {style_attr}>'
        f'<div class="metric-label" style="color: {lbl_color};">{label}</div>'
        f"{extra_html_top}"
        f'<div style="position: relative;">'
        f'<div class="metric-value" style="color: {val_color};">{value}</div>'
        f"{extra_html}"
        f"</div>"
        f"{subtitle_html}"
        f"</div>"
    )
