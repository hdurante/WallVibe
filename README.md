# GNOME Extra Tools (Python)

Proyecto open source para agregar funciones comunes y deseables de interfaz y wallpapers que normalmente no vienen integradas por defecto en GNOME.

App de escritorio para agregar controles de GNOME que no aparecen de forma clara en las interfaces de Ubuntu/Fedora/SUSE.

## Funciones incluidas

- Ajuste de opacidad para perfiles de Ptyxis por `gsettings`.
- Rotación aleatoria de wallpapers por carpeta cada X minutos.
- Configuración persistente en `config.json` para evitar cambios de código.
- Interfaz simple y funcional con Tkinter.

## Requisitos

- Linux con GNOME y `gsettings` disponible.
- Python 3.10+.
- Tkinter (preinstalado en Ubuntu, Fedora, SUSE).

## Instalación

### Automática (recomendado)
```bash
chmod +x install.sh
./install.sh
```

### Manual por distribución

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-tk
```

**Fedora/RHEL:**
```bash
sudo dnf install python3-tkinter
```

**SUSE:**
```bash
sudo zypper install python3-tk
```

**Arch/Manjaro:**
```bash
sudo pacman -S tk
```

## Ejecutar

```bash
cd /home/hdurante/Documentos/Workspace/Python/gnome-tools
python3 app.py
```

## Icono de la app en GNOME

Para evitar que GNOME muestre el engrane genérico, ahora el proyecto incluye:

- `assets/gnome-ico.png` (icono de la app)
- `install_launcher.sh` (crea `~/.local/share/applications/gnome-extra-tools.desktop`)

Pasos:

```bash
cd /home/hdurante/Documentos/Workspace/Python/gnome-tools
chmod +x install_launcher.sh
./install_launcher.sh
```

Si quieres tu propio icono, crea o exporta un PNG de 256x256 y guárdalo en:

`assets/gnome-ico.png`

La app cargará ese PNG como icono de ventana y el launcher lo usará automáticamente.

## Rotacion al cerrar GUI o reiniciar sesion

La rotacion iniciada desde la ventana se detiene al cerrar la app.
Para mantenerla activa automaticamente al iniciar sesion, usa el daemon sin GUI.
Ahora puedes controlarlo directamente desde la interfaz en la seccion **Daemon persistente**:

- Iniciar daemon
- Detener daemon
- Activar autostart
- Desactivar autostart

Tambien puedes usar comandos manuales si lo prefieres:

```bash
cd /home/hdurante/Documentos/Workspace/Python/gnome-tools
python3 wallpaper_daemon.py
```

### Crear autostart automaticamente

```bash
cd /home/hdurante/Documentos/Workspace/Python/gnome-tools
chmod +x install_autostart.sh
./install_autostart.sh
```

Esto crea `~/.config/autostart/gnome-extra-tools-wallpaper.desktop`.

### Probar una vez (sin dejar daemon corriendo)

```bash
python3 wallpaper_daemon.py --once
```

### Si prefieres .desktop manual

Ejemplo de entrada:

```ini
[Desktop Entry]
Type=Application
Name=GNOME Extra Tools Wallpaper Daemon
Exec=python3 /home/hdurante/Documentos/Workspace/Python/gnome-tools/wallpaper_daemon.py
X-GNOME-Autostart-enabled=true
Terminal=false
```

No necesitas `.sh` para esta funcionalidad: el proyecto ya controla autostart y daemon de forma nativa.

## Crear ejecutable con PyInstaller (opcional)

Si quieres distribuir como binario sin requerir Python:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
# Genera: ./dist/app (binario ejecutable ~70MB)
./dist/app
```

## Configuración

Al primer arranque se crea `config.json` automáticamente. Ejemplo:

```json
{
  "ptyxis": {
    "profile_id": "<id-ptyxis>",
    "opacity": 0.85
  },
  "wallpaper": {
    "folder": "/ruta/a/imagenes",
    "interval_minutes": 60,
    "extensions": [".jpg", ".jpeg", ".png", ".bmp", ".svg", ".webp"],
    "set_dark_variant": true
  }
}
```

## Licencia de wallpapers de ejemplo

Las imagenes dentro de la carpeta `Wallpaper/` se distribuyen con licencia propia para evitar ambiguedades con la licencia del codigo.

- Licencia: CC BY 4.0
- Detalle: `Wallpaper/LICENSE.md`
- Contexto y uso: `Wallpaper/README.md`

## Nota sobre el ID de perfil de Ptyxis

El comando equivalente es:

```bash
gsettings set org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/<id>/ opacity 0.85
```

La app detecta automáticamente tu perfil actual al iniciar.

## Módulos genéricos (sin dependencia GUI)

Los módulos core pueden usarse desde scripts, CLI o cualquier otro framework:

- `gnome_tools.config` — Gestión de configuración
- `gnome_tools.gnome_controls` — Interfaz con gsettings
- `gnome_tools.wallpaper` — Rotación de wallpapers

---

## ¿Por qué Tkinter?

### Compatibilidad multiplataforma
| Aspecto | Tkinter | GTK+4 | Qt5 |
|--------|---------|--------|-----|
| **Preinstalado Linux** | ✅ 99% | ⚠️ 50% | ⚠️ 30% |
| **Dependencias pip** | ❌ 0 | ✅ 1 | ✅ 2+ |
| **Tamaño** | 2 MB | 50 MB | 200+ MB |
| **Compilación en venv** | ✅ Automática | ❌ Requiere libs | ❌ Requiere libs |
| **PyInstaller** | ✅ Automático | ⚠️ Manual | ⚠️ Manual |

Tkinter es la opción más pragmática y portátil para herramientas Linux simples.

---

## Estructura del proyecto

```
gnome-extra-tools/
├── app.py                 # Interfaz Tkinter principal
├── install.sh             # Script de instalación automático
├── install_launcher.sh    # Crea launcher GNOME con icono
├── install_autostart.sh   # Crea el .desktop en ~/.config/autostart
├── assets/
│   └── gnome-ico.png      # Icono personalizado de la app
├── wallpaper_daemon.py    # Rotación sin GUI para autostart/login
├── config.json            # Configuración persistente (generado al inicio)
├── requirements.txt       # Sin dependencias externas (solo comentarios)
├── README.md              # Este archivo
└── gnome_tools/
    ├── __init__.py
    ├── config.py          # Gestor de configuración JSON
    ├── gnome_controls.py  # Interfaz con gsettings
    └── wallpaper.py       # Rotación de wallpapers con threading
```


