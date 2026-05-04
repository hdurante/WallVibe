#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APPLICATIONS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$APPLICATIONS_DIR/wallvibe.desktop"
OLD_DESKTOP_FILE="$APPLICATIONS_DIR/gnome-tools.desktop"
OLD_DESKTOP_FILE_2="$APPLICATIONS_DIR/gnome-extra-tools.desktop"
PYTHON_BIN="$(command -v python3)"

ICON_PATH="$PROJECT_DIR/assets/gnome-ico.png"

if [ ! -f "$ICON_PATH" ]; then
    echo "No se encontro el icono requerido: $ICON_PATH"
    exit 1
fi

mkdir -p "$APPLICATIONS_DIR"
rm -f "$OLD_DESKTOP_FILE"
rm -f "$OLD_DESKTOP_FILE_2"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=WallVibe
Comment=Linux Wallpaper Vibe
GenericName=Wallpaper Manager
TryExec=$PYTHON_BIN
Exec=$PYTHON_BIN $PROJECT_DIR/app.py
Path=$PROJECT_DIR
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Settings;
StartupNotify=true
StartupWMClass=WallVibe
EOF

chmod +x "$DESKTOP_FILE"

echo "Creado launcher: $DESKTOP_FILE"
echo "Icono usado: $ICON_PATH"
