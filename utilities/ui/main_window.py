from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Mapping
from tkinter import ttk
from typing import Any

from .backgrounds import BackgroundPainter, describe_background
from .dialogs import BackgroundDialog, WindowSizeDialog
from .settings_window import SettingsWindow


class SettingsDialog(tk.Toplevel):

    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.resizable(True, True)
        self.title("Настройки TranScr")
        self.iconbitmap(default='')

        self.window = SettingsWindow(self, **kwargs)

        parent.update_idletasks()
        width, height = 720, 500
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def close(self) -> None:
        self._close()


class MainWindow:
    def __init__(
            self,
            root: tk.Tk,
            *,
            saved_settings: Mapping[str, Any],
            ocr_labels: Mapping[str, str],
            ocr_values: Mapping[str, str],
            provider_labels: Mapping[str, str],
            provider_values: Mapping[str, str],
            initial_area_text: str,
            callbacks: Mapping[str, Callable[[], None]],
    ) -> None:
        self.root = root
        self._saved_settings = dict(saved_settings)
        self._ocr_labels = dict(ocr_labels)
        self._ocr_values = dict(ocr_values)
        self._provider_labels = dict(provider_labels)
        self._provider_values = dict(provider_values)
        self._initial_area_text = initial_area_text
        self._callbacks = dict(callbacks)
        self._configuration_enabled = True

        self.status_var = tk.StringVar(value="Готово. Проверьте настройки и запустите перевод.")
        self.background_var = tk.StringVar(value=describe_background(self._saved_settings))
        self.window_mode_var = tk.StringVar(
            value=self._saved_settings.get("window_mode", "fullscreen")
        )

        self._settings_dialog: SettingsDialog | None = None
        self._ui: SettingsWindow | None = None

        self._menu_items: list[tuple[int, Callable]] = []
        self._settings_available = True
        self._log_buffer: list[tuple[str, int]] = []

        self._build_ui()
        self._apply_window_mode(self.window_mode_var.get())

    def _build_ui(self) -> None:
        self.root.title("TranScr")
        self.root.minsize(820, 560)
        self.root.configure(background="#0f1626")

        style = ttk.Style(self.root)
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Main.TButton", font=("Segoe UI", 11, "bold"), padding=(18, 10))
        style.configure("Ghost.TButton", font=("Segoe UI", 10), padding=(14, 8))
        style.configure("Status.TLabel", font=("Segoe UI", 10))

        self.canvas = tk.Canvas(self.root, highlightthickness=0, borderwidth=0)
        self.canvas.pack(fill="both", expand=True)

        self.painter = BackgroundPainter(self.canvas)
        background = self._saved_settings.get("background") or {}
        self.painter.configure(
            background.get("kind", "default"),
            theme=background.get("theme", "Синий"),
            path=background.get("path"),
        )

        self._menu_items.clear()
        menu_font = ("Segoe UI", 10)
        menu_commands = [
            ("Настройки", self._on_settings_click),
            ("Выбор фона", lambda: self.open_background_picker()),
            ("Размер экрана", lambda: self.open_window_size_picker())
        ]

        self._settings_item_id = None
        for text, cmd in menu_commands:
            item_id = self.canvas.create_text(
                0, 0, text=text, font=menu_font, fill="#c8d4ea", anchor="e"
            )
            self._menu_items.append((item_id, cmd))
            self.canvas.tag_bind(item_id, "<Button-1>", lambda e, c=cmd: c())

            if text == "Настройки":
                self.canvas.tag_bind(
                    item_id, "<Enter>",
                    lambda e, i=item_id: self.canvas.itemconfig(i, fill="#ffffff") if getattr(self,
                                                                                              "_settings_available",
                                                                                              True) else None
                )
                self.canvas.tag_bind(
                    item_id, "<Leave>",
                    lambda e, i=item_id: self.canvas.itemconfig(i, fill="#c8d4ea") if getattr(self,
                                                                                              "_settings_available",
                                                                                              True) else None
                )
                self._settings_item_id = item_id
            else:
                self.canvas.tag_bind(item_id, "<Enter>", lambda e, i=item_id: self.canvas.itemconfig(i, fill="#ffffff"))
                self.canvas.tag_bind(item_id, "<Leave>", lambda e, i=item_id: self.canvas.itemconfig(i, fill="#c8d4ea"))

        card = tk.Frame(self.canvas, background="#111a2c", bd=0,
                        highlightbackground="#2a3a5c", highlightthickness=1)
        card_window = self.canvas.create_window(0, 0, anchor="center", window=card)
        self._card_window_id = card_window

        title = tk.Label(card, text="TranScr", font=("Segoe UI", 22, "bold"), fg="#f3f6ff", bg="#111a2c")
        title.pack(padx=34, pady=(24, 4))
        subtitle = tk.Label(card, text="Перевод экрана поверх оригинального текста", font=("Segoe UI", 10),
                            fg="#9fb2d6", bg="#111a2c")
        subtitle.pack(padx=34, pady=(0, 18))

        buttons = tk.Frame(card, bg="#111a2c")
        buttons.pack(padx=24, pady=(0, 10))

        self.start_button = tk.Button(
            buttons, text="Запустить переводчик",
            command=self._callbacks["start"],
            font=("Segoe UI", 11, "bold"), width=20, height=2,
            bg="#2f7d4a", fg="#ffffff", activebackground="#3a9259",
            activeforeground="#ffffff", relief="flat", bd=0, cursor="hand2"
        )
        self.start_button.grid(row=0, column=0, padx=6, pady=4)

        self.quick_area_button = tk.Button(
            buttons, text="Выбрать область",
            command=self._callbacks["select_quick_area"],
            state="disabled", font=("Segoe UI", 11, "bold"), width=18, height=2,
            bg="#2b4a7a", fg="#ffffff", activebackground="#355a91",
            activeforeground="#ffffff", disabledforeground="#7d8bb0",
            relief="flat", bd=0, cursor="hand2"
        )
        self.quick_area_button.grid(row=0, column=1, padx=6, pady=4)

        self.stop_button = tk.Button(
            buttons, text="Остановить",
            command=self._callbacks["stop"],
            state="disabled", font=("Segoe UI", 11, "bold"), width=14, height=2,
            bg="#7a2b2b", fg="#ffffff", activebackground="#913535",
            activeforeground="#ffffff", disabledforeground="#b07d7d",
            relief="flat", bd=0, cursor="hand2"
        )
        self.stop_button.grid(row=0, column=2, padx=6, pady=4)

        status = tk.Label(card, textvariable=self.status_var, font=("Segoe UI", 9), fg="#c8d4ea", bg="#111a2c",
                          wraplength=560, justify="center")
        status.pack(padx=24, pady=(4, 22))

        bottom_frame = tk.Frame(card, bg="#111a2c")
        bottom_frame.pack(padx=24, pady=(0, 20))

        tk.Button(
            bottom_frame, text="Выйти из программы",
            command=self._callbacks["exit"],
            font=("Segoe UI", 9), bg="#4a1a1a", fg="#e2c2c2",
            activebackground="#6a2a2a", activeforeground="#ffffff",
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
        ).pack(side="left", padx=5)

        self._card = card
        self._card_status = status
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, _event=None) -> None:
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        self.painter.repaint()
        self.canvas.coords(self._card_window_id, width // 2, height // 2)

        current_x = width - 16
        y = 20
        for item_id, _ in reversed(self._menu_items):
            self.canvas.coords(item_id, current_x, y)
            bbox = self.canvas.bbox(item_id)
            if bbox:
                current_x = bbox[0] - 24

    def _apply_window_mode(self, mode: str) -> None:
        try:
            if mode == "fullscreen":
                self.root.attributes("-fullscreen", True)
                self.root.state("normal")
            elif mode == "zoomed":
                self.root.attributes("-fullscreen", False)
                self.root.state("zoomed")
            elif mode == "1280x800":
                self.root.attributes("-fullscreen", False)
                self.root.geometry("1280x800")
            elif mode == "1600x900":
                self.root.attributes("-fullscreen", False)
                self.root.geometry("1600x900")
            else:
                self.root.attributes("-fullscreen", False)
                self.root.state("zoomed")
        except tk.TclError:
            pass
        self.window_mode_var.set(mode)
        self.root.after(50, self._on_canvas_resize)

    def _on_settings_click(self) -> None:
        self.open_settings()


    def set_settings_available(self, available: bool) -> None:
        self._settings_available = available
        if self._ui is not None:
            try:
                if self._settings_dialog.winfo_exists():
                    self._ui.set_settings_available(available)
            except tk.TclError:
                pass

    def _ensure_settings(self) -> SettingsWindow:
        if self._ui is not None:
            try:
                if not self._settings_dialog.winfo_exists():
                    raise tk.TclError
            except tk.TclError:
                self._ui = None
                self._settings_dialog = None

        if self._ui is not None:
            return self._ui

        dialog = SettingsDialog(
            self.root,
            main_window=self,
            saved_settings=self._saved_settings,
            ocr_labels=self._ocr_labels,
            ocr_values=self._ocr_values,
            provider_labels=self._provider_labels,
            provider_values=self._provider_values,
            initial_area_text=self._initial_area_text,
            callbacks=self._callbacks,
        )

        dialog.protocol("WM_DELETE_WINDOW", self._close_settings)


        self._settings_dialog = dialog
        self._ui = dialog.window

        self._ui.set_settings_available(self._settings_available)

        for msg, lvl in self._log_buffer:
            self._ui.append_log(msg, lvl)

        self._settings_dialog.withdraw()
        return self._ui

    def _close_settings(self) -> None:
        if self._settings_dialog is not None:
            try:
                self._settings_dialog.destroy()
            except Exception:
                pass
            self._settings_dialog = None
        self._ui = None

    def open_settings(self) -> None:
        self._close_settings()
        ui = self._ensure_settings()
        if self._settings_dialog is not None:
            try:
                self._settings_dialog.deiconify()
                self._settings_dialog.lift()
                self._settings_dialog.focus_force()
            except tk.TclError:
                self._settings_dialog = None
                self._ui = None
                self.open_settings()

    def open_background_picker(self) -> None:
        current = dict(self._saved_settings.get("background") or {})
        BackgroundDialog(self.root, current=current, on_apply=self._apply_background)

    def open_window_size_picker(self) -> None:
        WindowSizeDialog(self.root, current=self.window_mode_var.get(), on_apply=self._apply_window_mode_choice)

    def _apply_background(self, payload: dict) -> None:
        self._saved_settings["background"] = payload
        self.background_var.set(describe_background(self._saved_settings))
        self.painter.configure(payload.get("kind", "theme"), theme=payload.get("theme", "Синий"), path=payload.get("path"))
        save = self._callbacks.get("save_settings")
        if save is not None:
            try:
                save()
            except Exception as error:
                print(f"Ошибка сохранения настроек: {error}", flush=True)

    def _apply_window_mode_choice(self, mode: str) -> None:
        self._saved_settings["window_mode"] = mode
        self._apply_window_mode(mode)
        save = self._callbacks.get("save_settings")
        if save is not None:
            try:
                save()
            except Exception as error:
                print(f"Ошибка сохранения настроек: {error}", flush=True)


    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in {"start_button", "capture_button", "stop_button", "status_var"}:
            raise AttributeError(name)
        ui = self._ensure_settings()
        try:
            return getattr(ui, name)
        except AttributeError:
            raise AttributeError(name) from None



    def set_configuration_enabled(self, enabled: bool) -> None:
        self._configuration_enabled = bool(enabled)

        if self._ui is not None:
            try:
                if self._settings_dialog.winfo_exists():
                    self._ui.set_configuration_enabled(enabled)
                else:
                    self._ui = None
                    self._settings_dialog = None
            except tk.TclError:
                self._ui = None
                self._settings_dialog = None

    def append_log(self, message: str, level: int = 20) -> None:
        self._log_buffer.append((message, level))
        if len(self._log_buffer) > 2000:
            self._log_buffer.pop(0)

        if self._ui is not None:
            try:
                if self._settings_dialog.winfo_exists():
                    self._ui.append_log(message, level)
            except tk.TclError:
                pass

    def clear_log(self) -> None:
        self._log_buffer.clear()
        if self._ui is not None:
            self._ui.clear_log()

    @property
    def log_text(self):
        return self._ensure_settings().log_text

    @property
    def log_file_label(self):
        return self._ensure_settings().log_file_label