#!/usr/bin/env bash
# run_dashboard.sh — Script para ejecutar el Dashboard de Finanzas Oki-Nami en macOS.

export PATH="$HOME/.local/bin:$PATH"
export UV_PROJECT_ENVIRONMENT="$HOME/.local/share/OkiNami/.venv"
export PYTHONIOENCODING="utf-8"

# Desactivar IPv6 si está causando problemas con APIs externas (ej. punto de acceso móvil)
# networksetup -setv6off "Wi-Fi" 2>/dev/null

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/../Dashboard" || exit 1

echo "============================================="
echo "   Iniciando Dashboard Financiero Oki-Nami"
echo "============================================="

PORT=8505

# Si ya está corriendo en el puerto dedicado 8505, simplemente abrir el navegador
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}" | grep -q "200"; then
    echo "El dashboard ya está en ejecución en el puerto ${PORT}. Abriendo en el navegador..."
    open "http://localhost:${PORT}"
    exit 0
fi

(sleep 2 && open "http://localhost:${PORT}") &

if command -v uv >/dev/null 2>&1; then
    uv run python run_dashboard.py
elif [ -f "$HOME/.local/bin/uv" ]; then
    "$HOME/.local/bin/uv" run python run_dashboard.py
else
    python3 run_dashboard.py
fi
