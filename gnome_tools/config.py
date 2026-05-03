from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "first_run_initialized": False,
        "distro_folder_migrated": False,
    },
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
        "search_subfolders": False,
    },
}

DEFAULT_DISTRO_FOLDERS = {
    "./Wallpaper",
    "./Wallpaper/Ubuntu",
    "./Wallpaper/Fedora",
    "./Wallpaper/SuSE",
}


def _read_os_release() -> dict[str, str]:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in os_release.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")
        data[key] = value.lower()

    return data


def _detect_first_run_wallpaper_folder() -> str:
    info = _read_os_release()
    distro_id = info.get("id", "")
    distro_like = info.get("id_like", "")
    haystack = f"{distro_id} {distro_like}"

    if any(name in haystack for name in ("opensuse", "suse", "sle")):
        return "./Wallpaper/SuSE"
    if "fedora" in haystack:
        return "./Wallpaper/Fedora"
    if "ubuntu" in haystack:
        return "./Wallpaper/Ubuntu"

    return "./Wallpaper"


def _build_first_run_config() -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    wallpaper = config.setdefault("wallpaper", {})
    wallpaper["folder"] = _detect_first_run_wallpaper_folder()
    config.setdefault("app", {})["first_run_initialized"] = True
    config.setdefault("app", {})["distro_folder_migrated"] = True
    return config


def _apply_first_run_defaults_if_needed(config: dict[str, Any]) -> bool:
    app_cfg = config.setdefault("app", {})
    already_initialized = bool(app_cfg.get("first_run_initialized", False))
    if already_initialized:
        return False

    wallpaper = config.setdefault("wallpaper", {})
    folder = str(wallpaper.get("folder", "")).strip()
    if not folder or folder == "./Wallpaper":
        wallpaper["folder"] = _detect_first_run_wallpaper_folder()

    app_cfg["first_run_initialized"] = True
    return True


def _apply_distro_folder_migration_if_needed(config: dict[str, Any]) -> bool:
    app_cfg = config.setdefault("app", {})
    already_migrated = bool(app_cfg.get("distro_folder_migrated", False))
    if already_migrated:
        return False

    wallpaper = config.setdefault("wallpaper", {})
    folder = str(wallpaper.get("folder", "")).strip()
    detected_folder = _detect_first_run_wallpaper_folder()

    changed = False
    if folder in DEFAULT_DISTRO_FOLDERS and folder != detected_folder:
        wallpaper["folder"] = detected_folder
        changed = True

    app_cfg["distro_folder_migrated"] = True
    return True


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
            self.config = _build_first_run_config()
            self.save()
            return self.config

        raw = self.config_path.read_text(encoding="utf-8").strip()
        if not raw:
            self.config = _build_first_run_config()
            self.save()
            return self.config

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("El archivo de configuracion debe contener un objeto JSON.")

        self.config = _merge_defaults(data, DEFAULT_CONFIG)
        changed = _apply_first_run_defaults_if_needed(self.config)
        changed = _apply_distro_folder_migration_if_needed(self.config) or changed
        if changed:
            self.save()
        return self.config

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
