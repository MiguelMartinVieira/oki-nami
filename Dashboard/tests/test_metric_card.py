"""
test_metric_card.py — Tests para components/metric_card.py.
"""

from components.metric_card import render_metric_card


class TestMetricCard:
    def test_basic_metric_card(self):
        html = render_metric_card("Test Label", "+123.45 €")
        assert "Test Label" in html
        assert "+123.45 €" in html
        assert "metric-card" in html
        assert "premium-card" not in html

    def test_premium_metric_card(self):
        html = render_metric_card("Premium Label", "+5,000.00 €", premium=True)
        assert "premium-card" in html
        assert "Premium Label" in html

    def test_custom_color_no_bg(self):
        html = render_metric_card("Colored", "100 €", color="#FF0000")
        assert "color: #FF0000" in html
        assert "white !important" not in html

    def test_bg_color_tints_left_border(self):
        # bg_color en la API actual NO fuerza fondo lleno + texto blanco
        # (eso era el patron light antiguo). Ahora pinta un border-left
        # acento del color y el border-color general, coherente con dark.
        html = render_metric_card("Backgrounded", "50 €", bg_color="#00C853")
        assert "border-color: #00C853" in html
        assert "border-left: 3px solid #00C853" in html

    def test_custom_lbl_color(self):
        html = render_metric_card("Custom Label", "10 €", lbl_color="#123456")
        assert "color: #123456 !important" in html

    def test_subtitle_rendering(self):
        # El subtitle ahora usa la clase `metric-subtitle` (font-size por CSS
        # responsive en styles.py) en lugar de font-size inline.
        html = render_metric_card("Subtitled", "20 €", subtitle="This is a subtitle")
        assert "This is a subtitle" in html
        assert 'class="metric-subtitle"' in html

    def test_extra_html_insertion(self):
        extra = '<div class="extra-class">Extra Content</div>'
        html = render_metric_card("Extra", "15 €", extra_html=extra)
        assert extra in html

    def test_extra_class_applied(self):
        html = render_metric_card("Classy", "30 €", extra_class="fiscal-card")
        assert "fiscal-card" in html
        assert "metric-card" in html
