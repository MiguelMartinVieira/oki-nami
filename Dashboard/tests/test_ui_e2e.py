import os

import pytest
from streamlit.testing.v1 import AppTest

# Ruta relativa al entry point del dashboard (debe ser el script real de streamlit, no un launcher de subprocesos)
APP_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "app.py")


@pytest.mark.timeout(60)  # Añadir un timeout prudencial por las llamadas externas
def test_dashboard_renders_without_errors():
    """
    Simula la carga inicial del dashboard de forma End-to-End.
    Verifica que la UI no lanza excepciones no controladas
    durante el renderizado de la estructura principal.
    """
    # Configuramos el AppTest
    at = AppTest.from_file(APP_PATH)

    # Ejecutamos la app (el timeout es manejado por el plugin pytest-timeout si se usa,
    # pero aquí AppTest espera a que la app termine su ejecución natural)
    at.run(timeout=45)

    # Validamos que no haya excepciones
    assert not at.exception, (
        f"La inicialización del dashboard falló con excepciones: {at.exception}"
    )

    # Con datos disponibles deben renderizarse las pestañas principales. En
    # entornos sin datos (p.ej. CI sin credenciales ni CSVs locales) la app
    # muestra el aviso "configura credentials.json" y se detiene ANTES de las
    # tabs: eso también es un arranque válido (la clave es que no haya
    # excepciones, ya comprobado arriba).
    assert len(at.tabs) > 0 or len(at.info) > 0 or len(at.markdown) > 0, (
        "La app no renderizó elementos visuales principales ni aviso de datos."
    )
