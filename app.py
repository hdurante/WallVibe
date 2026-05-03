from __future__ import annotations

import fcntl
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from gnome_tools.config import ConfigManager, resolve_config_path
from gnome_tools.daemon_control import (
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    is_daemon_running,
    start_daemon,
    stop_daemon,
)
from gnome_tools.gnome_controls import (
    GSettingsError,
    detect_opacity_backend,
    get_current_terminal_profile_id,
    is_active_opacity_terminal_running,
    is_opacity_supported_terminal_available,
    open_active_opacity_terminal,
    set_terminal_opacity,
)
from gnome_tools.i18n import set_language, t
from gnome_tools.wallpaper import WallpaperRotator

# Detectar si estamos en PyInstaller para resolver rutas correctamente
if getattr(sys, 'frozen', False):
    # Si estamos compilados con PyInstaller, el directorio base es donde está el ejecutable
    BASE_DIR = Path(sys.executable).parent
else:
    # En desarrollo, es el directorio del script
    BASE_DIR = Path(__file__).parent

CONFIG_PATH = BASE_DIR / "config.json"
ICON_PATH = BASE_DIR / "assets" / "gnome-ico.png"
APP_WM_CLASS = "GnomeExtraTools"
APP_LOCK_PATH = Path.home() / ".cache" / "gnome-extra-tools" / "app.lock"

LANGUAGE_CODES = {"auto", "es", "en", "zh", "ja", "de"}


class GnomeToolsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__(className=APP_WM_CLASS)
        self.config_manager = ConfigManager(CONFIG_PATH)
        self.config_data = self.config_manager.load()
        self._apply_language_from_config()

        self.title(t("app_title"))
        self.geometry("700x550")
        self.minsize(650, 500)
        self._icon_image: tk.PhotoImage | None = None
        self._configure_window_icon()

        self.rotator: WallpaperRotator | None = None
        self._opacity_debounce_id: str | None = None

        self._build_ui()
        self._load_config_into_form()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_language_from_config(self) -> None:
        ui = self.config_data.get("ui", {})
        language = str(ui.get("language", "auto")).strip().lower()
        if language not in LANGUAGE_CODES:
            language = "auto"

        if language == "auto":
            set_language(None)
        else:
            set_language(language)

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label=t("menu_select_language"), command=self.open_language_dialog)
        menu_bar.add_cascade(label=t("menu_tools"), menu=tools_menu)
        self.config(menu=menu_bar)

    def _snapshot_form_state(self) -> dict[str, str | bool]:
        state: dict[str, str | bool] = {}
        if hasattr(self, "folder_var"):
            state["folder"] = self.folder_var.get()
        if hasattr(self, "interval_var"):
            state["interval"] = self.interval_var.get()
        if hasattr(self, "dark_variant_var"):
            state["dark_variant"] = bool(self.dark_variant_var.get())
        if hasattr(self, "search_subfolders_var"):
            state["search_subfolders"] = bool(self.search_subfolders_var.get())
        if hasattr(self, "profile_id_var"):
            state["profile_id"] = self.profile_id_var.get()
        if hasattr(self, "opacity_var"):
            state["opacity"] = str(int(self.opacity_var.get()))
        return state

    def _restore_form_state(self, state: dict[str, str | bool]) -> None:
        if "folder" in state:
            self.folder_var.set(str(state["folder"]))
        if "interval" in state:
            self.interval_var.set(str(state["interval"]))
        if "dark_variant" in state:
            self.dark_variant_var.set(bool(state["dark_variant"]))
        if "search_subfolders" in state:
            self.search_subfolders_var.set(bool(state["search_subfolders"]))
        if "profile_id" in state:
            self.profile_id_var.set(str(state["profile_id"]))
        if "opacity" in state:
            opacity_percent = int(str(state["opacity"]))
            self.opacity_var.set(opacity_percent)
            self.opacity_label.config(text=f"{opacity_percent}%")
        self.refresh_daemon_state()

    def _rebuild_ui_for_language(self) -> None:
        state = self._snapshot_form_state()
        for child in self.winfo_children():
            child.destroy()
        self._build_ui()
        self._restore_form_state(state)
        self.title(t("app_title"))

    def open_language_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(t("language_dialog_title"))
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        x = self.winfo_pointerx() + 10
        y = self.winfo_pointery() + 10
        dialog.geometry(f"380x180+{x}+{y}")

        current_lang = str(self.config_data.get("ui", {}).get("language", "auto"))
        selected_code = current_lang if current_lang in LANGUAGE_CODES else "auto"

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=t("language_dialog_message"), wraplength=340).pack(anchor="w", pady=(0, 8))

        # Keep language names fixed in their native form so users can always recover the UI language.
        options = [
            ("Sistema / System", "auto"),
            ("Español", "es"),
            ("English", "en"),
            ("中文", "zh"),
            ("日本語", "ja"),
            ("Deutsch", "de"),
        ]
        label_to_code = {label: code for label, code in options}
        code_to_label = {code: label for label, code in options}

        lang_display_var = tk.StringVar(value=code_to_label.get(selected_code, "Sistema / System"))
        language_combo = ttk.Combobox(
            frame,
            textvariable=lang_display_var,
            state="readonly",
            values=[label for label, _ in options],
        )
        language_combo.pack(fill=tk.X, pady=(0, 8))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)

        def _apply() -> None:
            selected_label = lang_display_var.get()
            selected = label_to_code.get(selected_label, "auto")
            self.config_data.setdefault("ui", {})["language"] = selected
            self.config_manager.config = self.config_data
            self.config_manager.save()
            self._apply_language_from_config()
            dialog.destroy()
            self._rebuild_ui_for_language()
            self.status_var.set(t("language_changed"))

        ttk.Button(buttons, text=t("language_apply"), command=_apply).pack(side=tk.RIGHT, padx=4)
        ttk.Button(buttons, text=t("language_cancel"), command=dialog.destroy).pack(side=tk.RIGHT)

    def _configure_window_icon(self) -> None:
        if not ICON_PATH.exists():
            return

        try:
            self._icon_image = tk.PhotoImage(file=str(ICON_PATH))
            self.iconphoto(True, self._icon_image)
        except tk.TclError:
            # Si el PNG no es compatible, se mantiene el icono por defecto.
            self._icon_image = None

    def _build_ui(self) -> None:
        self._build_menu()
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        wallpaper_frame = ttk.LabelFrame(root, text=t("wallpaper_section"), padding=10)
        wallpaper_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=6)

        ttk.Label(wallpaper_frame, text=t("folder_label")).grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.folder_var = tk.StringVar()
        ttk.Entry(wallpaper_frame, textvariable=self.folder_var).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6,
            pady=6,
        )
        ttk.Button(wallpaper_frame, text=t("select"), command=self.pick_folder).grid(
            row=0,
            column=2,
            padx=6,
            pady=6,
        )

        ttk.Label(wallpaper_frame, text=t("interval_label")).grid(
            row=1,
            column=0,
            sticky="w",
            padx=6,
            pady=6,
        )
        self.interval_var = tk.StringVar()
        ttk.Spinbox(wallpaper_frame, from_=1, to=1440, textvariable=self.interval_var, width=10).grid(
            row=1,
            column=1,
            sticky="w",
            padx=6,
            pady=6,
        )

        self.dark_variant_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            wallpaper_frame,
            text=t("dark_variant_label"),
            variable=self.dark_variant_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=4)

        self.search_subfolders_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            wallpaper_frame,
            text=t("search_subfolders_label"),
            variable=self.search_subfolders_var,
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=4)

        buttons = ttk.Frame(wallpaper_frame)
        buttons.grid(row=4, column=0, columnspan=3, sticky="ew", padx=6, pady=6)

        ttk.Button(buttons, text=t("try_now"), command=self.rotate_once).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text=t("start"), command=self.start_rotation).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text=t("stop"), command=self.stop_rotation).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text=t("apply_wallpaper"), command=self.apply_wallpaper_config).pack(side=tk.LEFT, padx=4)

        daemon_frame = ttk.LabelFrame(wallpaper_frame, text=t("daemon_section"), padding=8)
        daemon_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=6, pady=8)

        daemon_buttons_top = ttk.Frame(daemon_frame)
        daemon_buttons_top.pack(fill=tk.X)
        ttk.Button(daemon_buttons_top, text=t("start_daemon"), command=self.start_wallpaper_daemon).pack(
            side=tk.LEFT,
            padx=4,
        )
        ttk.Button(daemon_buttons_top, text=t("stop_daemon"), command=self.stop_wallpaper_daemon).pack(
            side=tk.LEFT,
            padx=4,
        )

        daemon_buttons_bottom = ttk.Frame(daemon_frame)
        daemon_buttons_bottom.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(
            daemon_buttons_bottom,
            text=t("enable_autostart"),
            command=self.enable_wallpaper_autostart,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )
        ttk.Button(
            daemon_buttons_bottom,
            text=t("disable_autostart"),
            command=self.disable_wallpaper_autostart,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        self.daemon_state_var = tk.StringVar(value=t("daemon_state_default"))
        ttk.Label(daemon_frame, textvariable=self.daemon_state_var, foreground="gray").pack(
            fill=tk.X,
            padx=4,
            pady=6,
        )

        ptyxis_frame = ttk.LabelFrame(root, text=t("ptyxis_section"), padding=10)
        ptyxis_frame.pack(fill=tk.X, padx=4, pady=6)

        ttk.Label(ptyxis_frame, text=t("profile_id_label")).grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.profile_id_var = tk.StringVar()
        self.profile_id_entry = ttk.Entry(
            ptyxis_frame,
            textvariable=self.profile_id_var,
            state="readonly",
        )
        self.profile_id_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6,
            pady=6,
        )
        self.profile_edit_button = ttk.Button(
            ptyxis_frame,
            text=t("edit_profile_id"),
            command=self.toggle_profile_id_edit,
        )
        self.profile_edit_button.grid(row=0, column=2, padx=6, pady=6)

        ttk.Label(ptyxis_frame, text=t("opacity_label"), foreground="gray").grid(
            row=1,
            column=0,
            sticky="w",
            padx=6,
            pady=6,
        )
        self.opacity_var = tk.IntVar(value=85)
        self.opacity_label = ttk.Label(ptyxis_frame, text="85%", width=5)
        self.opacity_label.grid(
            row=1,
            column=1,
            sticky="w",
            padx=6,
            pady=6,
        )

        opacity_scale = ttk.Scale(
            ptyxis_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.opacity_var,
            command=self._on_opacity_change,
        )
        opacity_scale.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=6)

        ttk.Button(ptyxis_frame, text=t("apply"), command=self.apply_opacity).grid(
            row=0,
            column=3,
            rowspan=3,
            padx=8,
            pady=6,
            sticky="nsew",
        )
        ptyxis_frame.columnconfigure(1, weight=1)
        wallpaper_frame.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(value=t("ready"))
        status_label = ttk.Label(root, textvariable=self.status_var, anchor="w", foreground="gray")
        status_label.pack(fill=tk.X, padx=4, pady=8)

        footer = ttk.Frame(root)
        footer.pack(fill=tk.X, padx=4, pady=8)
        ttk.Button(footer, text=t("save_config"), command=self.save_config).pack(side=tk.RIGHT, padx=4)

    def _load_config_into_form(self) -> None:
        ptyxis = self.config_data.get("ptyxis", {})
        wallpaper = self.config_data.get("wallpaper", {})

        backend = detect_opacity_backend()
        if backend == "ptyxis":
            self.profile_id_var.set(get_current_terminal_profile_id())
        elif backend == "kgx":
            self.profile_id_var.set("kgx")
        else:
            self.profile_id_var.set("")

        opacity_float = float(ptyxis.get("opacity", 0.85))
        opacity_percent = int(opacity_float * 100)
        self.opacity_var.set(opacity_percent)
        self.opacity_label.config(text=f"{opacity_percent}%")

        self.folder_var.set(str(wallpaper.get("folder", "")))
        self.interval_var.set(str(wallpaper.get("interval_minutes", 60)))
        self.dark_variant_var.set(bool(wallpaper.get("set_dark_variant", True)))
        self.search_subfolders_var.set(bool(wallpaper.get("search_subfolders", False)))
        self.refresh_daemon_state()

    def _on_opacity_change(self, value: str) -> None:
        percent = int(float(value))
        self.opacity_label.config(text=f"{percent}%")
        if self._opacity_debounce_id is not None:
            self.after_cancel(self._opacity_debounce_id)
        self._opacity_debounce_id = self.after(400, self._apply_opacity_silent)

    def toggle_profile_id_edit(self) -> None:
        is_readonly = self.profile_id_entry.cget("state") == "readonly"
        if is_readonly:
            self.profile_id_entry.config(state="normal")
            self.profile_edit_button.config(text=t("lock_profile_id"))
            self.status_var.set(t("profile_edit_enabled"))
            return

        self.profile_id_entry.config(state="readonly")
        self.profile_edit_button.config(text=t("edit_profile_id"))
        self.status_var.set(t("profile_edit_disabled"))

    def _update_config_from_form(self) -> None:
        opacity_percent = int(self.opacity_var.get())
        opacity_float = opacity_percent / 100.0

        self.config_data["ptyxis"] = {
            "opacity": round(opacity_float, 2),
        }

        self.config_data["wallpaper"] = {
            "folder": self.folder_var.get().strip(),
            "interval_minutes": int(self.interval_var.get()),
            "extensions": self.config_data.get("wallpaper", {}).get(
                "extensions",
                [".jpg", ".jpeg", ".png", ".bmp", ".svg", ".webp"],
            ),
            "set_dark_variant": bool(self.dark_variant_var.get()),
            "search_subfolders": bool(self.search_subfolders_var.get()),
        }

    def save_config(self) -> None:
        try:
            self._update_config_from_form()
            self.config_manager.config = self.config_data
            self.config_manager.save()
            self.status_var.set(t("config_saved", path=CONFIG_PATH))
        except ValueError as exc:
            messagebox.showerror(t("invalid_data"), str(exc))

    def pick_folder(self) -> None:
        selected = filedialog.askdirectory(title=t("select_folder_title"))
        if selected:
            self.folder_var.set(selected)

    def _apply_opacity_silent(self) -> None:
        try:
            opacity_percent = int(self.opacity_var.get())
            opacity_float = opacity_percent / 100.0
            profile_id = self.profile_id_var.get().strip()
            backend = set_terminal_opacity(opacity_float, profile_id)
            status_target = profile_id if backend == "ptyxis" else backend
            if not status_target:
                status_target = "terminal"
            self.status_var.set(t("opacity_applied", percent=opacity_percent, profile_id=status_target))
        except (ValueError, GSettingsError):
            pass

    def apply_opacity(self) -> None:
        try:
            if not is_opacity_supported_terminal_available():
                messagebox.showwarning(t("no_terminal_title"), t("no_terminal_message"))
                self.status_var.set(t("no_terminal_found"))
                return

            if not is_active_opacity_terminal_running():
                open_active_opacity_terminal()
                self.status_var.set(t("ptyxis_opened_confirmation"))

            opacity_percent = int(self.opacity_var.get())
            opacity_float = opacity_percent / 100.0
            profile_id = self.profile_id_var.get().strip()
            backend = set_terminal_opacity(opacity_float, profile_id)
            status_target = profile_id if backend == "ptyxis" else backend
            if not status_target:
                status_target = "terminal"
            self.status_var.set(t("opacity_applied", percent=opacity_percent, profile_id=status_target))
        except ValueError as exc:
            messagebox.showerror(t("invalid_data"), str(exc))
        except GSettingsError as exc:
            messagebox.showerror(t("gsettings_error"), str(exc))

    def _build_rotator(self) -> WallpaperRotator:
        folder = resolve_config_path(CONFIG_PATH.parent, self.folder_var.get().strip())
        interval = int(self.interval_var.get())
        extensions = self.config_data.get("wallpaper", {}).get(
            "extensions",
            [".jpg", ".jpeg", ".png", ".bmp", ".svg", ".webp"],
        )
        return WallpaperRotator(
            folder=folder,
            interval_minutes=interval,
            extensions=extensions,
            set_dark_variant=bool(self.dark_variant_var.get()),
            search_subfolders=bool(self.search_subfolders_var.get()),
        )

    def rotate_once(self) -> None:
        try:
            self._update_config_from_form()
            rotator = self._build_rotator()
            image = rotator.rotate_once()
            self.status_var.set(t("wallpaper_applied", name=image.name))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), str(exc))

    def start_rotation(self) -> None:
        try:
            if is_daemon_running(BASE_DIR):
                messagebox.showwarning(t("daemon_active_title"), t("daemon_active_message"))
                self.refresh_daemon_state()
                return

            self._update_config_from_form()
            self.save_config()

            self.rotator = self._build_rotator()
            self.rotator.start(on_change=self._on_wallpaper_changed, on_error=self._on_rotation_error)
            self.status_var.set(t("rotation_started"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), str(exc))

    def stop_rotation(self) -> None:
        if self.rotator:
            self.rotator.stop()
        self.status_var.set(t("rotation_stopped"))

    def apply_wallpaper_config(self) -> None:
        try:
            self._update_config_from_form()
            self.save_config()

            # Detener daemon si está corriendo
            if is_daemon_running(BASE_DIR):
                stop_daemon(BASE_DIR)

            # Detener rotador local si está activo
            if self.rotator and self.rotator.is_running:
                self.rotator.stop()

            # Reiniciar daemon con nuevos valores
            started = start_daemon(BASE_DIR)
            self.refresh_daemon_state()
            self.status_var.set(t("daemon_restarted") if started else t("daemon_restart_failed"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), str(exc))

    def refresh_daemon_state(self) -> None:
        daemon_text = t("daemon_running") if is_daemon_running(BASE_DIR) else t("daemon_stopped_state")
        autostart_text = t("autostart_enabled_state") if is_autostart_enabled() else t("autostart_disabled_state")
        self.daemon_state_var.set(t("daemon_state", daemon=daemon_text, autostart=autostart_text))

    def start_wallpaper_daemon(self) -> None:
        try:
            if self.rotator and self.rotator.is_running:
                self.rotator.stop()

            self._update_config_from_form()
            self.save_config()
            started = start_daemon(BASE_DIR)
            self.refresh_daemon_state()
            if started:
                self.status_var.set(t("daemon_started"))
            else:
                self.status_var.set(t("daemon_already_running"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), str(exc))

    def stop_wallpaper_daemon(self) -> None:
        try:
            stopped = stop_daemon(BASE_DIR)
            self.refresh_daemon_state()
            if stopped:
                self.status_var.set(t("daemon_stopped"))
            else:
                self.status_var.set(t("daemon_was_not_running"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), str(exc))

    def enable_wallpaper_autostart(self) -> None:
        try:
            self._update_config_from_form()
            self.save_config()
            desktop_file = enable_autostart(BASE_DIR)
            self.refresh_daemon_state()
            self.status_var.set(t("autostart_enabled", file=desktop_file))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), str(exc))

    def disable_wallpaper_autostart(self) -> None:
        try:
            disable_autostart()
            self.refresh_daemon_state()
            self.status_var.set(t("autostart_disabled"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), str(exc))

    def _on_wallpaper_changed(self, image_path: Path) -> None:
        self.after(0, lambda: self.status_var.set(t("wallpaper_rotating", name=image_path.name)))

    def _on_rotation_error(self, error: Exception) -> None:
        self.after(0, lambda: messagebox.showerror(t("rotation_error_title"), str(error)))
        self.after(0, lambda: self.status_var.set(t("rotation_error_stopped")))

    def _on_close(self) -> None:
        if self.rotator:
            self.rotator.stop()
        try:
            self.save_config()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


def main() -> None:
    lock_handle = _acquire_app_lock()
    if lock_handle is None:
        _show_already_running_warning()
        return

    try:
        app = GnomeToolsApp()
        app.mainloop()
    finally:
        _release_app_lock(lock_handle)


def _acquire_app_lock():
    APP_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = APP_LOCK_PATH.open("w", encoding="utf-8")

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None

    handle.write(str(Path.cwd()))
    handle.flush()
    return handle


def _release_app_lock(handle) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _show_already_running_warning() -> None:
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "GNOME Extra Tools",
            "La aplicacion ya esta abierta en otra ventana.",
        )
        root.destroy()
    except Exception:  # noqa: BLE001
        # Fallback for non-GUI environments.
        print("La aplicacion ya esta abierta en otra ventana.")


if __name__ == "__main__":
    # Detectar si se solicita ejecutar el daemon
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # Ejecutar en modo daemon (sin GUI)
        from gnome_tools.daemon_main import run_daemon
        
        daemon_config = BASE_DIR / "config.json"
        daemon_pid = BASE_DIR / ".wallpaper_daemon.pid"
        run_daemon(daemon_config, daemon_pid)
    else:
        # Ejecutar modo GUI (default)
        main()
