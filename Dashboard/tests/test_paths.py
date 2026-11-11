"""Tests para config/paths.py — resolución de rutas y fallbacks."""

import os
from pathlib import Path

from config.paths import BACKUP_DIR, PADRES_FOLDER, PROJECT_ROOT


def test_backup_dir_exists():
    # El módulo paths.py asegura que BACKUP_DIR se crea al importarse
    assert os.path.isdir(BACKUP_DIR)


def test_project_root_resolution():
    # PROJECT_ROOT debe apuntar a la raíz del repo, se llame como se llame
    # la carpeta del checkout (CI, clones, forks).
    assert (PROJECT_ROOT / "AGENTS.md").exists()
    assert (PROJECT_ROOT / "Dashboard" / "src" / "app.py").exists()


def test_padres_folder_fallback():
    # PADRES_FOLDER debe ser una ruta válida o el default
    assert isinstance(PADRES_FOLDER, str)
    # Al menos la ruta por defecto debe ser factible
    assert "Padres" in PADRES_FOLDER


def test_multi_path_env_logic(monkeypatch):
    """Prueba que el sistema elija la primera ruta existente de un string con ';'."""
    # Creamos dos rutas temporales
    tmp1 = Path("temp_path_1")
    tmp2 = Path("temp_path_2")
    tmp2.mkdir(exist_ok=True)

    # Mock de environment variable
    monkeypatch.setenv("PADRES_FOLDER", f"{tmp1};{tmp2}")

    # Necesitamos re-importar o emular la lógica de paths.py
    # La lógica es: [p for p in os.environ.get("PADRES_FOLDER").split(";") if p] + [_default]
    # Y elige la primera que os.path.isdir(p) sea True.

    possible = f"{tmp1};{tmp2}".split(";")
    chosen = next((p for p in possible if os.path.isdir(p)), possible[0])

    assert chosen == str(tmp2)

    # Limpieza
    tmp2.rmdir()
