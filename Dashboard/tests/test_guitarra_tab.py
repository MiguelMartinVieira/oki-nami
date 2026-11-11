"""
test_guitarra_tab.py — Tests unitarios para el módulo de guitarra (Oki-Nami Dashboard).
"""

import os

import pytest

from tabs.guitarra.fretboard import (
    NATURAL_NOTES,
    get_all_positions_of_note,
    get_note_name,
    get_octave_shortcut_target,
    normalize_note,
)
from tabs.guitarra.metronome import generate_random_exercise_notes, get_3_note_phrase
from tabs.guitarra.storage import get_practice_stats, load_practice_history, save_practice_session


def test_open_string_notes():
    """Verifica que las cuerdas al aire (traste 0) en afinación estándar sean E, A, D, G, B, E."""
    assert get_note_name(6, 0) == "E"  # Low E
    assert get_note_name(5, 0) == "A"
    assert get_note_name(4, 0) == "D"
    assert get_note_name(3, 0) == "G"
    assert get_note_name(2, 0) == "B"
    assert get_note_name(1, 0) == "E"  # High E


def test_12th_fret_rule():
    """El traste 12 debe tener exactamente la misma nota que la cuerda al aire."""
    for string_num in range(1, 7):
        open_note = get_note_name(string_num, 0)
        fret12_note = get_note_name(string_num, 12)
        assert open_note == fret12_note, (
            f"Cuerda {string_num}: Traste 0 ({open_note}) != Traste 12 ({fret12_note})"
        )


def test_b_c_and_e_f_rules():
    """Prueba que entre B y C y entre E y F haya solo 1 traste de diferencia en la 5ª cuerda."""
    # En la 5ª cuerda (A):
    # Traste 0 = A, Traste 2 = B, Traste 3 = C (1 traste entre B y C)
    # Traste 5 = D, Traste 7 = E, Traste 8 = F (1 traste entre E y F)
    assert get_note_name(5, 2) == "B"
    assert get_note_name(5, 3) == "C"

    assert get_note_name(5, 7) == "E"
    assert get_note_name(5, 8) == "F"


def test_octave_shortcuts():
    """Prueba los atajos de octavas."""
    # Shortcut 1: 6ª cuerda traste 5 (A) -> 4ª cuerda traste 7 (A)
    target = get_octave_shortcut_target(6, 5)
    assert target is not None
    target_str, target_fret, name = target
    assert target_str == 4
    assert target_fret == 7
    assert get_note_name(6, 5) == get_note_name(4, 7)

    # Shortcut 2: 4ª cuerda traste 5 (G) -> 2ª cuerda traste 8 (G)
    target2 = get_octave_shortcut_target(4, 5)
    assert target2 is not None
    target_str2, target_fret2, _ = target2
    assert target_str2 == 2
    assert target_fret2 == 8
    assert get_note_name(4, 5) == get_note_name(2, 8)


def test_random_exercise_notes():
    """Verifica que el generador de notas aleatorias devuelva la cantidad requerida de notas naturales."""
    notes = generate_random_exercise_notes(3, include_accidentals=False)
    assert len(notes) == 3
    for n in notes:
        assert n in NATURAL_NOTES


def test_3_note_phrase():
    """Verifica la generación de la frase ascendente de 3 notas."""
    phrase = get_3_note_phrase("A")
    assert phrase == ["A", "B", "C"]

    phrase_b = get_3_note_phrase("G")
    assert phrase_b == ["G", "A", "B"]


def test_practice_storage(tmp_path, monkeypatch):
    """Prueba el guardado y cálculo de estadísticas de sesiones de práctica."""
    fake_file = os.path.join(tmp_path, "test_guitar_practice.json")
    import tabs.guitarra.storage as storage_mod

    monkeypatch.setattr(storage_mod, "FILE_PATH", fake_file)
    monkeypatch.setattr(storage_mod, "CACHE_DIR", str(tmp_path))

    save_practice_session(
        "Ejercicio 1: Single String", duration_mins=5, bpm=50, notes_practiced=["A"]
    )
    stats = get_practice_stats()

    assert stats["total_sessions"] == 1
    assert stats["total_minutes"] == 5
    assert stats["max_bpm"] == 50
    assert stats["streak"] == 1


def test_exercise_render_functions(monkeypatch):
    """Verifica que las funciones de renderizado de ejercicios (_render_exercise_1..5) se ejecuten sin errores de variables."""
    from unittest.mock import MagicMock

    import tabs.guitarra.main as g_main

    # Mock de componentes de streamlit para pruebas sin interfaz gráfica activa
    monkeypatch.setattr("streamlit.markdown", lambda *a, **k: None)
    monkeypatch.setattr("streamlit.write", lambda *a, **k: None)
    monkeypatch.setattr("streamlit.button", lambda *a, **k: False)
    monkeypatch.setattr("streamlit.radio", lambda *a, **k: 6)
    monkeypatch.setattr(
        "streamlit.columns",
        lambda spec: [MagicMock() for _ in (spec if isinstance(spec, list) else range(spec))],
    )

    g_main._render_exercise_1(40)
    g_main._render_exercise_2(40)
    g_main._render_exercise_3(40)
    g_main._render_exercise_4("Ejercicio 4A", 40)
    g_main._render_exercise_5(40)
