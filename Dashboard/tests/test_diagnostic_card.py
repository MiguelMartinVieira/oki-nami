"""
test_diagnostic_card.py — Tests para components/diagnostic_card.py.

Valida que los helpers (`render_diagnostic_card`, `render_dual_card`)
produzcan HTML bien formado y respeten los parámetros visuales clave
(acento, altura, fondos dark). `_hex_to_rgba` se importa indirectamente
desde `components.charts.base` (fuente única).
"""

from components.diagnostic_card import (
    _hex_to_rgba,
    render_diagnostic_card,
    render_dual_card,
)


class TestHexToRgba:
    def test_valid_hex(self):
        assert _hex_to_rgba("#FF1744", 0.5) == "rgba(255,23,68,0.5)"

    def test_zero_alpha(self):
        assert _hex_to_rgba("#000000", 0.0) == "rgba(0,0,0,0.0)"

    def test_invalid_returns_original(self):
        # Si el formato no es #RRGGBB devuelve el input intacto
        assert _hex_to_rgba("not-a-hex", 0.5) == "not-a-hex"
        assert _hex_to_rgba("rgb(1,2,3)", 0.5) == "rgb(1,2,3)"
        assert _hex_to_rgba("#FFF", 0.5) == "#FFF"  # 4-char hex no soportado


class TestRenderDiagnosticCard:
    def test_basic_render(self):
        html = render_diagnostic_card("Mi Título", "<p>Cuerpo</p>", accent_color="#00E676")
        assert "Mi Título" in html
        assert "<p>Cuerpo</p>" in html
        assert "#00E676" in html

    def test_dark_background(self):
        html = render_diagnostic_card("X", "Y", accent_color="#FFFFFF")
        # Las cards de diagnóstico viven sobre #18181B o #1F1F23
        assert "#18181B" in html or "#1F1F23" in html

    def test_height_full(self):
        html_full = render_diagnostic_card("X", "Y", height_full=True)
        html_no_full = render_diagnostic_card("X", "Y", height_full=False)
        assert "height:100%" in html_full
        assert "height:100%" not in html_no_full

    def test_elevated_uses_lighter_bg(self):
        html_normal = render_diagnostic_card("X", "Y", elevated=False)
        html_elev = render_diagnostic_card("X", "Y", elevated=True)
        # elevated usa un zinc más claro
        assert "#1F1F23" in html_elev
        assert "#18181B" in html_normal

    def test_icon_rendered(self):
        html = render_diagnostic_card("X", "Y", icon="🛡️")
        assert "🛡️" in html


class TestRenderDualCard:
    def test_basic(self):
        html = render_dual_card(
            "BRUTO EQUIVALENTE",
            "3.01 €",
            "Tienes que ganar este bruto",
            accent_color="#FF4D6D",
        )
        assert "BRUTO EQUIVALENTE" in html
        assert "3.01 €" in html
        assert "#FF4D6D" in html
        # Roboto Mono para el valor grande
        assert "Roboto Mono" in html
