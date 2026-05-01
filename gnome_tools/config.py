from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "ui": {
        "language": "auto",
    },
    "ptyxis": {
        "opacity": 0.85,
    },
    "wallpaper": {
        "folder": "./Wallpaper",
        "interval_minutes": 60,
        "extensions": [".jpg", ".jpeg", ".png", ".bmp", ".svg", ".webp"],
        "set_dark_variant": True,
    },
}


def resolve_config_path(base_path: Path, configured_path: str) -> Path:
    path = Path(configured_path).expanduser()
    if path.is_absolute():
        return path
    return (base_path / path).resolve()


def _merge_defaults(user_config: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)
    for key, value in user_config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_defaults(value, merged[key])
        else:
            merged[key] = value
    return merged


class ConfigManager:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config: dict[str, Any] = deepcopy(DEFAULT_CONFIG)

    def load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            self.config = deepcopy(DEFAULT_CONFIG)
            self.save()
            return self.config

        raw = self.config_path.read_text(encoding="utf-8").strip()
        if not raw:
            self.config = deepcopy(DEFAULT_CONFIG)
            self.save()
            return self.config

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("El archivo de configuracion debe contener un objeto JSON.")

        self.config = _merge_defaults(data, DEFAULT_CONFIG)
        return self.config

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
