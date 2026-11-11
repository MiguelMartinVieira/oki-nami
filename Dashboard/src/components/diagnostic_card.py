"""
diagnostic_card.py — Tarjetas de diagnóstico/insight para el tema Abyssal Monochrome.

Sustituye los bloques HTML inline `background-color: white` que quedaban
del rediseño anterior. Renderiza una tarjeta oscura (`#18181B`) con un
borde translúcido, un título coloreado por acento y cuerpo HTML libre.
"""

from __future__ import annotations

# Reexport para compatibilidad con tests y módulos legacy. Fuente única en charts.base
from components.charts.base import _hex_to_rgba  # noqa: F401


def render_diagnostic_card(
    title: str,
    body_html: str,
    *,
    accent_color: str = "#A1A1AA",
    icon: str = "",
    height_full: bool = True,
    elevated: bool = False,
) -> str:
    """Genera el HTML de una tarjeta de diagnóstico coherente con el tema dark.

    Args:
        title: encabezado breve (se renderiza en `accent_color`).
        body_html: HTML libre del cuerpo. Puede contener `<b>`, `<br>`, etc.
        accent_color: color del título y del borde superior (acento).
        icon: emoji o icono opcional antes del título.
        height_full: si True, aplica `height:100%` para usar la altura del column.
        elevated: si True, fondo ligeramente más claro y mayor sombra (para
            destacar cards dentro de bloques agrupados).
    """
    bg = "#1F1F23" if elevated else "#18181B"
    height_style = "height:100%;" if height_full else ""
    border_top = _hex_to_rgba(accent_color, 0.55)
    border_main = "rgba(255,255,255,0.06)"
    shadow = "0 4px 14px rgba(0,0,0,0.35)" if elevated else "0 2px 8px rgba(0,0,0,0.25)"
    icon_html = f'<span style="margin-right:6px;">{icon}</span>' if icon else ""

    return (
        f'<div style="background:{bg}; border:1px solid {border_main}; '
        f"border-top:2px solid {border_top}; border-radius:12px; "
        f"padding:16px 18px; box-shadow:{shadow}; {height_style} "
        f"font-family:'Plus Jakarta Sans', sans-serif;\">"
        f'<div style="font-size:0.9rem; font-weight:700; color:{accent_color}; '
        f'margin-bottom:8px; letter-spacing:-0.01em;">{icon_html}{title}</div>'
        f'<div style="font-size:0.86rem; color:#E4E4E7; line-height:1.55;">'
        f"{body_html}</div>"
        f"</div>"
    )


def render_dual_card(
    headline: str,
    value_big: str,
    sub: str,
    *,
    accent_color: str = "#FF1744",
) -> str:
    """Tarjeta "Bruto equivalente" / "Coste oportunidad" — fondo dark con
    borde lateral fuerte por acento. Sustituye los antiguos gradientes
    rojo claro."""
    sub_html = (
        (f'<div style="font-size:0.78rem; margin-top:4px; color:#A1A1AA;">{sub}</div>')
        if sub
        else ""
    )

    return (
        f'<div style="background:#18181B; border:1px solid rgba(255,255,255,0.06); '
        f"border-left:4px solid {accent_color}; border-radius:12px; "
        f"padding:14px 18px; text-align:center; height:100%; display:flex; flex-direction:column; justify-content:center; "
        f"font-family:'Plus Jakarta Sans', sans-serif; "
        f'box-shadow:0 2px 10px rgba(0,0,0,0.3);">'
        f'<div style="font-size:0.78rem; font-weight:600; '
        f'color:{accent_color}; letter-spacing:0.04em; text-transform:uppercase;">'
        f"{headline}</div>"
        f'<div style="font-size:1.75rem; font-weight:700; margin-top:4px; '
        f"color:#FFFFFF; font-family:'Roboto Mono', monospace;\">"
        f"{value_big}</div>"
        f"{sub_html}"
        f"</div>"
    )
