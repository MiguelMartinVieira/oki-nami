#!/usr/bin/env bash
# disable_startup_mac.sh — Desinstala el auto-arranque del Dashboard Oki-Nami en macOS.

PLIST_PATH="$HOME/Library/LaunchAgents/com.okinami.dashboard.plist"

if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null
    rm -f "$PLIST_PATH"
    echo "Auto-arranque de Oki-Nami desactivado correctamente."
else
    echo "No había ningún auto-arranque instalado."
fi
