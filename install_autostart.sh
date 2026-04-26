#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/gnome-extra-tools-wallpaper.desktop"
OLD_DESKTOP_FILE="$AUTOSTART_DIR/gnome-tools-wallpaper.desktop"
PYTHON_BIN="$(command -v python3)"

mkdir -p "$AUTOSTART_DIR"
rm -f "$OLD_DESKTOP_FILE"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=GNOME Extra Tools Wallpaper Daemon
Comment=Rotacion de wallpapers desde config.json
Exec=$PYTHON_BIN $PROJECT_DIR/wallpaper_daemon.py
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Creado: $DESKTOP_FILE"
echo "Para probar ahora:"
echo "  $PYTHON_BIN $PROJECT_DIR/wallpaper_daemon.py --once"
