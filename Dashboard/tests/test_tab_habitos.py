"""Tests para tab_habitos.py — persistencia de eventos, bitácora de hábitos y resets.

NOTA: tab_habitos.py es un shim que reexporta de tabs.habitos.main. Para que
el monkeypatch llegue al código real hay que parchear `tabs.habitos.main.CACHE_FILE`
(no el shim) porque las funciones load_data/add_event/etc viven en main.py y
leen su propio CACHE_FILE local.
"""

import json
from pathlib import Path

import pytest

from tabs.habitos import main as habitos_main
from tabs.habitos import main as tab_habitos


@pytest.fixture
def mock_cache_file(tmp_path, monkeypatch):
    """Redirecciona la ruta de CACHE_FILE a un directorio temporal de test."""
    test_cache = tmp_path / "test_habitos_ahorros.json"
    # Patch en el módulo real (main.py), no en el shim
    monkeypatch.setattr(habitos_main, "CACHE_FILE", test_cache)
    return test_cache


def test_load_data_creates_default_file(mock_cache_file):
    """Verifica que si no existe el fichero se cree con la estructura inicial correcta."""
    assert not mock_cache_file.exists()
    data = tab_habitos.load_data()
    assert mock_cache_file.exists()
    assert data["current_month_total"] == 0.0
    assert data["current_events"] == []
    assert data["history_archive"] == []


def test_add_event(mock_cache_file):
    """Comprueba la inserción de eventos en la bitácora y la actualización del total."""
    tab_habitos.add_event("Café de la Uni", 1.80, "ahorro")
    data = tab_habitos.load_data()

    assert len(data["current_events"]) == 1
    assert data["current_month_total"] == 1.80
    event = data["current_events"][0]
    assert event["label"] == "Café de la Uni"
    assert event["type"] == "ahorro"
    assert event["value"] == 1.80
    assert "timestamp" in event
    assert "id" in event


def test_delete_event(mock_cache_file):
    """Valida la funcionalidad de deshacer (Undo) eliminando un registro por id."""
    tab_habitos.add_event("Café de la Uni", 1.80, "ahorro")
    tab_habitos.add_event("Monster", 2.00, "ahorro")

    data = tab_habitos.load_data()
    assert len(data["current_events"]) == 2

    id_to_delete = data["current_events"][0]["id"]
    tab_habitos.delete_event(id_to_delete)

    data_after = tab_habitos.load_data()
    assert len(data_after["current_events"]) == 1
    assert data_after["current_events"][0]["label"] == "Monster"
    assert data_after["current_month_total"] == 2.00


def test_archive_and_reset(mock_cache_file):
    """Comprueba el proceso de cierre del bote, su transferencia al archivo histórico y el reset."""
    tab_habitos.add_event("Snack", 2.00, "castigo_suave")
    tab_habitos.add_event("Faltar A Clase", 15.00, "castigo_grave")

    tab_habitos.archive_and_reset()

    data = tab_habitos.load_data()
    assert len(data["current_events"]) == 0
    assert data["current_month_total"] == 0.0
    assert len(data["history_archive"]) == 1

    archive = data["history_archive"][0]
    assert archive["total_suaves"] == 2.00
    assert archive["total_graves"] == 15.00
    assert archive["total_ahorros"] == 2.00
    assert archive["total_castigos"] == 15.00
    assert archive["total_mes"] == 17.00
    assert len(archive["events"]) == 2
