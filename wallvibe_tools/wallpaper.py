"""Wallpaper rotation engine for WallVibe.

Implements image discovery and randomized rotation with interval-based
threading, optional subfolder scanning, and callback hooks.

Author: Hector Manuel Durante Nunez
Contact:
- LinkedIn: https://www.linkedin.com/in/hdurante/
- GitHub: https://github.com/hdurante/
"""

from __future__ import annotations

import random
import threading
from pathlib import Path

from .wallvibe_tools import set_wallpaper


class WallpaperRotator:
    def __init__(
        self,
        folder: Path,
        interval_minutes: int,
        extensions: list[str],
        set_dark_variant: bool = True,
        search_subfolders: bool = False,
    ) -> None:
        self.folder = folder
        self.interval_minutes = max(1, int(interval_minutes))
        self.extensions = [ext.lower() for ext in extensions]
        self.set_dark_variant = set_dark_variant
        self.search_subfolders = search_subfolders

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _load_images(self) -> list[Path]:
        if not self.folder.exists() or not self.folder.is_dir():
            return []

        files = [
            path
            for path in self.folder.iterdir()
            if path.is_file() and path.suffix.lower() in self.extensions
        ]

        if not self.search_subfolders:
            return files

        # Search up to two levels total: root folder and one subfolder level.
        for child in self.folder.iterdir():
            if not child.is_dir():
                continue

            files.extend(
                path
                for path in child.iterdir()
                if path.is_file() and path.suffix.lower() in self.extensions
            )

        return files

    def rotate_once(self) -> Path:
        images = self._load_images()
        if not images:
            raise FileNotFoundError("No se encontraron imagenes en la carpeta seleccionada.")

        chosen = random.choice(images)
        set_wallpaper(str(chosen.resolve()), set_dark_variant=self.set_dark_variant)
        return chosen

    def start(self, on_change=None, on_error=None) -> None:
        if self.is_running:
            return

        self._stop_event.clear()

        def _runner() -> None:
            while not self._stop_event.is_set():
                try:
                    image = self.rotate_once()
                    if on_change:
                        on_change(image)
                except Exception as exc:  # noqa: BLE001
                    if on_error:
                        on_error(exc)
                    self._stop_event.set()
                    return

                seconds = self.interval_minutes * 60
                if self._stop_event.wait(timeout=seconds):
                    return

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
