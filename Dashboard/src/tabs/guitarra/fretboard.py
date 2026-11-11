"""
fretboard.py — Motor visual y lógico del diapasón de guitarra (Dark Bento UI).

Proporciona funciones para calcular notas en cualquier posición del mástil,
encontrar octavas y renderizar el diapasón interactivo.
"""

# Notas en la escala cromática
CHROMATIC_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CHROMATIC_FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
NATURAL_NOTES = ["A", "B", "C", "D", "E", "F", "G"]

# Afinación estándar de 6 cuerdas: de 1ª (High E) a 6ª (Low E)
# Índice 0: 1ª Cuerda (High E)
# Índice 1: 2ª Cuerda (B)
# Índice 2: 3ª Cuerda (G)
# Índice 3: 4ª Cuerda (D)
# Índice 4: 5ª Cuerda (A)
# Índice 5: 6ª Cuerda (Low E)
STRING_NAMES = ["e", "B", "G", "D", "A", "E"]
STRING_OPEN_SEMITONES = [4, 11, 7, 2, 9, 4]  # Relativo a C (E=4, B=11, G=7, D=2, A=9, E=4)


def get_note_name(string_num: int, fret: int, prefer_flats: bool = False) -> str:
    """
    Retorna el nombre de la nota dada la cuerda (1 a 6) y el traste (0 a 15).
    string_num: 1 para High E, 6 para Low E.
    """
    if not (1 <= string_num <= 6):
        raise ValueError("string_num debe estar entre 1 y 6")
    idx = string_num - 1
    base_semitone = STRING_OPEN_SEMITONES[idx]
    semitone = (base_semitone + fret) % 12
    return CHROMATIC_FLATS[semitone] if prefer_flats else CHROMATIC_SHARPS[semitone]


def normalize_note(note: str) -> str:
    """Convierte notas equivalentes (ej. Db -> C#, A# -> Bb) a una forma estándar."""
    n = note.strip()
    mapping = {
        "C#": "C#",
        "DB": "C#",
        "C♭": "B",
        "D#": "D#",
        "EB": "D#",
        "F#": "F#",
        "GB": "F#",
        "G#": "G#",
        "AB": "G#",
        "A#": "A#",
        "BB": "A#",
        "B#": "C",
        "E#": "F",
    }
    return mapping.get(n.upper(), n.upper())


def get_all_positions_of_note(note_target: str, max_fret: int = 15) -> list[tuple[int, int]]:
    """
    Devuelve una lista de tuplas (string_num, fret) donde se encuentra la nota objetivo.
    string_num va de 1 (High E) a 6 (Low E).
    """
    norm_target = normalize_note(note_target)
    positions = []
    for string_num in range(1, 7):
        for fret in range(0, max_fret + 1):
            n_sharp = normalize_note(get_note_name(string_num, fret, prefer_flats=False))
            n_flat = normalize_note(get_note_name(string_num, fret, prefer_flats=True))
            if norm_target in (n_sharp, n_flat):
                positions.append((string_num, fret))
    return positions


def get_octave_shortcut_target(string_num: int, fret: int) -> tuple[int, int, str] | None:
    """
    Calcula la posición objetivo del atajo de octava según el vídeo de GuitarZero2Hero.
    Devuelve (target_string_num, target_fret, shortcut_name) o None si sale del diapasón.
    """
    # Shortcut 1: Cuerdas 6 y 5 -> +2 trastes, +2 cuerdas abajo (num cdo disminuye: 6->4, 5->3)
    if string_num in (6, 5):
        target_str = string_num - 2
        target_fret = fret + 2
        if 0 <= target_fret <= 15:
            return (target_str, target_fret, "Shortcut 1 (+2 trastes, +2 cuerdas abajo)")

    # Shortcut 2: Cuerdas 4 y 3 -> +3 trastes, +2 cuerdas abajo (4->2, 3->1)
    elif string_num in (4, 3):
        target_str = string_num - 2
        target_fret = fret + 3
        if 0 <= target_fret <= 15:
            return (target_str, target_fret, "Shortcut 2 (+3 trastes, +2 cuerdas abajo)")

    # Shortcut 4: Cuerda 6 -> 1ª cuerda en el mismo traste
    elif string_num == 6:
        return (1, fret, "Shortcut 4 (Mismo traste en 1ª cuerda - 2 octavas)")

    return None


def generate_fretboard_html(
    highlight_positions: list[tuple[int, int]] | None = None,
    highlight_note: str | None = None,
    show_all_notes: bool = False,
    max_fret: int = 15,
) -> str:
    """
    Genera el HTML/CSS interactivo con estilo Dark Bento para renderizar el diapasón.
    highlight_positions: Lista de tuplas (string_num [1-6], fret [0-15]).
    highlight_note: Nombre de nota que se desea destacar globalmente.
    """
    highlight_set = set(highlight_positions) if highlight_positions else set()
    if highlight_note:
        auto_positions = get_all_positions_of_note(highlight_note, max_fret=max_fret)
        highlight_set.update(auto_positions)

    # Trastes con inlays característicos
    single_inlays = {3, 5, 7, 9, 15}
    double_inlays = {12}

    html = []
    html.append(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    body {
        margin: 0;
        padding: 0;
        background: transparent;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .fretboard-container {
        width: 100%;
        overflow-x: auto;
        padding: 16px 8px;
        background: #121215;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        box-sizing: border-box;
    }
    .fretboard-table {
        border-collapse: collapse;
        width: 100%;
        min-width: 800px;
        user-select: none;
    }
    .fretboard-header-cell {
        text-align: center;
        font-size: 0.72rem;
        font-weight: 700;
        color: #71717A;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }
    .fretboard-header-cell.inlay-header {
        color: #3B82F6;
    }
    .string-label {
        font-weight: 700;
        font-size: 0.85rem;
        color: #A1A1AA;
        padding-right: 12px;
        text-align: right;
        width: 40px;
    }
    .fret-cell {
        position: relative;
        height: 38px;
        border-right: 2px solid #3F3F46;
        vertical-align: middle;
        text-align: center;
        background: #18181B;
    }
    .fret-cell.nut {
        border-right: 4px solid #E4E4E7;
        background: #09090B;
    }
    /* Línea visual de la cuerda */
    .string-line {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        transform: translateY(-50%);
        z-index: 1;
    }
    .note-badge {
        position: relative;
        z-index: 2;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        font-size: 0.75rem;
        font-weight: 700;
        color: #71717A;
        background: rgba(24, 24, 27, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.2s ease;
    }
    .note-badge.highlighted {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, #3B82F6 0%, rgba(29, 78, 216, 0.9) 100%) !important;
        border-color: #60A5FA !important;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.6) !important;
        transform: scale(1.15);
    }
    .note-badge.target-main {
        background: linear-gradient(135deg, #10B981 0%, #047857 100%) !important;
        border-color: #34D399 !important;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.7) !important;
        color: #FFFFFF !important;
        transform: scale(1.2);
    }
    .inlay-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.25);
        margin: 0 auto;
    }
    .inlay-double {
        display: flex;
        gap: 4px;
        justify-content: center;
    }
    </style>
    """
    )

    html.append('<div class="fretboard-container">')
    html.append('<table class="fretboard-table">')

    # Fila de cabecera (números de traste)
    html.append("<tr>")
    html.append('<th class="string-label">Cuerda</th>')
    for f in range(0, max_fret + 1):
        is_inlay = f in single_inlays or f in double_inlays
        cls = "fretboard-header-cell inlay-header" if is_inlay else "fretboard-header-cell"
        txt = "Aire" if f == 0 else f"T{f}"
        html.append(f'<th class="{cls}">{txt}</th>')
    html.append("</tr>")

    # Filas para cada cuerda (1ª a 6ª)
    string_heights = [1.0, 1.3, 1.7, 2.1, 2.6, 3.2]

    for s_idx in range(6):
        string_num = s_idx + 1  # 1 a 6
        s_name = STRING_NAMES[s_idx]
        s_height = string_heights[s_idx]

        html.append("<tr>")
        html.append(f'<td class="string-label">{s_name} ({string_num}ª)</td>')

        for f in range(0, max_fret + 1):
            cell_cls = "fret-cell nut" if f == 0 else "fret-cell"
            note_name = get_note_name(string_num, f)
            is_highlighted = (string_num, f) in highlight_set

            # Estilo del badge
            badge_cls = "note-badge"
            if is_highlighted:
                badge_cls += " highlighted"
                if highlight_note and normalize_note(note_name) == normalize_note(highlight_note):
                    badge_cls += " target-main"

            # Decidir si mostrar el texto de la nota
            display_txt = ""
            if is_highlighted or show_all_notes or f == 0:
                display_txt = note_name

            badge_html = (
                f'<div class="{badge_cls}">{display_txt}</div>'
                if (display_txt or is_highlighted)
                else ""
            )

            html.append(f'<td class="{cell_cls}">')
            html.append(
                f'<div class="string-line" style="height:{s_height}px; background:#71717A;"></div>'
            )
            html.append(badge_html)
            html.append("</td>")

        html.append("</tr>")

    # Fila inferior de inlays
    html.append("<tr>")
    html.append('<td class="string-label"></td>')
    for f in range(0, max_fret + 1):
        html.append('<td style="text-align:center; padding-top:6px;">')
        if f in single_inlays:
            html.append('<div class="inlay-dot"></div>')
        elif f in double_inlays:
            html.append(
                '<div class="inlay-double"><div class="inlay-dot"></div><div class="inlay-dot"></div></div>'
            )
        html.append("</td>")
    html.append("</tr>")

    html.append("</table>")
    html.append("</div>")

    return "".join(html)


def render_fretboard(
    highlight_positions: list[tuple[int, int]] | None = None,
    highlight_note: str | None = None,
    show_all_notes: bool = False,
    max_fret: int = 15,
    height: int = 340,
):
    """
    Renderiza el diapasón interactivo dentro de un iframe sandboxed usando st.components.v1.html.
    Garantiza que las tablas y estilos CSS no sean eliminados por el formateador Markdown de Streamlit.
    """
    import streamlit.components.v1 as components

    html_code = generate_fretboard_html(
        highlight_positions=highlight_positions,
        highlight_note=highlight_note,
        show_all_notes=show_all_notes,
        max_fret=max_fret,
    )
    components.html(html_code, height=height, scrolling=True)
