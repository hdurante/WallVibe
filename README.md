# Linux Wallpaper Vibe (WallVibe)

Open source Linux desktop app to manage wallpaper rotation and terminal opacity in a practical way.

WallVibe targets GNOME, KDE Plasma, and XFCE environments, with persistent configuration and optional daemon mode.

## Features

- Random wallpaper rotation from a selected folder at configurable intervals.
- Terminal opacity control for Ptyxis profiles through gsettings.
- Persistent JSON configuration file (config.json).
- GUI app built with Tkinter.
- Optional daemon mode for wallpaper rotation after login.

## Requirements

- Linux desktop session: GNOME, KDE Plasma, or XFCE.
- Python 3.10+
- Tkinter

### Install Tkinter by distro

Ubuntu/Debian:

```bash
sudo apt-get install python3-tk
```

Fedora/RHEL:

```bash
sudo dnf install python3-tkinter
```

SUSE:

```bash
sudo zypper install python3-tk
```

Arch/Manjaro:

```bash
sudo pacman -S tk
```

## Installation

Automatic setup (recommended):

```bash
chmod +x install.sh
./install.sh
```

## Run

From the project root:

```bash
python3 app.py
```

## GNOME Launcher and App Icon

The project includes:

- assets/WallVibe
- install_launcher.sh

Create local launcher:

```bash
chmod +x install_launcher.sh
./install_launcher.sh
```

This generates:

- ~/.local/share/applications/wallvibe.desktop

## Daemon Mode (persistent wallpaper rotation)

You can manage the daemon from the GUI or run it manually.

Run daemon manually:

```bash
python3 wallpaper_daemon.py
```

Run one cycle only:

```bash
python3 wallpaper_daemon.py --once
```

Enable autostart helper:

```bash
chmod +x install_autostart.sh
./install_autostart.sh
```

This generates:

- ~/.config/autostart/wallvibe-wallpaper.desktop

## Configuration

On first run, the app creates config.json automatically.

Example:

```json
{
  "app": {
    "first_run_initialized": true,
    "distro_folder_migrated": true
  },
  "ui": {
    "language": "auto"
  },
  "ptyxis": {
    "opacity": 0.85
  },
  "wallpaper": {
    "folder": "./Wallpaper/Debian",
    "interval_minutes": 60,
    "extensions": [".jpg", ".jpeg", ".png", ".bmp", ".svg", ".webp"],
    "set_dark_variant": true,
    "search_subfolders": false
  }
}
```

### KDE Plasma Note

For KDE wallpaper control, install qdbus or qdbus6.

Fedora/RHEL:

```bash
sudo dnf install qdbus
```

Ubuntu/Debian:

```bash
sudo apt install qdbus
```

Arch/Manjaro:

```bash
sudo pacman -S qdbus
```

## Build Binary (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
./dist/wallvibe
```

## Core Modules

- wallvibe_tools.config: configuration management
- wallvibe_tools.wallvibe_tools: gsettings and desktop integration helpers
- wallvibe_tools.wallpaper: wallpaper rotation logic

## Contact

- LinkedIn: https://www.linkedin.com/in/hdurante/
- GitHub: https://github.com/hdurante/

## Author

- Hector Manuel Durante Nunez

## License

Code license:

- MIT License (see LICENSE)

Wallpaper samples license:

- CC BY 4.0 (see Wallpaper/LICENSE.md)
- Additional notes: Wallpaper/README.md

## Project Structure

```text
wallvibe/
├── app.py
├── wallpaper_daemon.py
├── config.json
├── install.sh
├── install_launcher.sh
├── install_autostart.sh
├── assets/
├── locale/
├── Wallpaper/
└── wallvibe_tools/
```


