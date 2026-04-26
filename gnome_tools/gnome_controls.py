from __future__ import annotations

import shutil
import subprocess


class GSettingsError(RuntimeError):
    pass


def _run_gsettings_set(schema: str, key: str, value: str, path: str | None = None) -> None:
    schema_with_path = f"{schema}:{path}" if path else schema
    cmd = ["gsettings", "set", schema_with_path, key, value]

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Error desconocido ejecutando gsettings"
        raise GSettingsError(stderr)


def set_ptyxis_opacity(profile_id: str, opacity: float) -> None:
    if not profile_id.strip():
        raise ValueError("Debes indicar el profile_id de Ptyxis.")

    if opacity < 0.0 or opacity > 1.0:
        raise ValueError("La opacidad debe estar entre 0.0 y 1.0.")

    path = f"/org/gnome/Ptyxis/Profiles/{profile_id.strip()}/"
    _run_gsettings_set("org.gnome.Ptyxis.Profile", "opacity", f"{opacity:.2f}", path)


def _run_gsettings_get(schema: str, key: str, path: str | None = None) -> str:
    schema_with_path = f"{schema}:{path}" if path else schema
    cmd = ["gsettings", "get", schema_with_path, key]

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip().strip("'\"")


def get_ptyxis_current_profile_id() -> str:
    """Intenta obtener el profile UUID actual de Ptyxis."""
    profile_uuid = _run_gsettings_get("org.gnome.Ptyxis", "default-profile-uuid")
    return profile_uuid or ""


def is_ptyxis_available() -> bool:
    return shutil.which("ptyxis") is not None


def _is_process_running(process_name: str) -> bool:
    result = subprocess.run(["pgrep", "-x", process_name], check=False, capture_output=True, text=True)
    return result.returncode == 0


def is_ptyxis_running() -> bool:
    return _is_process_running("ptyxis")


def open_ptyxis() -> None:
    result = subprocess.run(["ptyxis", "--new-window"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "No se pudo abrir Ptyxis"
        raise GSettingsError(stderr)


def ensure_terminal_visible() -> tuple[str | None, bool]:
    """Retorna (nombre_terminal, se_abrio_ahora)."""
    terminal_candidates = [
        ("ptyxis", ["ptyxis", "--new-window"]),
        ("kgx", ["kgx"]),
        ("gnome-terminal", ["gnome-terminal"]),
        ("xfce4-terminal", ["xfce4-terminal"]),
        ("konsole", ["konsole"]),
        ("xterm", ["xterm"]),
    ]

    available: list[tuple[str, list[str]]] = []
    for name, cmd in terminal_candidates:
        if shutil.which(cmd[0]) is not None:
            available.append((name, cmd))

    if not available:
        return None, False

    for name, _ in available:
        if _is_process_running(name):
            return name, False

    name, cmd = available[0]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or f"No se pudo abrir {name}"
        raise GSettingsError(stderr)
    return name, True


def set_wallpaper(image_path: str, set_dark_variant: bool = True) -> None:
    uri = f"file://{image_path}"
    _run_gsettings_set("org.gnome.desktop.background", "picture-uri", f'"{uri}"')

    if set_dark_variant:
        _run_gsettings_set("org.gnome.desktop.background", "picture-uri-dark", f'"{uri}"')
