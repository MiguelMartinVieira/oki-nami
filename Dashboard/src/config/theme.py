"""
theme.py — Paletas de colores y estilos visuales.

Tema "Abyssal Monochrome / Dark Bento": fondo `#09090B`, neón crimson/mint
y un toque lavanda para la sub-cuenta de Padres.
"""

# ──────────────────────────────────────────────
# 🎨 Paletas de color por categoría dinámica
# ──────────────────────────────────────────────

CATEGORY_COLORS_GASTOS: dict[str, str] = {
    "Gastos Cafeína": "#FF4D6D",  # Lighter crimson
    "Gastos Alcohol & Friends": "#FF1744",  # Base crimson
    "Gastos Comida": "#E00034",  # Darker crimson
    "Gastos Transporte": "#FF7A92",  # Pale crimson
    "Gastos Gym": "#C90029",  # Deep crimson
    "Gastos Viajes": "#FF9EAF",  # Very pale crimson
    "Gastos Puntuales/Otros...": "#A60022",  # Very deep crimson
}

CATEGORY_COLORS_INGRESOS: dict[str, str] = {
    "Ingresos Sueldo": "#00C853",  # Darker mint
    "Ingresos Ítaca": "#009624",  # Deep mint
    "Ingresos Paga": "#00E676",  # Base mint
    "Ingresos Puntuales...": "#33FF99",  # Lighter mint
}

_GASTOS_CATCHALL_COLOR = "#FF1744"  # Base crimson fallback
_INGRESOS_CATCHALL_COLOR = "#00E676"  # Base mint fallback

# ──────────────────────────────────────────────
# Colores Específicos (Monocromo & Neón)
# ──────────────────────────────────────────────
COLOR_SP500 = "#64748B"
COLOR_BERKSHIRE = "#2563EB"
COLOR_EFECTIVO_TR = "#F59E0B"
COLOR_EFECTIVO_FISICO = "#854D0E"
COLOR_BOKATAS = "#3AABCE"  # Azul brand del logo de la ONG Bokatas
COLOR_PADRES = "#A78BFA"  # Lavanda (Tailwind violet-400) — identidad del TAB Padres
COLOR_TE_DEBEN = "#EA580C"  # Naranja chillón — card "Te Deben" (cuentas 131+132 agrupadas)
COLOR_INGRESOS = "#00E676"
COLOR_GASTOS = "#FF1744"
COLOR_AHORRO = "#00E676"

COLOR_POSITIVO = "#00E676"
COLOR_POSITIVO_BG = "rgba(0, 230, 118, 0.1)"
COLOR_NEGATIVO = "#FF1744"
COLOR_NEGATIVO_BG = "rgba(255, 23, 68, 0.1)"

COLOR_FONDO_APP = "#09090B"
COLOR_TEXTO_PRIMARIO = "#FFFFFF"
COLOR_TEXTO_SECUNDARIO = "#A1A1AA"
COLOR_RECON_FUTURE = "#00B8D9"
COLOR_RECON_FUTURE_BG = "rgba(0, 184, 217, 0.1)"
COLOR_PREMIUM_START = "#09090B"
COLOR_PREMIUM_END = "#18181B"

# ──────────────────────────────────────────────
# Design tokens (Abyssal Monochrome — superficies y tipografía)
# ──────────────────────────────────────────────
# Estos tokens centralizan valores que aparecen 10-70 veces en la UI.
# Cambiarlos aquí afecta a TODAS las cards/notices/markers automáticamente.

# Superficies (de oscura a clara)
COLOR_BG_CARD = "#18181B"  # Card base sobre #09090B (panel oscuro estándar)
COLOR_BG_CARD_ELEVATED = "#1F1F23"  # Card destacada (hover, elevated diagnostic)

# Texto (más opaco → más sutil)
COLOR_TEXTO_BODY = "#E4E4E7"  # Cuerpo de cards/notices (algo menos que #FFFFFF)
COLOR_TEXTO_MUTED = "#71717A"  # Subtítulos, captions, metadatos

# Bordes translúcidos
BORDER_SOFT = "rgba(255,255,255,0.06)"  # Borde 1px sutil sobre dark
BORDER_HAIRLINE = "rgba(255,255,255,0.10)"  # Borde 1px ligeramente más visible

# Identidades de tab (acento usado en CSS markers)
COLOR_HABITOS_BURDEOS = "#B30059"  # Burdeos identidad del TAB Hábitos y Ahorros

# Cash Denomination Tracker
COLOR_BILL = "#854D0E"  # Ámbar oscuro para billetes (= EFECTIVO_FISICO)
COLOR_COIN = "#94A3B8"  # Plateado metálico para monedas

# Tipografía
FONT_PRIMARY = "'Plus Jakarta Sans', sans-serif"  # Texto general (labels, body)
FONT_MONO = "'Roboto Mono', monospace"  # Cifras grandes en metric cards

# Shadows estándar (cards normales vs elevated)
SHADOW_CARD = "0 2px 8px rgba(0,0,0,0.25)"
SHADOW_CARD_ELEVATED = "0 4px 14px rgba(0,0,0,0.35)"


def get_category_color(category_name: str, is_expense: bool) -> str:
    palette = CATEGORY_COLORS_GASTOS if is_expense else CATEGORY_COLORS_INGRESOS
    fallback = _GASTOS_CATCHALL_COLOR if is_expense else _INGRESOS_CATCHALL_COLOR
    if category_name in palette:
        return palette[category_name]
    name_lower = str(category_name).lower()
    for key, color in palette.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return color
    return fallback
