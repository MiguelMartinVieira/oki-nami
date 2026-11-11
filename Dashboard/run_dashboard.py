"""
Entry point para el Dashboard de Finanzas.
Ejecuta: python run_dashboard.py
"""

import os
import subprocess
import sys


def main() -> None:
    """Arranca Streamlit apuntando a src/app.py."""
    python_exe = sys.executable

    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, "src", "app.py")

    command = [
        python_exe,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port",
        "8505",
    ]

    print("=" * 44)
    print("  Iniciando Dashboard Financiero 2.0")
    print(f"  Python  : {python_exe}")
    print(f"  App     : {app_path}")
    print("=" * 44)

    try:
        subprocess.run(command)
    except KeyboardInterrupt:
        print("\nDeteniendo el dashboard...")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
