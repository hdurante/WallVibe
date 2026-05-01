from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

AUTOSTART_FILE_NAME = "gnome-extra-tools-wallpaper.desktop"
LEGACY_AUTOSTART_FILE_NAME = "gnome-tools-wallpaper.desktop"
PID_FILE_NAME = ".wallpaper_daemon.pid"
ICON_FILE_NAME = "gnome-ico.png"


def autostart_file_path() -> Path:
    return Path.home() / ".config" / "autostart" / AUTOSTART_FILE_NAME


def legacy_autostart_file_path() -> Path:
    return Path.home() / ".config" / "autostart" / LEGACY_AUTOSTART_FILE_NAME


def pid_file_path(project_dir: Path) -> Path:
    return project_dir / PID_FILE_NAME


def icon_file_path(project_dir: Path) -> Path:
    return project_dir / "assets" / ICON_FILE_NAME


def daemon_command(project_dir: Path, python_executable: str | None = None) -> list[str]:
    # Detectar si estamos en un binario compilado por PyInstaller
    is_frozen = getattr(sys, 'frozen', False)
    
    if is_frozen:
        # Si estamos compilados, ejecutar el binario unificado con --daemon
        gnome_tools_exe = Path(sys.executable).parent / "gnome-extra-tools"
        if gnome_tools_exe.exists():
            return [str(gnome_tools_exe), "--daemon"]
    
    # Modo desarrollo: ejecutar app.py con --daemon
    python_bin = python_executable or sys.executable or "python3"
    app_script = project_dir / "app.py"

    return [
        python_bin,
        str(app_script),
        "--daemon",
    ]


def _pid_from_file(pid_path: Path) -> int | None:
    if not pid_path.exists():
        return None

    raw = pid_path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    try:
        return int(raw)
    except ValueError:
        return None


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def is_daemon_running(project_dir: Path) -> bool:
    pid_path = pid_file_path(project_dir)
    pid = _pid_from_file(pid_path)
    if pid is None:
        return False

    if _is_pid_alive(pid):
        return True

    try:
        pid_path.unlink(missing_ok=True)
    except OSError:
        pass
    return False


def start_daemon(project_dir: Path, python_executable: str | None = None) -> bool:
    if is_daemon_running(project_dir):
        return False

    cmd = daemon_command(project_dir, python_executable)
    process = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=str(project_dir),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    pid_path = pid_file_path(project_dir)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if is_daemon_running(project_dir):
            return True
        if process.poll() is not None:
            return False
        time.sleep(0.05)

    return is_daemon_running(project_dir)


def stop_daemon(project_dir: Path) -> bool:
    pid_path = pid_file_path(project_dir)
    pid = _pid_from_file(pid_path)
    if pid is None:
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pid_path.unlink(missing_ok=True)
        return False

    return True


def is_autostart_enabled() -> bool:
    return autostart_file_path().exists() or legacy_autostart_file_path().exists()


def enable_autostart(project_dir: Path, python_executable: str | None = None) -> Path:
    desktop_path = autostart_file_path()
    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_autostart_file_path().unlink(missing_ok=True)

    command = daemon_command(project_dir, python_executable)
    exec_line = " ".join(_shell_quote(part) for part in command)
    icon_path = icon_file_path(project_dir)

    desktop_content = "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Name=GNOME Extra Tools Wallpaper Daemon",
            "Comment=Rotacion de wallpapers desde config.json",
            f"Exec={exec_line}",
            f"Path={project_dir}",
            f"Icon={icon_path}",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "",
        ]
    )

    desktop_path.write_text(desktop_content, encoding="utf-8")
    return desktop_path


def disable_autostart() -> None:
    autostart_file_path().unlink(missing_ok=True)
    legacy_autostart_file_path().unlink(missing_ok=True)


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
