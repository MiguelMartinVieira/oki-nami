"""
test_aesthetic_contract.py — Contrato visual del Dashboard "Abyssal Monochrome".

OBJETIVO: blindar la estética recuperada tras el desastre Antigravity de 2026-05-24
para que nuevas features NO la rompan accidentalmente. Cualquier cambio que altere
estos contratos debe ser EXPLÍCITO (actualizar test + theme.py a la vez).

Cobertura:
  1. Constantes de color exactas en theme.py
  2. config.toml Streamlit en modo dark con valores fijos
  3. CSS markers per-tab (padres lavanda, bokatas azul, habitos burdeos)
  4. Helpers reutilizables: render_neutral_notice, render_diagnostic_card, render_dual_card
  5. metric_card API: color, bg_color, premium, subtitle, lbl_color, extra_class
  6. styles.py contiene reglas clave del Abyssal Monochrome
  7. Subpaquetes tabs/* exponen render() invocable
  8. Shims tab_*.py reexportan render
  9. NO hay hex codes light-theme leakeados en tabs (DCFCE7, FEE2E2, 166534, etc)
 10. Static assets (Background.png, Logo.png, Logo.ico) existen con tamaño esperado
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

# ──────────────────────────────────────────────
# Paths base
# ──────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = REPO_ROOT / "Dashboard"
SRC = DASHBOARD / "src"


# ══════════════════════════════════════════════
# 1. Constantes de color exactas (theme.py)
# ══════════════════════════════════════════════


class TestThemeColorConstants:
    """Los hex codes de la paleta Abyssal Monochrome son CONTRATO. Cambiar
    cualquiera de estos valores rompe la identidad visual y requiere actualizar
    este test conscientemente."""

    EXPECTED = {
        # Identidad cuentas/categorías
        "COLOR_SP500": "#64748B",
        "COLOR_BERKSHIRE": "#2563EB",
        "COLOR_EFECTIVO_TR": "#F59E0B",
        "COLOR_EFECTIVO_FISICO": "#854D0E",
        "COLOR_BOKATAS": "#3AABCE",
        "COLOR_PADRES": "#A78BFA",  # Lavanda — TAB Padres
        "COLOR_TE_DEBEN": "#EA580C",  # Naranja — card Te Deben (≠ Padres)
        # Semántica
        "COLOR_INGRESOS": "#00E676",
        "COLOR_GASTOS": "#FF1744",
        "COLOR_AHORRO": "#00E676",
        "COLOR_POSITIVO": "#00E676",
        "COLOR_NEGATIVO": "#FF1744",
        # Backgrounds translúcidos (dark-theme aware)
        "COLOR_POSITIVO_BG": "rgba(0, 230, 118, 0.1)",
        "COLOR_NEGATIVO_BG": "rgba(255, 23, 68, 0.1)",
        "COLOR_RECON_FUTURE": "#00B8D9",
        "COLOR_RECON_FUTURE_BG": "rgba(0, 184, 217, 0.1)",
        # Base del tema
        "COLOR_FONDO_APP": "#09090B",  # Negro profundo
        "COLOR_TEXTO_PRIMARIO": "#FFFFFF",
        "COLOR_TEXTO_SECUNDARIO": "#A1A1AA",
        "COLOR_PREMIUM_START": "#09090B",
        "COLOR_PREMIUM_END": "#18181B",
        # Design tokens (superficies, texto, identidades de tab)
        "COLOR_BG_CARD": "#18181B",
        "COLOR_BG_CARD_ELEVATED": "#1F1F23",
        "COLOR_TEXTO_BODY": "#E4E4E7",
        "COLOR_TEXTO_MUTED": "#71717A",
        "COLOR_HABITOS_BURDEOS": "#B30059",
        "BORDER_SOFT": "rgba(255,255,255,0.06)",
        "BORDER_HAIRLINE": "rgba(255,255,255,0.10)",
        "FONT_PRIMARY": "'Plus Jakarta Sans', sans-serif",
        "FONT_MONO": "'Roboto Mono', monospace",
        "SHADOW_CARD": "0 2px 8px rgba(0,0,0,0.25)",
        "SHADOW_CARD_ELEVATED": "0 4px 14px rgba(0,0,0,0.35)",
    }

    @pytest.mark.parametrize("name,expected", EXPECTED.items())
    def test_color_constant_exact_value(self, name, expected):
        from config import theme

        actual = getattr(theme, name, None)
        assert actual is not None, f"Falta constante {name} en config/theme.py"
        assert actual == expected, (
            f"{name} cambió de {expected!r} a {actual!r}. Si fue intencional, actualiza ESTE test."
        )

    def test_padres_y_te_deben_son_distintos(self):
        """Lavanda (Padres tab) y naranja (Te Deben card) deben mantenerse
        separados — son identidades visuales DISTINTAS aunque comparten cuentas."""
        from config.theme import COLOR_PADRES, COLOR_TE_DEBEN

        assert COLOR_PADRES != COLOR_TE_DEBEN

    def test_paleta_gastos_es_crimson_neon(self):
        """Todos los gastos viven en la rampa crimson (#FF1744 base, variantes
        más claras / más oscuras)."""
        from config.theme import CATEGORY_COLORS_GASTOS

        assert CATEGORY_COLORS_GASTOS, "CATEGORY_COLORS_GASTOS está vacío"
        # Todos deben empezar por #FF, #E0, #FF7, #FF9, #C9 o #A6 (rampa crimson)
        valid_prefixes = ("#FF", "#E0", "#C9", "#A6")
        for cat, color in CATEGORY_COLORS_GASTOS.items():
            assert color.upper().startswith(valid_prefixes), (
                f"{cat} usa {color}, fuera de rampa crimson neón"
            )

    def test_paleta_ingresos_es_mint_neon(self):
        """Todos los ingresos viven en la rampa mint (#00E676 base)."""
        from config.theme import CATEGORY_COLORS_INGRESOS

        assert CATEGORY_COLORS_INGRESOS
        valid_prefixes = ("#00", "#33")
        for cat, color in CATEGORY_COLORS_INGRESOS.items():
            assert color.upper().startswith(valid_prefixes), (
                f"{cat} usa {color}, fuera de rampa mint neón"
            )


# ══════════════════════════════════════════════
# 2. Streamlit config.toml en dark mode
# ══════════════════════════════════════════════


class TestStreamlitConfig:
    """El theme nativo de Streamlit debe estar en dark mode con los colores
    base. Si esto se rompe, el tema vuelve al rojo crimson chillón del primary
    o al fondo blanco light, y se ve frankenstein."""

    EXPECTED = {
        "theme.base": "dark",
        "theme.primaryColor": "#FFFFFF",
        "theme.backgroundColor": "#09090B",
        "theme.secondaryBackgroundColor": "#18181B",
        "theme.textColor": "#FFFFFF",
        "server.enableStaticServing": True,
    }

    @pytest.fixture(
        params=[
            "Dashboard/.streamlit/config.toml",  # dashboard local
        ]
    )
    def config(self, request):
        p = REPO_ROOT / request.param
        assert p.exists(), f"Falta {p}"
        return tomllib.loads(p.read_text(encoding="utf-8"))

    @pytest.mark.parametrize("dotted,expected", EXPECTED.items())
    def test_config_key(self, config, dotted, expected):
        section, key = dotted.split(".", 1)
        actual = config.get(section, {}).get(key)
        assert actual == expected, f"config.toml {dotted}={actual!r}, esperado {expected!r}"


# ══════════════════════════════════════════════
# 3. CSS markers por-tab (identidad visual)
# ══════════════════════════════════════════════


class TestTabCssMarkers:
    """Cada tab con identidad de color usa un marker DOM `<div id="X-tab-marker">`
    + CSS escopado vía `:has()`. Sin este patrón los botones del tab no reciben
    el acento (lavanda Padres, azul Bokatas, burdeos Hábitos)."""

    def test_padres_tab_marker_y_lavanda(self):
        """tab_padres ahora usa render_tab_accent_marker('padres-tab-marker', COLOR_PADRES).
        Verificamos que el marker_id literal y la referencia a COLOR_PADRES
        están presentes en el código fuente (el HTML real lo emite el helper)."""
        txt = (SRC / "tabs" / "padres" / "main.py").read_text(encoding="utf-8")
        assert "padres-tab-marker" in txt, "Falta el marker_id 'padres-tab-marker'"
        assert "COLOR_PADRES" in txt, "tab_padres debe importar/usar COLOR_PADRES"
        # Las notices inline lavanda siguen presentes (rgba(167,139,250) o #A78BFA)
        assert "rgba(167,139,250" in txt or "rgba(167, 139, 250" in txt or "#A78BFA" in txt

    def test_bokatas_tab_marker_y_azul(self):
        txt = (SRC / "tabs" / "bokatas" / "main.py").read_text(encoding="utf-8")
        assert "bokatas-tab-marker" in txt
        assert "render_tab_accent_marker" in txt

    def test_habitos_tab_marker_y_burdeos(self):
        txt = (SRC / "tabs" / "habitos" / "main.py").read_text(encoding="utf-8")
        assert "#habitos-tab-marker" in txt
        # Burdeos #B30059 = rgba(179, 0, 89, x)
        assert "#B30059" in txt or "rgba(179, 0, 89" in txt or "rgba(179,0,89" in txt

    def test_habitos_no_giant_text_bug(self):
        """Verifica que las reglas de logos personalizados para Ahorros
        estén ubicadas después de la regla de emojis gigantes (42px) en el CSS
        de habitos/main.py, previniendo que la regla global sobreescriba el tamaño."""
        txt = (SRC / "tabs" / "habitos" / "main.py").read_text(encoding="utf-8")

        idx_emoji_rule = txt.find("font-size: 0.82rem !important")
        assert idx_emoji_rule != -1, "Falta la regla de font-size base para botones"

        idx_ahorro_rule = txt.find("st-key-btn_ahorro_00")
        assert idx_ahorro_rule != -1, "Falta la regla CSS para st-key-btn_ahorro_00"

        assert idx_ahorro_rule > idx_emoji_rule, (
            "ERROR: La regla CSS para st-key-btn_ahorro_00 está antes de la regla "
            "de emojis gigantes de 42px. Esto provoca que el texto del botón se vea gigante. "
            "Mueve los estilos de los logos de Ahorros al final de la sección CSS."
        )


# ══════════════════════════════════════════════
# 4. Helpers reutilizables (HTML contracts)
# ══════════════════════════════════════════════


class TestDiagnosticCard:
    """Contrato de las tarjetas de diagnóstico/dual usadas en coste_real, sankey, etc."""

    def test_render_diagnostic_card_html(self):
        from components.diagnostic_card import render_diagnostic_card

        html = render_diagnostic_card("Título", "Cuerpo <b>html</b>", accent_color="#FF1744")
        assert "background:#18181B" in html
        assert "#FF1744" in html
        assert "Título" in html
        assert "Cuerpo <b>html</b>" in html
        assert "Plus Jakarta Sans" in html

    def test_render_diagnostic_card_elevated_aumenta_sombra(self):
        from components.diagnostic_card import render_diagnostic_card

        normal = render_diagnostic_card("X", "Y")
        elevated = render_diagnostic_card("X", "Y", elevated=True)
        assert normal != elevated
        assert "#1F1F23" in elevated  # bg más claro
        assert "0 4px 14px" in elevated  # sombra más grande

    def test_render_dual_card_html(self):
        from components.diagnostic_card import render_dual_card

        html = render_dual_card("HEADLINE", "1.234,56 €", "subtítulo", accent_color="#A78BFA")
        assert "#A78BFA" in html
        assert "border-left:4px solid #A78BFA" in html
        assert "HEADLINE" in html
        assert "1.234,56 €" in html
        assert "subtítulo" in html
        # El valor grande usa Roboto Mono monoespaciada
        assert "Roboto Mono" in html


# ══════════════════════════════════════════════
# 5. metric_card API
# ══════════════════════════════════════════════


class TestMetricCardContract:
    """Contrato actualizado de render_metric_card. Si cambia, romperá tabs."""

    def test_premium_aplica_clase(self):
        from components.metric_card import render_metric_card

        html = render_metric_card("L", "V", premium=True)
        assert "premium-card" in html

    def test_color_pinta_value(self):
        from components.metric_card import render_metric_card

        html = render_metric_card("L", "V", color="#00E676")
        assert "color: #00E676" in html

    def test_bg_color_pinta_border_left(self):
        from components.metric_card import render_metric_card

        html = render_metric_card("L", "V", bg_color="#3AABCE")
        assert "border-color: #3AABCE" in html
        assert "border-left: 3px solid #3AABCE" in html

    def test_subtitle_usa_clase_responsive(self):
        from components.metric_card import render_metric_card

        html = render_metric_card("L", "V", subtitle="sub")
        assert 'class="metric-subtitle"' in html
        assert "sub" in html

    def test_lbl_color_aplica_important(self):
        from components.metric_card import render_metric_card

        html = render_metric_card("L", "V", lbl_color="#A78BFA")
        assert "color: #A78BFA !important" in html


# ══════════════════════════════════════════════
# 6. styles.py contiene reglas clave
# ══════════════════════════════════════════════


class TestGlobalStyles:
    """styles.py es el CSS global inyectado en app.py. Debe contener las
    reglas mínimas del Abyssal Monochrome."""

    @pytest.fixture
    def css(self):
        return (SRC / "components" / "styles.py").read_text(encoding="utf-8")

    def test_fondo_app_negro(self, css):
        assert "#09090B" in css

    def test_tipografia_plus_jakarta_sans(self, css):
        assert "Plus Jakarta Sans" in css

    def test_tipografia_roboto_mono(self, css):
        assert "Roboto Mono" in css

    def test_background_image_static(self, css):
        # Streamlit static: app/static/Background.png
        assert "Background.png" in css

    def test_tab_highlight_blanco(self, css):
        # Override CSS del indicador de tab activo (blanco puro)
        assert "tab-highlight" in css
        assert "#FFFFFF" in css


# ══════════════════════════════════════════════
# 7. Subpaquetes exponen render()
# ══════════════════════════════════════════════


class TestSubpackageRenderExports:
    """Cada subpaquete tabs/<x> y components/charts debe exponer su render()
    o build_* publico para que app.py + tabs externos sigan importando."""

    @pytest.mark.parametrize(
        "module,attr",
        [
            ("tabs.resumen", "render"),
            ("tabs.diario", "render"),
            ("tabs.inversiones", "render"),
            ("tabs.habitos.main", "render"),
            ("tabs.padres", "render"),
            ("tabs.bokatas", "render"),
            ("tabs.guitarra", "render"),
        ],
    )
    def test_module_exposes_callable(self, module, attr):
        import importlib

        m = importlib.import_module(module)
        fn = getattr(m, attr, None)
        assert callable(fn), f"{module}.{attr} no es callable"


class TestTabPackages:
    """Verifica que los subpaquetes modulares en tabs/ expongan la función de renderizado."""

    @pytest.mark.parametrize(
        "subpackage",
        [
            "resumen",
            "diario",
            "inversiones",
            "habitos.main",
            "padres",
            "bokatas",
            "guitarra",
        ],
    )
    def test_subpackage_exposes_render(self, subpackage):
        import importlib

        m = importlib.import_module(f"tabs.{subpackage}")
        assert hasattr(m, "render"), f"tabs.{subpackage} no expone render"


# ══════════════════════════════════════════════
# 8. NO hex codes light-theme en tabs/components
# ══════════════════════════════════════════════

# Lista de hex codes "light theme" prohibidos en código de UI. Estos rompen
# la coherencia visual sobre el fondo #09090B (texto invisible o cajas blancas).
_LIGHT_THEME_HEX_FORBIDDEN = [
    "#DCFCE7",  # light green bg → debe ser rgba(0,230,118,0.1)
    "#FEE2E2",  # light red bg   → debe ser rgba(255,23,68,0.1)
    "#FEF3C7",  # light amber bg → debe ser rgba(245,158,11,0.1)
    "#DBEAFE",  # light blue bg  → debe ser rgba(96,165,250,0.1)
    "#F1F5F9",  # slate-100 bg
    "#FECACA",  # light pink fill (legacy charts)
    "#86EFAC",  # light mint (legacy charts)
    "#166534",  # dark green text on light bg
    "#991B1B",  # dark red text on light bg
    "#B45309",  # amber dark on light bg
    "#1D4ED8",  # blue dark on light bg
    "#1E40AF",  # blue darker on light bg
    "#EF5350",  # material red opaco
    "#66BB6A",  # material green opaco
]

# Excepciones legítimas: charts.py heatmap usa gradientes con colores claros
# como tope pastel para datos de baja intensidad (visualmente correcto sobre
# el panel oscuro del gráfico, no sobre el fondo de la app).
_HEX_LEAK_EXCLUDE_FILES = {
    "charts.py",  # heatmaps + scales con paletas multi-color
    "charts/heatmap.py",
    "charts/radar.py",
}


class TestNoLightThemeLeakage:
    """Hunt: hex codes de tema light NO deben aparecer en código de UI tabs/.
    Si un test falla aquí, alguien introdujo un color light en el dashboard dark."""

    @pytest.fixture
    def ui_py_files(self):
        files = []
        for root in [SRC / "tabs", SRC / "components"]:
            for f in root.rglob("*.py"):
                rel = str(f.relative_to(SRC))
                # Skip excepciones legítimas
                if any(exc in rel.replace("\\", "/") for exc in _HEX_LEAK_EXCLUDE_FILES):
                    continue
                files.append(f)
        return files

    @pytest.mark.parametrize("hex_code", _LIGHT_THEME_HEX_FORBIDDEN)
    def test_hex_not_leaked_in_tabs(self, hex_code, ui_py_files):
        leaks = []
        for f in ui_py_files:
            txt = f.read_text(encoding="utf-8")
            if hex_code in txt or hex_code.lower() in txt:
                leaks.append(str(f.relative_to(SRC)))
        assert not leaks, (
            f"Light-theme hex {hex_code} encontrado en: {leaks}. "
            f"Usar versión dark / rgba() translúcida."
        )


# ══════════════════════════════════════════════
# 9. Hardcoding hunt: COLOR_PADRES vs COLOR_TE_DEBEN
# ══════════════════════════════════════════════


class TestNoHardcodedColorPadres:
    """COLOR_PADRES (#A78BFA lavanda) y COLOR_TE_DEBEN (#EA580C naranja) son
    DIFERENTES por diseño. Si el "Te Deben" del Portfolio aparece en lavanda,
    es que se está usando COLOR_PADRES por error en tabs/inversiones.

    Test: en tabs/inversiones/ NO debe aparecer 'COLOR_PADRES' (usar TE_DEBEN).
    """

    def test_inversiones_no_usa_color_padres(self):
        for f in (SRC / "tabs" / "inversiones").rglob("*.py"):
            txt = f.read_text(encoding="utf-8")
            assert "COLOR_PADRES" not in txt, (
                f"{f.name} importa o usa COLOR_PADRES — debe usar COLOR_TE_DEBEN "
                "para la card 'Te Deben' y el segmento del donut/área."
            )

    def test_charts_subpackage_no_usa_color_padres_para_te_deben(self):
        """En components/charts/line.py el series_config 'Te Deben' debe
        usar COLOR_TE_DEBEN o el hex literal #EA580C, NUNCA COLOR_PADRES."""
        line_py = SRC / "components" / "charts" / "line.py"
        if not line_py.exists():
            pytest.skip("charts/line.py no encontrado")
        txt = line_py.read_text(encoding="utf-8")
        # Buscar la línea de Te Deben config
        match = re.search(r'"Te Deben":\s*\([^)]*\)', txt)
        if match:
            te_deben_line = match.group(0)
            assert "COLOR_PADRES" not in te_deben_line, (
                "Te Deben en line.py usa COLOR_PADRES (lavanda) — esperado COLOR_TE_DEBEN."
            )


# ═════════════════════════════════════════════════


class TestStaticAssets:
    """Background.png + logos deben existir en src/static/ para que styles.py
    + setup_startup.ps1 funcionen. Si faltan, el fondo dark se queda en negro
    plano (sin la onda Hokusai) y el shortcut pierde el icono."""

    @pytest.mark.parametrize(
        "name,min_size_kb",
        [
            ("Background.png", 1000),  # ≥ 1 MB (suele ser 8 MB)
            ("Logo.png", 50),  # ≥ 50 KB
            ("Logo.ico", 5),  # ≥ 5 KB (multi-size .ico)
            ("logo_bokatas.png", 10),
            ("logo_arrows.png", 10),
        ],
    )
    def test_asset_present_with_min_size(self, name, min_size_kb):
        path = SRC / "static" / name
        assert path.exists(), f"Falta asset {path}"
        size_kb = path.stat().st_size / 1024
        assert size_kb >= min_size_kb, f"{name} pesa {size_kb:.1f} KB, esperado >= {min_size_kb} KB"


# ══════════════════════════════════════════════
# 12. Helpers de notice por-tab no llaman a st.info para mensajes persistentes
# ══════════════════════════════════════════════


# ══════════════════════════════════════════════
# 13. Helper components/tab_markers.py
# ══════════════════════════════════════════════


class TestTabMarkersHelper:
    """Contrato del helper centralizado para CSS markers por-tab. Si lo rompes,
    Padres pierde el lavanda, Bokatas el azul, etc."""

    def test_hex_to_rgb_tuple_basico(self):
        from components.tab_markers import _hex_to_rgb_tuple

        assert _hex_to_rgb_tuple("#A78BFA") == (167, 139, 250)
        assert _hex_to_rgb_tuple("A78BFA") == (167, 139, 250)  # sin '#'
        assert _hex_to_rgb_tuple("#000000") == (0, 0, 0)
        assert _hex_to_rgb_tuple("#FFFFFF") == (255, 255, 255)

    def test_hex_to_rgb_tuple_invalido_lanza(self):
        from components.tab_markers import _hex_to_rgb_tuple

        with pytest.raises(ValueError):
            _hex_to_rgb_tuple("#XYZ")
        with pytest.raises(ValueError):
            _hex_to_rgb_tuple("not-a-hex")

    def test_tab_accent_marker_css_estructura(self):
        from components.tab_markers import tab_accent_marker_css

        html = tab_accent_marker_css("test-marker", "#A78BFA")
        # Marker DOM oculto
        assert '<div id="test-marker"' in html
        assert 'style="display:none;"' in html
        # Selectores escopados por :has()
        assert "div.element-container:has(#test-marker)" in html
        # Acento aplicado (color hex)
        assert "#A78BFA" in html
        # RGB derivado del hex (167, 139, 250)
        assert "rgba(167, 139, 250" in html
        # Estados idle + hover
        assert "0.25" in html  # alpha_idle default
        assert "0.55" in html  # alpha_hover default
        # Transición suave
        assert "transition:" in html

    def test_tab_accent_marker_css_strip_hash_del_marker_id(self):
        """El helper debe aceptar tanto 'test-marker' como '#test-marker'."""
        from components.tab_markers import tab_accent_marker_css

        h1 = tab_accent_marker_css("test-marker", "#FF1744")
        h2 = tab_accent_marker_css("#test-marker", "#FF1744")
        assert h1 == h2

    def test_tab_accent_marker_css_parametros_custom(self):
        from components.tab_markers import tab_accent_marker_css

        html = tab_accent_marker_css(
            "x",
            "#3AABCE",
            border_width_left=5,
            alpha_idle=0.10,
            alpha_hover=0.80,
            alpha_glow=0.40,
        )
        assert "border-left: 5px solid #3AABCE" in html
        assert "0.1" in html or "0.10" in html
        assert "0.8" in html or "0.80" in html
        assert "0.4" in html or "0.40" in html

    def test_render_accent_notice_html(self):
        from components.tab_markers import render_accent_notice

        html = render_accent_notice("Hola mundo", "#B30059", icon="🎯")
        assert "Hola mundo" in html
        assert "🎯" in html
        # Fondo translúcido del acento (Python f-string puede emitir 0.15 ó 0.3)
        assert "rgba(179,0,89,0.15)" in html
        # Borde — alpha 0.3 puede formatearse como '0.3' (no '0.30') por f-string
        assert "rgba(179,0,89,0.3)" in html or "rgba(179,0,89,0.30)" in html
        # Color de texto = acento
        assert "color:#B30059" in html
        # Tipografía del tema
        assert "Plus Jakarta Sans" in html

    def test_render_accent_notice_sin_icon(self):
        from components.tab_markers import render_accent_notice

        html = render_accent_notice("Solo texto", "#FF1744")
        assert "Solo texto" in html
        # Sin icon, NO debe haber espacio inicial sobrante
        assert ">Solo texto<" in html or "Solo texto</div>" in html

    def test_tab_padres_usa_helper(self):
        """tab_padres importa render_tab_accent_marker (no inline CSS marker)."""
        txt = (SRC / "tabs" / "padres" / "main.py").read_text(encoding="utf-8")
        assert "render_tab_accent_marker" in txt, (
            "tab_padres debe usar el helper en lugar de CSS marker inline duplicado."
        )
