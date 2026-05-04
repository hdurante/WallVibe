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


def _run_gsettings_get(schema: str, key: str, path: str | None = None) -> str:
    schema_with_path = f"{schema}:{path}" if path else schema
    cmd = ["gsettings", "get", schema_with_path, key]

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip().strip("'\"")


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

    enabled = "true" if opacity < 0.99 else "false"
    _run_gsettings_set("org.gnome.Console", "transparency", enabled)


def set_xfce4_terminal_transparency(opacity: float) -> None:
    if opacity < 0.0 or opacity > 1.0:
        raise ValueError("La opacidad debe estar entre 0.0 y 1.0.")

    config_path = Path.home() / ".config/xfce4/terminal/terminalrc"
    if not config_path.exists():
        raise GSettingsError("No se encontro el archivo de configuracion de xfce4-terminal.")

    lines = config_path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    found_alpha = False
    found_comp = False
    value = int(opacity * 100)

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("BackgroundAlpha="):
            new_lines.append(f"BackgroundAlpha={value}")
            found_alpha = True
            continue
        if stripped.startswith("ColorBackgroundVary="):
            new_lines.append("ColorBackgroundVary=TRUE")
            found_comp = True
            continue
        new_lines.append(line)

    if not found_alpha:
        new_lines.append(f"BackgroundAlpha={value}")
    if not found_comp:
        new_lines.append("ColorBackgroundVary=TRUE")

    config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def set_tilix_transparency(opacity: float) -> None:
    if opacity < 0.0 or opacity > 1.0:
        raise ValueError("La opacidad debe estar entre 0.0 y 1.0.")

    value = int(opacity * 100)
    result = subprocess.run(
        [
            "dconf",
            "write",
            "/com/gexperts/Tilix/profiles/default/background-transparency-percent",
            str(value),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "No se pudo aplicar transparencia en Tilix."
        raise GSettingsError(stderr)


def set_terminator_transparency(_opacity: float) -> None:
    raise GSettingsError("Soporte para transparencia en Terminator no implementado aun.")


def get_ptyxis_current_profile_id() -> str:
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

    return ""


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
    xfce4_terminal_supported = shutil.which("xfce4-terminal") is not None
    tilix_supported = shutil.which("tilix") is not None
    terminator_supported = shutil.which("terminator") is not None

    if any(name in desktop_hint for name in ("kde", "plasma")):
        if konsole_supported:
            return "konsole"
        if kgx_supported:
            return "kgx"
        if ptyxis_supported:
            return "ptyxis"
        return None

    if "xfce" in desktop_hint:
        if xfce4_terminal_supported:
            return "xfce4-terminal"
        if tilix_supported:
            return "tilix"
        if terminator_supported:
            return "terminator"
        return None

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
    if xfce4_terminal_supported:
        return "xfce4-terminal"
    if tilix_supported:
        return "tilix"
    if terminator_supported:
        return "terminator"
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
    if backend == "kgx":
        set_kgx_transparency(opacity)
        return "kgx"
    if backend == "xfce4-terminal":
        set_xfce4_terminal_transparency(opacity)
        return "xfce4-terminal"
    if backend == "tilix":
        set_tilix_transparency(opacity)
        return "tilix"
    if backend == "terminator":
        set_terminator_transparency(opacity)
        return "terminator"
    if backend == "konsole":
        raise GSettingsError("Konsole detectado. Ajuste de transparencia para Konsole se agregara en la siguiente fase.")
    raise GSettingsError("No se detecto un backend compatible para opacidad.")


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
        raise GSettingsError(result.stderr.strip() or "No se pudo abrir Ptyxis")


def open_kgx() -> None:
    if shutil.which("kgx") is not None:
        cmd = ["kgx"]
    elif shutil.which("gnome-console") is not None:
        cmd = ["gnome-console"]
    else:
        raise GSettingsError("No se encontro KGX/GNOME Console.")

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise GSettingsError(result.stderr.strip() or "No se pudo abrir KGX")


def open_konsole() -> None:
    if shutil.which("konsole") is None:
        raise GSettingsError("No se encontro Konsole.")

    result = subprocess.run(["konsole"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise GSettingsError(result.stderr.strip() or "No se pudo abrir Konsole")


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
    if backend == "xfce4-terminal":
        return _is_process_running("xfce4-terminal")
    if backend == "tilix":
        return _is_process_running("tilix")
    if backend == "terminator":
        return _is_process_running("terminator")
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
    if backend == "xfce4-terminal":
        subprocess.run(["xfce4-terminal"], check=False, capture_output=True, text=True)
        return
    if backend == "tilix":
        subprocess.run(["tilix"], check=False, capture_output=True, text=True)
        return
    if backend == "terminator":
        subprocess.run(["terminator"], check=False, capture_output=True, text=True)
        return
    raise GSettingsError("No se detecto terminal compatible para aplicar opacidad.")


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
    if "xfce" in desktop:
        return "xfce"
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

    if backend == "xfce":
        if shutil.which("xfconf-query") is None:
            raise GSettingsError("No se encontro xfconf-query para controlar el wallpaper en XFCE.")
        return backend

    raise GSettingsError("Entorno de escritorio no soportado para wallpaper (soportados: GNOME, KDE y XFCE).")


def _set_wallpaper_gnome(image_path: str, set_dark_variant: bool = True) -> None:
    uri = f"file://{image_path}"
    _run_gsettings_set("org.gnome.desktop.background", "picture-uri", f'"{uri}"')

    if set_dark_variant:
        _run_gsettings_set("org.gnome.desktop.background", "picture-uri-dark", f'"{uri}"')


def _set_wallpaper_kde(image_path: str) -> None:
    uri = f"file://{image_path}"
    qdbus_cmd = "qdbus6" if shutil.which("qdbus6") is not None else "qdbus"

    script = (
        "var allDesktops = desktops();"
        "for (var i = 0; i < allDesktops.length; i++) {"
        "  var d = allDesktops[i];"
        "  d.wallpaperPlugin = 'org.kde.image';"
        "  d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];"
        "  d.writeConfig('Image', '__URI__');"
        "}"
    ).replace("__URI__", uri)

    cmd = [
        qdbus_cmd,
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
        script,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise GSettingsError(result.stderr.strip() or "No se pudo aplicar wallpaper en KDE Plasma")


def _set_wallpaper_xfce(image_path: str) -> None:
    props = subprocess.run(
        ["xfconf-query", "-c", "xfce4-desktop", "-l"],
        check=False,
        capture_output=True,
        text=True,
    )
    if props.returncode != 0:
        raise GSettingsError("No se pudo obtener las propiedades de xfce4-desktop.")

    updated = False
    for line in props.stdout.splitlines():
        if "last-image" not in line:
            continue
        subprocess.run(
            ["xfconf-query", "-c", "xfce4-desktop", "-p", line.strip(), "-s", image_path],
            check=False,
            capture_output=True,
            text=True,
        )
        updated = True

    if not updated:
        raise GSettingsError("No se detectaron propiedades de wallpaper en xfce4-desktop.")


def set_wallpaper(image_path: str, set_dark_variant: bool = True) -> None:
    backend = ensure_wayland_wallpaper_compatibility()
    if backend == "gnome":
        _set_wallpaper_gnome(image_path, set_dark_variant=set_dark_variant)
        return
    if backend == "kde":
        _set_wallpaper_kde(image_path)
        return
    if backend == "xfce":
        _set_wallpaper_xfce(image_path)
        return

    raise GSettingsError("No se detecto backend de wallpaper compatible.")
