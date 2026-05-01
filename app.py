from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from gnome_tools.config import ConfigManager
from gnome_tools.daemon_control import (
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    is_daemon_running,
    start_daemon,
    stop_daemon,
)
from gnome_tools.gnome_controls import (
    ensure_terminal_visible,
    GSettingsError,
    get_ptyxis_current_profile_id,
    is_ptyxis_available,
    is_ptyxis_running,
    open_ptyxis,
    set_ptyxis_opacity,
)
from gnome_tools.wallpaper import WallpaperRotator

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
ICON_PATH = BASE_DIR / "assets" / "gnome-ico.png"


class GnomeToolsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("GNOME Extra Tools")
        self.geometry("700x550")
        self.minsize(650, 500)
        self._icon_image: tk.PhotoImage | None = None
        self._configure_window_icon()

        self.config_manager = ConfigManager(CONFIG_PATH)
        self.config_data = self.config_manager.load()

        self.rotator: WallpaperRotator | None = None

        self._build_ui()
        self._load_config_into_form()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ptyxis_frame = ttk.LabelFrame(root, text="Ptyxis", padding=10)

        ttk.Label(ptyxis_frame, text="Profile ID:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
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
            text="Editar Profile ID",
            command=self.toggle_profile_id_edit,
        )
        self.profile_edit_button.grid(row=0, column=2, padx=6, pady=6)

        ttk.Label(ptyxis_frame, text="Opacidad (%):", foreground="gray").grid(
            row=1,
            column=0,
            sticky="w",
            padx=6,
            pady=6,
        )
        self._opacity_debounce_id: str | None = None
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

        ttk.Button(ptyxis_frame, text="Aplicar", command=self.apply_opacity).grid(
            row=0,
            column=3,
            rowspan=3,
            padx=8,
            pady=6,
            sticky="nsew",
        )
        ptyxis_frame.columnconfigure(1, weight=1)

        wallpaper_frame = ttk.LabelFrame(root, text="Rotación de wallpapers", padding=10)
        wallpaper_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=6)

        ptyxis_frame.pack(fill=tk.X, padx=4, pady=6)

        ttk.Label(wallpaper_frame, text="Carpeta:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.folder_var = tk.StringVar()
        ttk.Entry(wallpaper_frame, textvariable=self.folder_var).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6,
            pady=6,
        )
        ttk.Button(wallpaper_frame, text="Seleccionar", command=self.pick_folder).grid(
            row=0,
            column=2,
            padx=6,
            pady=6,
        )

        ttk.Label(wallpaper_frame, text="Intervalo (min):").grid(
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
            text="Actualizar también en modo oscuro",
            variable=self.dark_variant_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=4)

        buttons = ttk.Frame(wallpaper_frame)
        buttons.grid(row=3, column=0, columnspan=3, sticky="ew", padx=6, pady=6)

        ttk.Button(buttons, text="Probar ahora", command=self.rotate_once).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Iniciar", command=self.start_rotation).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Detener", command=self.stop_rotation).pack(side=tk.LEFT, padx=4)

        daemon_frame = ttk.LabelFrame(wallpaper_frame, text="Daemon persistente", padding=8)
        daemon_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=6, pady=8)

        daemon_buttons = ttk.Frame(daemon_frame)
        daemon_buttons.pack(fill=tk.X)
        ttk.Button(daemon_buttons, text="Iniciar daemon", command=self.start_wallpaper_daemon).pack(
            side=tk.LEFT,
            padx=4,
        )
        ttk.Button(daemon_buttons, text="Detener daemon", command=self.stop_wallpaper_daemon).pack(
            side=tk.LEFT,
            padx=4,
        )
        ttk.Button(daemon_buttons, text="Activar autostart", command=self.enable_wallpaper_autostart).pack(
            side=tk.LEFT,
            padx=4,
        )
        ttk.Button(daemon_buttons, text="Desactivar autostart", command=self.disable_wallpaper_autostart).pack(
            side=tk.LEFT,
            padx=4,
        )

        self.daemon_state_var = tk.StringVar(value="Daemon: detenido | Autostart: desactivado")
        ttk.Label(daemon_frame, textvariable=self.daemon_state_var, foreground="gray").pack(
            fill=tk.X,
            padx=4,
            pady=6,
        )

        self.status_var = tk.StringVar(value="Listo")
        status_label = ttk.Label(root, textvariable=self.status_var, anchor="w", foreground="gray")
        status_label.pack(fill=tk.X, padx=4, pady=8)

        footer = ttk.Frame(root)
        footer.pack(fill=tk.X, padx=4, pady=8)
        ttk.Button(footer, text="Guardar config", command=self.save_config).pack(side=tk.RIGHT, padx=4)

        wallpaper_frame.columnconfigure(1, weight=1)

    def _load_config_into_form(self) -> None:
        ptyxis = self.config_data.get("ptyxis", {})
        wallpaper = self.config_data.get("wallpaper", {})

        profile_id = str(ptyxis.get("profile_id", "")).strip()
        if not profile_id:
            profile_id = get_ptyxis_current_profile_id()
        self.profile_id_var.set(profile_id)

        opacity_float = float(ptyxis.get("opacity", 0.85))
        opacity_percent = int(opacity_float * 100)
        self.opacity_var.set(opacity_percent)
        self.opacity_label.config(text=f"{opacity_percent}%")

        self.folder_var.set(str(wallpaper.get("folder", "")))
        self.interval_var.set(str(wallpaper.get("interval_minutes", 60)))
        self.dark_variant_var.set(bool(wallpaper.get("set_dark_variant", True)))
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
            self.profile_edit_button.config(text="Bloquear Profile ID")
            self.status_var.set("Edición de Profile ID activada")
            return

        self.profile_id_entry.config(state="readonly")
        self.profile_edit_button.config(text="Editar Profile ID")
        self.status_var.set("Profile ID bloqueado")

    def _update_config_from_form(self) -> None:
        opacity_percent = int(self.opacity_var.get())
        opacity_float = opacity_percent / 100.0

        self.config_data["ptyxis"] = {
            "profile_id": self.profile_id_var.get().strip(),
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
        }

    def save_config(self) -> None:
        try:
            self._update_config_from_form()
            self.config_manager.config = self.config_data
            self.config_manager.save()
            self.status_var.set(f"✓ Config guardada en: {CONFIG_PATH}")
        except ValueError as exc:
            messagebox.showerror("Error de validación", str(exc))

    def pick_folder(self) -> None:
        selected = filedialog.askdirectory(title="Selecciona carpeta de imágenes")
        if selected:
            self.folder_var.set(selected)

    def _apply_opacity_silent(self) -> None:
        """Aplica la opacidad directamente sin abrir terminales ni mostrar diálogos."""
        try:
            profile_id = self.profile_id_var.get().strip()
            opacity_percent = int(self.opacity_var.get())
            opacity_float = opacity_percent / 100.0
            set_ptyxis_opacity(profile_id, opacity_float)
            self.status_var.set(f"✓ Opacidad aplicada ({opacity_percent}%) al perfil {profile_id}")
        except (ValueError, GSettingsError):
            pass  # Errores silenciosos durante el arrastre; el botón Aplicar los mostrará

    def apply_opacity(self) -> None:
        try:
            terminal_name, opened_now = ensure_terminal_visible()

            if not is_ptyxis_available():
                if terminal_name is None:
                    messagebox.showwarning(
                        "Sin terminal",
                        "No se detectó Ptyxis ni otra terminal instalada para abrir.",
                    )
                    self.status_var.set("No se encontró terminal instalada")
                else:
                    action_text = "abierta" if opened_now else "activa"
                    messagebox.showwarning(
                        "Compatibilidad",
                        (
                            "Se detectó una terminal alternativa "
                            f"({terminal_name}, {action_text}), pero este ajuste de opacidad "
                            "solo es compatible con perfiles de Ptyxis."
                        ),
                    )
                    self.status_var.set(
                        f"Terminal {terminal_name} {action_text}; opacidad solo compatible con Ptyxis"
                    )
                return

            if not is_ptyxis_running():
                open_ptyxis()
                self.status_var.set("Se abrió Ptyxis para confirmar que está activo")

            profile_id = self.profile_id_var.get().strip()
            opacity_percent = int(self.opacity_var.get())
            opacity_float = opacity_percent / 100.0
            set_ptyxis_opacity(profile_id, opacity_float)
            self.status_var.set(f"✓ Opacidad aplicada ({opacity_percent}%) al perfil {profile_id}")
        except ValueError as exc:
            messagebox.showerror("Datos inválidos", str(exc))
        except GSettingsError as exc:
            messagebox.showerror("Error gsettings", str(exc))

    def _build_rotator(self) -> WallpaperRotator:
        folder = Path(self.folder_var.get().strip())
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
        )

    def rotate_once(self) -> None:
        try:
            self._update_config_from_form()
            rotator = self._build_rotator()
            image = rotator.rotate_once()
            self.status_var.set(f"✓ Wallpaper aplicado: {image.name}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def start_rotation(self) -> None:
        try:
            if is_daemon_running(BASE_DIR):
                messagebox.showwarning(
                    "Daemon activo",
                    "El daemon persistente está activo. Deténlo antes de iniciar la rotación en esta ventana.",
                )
                self.refresh_daemon_state()
                return

            self._update_config_from_form()
            self.save_config()

            self.rotator = self._build_rotator()
            self.rotator.start(on_change=self._on_wallpaper_changed, on_error=self._on_rotation_error)
            self.status_var.set("✓ Rotación iniciada")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def stop_rotation(self) -> None:
        if self.rotator:
            self.rotator.stop()
        self.status_var.set("⊘ Rotación detenida")

    def refresh_daemon_state(self) -> None:
        daemon_text = "activo" if is_daemon_running(BASE_DIR) else "detenido"
        autostart_text = "activado" if is_autostart_enabled() else "desactivado"
        self.daemon_state_var.set(f"Daemon: {daemon_text} | Autostart: {autostart_text}")

    def start_wallpaper_daemon(self) -> None:
        try:
            if self.rotator and self.rotator.is_running:
                self.rotator.stop()

            self._update_config_from_form()
            self.save_config()
            started = start_daemon(BASE_DIR)
            self.refresh_daemon_state()
            if started:
                self.status_var.set("✓ Daemon de wallpaper iniciado")
            else:
                self.status_var.set("✓ Daemon ya estaba activo (no se reinició)")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def stop_wallpaper_daemon(self) -> None:
        try:
            stopped = stop_daemon(BASE_DIR)
            self.refresh_daemon_state()
            if stopped:
                self.status_var.set("⊘ Daemon de wallpaper detenido")
            else:
                self.status_var.set("⊘ Daemon no estaba activo")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def enable_wallpaper_autostart(self) -> None:
        try:
            self._update_config_from_form()
            self.save_config()
            desktop_file = enable_autostart(BASE_DIR)
            self.refresh_daemon_state()
            self.status_var.set(f"✓ Autostart activado: {desktop_file}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def disable_wallpaper_autostart(self) -> None:
        try:
            disable_autostart()
            self.refresh_daemon_state()
            self.status_var.set("⊘ Autostart desactivado")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def _on_wallpaper_changed(self, image_path: Path) -> None:
        self.after(0, lambda: self.status_var.set(f"↻ Wallpaper: {image_path.name}"))

    def _on_rotation_error(self, error: Exception) -> None:
        self.after(0, lambda: messagebox.showerror("Error en rotación", str(error)))
        self.after(0, lambda: self.status_var.set("ERROR: rotación detenida"))

    def _on_close(self) -> None:
        if self.rotator:
            self.rotator.stop()
        try:
            self.save_config()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


def main() -> None:
    app = GnomeToolsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
