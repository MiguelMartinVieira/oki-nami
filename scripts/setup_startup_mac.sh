#!/usr/bin/env bash
# setup_startup_mac.sh — Instala el auto-arranque del Dashboard Oki-Nami al iniciar sesión en macOS.

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/com.okinami.dashboard.plist"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_dashboard.sh"

mkdir -p "$PLIST_DIR"

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.okinami.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/okinami_dashboard.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/okinami_dashboard.err</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo "================================================================"
echo " AUTO-ARRANQUE INSTALADO EN macOS (LaunchAgent)"
echo "================================================================"
echo " Agente creado en: $PLIST_PATH"
echo " Se iniciará automáticamente al iniciar sesión en tu Mac."
