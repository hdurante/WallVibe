from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

AUTOSTART_FILE_NAME = "gnome-extra-tools-wallpaper.desktop"
LEGACY_AUTOSTART_FILE_NAME = "gnome-tools-wallpaper.desktop"
PID_FILE_NAME = ".wallpaper_daemon.pid"


def autostart_file_path() -> Path:
    return Path.home() / ".config" / "autostart" / AUTOSTART_FILE_NAME


def legacy_autostart_file_path() -> Path:
    return Path.home() / ".config" / "autostart" / LEGACY_AUTOSTART_FILE_NAME


def pid_file_path(project_dir: Path) -> Path:
    return project_dir / PID_FILE_NAME


def daemon_command(project_dir: Path, python_executable: str | None = None) -> list[str]:
    python_bin = python_executable or sys.executable or "python3"
    daemon_script = project_dir / "wallpaper_daemon.py"
    config_path = project_dir / "config.json"
    pid_path = pid_file_path(project_dir)

    return [
        python_bin,
        str(daemon_script),
        "--config",
        str(config_path),
        "--pid-file",
        str(pid_path),
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
    subprocess.Popen(  # noqa: S603
        cmd,
        cwd=str(project_dir),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


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

    desktop_content = "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Name=GNOME Extra Tools Wallpaper Daemon",
            "Comment=Rotacion de wallpapers desde config.json",
            f"Exec={exec_line}",
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
