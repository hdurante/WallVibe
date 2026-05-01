from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

from gnome_tools.config import ConfigManager, resolve_config_path
from gnome_tools.wallpaper import WallpaperRotator
import threading


def run_daemon(config_path: Path, pid_path: Path) -> None:
    """Ejecutar el daemon de rotación de wallpapers."""
    daemon = WallpaperDaemon(config_path, pid_path)
    daemon.start()


class WallpaperDaemon:
    def __init__(self, config_path: Path, pid_path: Path) -> None:
        self.config_path = config_path
        self.pid_path = pid_path
        self._stop_event = threading.Event()
        self.rotator: WallpaperRotator | None = None

    def _load_rotator(self) -> WallpaperRotator:
        manager = ConfigManager(self.config_path)
        config_data = manager.load()

        wallpaper = config_data.get("wallpaper", {})
        raw_folder = str(wallpaper.get("folder", "")).strip()
        folder = resolve_config_path(self.config_path.parent, raw_folder)
        interval = int(wallpaper.get("interval_minutes", 60))
        extensions = wallpaper.get("extensions", [".jpg", ".jpeg", ".png", ".bmp", ".svg", ".webp"])
        set_dark_variant = bool(wallpaper.get("set_dark_variant", True))

        if not folder:
            raise ValueError("No hay carpeta configurada. Abre la GUI y guarda una carpeta de wallpapers.")

        return WallpaperRotator(
            folder=folder,
            interval_minutes=interval,
            extensions=extensions,
            set_dark_variant=set_dark_variant,
        )

    def _handle_signal(self, signum: int, _frame) -> None:
        print(f"[wallpaper-daemon] Senal {signum} recibida. Cerrando...")
        self.stop()

    def start(self) -> None:
        self._claim_pid_file()
        self.rotator = self._load_rotator()

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self.rotator.start(on_change=self._on_change, on_error=self._on_error)
        print("[wallpaper-daemon] Iniciado.")

        while not self._stop_event.wait(timeout=0.5):
            pass

        self._clear_pid_file()

    def stop(self) -> None:
        self._stop_event.set()
        if self.rotator:
            self.rotator.stop()

    def _claim_pid_file(self) -> None:
        if self.pid_path.exists():
            raw = self.pid_path.read_text(encoding="utf-8").strip()
            if raw:
                try:
                    old_pid = int(raw)
                    os.kill(old_pid, 0)
                    print(f"[wallpaper-daemon] Ya hay un daemon corriendo (PID {old_pid}).")
                    sys.exit(1)
                except (ProcessLookupError, ValueError):
                    pass

        self.pid_path.write_text(str(os.getpid()), encoding="utf-8")

    def _clear_pid_file(self) -> None:
        try:
            self.pid_path.unlink()
        except OSError:
            pass

    def _on_change(self, _) -> None:
        pass

    def _on_error(self, error: Exception) -> None:
        print(f"[wallpaper-daemon] Error: {error}")
