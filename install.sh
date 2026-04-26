#!/bin/bash
# Script de instalación universal para GNOME Extra Tools

set -e

echo "=== GNOME Extra Tools - Instalador ==="
echo ""

# Detectar distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ No se pudo detectar la distribución"
    exit 1
fi

echo "📦 Distribución detectada: $OS"
echo ""

# Instalar python3-tk según la distro
case "$OS" in
    ubuntu|debian)
        echo "🔧 Instalando para Ubuntu/Debian..."
        sudo apt-get update -qq
        sudo apt-get install -y python3-tk python3-venv
        echo "✓ python3-tk instalado"
        ;;
    fedora)
        echo "🔧 Instalando para Fedora..."
        sudo dnf install -y python3-tkinter
        echo "✓ python3-tkinter instalado"
        ;;
    rhel|centos)
        echo "🔧 Instalando para RHEL/CentOS..."
        sudo yum install -y python3-tkinter
        echo "✓ python3-tkinter instalado"
        ;;
    opensuse*)
        echo "🔧 Instalando para SUSE..."
        sudo zypper install -y python3-tk
        echo "✓ python3-tk instalado"
        ;;
    arch|manjaro)
        echo "🔧 Instalando para Arch/Manjaro..."
        sudo pacman -S --noconfirm tk
        echo "✓ tk instalado"
        ;;
    *)
        echo "⚠️  Distribución no soportada automáticamente: $OS"
        echo "Instala manualmente: python3-tk (o su equivalente)"
        exit 1
        ;;
esac

echo ""
echo "✓ Instalación completada"
echo ""
echo "Para ejecutar la app:"
echo "  cd $(dirname "$0")"
echo "  python3 app.py"
echo ""
