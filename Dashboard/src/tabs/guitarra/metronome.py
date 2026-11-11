"""
metronome.py — Componente de metrónomo interactivo, temporizador y generador de ejercicios.
"""

import random

import streamlit as st
import streamlit.components.v1 as components

from .fretboard import CHROMATIC_SHARPS, NATURAL_NOTES


def generate_random_exercise_notes(
    count: int = 1,
    include_accidentals: bool = False,
    seed: int = None,
) -> list[str]:
    """Genera una lista de notas aleatorias para los ejercicios de práctica."""
    if seed is not None:
        random.seed(seed)

    pool = CHROMATIC_SHARPS if include_accidentals else NATURAL_NOTES
    return random.sample(pool, min(count, len(pool)))


def get_3_note_phrase(target_note: str) -> list[str]:
    """Genera la frase ascendente de 3 notas de la escala natural empezando en target_note."""
    note_clean = target_note.upper().strip()
    if note_clean not in NATURAL_NOTES:
        note_clean = "A"

    idx = NATURAL_NOTES.index(note_clean)
    phrase = [
        NATURAL_NOTES[idx],
        NATURAL_NOTES[(idx + 1) % len(NATURAL_NOTES)],
        NATURAL_NOTES[(idx + 2) % len(NATURAL_NOTES)],
    ]
    return phrase


def render_metronome_widget(default_bpm: int = 40) -> int:
    """
    Renderiza el metrónomo interactivo WebAudio con alto volumen, selector de timbre y pulso visual.
    Devuelve el BPM seleccionado por el usuario.
    """
    col1, col2 = st.columns([2, 3])

    with col1:
        bpm = st.slider(
            "⚡ Metrónomo (BPM)",
            min_value=30,
            max_value=180,
            value=default_bpm,
            step=5,
            help="GuitarZero2Hero recomienda comenzar a 40 BPM para internalizar.",
        )

    with col2:
        metronome_html = f"""
        <div id="metronome-card" style="
            background: #18181B;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 12px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <button id="btn-toggle-metro" onclick="toggleMetronome()" style="
                    background: linear-gradient(135deg, #3B82F6 0%, rgba(29, 78, 216, 0.9) 100%);
                    border: none;
                    color: white;
                    padding: 8px 18px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 0.85rem;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
                    transition: all 0.2s ease;
                ">▶ START</button>

                <div id="visual-beat" style="
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.1);
                    border: 2px solid rgba(255,255,255,0.2);
                    transition: background 0.05s ease, transform 0.05s ease;
                "></div>

                <!-- Control de Volumen -->
                <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px;">
                    <span style="font-size: 0.9rem;" title="Volumen Alto">🔊</span>
                    <input type="range" id="vol-slider" min="0.2" max="2.0" step="0.1" value="1.5" style="
                        width: 75px;
                        cursor: pointer;
                        accent-color: #3B82F6;
                    " oninput="updateVolLabel(this.value)">
                    <span id="vol-label" style="font-size: 0.72rem; color: #A1A1AA; font-weight: 600; min-width: 32px;">150%</span>
                </div>
            </div>

            <div style="text-align: right;">
                <span style="font-family: 'Roboto Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #FFFFFF;">{bpm}</span>
                <span style="font-size: 0.75rem; color: #71717A; display: block;">BPM</span>
            </div>
        </div>

        <script>
        let audioCtx = null;
        let isRunning = false;
        let timerId = null;
        let bpm = {bpm};

        function updateVolLabel(val) {{
            const lbl = document.getElementById('vol-label');
            if (lbl) {{
                lbl.innerText = Math.round(val * 100) + '%';
            }}
        }}

        function playClick() {{
            try {{
                if (!audioCtx) {{
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }}
                if (audioCtx.state === 'suspended') {{
                    audioCtx.resume();
                }}

                const volSlider = document.getElementById('vol-slider');
                const userVol = volSlider ? parseFloat(volSlider.value) : 1.5;

                const now = audioCtx.currentTime;
                
                // Oscilador 1: Tono percusivo primario (1200Hz triángulo)
                const osc1 = audioCtx.createOscillator();
                const gain1 = audioCtx.createGain();
                osc1.type = 'triangle';
                osc1.frequency.setValueAtTime(1200, now);
                gain1.gain.setValueAtTime(userVol, now);
                gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
                osc1.connect(gain1);
                gain1.connect(audioCtx.destination);
                osc1.start(now);
                osc1.stop(now + 0.06);

                // Oscilador 2: Pop penetrante (800Hz seno con más ataque para cortar el sonido de la guitarra)
                const osc2 = audioCtx.createOscillator();
                const gain2 = audioCtx.createGain();
                osc2.type = 'sine';
                osc2.frequency.setValueAtTime(800, now);
                gain2.gain.setValueAtTime(userVol * 0.7, now);
                gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
                osc2.connect(gain2);
                gain2.connect(audioCtx.destination);
                osc2.start(now);
                osc2.stop(now + 0.04);

                // Pulso visual
                const beatEl = document.getElementById('visual-beat');
                if (beatEl) {{
                    beatEl.style.background = '#10B981';
                    beatEl.style.boxShadow = '0 0 16px #10B981';
                    beatEl.style.transform = 'scale(1.35)';
                    setTimeout(() => {{
                        beatEl.style.background = 'rgba(255,255,255,0.1)';
                        beatEl.style.boxShadow = 'none';
                        beatEl.style.transform = 'scale(1.0)';
                    }}, 90);
                }}
            }} catch (err) {{
                console.error("Error reproduciendo metrónomo WebAudio:", err);
            }}
        }}

        function toggleMetronome() {{
            const btn = document.getElementById('btn-toggle-metro');
            if (isRunning) {{
                if (timerId) clearInterval(timerId);
                isRunning = false;
                if (btn) {{
                    btn.innerText = '▶ START';
                    btn.style.background = 'linear-gradient(135deg, #3B82F6 0%, rgba(29, 78, 216, 0.9) 100%)';
                }}
            }} else {{
                playClick();
                const intervalMs = (60 / bpm) * 1000;
                timerId = setInterval(playClick, intervalMs);
                isRunning = true;
                if (btn) {{
                    btn.innerText = '⏸ PAUSE';
                    btn.style.background = 'linear-gradient(135deg, #EF4444 0%, #B91C1C 100%)';
                }}
            }}
        }}
        </script>
        """
        components.html(metronome_html, height=70)

    return bpm
