"""
storage.py — Persistencia local de sesiones de práctica de guitarra.

Almacena datos en .cache/guitar_practice.json.
"""

import datetime
import json
import os
from typing import Any

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".cache")
FILE_PATH = os.path.join(CACHE_DIR, "guitar_practice.json")


def _ensure_file():
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(FILE_PATH):
        initial_data = {
            "sessions": [],
            "streak": 0,
            "last_practice_date": None,
        }
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)


def load_practice_history() -> dict[str, Any]:
    """Carga el historial completo de práctica desde el archivo JSON."""
    _ensure_file()
    try:
        with open(FILE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sessions": [], "streak": 0, "last_practice_date": None}


def save_practice_session(
    exercise_name: str,
    duration_mins: int = 5,
    bpm: int = 40,
    notes_practiced: list[str] = None,
) -> dict[str, Any]:
    """
    Registra una nueva sesión de práctica completada y actualiza la racha de días consecutivos.
    """
    data = load_practice_history()
    today_str = datetime.date.today().isoformat()
    now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Actualizar racha (streak)
    last_date_str = data.get("last_practice_date")
    if last_date_str:
        last_date = datetime.date.fromisoformat(last_date_str)
        delta_days = (datetime.date.today() - last_date).days
        if delta_days == 1:
            data["streak"] = data.get("streak", 0) + 1
        elif delta_days > 1:
            data["streak"] = 1
        # si delta_days == 0 (mismo día), mantiene la racha
    else:
        data["streak"] = 1

    data["last_practice_date"] = today_str

    new_session = {
        "timestamp": now_ts,
        "date": today_str,
        "exercise": exercise_name,
        "duration_mins": duration_mins,
        "bpm": bpm,
        "notes": notes_practiced or [],
    }

    data.setdefault("sessions", []).append(new_session)

    try:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando sesión de práctica de guitarra: {e}")

    return data


def get_practice_stats() -> dict[str, Any]:
    """Calcula métricas agregadas de práctica acumulada."""
    data = load_practice_history()
    sessions = data.get("sessions", [])

    total_sessions = len(sessions)
    total_minutes = sum(s.get("duration_mins", 5) for s in sessions)
    max_bpm = max((s.get("bpm", 40) for s in sessions), default=40)
    streak = data.get("streak", 0)

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "max_bpm": max_bpm,
        "streak": streak,
        "last_practice": data.get("last_practice_date"),
    }
