"""
conftest.py — Configuración compartida de pytest.

Añade Dashboard/src/ al path para que los imports funcionen sin instalar.
"""

import sys
from pathlib import Path

# Insertar src/ en el path para que los tests puedan importar los módulos
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def pytest_configure(config):
    # Registrar el marcador 'timeout' para evitar advertencias de Pytest
    config.addinivalue_line("markers", "timeout(seconds): tiempo máximo de ejecución para el test.")
