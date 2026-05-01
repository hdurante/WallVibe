from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
from pathlib import Path

from gnome_tools.config import ConfigManager
from gnome_tools.config import ConfigManager, resolve_config_path
from gnome_tools.wallpaper import WallpaperRotator

BASE_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"
DEFAULT_PID_PATH = BASE_DIR / ".wallpaper_daemon.pid"


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
                    raise RuntimeError("El daemon ya está en ejecución.")
                except ProcessLookupError:
                    pass
                except ValueError:
                    pass

        self.pid_path.write_text(str(os.getpid()), encoding="utf-8")

    def _clear_pid_file(self) -> None:
        try:
            self.pid_path.unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def _on_change(image_path: Path) -> None:
        print(f"[wallpaper-daemon] Wallpaper aplicado: {image_path.name}")

    def _on_error(self, error: Exception) -> None:
        print(f"[wallpaper-daemon] Error: {error}", file=sys.stderr)
        self.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daemon de rotacion de wallpapers para GNOME.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Ruta al config.json (por defecto: ./config.json)",
    )
    parser.add_argument(
        "--pid-file",
        default=str(DEFAULT_PID_PATH),
        help="Ruta para guardar el PID del daemon.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Aplica un wallpaper una vez y sale.",
    )
    return parser.parse_args()


def run_once(config_path: Path) -> int:
    manager = ConfigManager(config_path)
    config_data = manager.load()
    wallpaper = config_data.get("wallpaper", {})

    raw_folder = str(wallpaper.get("folder", "")).strip()
    folder = resolve_config_path(config_path.parent, raw_folder)
    interval = int(wallpaper.get("interval_minutes", 60))
    extensions = wallpaper.get("extensions", [".jpg", ".jpeg", ".png", ".bmp", ".svg", ".webp"])
    set_dark_variant = bool(wallpaper.get("set_dark_variant", True))

    rotator = WallpaperRotator(
        folder=folder,
        interval_minutes=interval,
        extensions=extensions,
        set_dark_variant=set_dark_variant,
    )
    image = rotator.rotate_once()
    print(f"[wallpaper-daemon] Wallpaper aplicado una vez: {image.name}")
    return 0


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    pid_path = Path(args.pid_file).expanduser().resolve()

    try:
        if args.once:
            return run_once(config_path)

        daemon = WallpaperDaemon(config_path, pid_path)
        daemon.start()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[wallpaper-daemon] Error fatal: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
