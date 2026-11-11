"""Small modal dialogs: background picker and window size picker."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from .backgrounds import THEMES


def _center(window: tk.Toplevel, parent: tk.Misc, width: int, height: int) -> None:
    parent.update_idletasks()
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


class BackgroundDialog(tk.Toplevel):
    """Pick a built-in theme or a custom image for the main background."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        current: dict,
        on_apply,
    ) -> None:
        super().__init__(parent)
        self.title("Выбор фона")
        self.transient(parent)
        self.resizable(False, False)
        self._on_apply = on_apply

        self.kind_var = tk.StringVar(
            value="image" if current.get("kind") == "image" else "theme"
        )
        self.theme_var = tk.StringVar(value=current.get("theme") or "Синий")
        self.path_var = tk.StringVar(value=current.get("path") or "")

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)

        themes_row = ttk.Frame(body)
        themes_row.grid(row=0, column=0, sticky="ew")
        ttk.Radiobutton(
            themes_row, text="Существующая тема", value="theme",
            variable=self.kind_var, command=self._sync_state,
        ).pack(anchor="w")
        self.theme_combo = ttk.Combobox(
            themes_row, textvariable=self.theme_var,
            values=list(THEMES), state="readonly", width=28,
        )
        self.theme_combo.pack(anchor="w", padx=(22, 0), pady=(4, 10))

        image_row = ttk.Frame(body)
        image_row.grid(row=1, column=0, sticky="ew")
        ttk.Radiobutton(
            image_row, text="Своя картинка", value="image",
            variable=self.kind_var, command=self._sync_state,
        ).pack(anchor="w")
        picker = ttk.Frame(image_row)
        picker.pack(anchor="w", padx=(22, 0), pady=(4, 0), fill="x")
        picker.columnconfigure(0, weight=1)
        self.path_entry = ttk.Entry(picker, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, sticky="ew")
        self.browse_button = ttk.Button(
            picker, text="Обзор…", command=self._browse
        )
        self.browse_button.grid(row=0, column=1, padx=(6, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=2, column=0, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(
            side="right", padx=(6, 0)
        )
        ttk.Button(buttons, text="Применить", command=self._apply).pack(side="right")

        self._sync_state()
        _center(self, parent, 460, 240)
        self.grab_set()
        self.focus_set()

    def destroy(self) -> None:
        # Always release the grab so the parent window stays clickable.
        try:
            self.grab_release()
        except tk.TclError:
            pass
        super().destroy()

    def _sync_state(self) -> None:
        theme_state = "readonly" if self.kind_var.get() == "theme" else "disabled"
        image_state = "normal" if self.kind_var.get() == "image" else "disabled"
        self.theme_combo.configure(state=theme_state)
        self.path_entry.configure(state=image_state)
        self.browse_button.configure(state=image_state)

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Выберите фоновое изображение",
            filetypes=[
                ("Изображения", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"),
                ("Все файлы", "*.*"),
            ],
        )
        if path:
            self.path_var.set(path)

    def _apply(self) -> None:
        kind = self.kind_var.get()
        path = self.path_var.get().strip()
        if kind == "image" and not path:
            # Do not silently switch to an empty image; keep the dialog open.
            self.path_entry.focus_set()
            return
        if kind == "image":
            payload = {"kind": "image", "path": path, "theme": self.theme_var.get()}
        else:
            payload = {"kind": "theme", "path": None, "theme": self.theme_var.get()}
        self._on_apply(payload)
        self.destroy()


class WindowSizeDialog(tk.Toplevel):
    """Pick the window mode: fullscreen, zoomed or a fixed size."""

    OPTIONS = (
        ("fullscreen", "Полный экран"),
        ("zoomed", "Развёрнуто на весь экран"),
        ("1280x800", "Окно 1280 × 800"),
        ("1600x900", "Окно 1600 × 900"),
    )

    def __init__(self, parent: tk.Misc, *, current: str, on_apply) -> None:
        super().__init__(parent)
        self.title("Размер экрана")
        self.transient(parent)
        self.resizable(False, False)
        self._on_apply = on_apply

        self.mode_var = tk.StringVar(
            value=current if current in {key for key, _ in self.OPTIONS} else "fullscreen"
        )

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        for key, label in self.OPTIONS:
            ttk.Radiobutton(
                body, text=label, value=key, variable=self.mode_var
            ).pack(anchor="w", pady=2)

        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(
            side="right", padx=(6, 0)
        )
        ttk.Button(buttons, text="Применить", command=self._apply).pack(side="right")

        _center(self, parent, 340, 220)
        self.grab_set()
        self.focus_set()

    def destroy(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        super().destroy()

    def _apply(self) -> None:
        self._on_apply(self.mode_var.get())
        self.destroy()