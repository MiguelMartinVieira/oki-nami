"""
widget_api.py — Servidor de métricas en JSON estático para Widgets móviles (Scriptable / Shortcuts / Android).

Escribe periódicamente Dashboard/src/static/widgets_metrics.json
que se sirve automáticamente en /app/static/widgets_metrics.json.
"""

import datetime
import json
import os
from typing import Any

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
JSON_PATH = os.path.join(STATIC_DIR, "widgets_metrics.json")


def update_widget_metrics_file(
    total_patrimonio: float = 0.0,
    ahorro_ytd: float = 0.0,
    tr_cash: float = 0.0,
    metalico_fisico: float = 0.0,
    guitar_streak: int = 0,
    bote_habitos: float = 0.0,
) -> dict[str, Any]:
    """Genera y guarda el JSON de métricas para consumo por los widgets móviles."""
    os.makedirs(STATIC_DIR, exist_ok=True)

    metrics_payload = {
        "status": "ok",
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            "total_patrimonio": round(total_patrimonio, 2),
            "total_patrimonio_str": f"{total_patrimonio:,.2f} €",
            "ahorro_ytd": round(ahorro_ytd, 2),
            "ahorro_ytd_str": f"{ahorro_ytd:,.2f} €",
            "tr_cash": round(tr_cash, 2),
            "metalico_fisico": round(metalico_fisico, 2),
            "guitar_streak": guitar_streak,
            "guitar_streak_str": f"🔥 {guitar_streak} Días",
            "bote_habitos": round(bote_habitos, 2),
            "bote_habitos_str": f"{bote_habitos:,.2f} €",
        },
    }

    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(metrics_payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error escribiendo widgets_metrics.json: {e}")

    return metrics_payload
