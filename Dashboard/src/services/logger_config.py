"""
logger_config.py — Configuración centralizada de logging para el Dashboard.
"""

import logging


def setup_logging():
    """Configura el logging global y silencia warnings ruidosos de Streamlit."""
    # Configuración básica
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Mutear warnings de ScriptRunContext en threads (evita spam en la terminal)
    # Streamlit suele lanzar estos warnings cuando se usan widgets desde threads,
    # pero aquí los usamos para carga de datos pura.
    logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(
        logging.ERROR
    )
    logging.getLogger("streamlit.runtime.scriptrunner.script_run_context").setLevel(logging.ERROR)

    # Reducir ruido de otras librerías
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
