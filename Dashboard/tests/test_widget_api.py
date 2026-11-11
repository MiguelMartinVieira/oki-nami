"""
test_widget_api.py — Tests unitarios para el generador de métricas de widgets móviles.
"""

import json
import os

import pytest

from services.widget_api import update_widget_metrics_file


def test_widget_metrics_file_generation(tmp_path, monkeypatch):
    fake_json_path = os.path.join(tmp_path, "widgets_metrics.json")
    import services.widget_api as w_mod

    monkeypatch.setattr(w_mod, "JSON_PATH", fake_json_path)
    monkeypatch.setattr(w_mod, "STATIC_DIR", str(tmp_path))

    res = update_widget_metrics_file(
        total_patrimonio=1234.56,
        ahorro_ytd=500.0,
        tr_cash=200.0,
        metalico_fisico=50.0,
        guitar_streak=5,
        bote_habitos=100.0,
    )

    assert res["status"] == "ok"
    assert res["metrics"]["total_patrimonio"] == 1234.56
    assert res["metrics"]["guitar_streak"] == 5
    assert os.path.exists(fake_json_path)

    with open(fake_json_path, encoding="utf-8") as f:
        data = json.load(f)
        assert data["metrics"]["total_patrimonio_str"] == "1,234.56 €"
        assert data["metrics"]["guitar_streak_str"] == "🔥 5 Días"
