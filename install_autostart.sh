#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/wallvibe-wallpaper.desktop"
OLD_DESKTOP_FILE="$AUTOSTART_DIR/gnome-tools-wallpaper.desktop"
OLD_DESKTOP_FILE_2="$AUTOSTART_DIR/gnome-extra-tools-wallpaper.desktop"
PYTHON_BIN="$(command -v python3)"
ICON_PATH="$PROJECT_DIR/assets/gnome-ico.png"

mkdir -p "$AUTOSTART_DIR"
rm -f "$OLD_DESKTOP_FILE"
rm -f "$OLD_DESKTOP_FILE_2"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=WallVibe Wallpaper Daemon
Comment=Linux Wallpaper Vibe - rotacion automatica de wallpapers
Exec=$PYTHON_BIN $PROJECT_DIR/wallpaper_daemon.py
Path=$PROJECT_DIR
Icon=$ICON_PATH
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Creado: $DESKTOP_FILE"
echo "Para probar ahora:"
echo "  $PYTHON_BIN $PROJECT_DIR/wallpaper_daemon.py --once"
