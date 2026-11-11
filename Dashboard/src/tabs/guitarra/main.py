"""
main.py — Orquestador visual de la Pestaña Guitarra (Oki-Nami Dashboard).

Implementa la interfaz para interiorizar las notas del diapasón
basada en la metodología de GuitarZero2Hero (Dave Tran).
"""

import streamlit as st

from .fretboard import (
    NATURAL_NOTES,
    STRING_NAMES,
    get_all_positions_of_note,
    get_note_name,
    render_fretboard,
)
from .metronome import (
    generate_random_exercise_notes,
    get_3_note_phrase,
    render_metronome_widget,
)
from .storage import get_practice_stats, load_practice_history, save_practice_session


def render():
    """Renderiza la pestaña principal de Guitarra."""

    # Métricas de práctica rápida en la parte superior
    stats = get_practice_stats()
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card" style="padding:14px 18px; height:80px; display:flex; flex-direction:column; justify-content:center;">
                <div class="metric-label" style="font-size:0.7rem; color:#A1A1AA;">🔥 RACHA ACTUAL</div>
                <div style="font-size:1.4rem; font-weight:700; color:#10B981;">{stats["streak"]} Días</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card" style="padding:14px 18px; height:80px; display:flex; flex-direction:column; justify-content:center;">
                <div class="metric-label" style="font-size:0.7rem; color:#A1A1AA;">⏱️ TIEMPO PRACTICADO</div>
                <div style="font-size:1.4rem; font-weight:700; color:#3B82F6;">{stats["total_minutes"]} min</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card" style="padding:14px 18px; height:80px; display:flex; flex-direction:column; justify-content:center;">
                <div class="metric-label" style="font-size:0.7rem; color:#A1A1AA;">⚡ BPM MÁXIMO</div>
                <div style="font-size:1.4rem; font-weight:700; color:#F59E0B;">{stats["max_bpm"]} BPM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card" style="padding:14px 18px; height:80px; display:flex; flex-direction:column; justify-content:center;">
                <div class="metric-label" style="font-size:0.7rem; color:#A1A1AA;">🎓 SESIONES COMPLETADAS</div>
                <div style="font-size:1.4rem; font-weight:700; color:#E4E4E7;">{stats["total_sessions"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # Sub-pestañas principales
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(
        [
            "⚡ Ejercicios Autónomos",
            "🎸 Diapasón Interactivo",
            "📖 Guía & Teoría del Vídeo",
            "📊 Racha & Historial",
        ]
    )

    # ──────────────────────────────────────────────
    # Sub-tab 1: Entrenador Autónomo de Ejercicios
    # ──────────────────────────────────────────────
    with sub_tab1:
        bpm_active = render_metronome_widget(default_bpm=40)

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.08); margin:16px 0;'>",
            unsafe_allow_html=True,
        )

        ex_choice = st.selectbox(
            "Ejercicio a practicar",
            label_visibility="collapsed",
            options=[
                "Ejercicio 1: Memorización Horizontal por Cuerda (Notas Naturales)",
                "Ejercicio 2: Recorrido Vertical de 1 Nota con Metrónomo",
                "Ejercicio 3: Frase Ascendente de 3 Notas (Lick Melódico)",
                "Ejercicio 4A: Multi-Nota (2 Notas en la misma cuerda)",
                "Ejercicio 4B: Multi-Nota (2 Notas alternando cuerdas)",
                "Ejercicio 4C: Multi-Nota (3 Notas en la misma cuerda)",
                "Ejercicio 4D: Multi-Nota (3 Notas alternando cuerdas)",
                "Ejercicio 5: Rutina de Saltos de Octavas en Cadena",
            ],
        )

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        if "Ejercicio 1" in ex_choice:
            _render_exercise_1(bpm_active)
        elif "Ejercicio 2" in ex_choice:
            _render_exercise_2(bpm_active)
        elif "Ejercicio 3" in ex_choice:
            _render_exercise_3(bpm_active)
        elif "Ejercicio 4" in ex_choice:
            _render_exercise_4(ex_choice, bpm_active)
        elif "Ejercicio 5" in ex_choice:
            _render_exercise_5(bpm_active)

    # ──────────────────────────────────────────────
    # Sub-tab 2: Diapasón Interactivo Explorer
    # ──────────────────────────────────────────────
    with sub_tab2:
        st.markdown("### 🎸 Explorador Interactivo del Diapasón")
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            sel_note = st.selectbox(
                "Destacar Nota Global:",
                options=["(Ninguna)"] + NATURAL_NOTES + ["C#", "D#", "F#", "G#", "A#"],
            )
        with col_e2:
            show_all = st.checkbox("Mostrar nombres en TODAS las notas", value=False)

        highlight_list = []
        if sel_note != "(Ninguna)":
            highlight_list = get_all_positions_of_note(sel_note, max_fret=15)
            st.info(
                f"📍 La nota **{sel_note}** se repite **{len(highlight_list)} veces** entre los trastes 0 y 15."
            )

        render_fretboard(
            highlight_positions=highlight_list,
            highlight_note=sel_note if sel_note != "(Ninguna)" else None,
            show_all_notes=show_all,
            max_fret=15,
        )

    # ──────────────────────────────────────────────
    # Sub-tab 3: Guía & Teoría del Vídeo
    # ──────────────────────────────────────────────
    with sub_tab3:
        _render_video_theory_guide()

    # ──────────────────────────────────────────────
    # Sub-tab 4: Racha & Historial de Práctica
    # ──────────────────────────────────────────────
    with sub_tab4:
        _render_history_tab()


def _render_exercise_1(bpm: int):
    st.markdown(
        """
        <div style="background:#18181B; border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:16px;">
            <h4 style="color:#10B981; margin-top:0;">📌 Ejercicio 1: Memorización Horizontal por Cuerda Individual</h4>
            <p style="color:#E4E4E7; font-size:0.9rem;">
                <strong>Instrucciones:</strong> Elige una sola cuerda. Avanza traste a traste pronunciando <strong>EN VOZ ALTA</strong> únicamente las notas naturales (<code>A, B, C, D, E, F, G</code>).
            </p>
            <ul>
                <li>Recordatorio: Entre <strong>B y C</strong> y entre <strong>E y F</strong> hay solo <strong>1 traste</strong> de distancia. Entre el resto, <strong>2 trastes</strong>.</li>
                <li><strong>Autochequeo:</strong> Al llegar al traste 12 DEBE coincidir con la nota de la cuerda al aire.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    sel_str = st.radio(
        "Selecciona la cuerda a practicar:",
        options=[6, 5, 4, 3, 2, 1],
        format_func=lambda x: f"Cuerda {x} ({STRING_NAMES[x - 1]})",
        horizontal=True,
    )

    # Mostrar la secuencia de notas naturales en esa cuerda
    notes_seq = []
    positions = []
    for f in range(0, 13):
        n = get_note_name(sel_str, f)
        if n in NATURAL_NOTES or f == 0:
            notes_seq.append(f"T{f}: **{n}**")
            positions.append((sel_str, f))

    st.write("📍 **Secuencia de notas naturales en esta cuerda (Trastes 0 a 12):**")
    st.write(" $\\rightarrow$ ".join(notes_seq))

    render_fretboard(highlight_positions=positions, show_all_notes=False)

    _render_complete_practice_button("Ejercicio 1: Single String", bpm)


def _render_exercise_2(bpm: int):
    if "ex2_target" not in st.session_state:
        st.session_state["ex2_target"] = generate_random_exercise_notes(1)[0]

    col_btn, col_target = st.columns([1, 3])
    with col_btn:
        if st.button("🎲 Cambiar Nota Objetivo", key="btn_rand_ex2"):
            st.session_state["ex2_target"] = generate_random_exercise_notes(1)[0]

    target = st.session_state["ex2_target"]

    st.markdown(
        f"""
        <div style="background:#18181B; border:1px solid #10B981; border-radius:12px; padding:16px; margin-bottom:12px;">
            <div style="font-size:0.8rem; color:#A1A1AA; text-transform:uppercase;">Nota Objetivo a Encontrar:</div>
            <div style="font-size:2.8rem; font-weight:800; color:#10B981; font-family:'Roboto Mono',monospace;">{target}</div>
            <p style="color:#E4E4E7; font-size:0.88rem; margin-bottom:0;">
                Con el metrónomo activo a <strong>{bpm} BPM</strong>, toca la nota <strong>{target}</strong> en la 6ª cuerda, luego en la 5ª, 4ª, 3ª, 2ª, 1ª y regresa a la 6ª diciendo <em>"{target}"</em> en voz alta en cada pulso.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    positions = get_all_positions_of_note(target, max_fret=15)
    render_fretboard(highlight_positions=positions, highlight_note=target)

    _render_complete_practice_button(
        f"Ejercicio 2: Vertical Single Note ({target})", bpm, notes=[target]
    )


def _render_exercise_3(bpm: int):
    if "ex3_root" not in st.session_state:
        st.session_state["ex3_root"] = generate_random_exercise_notes(1)[0]

    if st.button("🎲 Cambiar Nota Raíz del Lick", key="btn_rand_ex3"):
        st.session_state["ex3_root"] = generate_random_exercise_notes(1)[0]

    root = st.session_state["ex3_root"]
    phrase = get_3_note_phrase(root)
    phrase_str = " - ".join(phrase)

    st.markdown(
        f"""
        <div style="background:#18181B; border:1px solid #3B82F6; border-radius:12px; padding:16px; margin-bottom:12px;">
            <div style="font-size:0.8rem; color:#A1A1AA; text-transform:uppercase;">Frase Melódica de 3 Notas:</div>
            <div style="font-size:2.2rem; font-weight:800; color:#3B82F6; font-family:'Roboto Mono',monospace;">{phrase_str}</div>
            <p style="color:#E4E4E7; font-size:0.88rem; margin-bottom:0;">
                Toca la frase <strong>{phrase_str}</strong> en la 6ª cuerda, luego desciende a la 5ª, 4ª, 3ª, 2ª y 1ª cuerda con el metrónomo a <strong>{bpm} BPM</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_pos = []
    for n in phrase:
        all_pos.extend(get_all_positions_of_note(n, max_fret=15))

    render_fretboard(highlight_positions=all_pos, show_all_notes=True)

    _render_complete_practice_button(
        f"Ejercicio 3: Frase 3 Notas ({phrase_str})", bpm, notes=phrase
    )


def _render_exercise_4(variant: str, bpm: int):
    num_notes = 3 if ("4C" in variant or "4D" in variant) else 2
    alternate = "alternando" in variant.lower()

    if (
        "ex4_notes" not in st.session_state
        or len(st.session_state.get("ex4_notes", [])) != num_notes
    ):
        st.session_state["ex4_notes"] = generate_random_exercise_notes(num_notes)

    if st.button("🎲 Generar Nuevas Notas Aleatorias", key="btn_rand_ex4"):
        st.session_state["ex4_notes"] = generate_random_exercise_notes(num_notes)

    notes = st.session_state["ex4_notes"]
    notes_str = " , ".join(notes)

    desc_mode = "intercalando entre cuerdas" if alternate else "ambas en la misma cuerda"

    st.markdown(
        f"""
        <div style="background:#18181B; border:1px solid #F59E0B; border-radius:12px; padding:16px; margin-bottom:12px;">
            <div style="font-size:0.8rem; color:#A1A1AA; text-transform:uppercase;">Variante {variant.split(":")[0]}:</div>
            <div style="font-size:2.2rem; font-weight:800; color:#F59E0B; font-family:'Roboto Mono',monospace;">{notes_str}</div>
            <p style="color:#E4E4E7; font-size:0.88rem; margin-bottom:0;">
                Toca las notas <strong>{notes_str}</strong> {desc_mode} recorriendo el mástil de la 6ª a la 1ª cuerda a <strong>{bpm} BPM</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_pos = []
    for n in notes:
        all_pos.extend(get_all_positions_of_note(n, max_fret=15))

    render_fretboard(highlight_positions=all_pos, show_all_notes=True)

    _render_complete_practice_button(f"{variant.split(':')[0]} ({notes_str})", bpm, notes=notes)


def _render_exercise_5(bpm: int):
    if "ex5_start" not in st.session_state:
        st.session_state["ex5_start"] = ("C#", 6, 9)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🎲 Cambiar Nota Inicial de Octavas", key="btn_rand_ex5"):
            note = generate_random_exercise_notes(1, include_accidentals=True)[0]
            pos = get_all_positions_of_note(note, max_fret=12)
            if pos:
                s, f = pos[0]
                st.session_state["ex5_start"] = (note, s, f)

    start_note, start_str, start_fret = st.session_state["ex5_start"]

    st.markdown(
        f"""
        <div style="background:#18181B; border:1px solid #EC4899; border-radius:12px; padding:16px; margin-bottom:12px;">
            <div style="font-size:0.8rem; color:#A1A1AA; text-transform:uppercase;">Nota Inicial de Octavas:</div>
            <div style="font-size:2.2rem; font-weight:800; color:#EC4899; font-family:'Roboto Mono',monospace;">{start_note} (Cuerda {start_str}, Traste {start_fret})</div>
            <p style="color:#E4E4E7; font-size:0.88rem; margin-bottom:0;">
                Aplica en cadena los <strong>Atajos de Octava (Shortcuts 1, 2, 3, 4)</strong> saltando por el diapasón pronunciando <em>"{start_note}"</em> en voz alta en cada pulso de <strong>{bpm} BPM</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_octaves = get_all_positions_of_note(start_note, max_fret=15)
    render_fretboard(highlight_positions=all_octaves, highlight_note=start_note)

    _render_complete_practice_button(
        f"Ejercicio 5: Saltos de Octavas ({start_note})", bpm, notes=[start_note]
    )


def _render_complete_practice_button(ex_name: str, bpm: int, notes: list = None):
    st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
    if st.button(
        "✅ Registrar Sesión de Práctica Completada (5 min)",
        type="primary",
        key=f"btn_done_{ex_name}",
    ):
        save_practice_session(
            exercise_name=ex_name, duration_mins=5, bpm=bpm, notes_practiced=notes
        )
        st.balloons()
        st.success(
            f"🎉 ¡Sesión de práctica de 5 min en '{ex_name}' registrada con éxito! Racha actualizada."
        )
        st.rerun()


def _render_video_theory_guide():
    st.markdown("### 📖 Guía Teórica Exhaustiva del Vídeo")
    st.markdown(
        """
        <div style="background:#18181B; border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:20px; margin-bottom:20px;">
            <h4 style="color:#3B82F6; margin-top:0;">📺 Vídeo Original: How To Memorize The Notes Of The Fretboard</h4>
            <p style="color:#A1A1AA; font-size:0.9rem;">
                Autor: <strong>GuitarZero2Hero (Dave Tran)</strong> | URL: <a href="https://www.youtube.com/watch?v=jTCyiq5mjn8" target="_blank" style="color:#60A5FA;">https://www.youtube.com/watch?v=jTCyiq5mjn8</a>
            </p>
            <p style="color:#E4E4E7; font-size:0.9rem;">
                La premisa del vídeo radica en la distinción entre <strong>Saber</strong> el diapasón (deducir notas contando trastes) e <strong>Interiorizar</strong> el diapasón (reconocimiento instantáneo al tacto, como escribir en un teclado sin mirar).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            <div class="metric-card">
                <h4 style="color:#10B981; margin-top:0;">🎵 Regla del Alfabeto Musical</h4>
                <p style="font-size:0.88rem; color:#E4E4E7;">
                    El alfabeto musical contiene 12 notas cromáticas. Entre <strong>B y C</strong> y entre <strong>E y F</strong> NO existen sostenidos ni bemoles (1 semitono = 1 traste).
                </p>
                <div style="background:rgba(16,185,129,0.1); border-left:3px solid #10B981; padding:8px 12px; font-size:0.82rem; color:#A1A1AA;">
                    💡 <em>Chiste de Los Simpsons:</em> El cuarteto vocal "Los B-Sharps" (Los Sostenidos) se llama así porque la nota B# no existe en el sistema estándar.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="metric-card">
                <h4 style="color:#F59E0B; margin-top:0;">📌 Puntos de Referencia</h4>
                <p style="font-size:0.88rem; color:#E4E4E7;">
                    Cuerdas al aire: <strong>E - A - D - G - B - E</strong> (Mnemotecnia: <em>"Eat All Day Get Big Easy"</em>).
                </p>
                <p style="font-size:0.88rem; color:#E4E4E7;">
                    <strong>Traste 12:</strong> Duplica las notas de las cuerdas al aire una octava más agudas.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("#### ⚡ Los 4 Atajos de Octavas (Octave Shape Shortcuts)")

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(
            """
            <div class="metric-card" style="padding:14px;">
                <div style="color:#3B82F6; font-weight:700; font-size:0.85rem;">Shortcut 1</div>
                <div style="font-size:0.78rem; color:#A1A1AA; margin-top:4px;">Cuerdas 6 y 5</div>
                <div style="font-size:0.85rem; font-weight:600; color:#FFFFFF; margin-top:6px;">+2 Trastes<br>+2 Cuerdas abajo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sc2:
        st.markdown(
            """
            <div class="metric-card" style="padding:14px;">
                <div style="color:#3B82F6; font-weight:700; font-size:0.85rem;">Shortcut 2</div>
                <div style="font-size:0.78rem; color:#A1A1AA; margin-top:4px;">Cuerdas 4 y 3</div>
                <div style="font-size:0.85rem; font-weight:600; color:#FFFFFF; margin-top:6px;">+3 Trastes<br>+2 Cuerdas abajo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sc3:
        st.markdown(
            """
            <div class="metric-card" style="padding:14px;">
                <div style="color:#3B82F6; font-weight:700; font-size:0.85rem;">Shortcut 3</div>
                <div style="font-size:0.78rem; color:#A1A1AA; margin-top:4px;">Cuerdas 5 y 4</div>
                <div style="font-size:0.85rem; font-weight:600; color:#FFFFFF; margin-top:6px;">-2 Trastes pala<br>+3 Cuerdas abajo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sc4:
        st.markdown(
            """
            <div class="metric-card" style="padding:14px;">
                <div style="color:#3B82F6; font-weight:700; font-size:0.85rem;">Shortcut 4</div>
                <div style="font-size:0.78rem; color:#A1A1AA; margin-top:4px;">Cuerda 6 a 1</div>
                <div style="font-size:0.85rem; font-weight:600; color:#FFFFFF; margin-top:6px;">Mismo Traste<br>(2 octavas más alta)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_history_tab():
    st.markdown("### 📊 Historial & Registro de Práctica acumulada")

    history = load_practice_history()
    sessions = history.get("sessions", [])

    if not sessions:
        st.info(
            "👋 Aún no has registrado ninguna sesión de práctica. Completa un ejercicio en el Entrenador Autónomo para comenzar tu racha."
        )
        return

    st.markdown(f"**Total de Sesiones Registradas:** {len(sessions)}")

    # Formatear la lista de sesiones
    table_data = []
    for s in reversed(sessions):
        table_data.append(
            {
                "Fecha y Hora": s.get("timestamp"),
                "Ejercicio": s.get("exercise"),
                "Duración": f"{s.get('duration_mins', 5)} min",
                "BPM": s.get("bpm", 40),
                "Notas Practicadas": ", ".join(s.get("notes", [])),
            }
        )

    st.dataframe(table_data, use_container_width=True)
