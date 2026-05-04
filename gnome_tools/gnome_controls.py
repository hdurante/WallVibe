from __future__ import annotations

import ast
import os
import shutil
import subprocess
from pathlib import Path


class GSettingsError(RuntimeError):
    pass


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
        data[key.strip().lower()] = value.strip().strip('"').strip("'").lower()

    return data


def _list_schemas() -> set[str]:
    result = subprocess.run(["gsettings", "list-schemas"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


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


def set_kgx_transparency(opacity: float) -> None:
    if opacity < 0.0 or opacity > 1.0:
        raise ValueError("La opacidad debe estar entre 0.0 y 1.0.")

    # KGX/gnome-console exposes transparency as boolean via gsettings.
    enabled = "true" if opacity < 0.99 else "false"
    _run_gsettings_set("org.gnome.Console", "transparency", enabled)


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
    if profile_uuid:
        return profile_uuid

    raw_uuids = _run_gsettings_get("org.gnome.Ptyxis", "profile-uuids")
    if not raw_uuids:
        return ""

    try:
        parsed = ast.literal_eval(raw_uuids)
    except (SyntaxError, ValueError):
        return ""

    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, str) and item.strip():
                return item.strip()

    return profile_uuid or ""


def is_ptyxis_available() -> bool:
    return shutil.which("ptyxis") is not None


def is_kgx_available() -> bool:
    return shutil.which("kgx") is not None or shutil.which("gnome-console") is not None


def is_konsole_available() -> bool:
    return shutil.which("konsole") is not None


def detect_opacity_backend() -> str | None:
    info = _read_os_release()
    distro_hint = f"{info.get('id', '')} {info.get('id_like', '')}"
    desktop_hint = " ".join(
        [
            os.environ.get("XDG_CURRENT_DESKTOP", ""),
            os.environ.get("DESKTOP_SESSION", ""),
            os.environ.get("KDE_FULL_SESSION", ""),
        ]
    ).lower()
    schemas = _list_schemas()

    ptyxis_supported = is_ptyxis_available() and "org.gnome.Ptyxis" in schemas
    kgx_supported = is_kgx_available() and "org.gnome.Console" in schemas
    konsole_supported = is_konsole_available()

    if any(name in desktop_hint for name in ("kde", "plasma")):
        if konsole_supported:
            return "konsole"
        if kgx_supported:
            return "kgx"
        if ptyxis_supported:
            return "ptyxis"
        return None

    # Distro-aware priority: Ubuntu usually favors Ptyxis, while Fedora/SuSE often use KGX.
    if any(name in distro_hint for name in ("fedora", "suse", "opensuse", "sle")):
        if kgx_supported:
            return "kgx"
        if ptyxis_supported:
            return "ptyxis"
        return None

    if ptyxis_supported:
        return "ptyxis"
    if konsole_supported:
        return "konsole"
    if kgx_supported:
        return "kgx"
    return None


def get_current_terminal_profile_id() -> str:
    backend = detect_opacity_backend()
    if backend == "ptyxis":
        return get_ptyxis_current_profile_id()
    return ""


def set_terminal_opacity(opacity: float, profile_id: str = "") -> str:
    backend = detect_opacity_backend()
    if backend == "ptyxis":
        set_ptyxis_opacity(profile_id, opacity)
        return "ptyxis"
    if backend == "konsole":
        raise GSettingsError("Konsole detectado. Ajuste de transparencia para Konsole se agregara en la siguiente fase.")
    if backend == "kgx":
        set_kgx_transparency(opacity)
        return "kgx"
    raise GSettingsError("No se detecto un backend compatible para opacidad (Ptyxis/KGX).")


def _is_process_running(process_name: str) -> bool:
    result = subprocess.run(["pgrep", "-x", process_name], check=False, capture_output=True, text=True)
    return result.returncode == 0


def is_ptyxis_running() -> bool:
    return _is_process_running("ptyxis")


def is_kgx_running() -> bool:
    return _is_process_running("kgx") or _is_process_running("gnome-console")


def is_konsole_running() -> bool:
    return _is_process_running("konsole")


def open_ptyxis() -> None:
    result = subprocess.run(["ptyxis", "--new-window"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "No se pudo abrir Ptyxis"
        raise GSettingsError(stderr)


def open_kgx() -> None:
    if shutil.which("kgx") is not None:
        cmd = ["kgx"]
    elif shutil.which("gnome-console") is not None:
        cmd = ["gnome-console"]
    else:
        raise GSettingsError("No se encontro KGX/GNOME Console.")

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "No se pudo abrir KGX"
        raise GSettingsError(stderr)


def open_konsole() -> None:
    if shutil.which("konsole") is None:
        raise GSettingsError("No se encontro Konsole.")

    result = subprocess.run(["konsole"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "No se pudo abrir Konsole"
        raise GSettingsError(stderr)


def is_opacity_supported_terminal_available() -> bool:
    return detect_opacity_backend() is not None


def is_active_opacity_terminal_running() -> bool:
    backend = detect_opacity_backend()
    if backend == "ptyxis":
        return is_ptyxis_running()
    if backend == "konsole":
        return is_konsole_running()
    if backend == "kgx":
        return is_kgx_running()
    return False


def open_active_opacity_terminal() -> None:
    backend = detect_opacity_backend()
    if backend == "ptyxis":
        open_ptyxis()
        return
    if backend == "konsole":
        open_konsole()
        return
    if backend == "kgx":
        open_kgx()
        return
    raise GSettingsError("No se detecto terminal compatible para aplicar opacidad.")


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


def is_wayland_session() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"


def detect_wallpaper_backend() -> str | None:
    desktop = " ".join(
        [
            os.environ.get("XDG_CURRENT_DESKTOP", ""),
            os.environ.get("DESKTOP_SESSION", ""),
            os.environ.get("KDE_FULL_SESSION", ""),
        ]
    ).lower()

    if any(name in desktop for name in ("kde", "plasma")):
        return "kde"
    if any(name in desktop for name in ("gnome", "ubuntu")):
        return "gnome"
    return None


def ensure_wayland_wallpaper_compatibility() -> str:
    if not is_wayland_session():
        raise GSettingsError("La rotacion de wallpaper requiere una sesion Wayland.")

    backend = detect_wallpaper_backend()
    if backend == "kde":
        if shutil.which("qdbus6") is None and shutil.which("qdbus") is None:
            raise GSettingsError("No se encontro qdbus/qdbus6 para controlar el wallpaper en KDE Plasma.")
        return backend

    if backend == "gnome":
        return backend

    raise GSettingsError("Entorno de escritorio no soportado para wallpaper (soportados: GNOME y KDE).")


def _set_wallpaper_gnome(image_path: str, set_dark_variant: bool = True) -> None:
    uri = f"file://{image_path}"
    _run_gsettings_set("org.gnome.desktop.background", "picture-uri", f'"{uri}"')

    if set_dark_variant:
        _run_gsettings_set("org.gnome.desktop.background", "picture-uri-dark", f'"{uri}"')


def _set_wallpaper_kde(image_path: str) -> None:
    uri = f"file://{image_path}"
    qdbus_cmd = "qdbus6" if shutil.which("qdbus6") is not None else "qdbus"

    script = """
var allDesktops = desktops();
for (var i = 0; i < allDesktops.length; i++) {
    var d = allDesktops[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "__URI__");
}
""".strip().replace("__URI__", uri)

    cmd = [
        qdbus_cmd,
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
        script,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "No se pudo aplicar wallpaper en KDE Plasma"
        raise GSettingsError(stderr)


def set_wallpaper(image_path: str, set_dark_variant: bool = True) -> None:
    backend = ensure_wayland_wallpaper_compatibility()
    if backend == "gnome":
        _set_wallpaper_gnome(image_path, set_dark_variant=set_dark_variant)
        return
    if backend == "kde":
        _set_wallpaper_kde(image_path)
        return

    raise GSettingsError("No se detecto backend de wallpaper compatible.")
