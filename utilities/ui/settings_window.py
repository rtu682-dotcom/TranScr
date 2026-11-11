from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Mapping
from tkinter import filedialog, ttk
from typing import Any

_MODIFIER_ALIASES = {
    "control": "ctrl",
    "ctrl": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "win": "windows",
    "windows": "windows",
}
_KEYSYM_ALIASES = {
    "escape": "esc",
    "return": "enter",
    "prior": "page up",
    "next": "page down",
    "backspace": "backspace",
    "delete": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "tab": "tab",
    "space": "space",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "print": "print screen",
    "scroll_lock": "scroll lock",
    "pause": "pause",
}


def _format_hotkey(event: tk.Event) -> str | None:

    keysym = (event.keysym or "").lower()
    if keysym in {
        "control_l", "control_r", "alt_l", "alt_r", "shift_l", "shift_r",
        "win_l", "win_r", "super_l", "super_r",
    }:
        return None
    parts: list[str] = []
    state = int(event.state or 0)
    if state & 0x0004:
        parts.append("ctrl")
    if state & 0x0008:
        parts.append("shift")
    if state & 0x0001:
        parts.append("alt")
    if state & 0x0040:
        parts.append("windows")

    if keysym in _KEYSYM_ALIASES:
        key = _KEYSYM_ALIASES[keysym]
    elif keysym.startswith("f") and keysym[1:].isdigit():
        key = keysym
    elif len(keysym) == 1:
        key = keysym
    else:
        key = keysym.replace("_", " ")
    parts.append(key)
    return "+".join(parts)


class SettingsWindow:

    DEFAULT_STATUS = "Готово."
    COLOR_OK = "#245c35"
    COLOR_WARN = "#8a5a00"
    COLOR_ERR = "#8b1a1a"

    def __init__(
        self,
        root: tk.Tk,
        *,
        main_window: Any = None,
        saved_settings: Mapping[str, Any],
        ocr_labels: Mapping[str, str],
        ocr_values: Mapping[str, str],
        provider_labels: Mapping[str, str],
        provider_values: Mapping[str, str],
        initial_area_text: str,
        callbacks: Mapping[str, Callable[[], None]],
    ) -> None:
        self.root = root
        self._main_window = main_window
        self._callbacks = callbacks
        self.ocr_labels = dict(ocr_labels)
        self.ocr_values = dict(ocr_values)
        self.provider_labels = dict(provider_labels)
        self.provider_values = dict(provider_values)

        self.ocr_var = tk.StringVar(
            value=self.ocr_values.get(
                saved_settings.get("ocr", "windows"), "Windows OCR"
            )
        )
        provider = saved_settings.get("provider", "mymemory")
        self.provider_var = tk.StringVar(
            value=self.provider_labels.get(provider, self.provider_labels["mymemory"])
        )
        fallback = saved_settings.get("fallback_provider", "argos")
        self.fallback_provider_var = tk.StringVar(
            value=self.provider_labels.get(fallback, self.provider_labels["argos"])
        )
        self.hybrid_var = tk.BooleanVar(
            value=bool(saved_settings.get("hybrid_enabled", False))
        )
        self.start_hotkey_var = tk.StringVar(
            value=saved_settings.get("start_hotkey", "alt+t")
        )
        self.quick_area_hotkey_var = tk.StringVar(
            value=saved_settings.get("quick_area_hotkey", "alt+q")
        )
        self.dismiss_mode_var = tk.StringVar(
            value=saved_settings.get("dismiss_mode", "any")
        )
        self.dismiss_hotkey_var = tk.StringVar(
            value=saved_settings.get("dismiss_hotkey", "esc")
        )
        self.area_var = tk.StringVar(value=initial_area_text)
        self.save_debug_var = tk.BooleanVar(
            value=bool(saved_settings.get("save_debug_screenshots", False))
        )
        self.status_var = tk.StringVar(value=self.DEFAULT_STATUS)

        self._configuration_enabled = True
        self._recording_hotkey_for: ttk.Entry | None = None
        self._build_widgets()


    def _build_widgets(self) -> None:
        style = ttk.Style(self.root)

        outer = ttk.Frame(self.root, padding=(12, 10, 12, 10))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(outer)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.settings_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.settings_tab, text="  Настройки  ")
        self.notebook.add(self.log_tab, text="  Журнал  ")

        self._build_settings_tab()
        self._build_log_tab()

        bottom_bar = ttk.Frame(outer)
        bottom_bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))


        ttk.Button(
            bottom_bar,
            text="Сохранить настройки",
            command=self._save_and_close
        ).pack(side="right")

        ttk.Button(
            bottom_bar,
            text="Закрыть",
            command=self._close_dialog
        ).pack(side="right", padx=(0, 8))


    def _build_settings_tab(self) -> None:
        self.settings_tab.columnconfigure(0, weight=1)
        self.settings_tab.rowconfigure(0, weight=1)

        canvas = tk.Canvas(self.settings_tab, highlightthickness=0, borderwidth=0)
        canvas.grid(row=0, column=0, sticky="nsew")


        body = ttk.Frame(canvas, padding=(12, 10))
        window_id = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )
        body.bind("<Enter>", lambda _e: canvas.bind_all(
            "<MouseWheel>",
            lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units"),
        ))
        body.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        body.columnconfigure(0, weight=1)

        engine = ttk.LabelFrame(body, text="Обработка и перевод", style="Card.TLabelframe")
        engine.grid(row=0, column=0, sticky="ew")
        engine.columnconfigure(1, weight=1)
        ttk.Label(engine, text="Распознавание текста (OCR)").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 6)
        )
        self.ocr_combo = ttk.Combobox(
            engine, textvariable=self.ocr_var,
            values=list(self.ocr_labels), state="readonly",
        )
        self.ocr_combo.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        self.ocr_combo.bind("<<ComboboxSelected>>", lambda _e: self._save())

        ttk.Label(engine, text="Основной переводчик").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=6
        )
        self.provider_combo = ttk.Combobox(
            engine, textvariable=self.provider_var,
            values=list(self.provider_values), state="readonly",
        )
        self.provider_combo.grid(row=1, column=1, sticky="ew", pady=6)
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_primary_provider_changed)

        ttk.Label(engine, text="Резервный переводчик").grid(
            row=2, column=0, sticky="w", padx=(0, 12), pady=6
        )
        self.fallback_combo = ttk.Combobox(
            engine, textvariable=self.fallback_provider_var,
            values=list(self.provider_values), state="disabled",
        )
        self.fallback_combo.grid(row=2, column=1, sticky="ew", pady=6)
        self.fallback_combo.bind("<<ComboboxSelected>>", self._on_fallback_changed)

        hybrid_row = ttk.Frame(engine)
        hybrid_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.hybrid_button = ttk.Checkbutton(
            hybrid_row,
            text="Гибридный режим (основной + резервный)",
            variable=self.hybrid_var,
            command=self._on_hybrid_toggled,
        )
        self.hybrid_button.pack(side="left")
        self._update_hybrid_controls()

        hotkeys = ttk.LabelFrame(body, text="Горячие клавиши", style="Card.TLabelframe")
        hotkeys.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        hotkeys.columnconfigure(1, weight=1)

        ttk.Label(hotkeys, text="Запуск перевода").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 4)
        )
        self.start_hotkey_entry = ttk.Entry(
            hotkeys, textvariable=self.start_hotkey_var, width=26
        )
        self.start_hotkey_entry.grid(row=0, column=1, sticky="ew", pady=(0, 4))
        self._attach_hotkey_recorder(self.start_hotkey_entry, hotkeys, row=0)
        ttk.Label(
            hotkeys, text="Например: alt+t, ctrl+shift+x, f8",
            style="Hint.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(0, 8))

        ttk.Label(hotkeys, text="Выделить и перевести").grid(
            row=2, column=0, sticky="w", padx=(0, 12), pady=(4, 4)
        )
        self.quick_area_hotkey_entry = ttk.Entry(
            hotkeys, textvariable=self.quick_area_hotkey_var, width=26
        )
        self.quick_area_hotkey_entry.grid(row=2, column=1, sticky="ew", pady=(4, 4))
        self._attach_hotkey_recorder(self.quick_area_hotkey_entry, hotkeys, row=2)

        ttk.Label(hotkeys, text="Сброс перевода").grid(
            row=3, column=0, sticky="nw", padx=(0, 12), pady=(8, 0)
        )
        dismiss_box = ttk.Frame(hotkeys)
        dismiss_box.grid(row=3, column=1, sticky="ew", pady=(8, 0))
        dismiss_box.columnconfigure(0, weight=1)
        radios = ttk.Frame(dismiss_box)
        radios.grid(row=0, column=0, sticky="w")
        self.dismiss_any_radio = ttk.Radiobutton(
            radios, text="Любая клавиша", value="any",
            variable=self.dismiss_mode_var, command=self._on_dismiss_mode_changed,
        )
        self.dismiss_any_radio.pack(side="left")
        self.dismiss_custom_radio = ttk.Radiobutton(
            radios, text="Сочетание", value="hotkey",
            variable=self.dismiss_mode_var, command=self._on_dismiss_mode_changed,
        )
        self.dismiss_custom_radio.pack(side="left", padx=(14, 0))

        self.dismiss_hotkey_entry = ttk.Entry(
            dismiss_box, textvariable=self.dismiss_hotkey_var, width=26
        )
        self.dismiss_hotkey_entry.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._attach_hotkey_recorder(self.dismiss_hotkey_entry, dismiss_box, row=1)
        self._update_dismiss_controls()

        for entry in (
            self.start_hotkey_entry,
            self.quick_area_hotkey_entry,
            self.dismiss_hotkey_entry,
        ):
            entry.bind("<FocusOut>", lambda _e: self._save())

    def _build_log_tab(self) -> None:
        self.log_tab.columnconfigure(0, weight=1)
        self.log_tab.rowconfigure(0, weight=1)

        log_frame = ttk.Frame(self.log_tab)
        log_frame.grid(row=0, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame, wrap="word", state="disabled", height=20,
            font=("Consolas", 9), background="#17191c", foreground="#e7e7e7",
            insertbackground="#ffffff", relief="flat", padx=8, pady=8,
        )
        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        for tag, color in (
            ("INFO", "#e7e7e7"), ("WARNING", "#ffcc66"),
            ("ERROR", "#ff7777"), ("DEBUG", "#9dc7ff"),
        ):
            self.log_text.tag_configure(tag, foreground=color)

        controls = ttk.Frame(self.log_tab)
        controls.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        controls.columnconfigure(1, weight=1)
        ttk.Button(controls, text="Очистить", command=self.clear_log).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(controls, text="Копировать всё", command=self._copy_log).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Button(controls, text="Сохранить в файл…", command=self._save_log).grid(
            row=0, column=2, sticky="w", padx=(8, 0)
        )
        self.log_file_label = ttk.Label(
            controls, text="Файл журнала недоступен",
            foreground="#666666", style="Hint.TLabel",
        )
        self.log_file_label.grid(row=0, column=3, sticky="e", padx=(8, 0))


    def _attach_hotkey_recorder(
        self, entry: ttk.Entry, parent: ttk.Frame, *, row: int
    ) -> None:
        button = ttk.Button(
            parent, text="Записать",
            command=lambda e=entry: self._begin_recording(e),
        )
        button.grid(row=row, column=2, padx=(8, 0), sticky="w")
        entry._recorder_button = button

    def _begin_recording(self, entry: ttk.Entry) -> None:
        if self._recording_hotkey_for is not None:
            self._cancel_recording()
        self._recording_hotkey_for = entry
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, "Нажмите сочетание…")
        entry.focus_set()
        self.status_var.set("Зажмите модификатор(ы) и нажмите клавишу. Esc — отмена.")
        entry.bind("<KeyPress>", self._on_record_keypress)

    def _on_record_keypress(self, event: tk.Event) -> str | None:
        if self._recording_hotkey_for is None:
            return None
        if event.keysym == "Escape":
            self._cancel_recording()
            return "break"
        formatted = _format_hotkey(event)
        if formatted is None:
            return "break"
        self._recording_hotkey_for.delete(0, "end")
        self._recording_hotkey_for.insert(0, formatted)
        self._finish_recording()
        self._save()
        return "break"

    def _finish_recording(self) -> None:
        if self._recording_hotkey_for is not None:
            self._recording_hotkey_for.unbind("<KeyPress>")
            self._recording_hotkey_for = None
        self.status_var.set(self.DEFAULT_STATUS)

    def _cancel_recording(self) -> None:
        if self._recording_hotkey_for is not None:
            self._recording_hotkey_for.unbind("<KeyPress>")
            self._recording_hotkey_for = None
        self.status_var.set("Запись сочетания отменена.")

    def _copy_log(self) -> None:
        try:
            content = self.log_text.get("1.0", "end-1c")
        except tk.TclError:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.status_var.set("Журнал скопирован в буфер обмена.")

    def _save_log(self) -> None:
        try:
            content = self.log_text.get("1.0", "end-1c")
        except tk.TclError:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить журнал",
            defaultextension=".log",
            filetypes=[("Журнал", "*.log"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as error:
            self.status_var.set(f"Не удалось сохранить журнал: {error}")
            return
        self.status_var.set(f"Журнал сохранён: {path}")


    def append_log(self, message: str, level: int = 20) -> None:
        if not hasattr(self, "log_text"):
            return
        if level >= 40:
            tag = "ERROR"
        elif level >= 30:
            tag = "WARNING"
        elif level <= 10:
            tag = "DEBUG"
        else:
            tag = "INFO"
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"{message}\n", (tag,))
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > 2000:
                self.log_text.delete("1.0", f"{line_count - 1800}.0")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except tk.TclError:
            pass

    def set_settings_available(self, available: bool) -> None:
        if available:
            self.notebook.tab(0, state="normal")
            self.set_configuration_enabled(True)
        else:
            self.notebook.tab(0, state="disabled")
            if self.notebook.index(self.notebook.select()) == 0:
                self.notebook.select(1)
            self.set_configuration_enabled(False)


    def clear_log(self) -> None:
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
        except tk.TclError:
            pass

    def set_configuration_enabled(self, enabled: bool) -> None:
        self._configuration_enabled = bool(enabled)
        widget_state = "readonly" if enabled else "disabled"

        self.ocr_combo.configure(state=widget_state)
        self.provider_combo.configure(state=widget_state)

        self.hybrid_button.configure(state="normal" if enabled else "disabled")

        for entry in (
                self.start_hotkey_entry,
                self.quick_area_hotkey_entry,
                self.dismiss_hotkey_entry,
        ):
            entry.configure(state="normal" if enabled else "disabled")
            button = getattr(entry, "_recorder_button", None)
            if button is not None:
                button.configure(state="normal" if enabled else "disabled")

        state = "normal" if enabled else "disabled"
        self.dismiss_any_radio.configure(state=state)
        self.dismiss_custom_radio.configure(state=state)

        self._update_hybrid_controls()
        self._update_dismiss_controls()



    def _on_hybrid_toggled(self) -> None:
        self._update_hybrid_controls()
        self._save()

    def _update_hybrid_controls(self) -> None:
        can_edit_fallback = self._configuration_enabled and self.hybrid_var.get()
        self.fallback_combo.configure(
            state="readonly" if can_edit_fallback else "disabled"
        )

    def _on_primary_provider_changed(self, _event=None) -> None:
        if self.provider_var.get() == self.fallback_provider_var.get():
            primary = self.provider_values.get(self.provider_var.get(), "mymemory")
            replacement = "argos" if primary != "argos" else "mymemory"
            self.fallback_provider_var.set(self.provider_labels[replacement])
        self._save()

    def _on_fallback_changed(self, _event=None) -> None:
        if self.provider_var.get() == self.fallback_provider_var.get():
            primary = self.provider_values.get(self.provider_var.get(), "mymemory")
            replacement = "argos" if primary != "argos" else "mymemory"
            self.fallback_provider_var.set(self.provider_labels[replacement])
        self._save()

    def _on_dismiss_mode_changed(self) -> None:
        self._update_dismiss_controls()
        self._save()

    def _update_dismiss_controls(self) -> None:
        state = "normal" if self._configuration_enabled else "disabled"
        self.dismiss_any_radio.configure(state=state)
        self.dismiss_custom_radio.configure(state=state)
        self.dismiss_hotkey_entry.configure(
            state="normal"
            if self._configuration_enabled and self.dismiss_mode_var.get() == "hotkey"
            else "disabled"
        )

    def _close_dialog(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass


    def _save_and_close(self) -> None:
        if not self._configuration_enabled:
            self._close_dialog()
            return
        self._save()
        self._close_dialog()

    def _save(self) -> None:
        if not self._configuration_enabled:
            return

        # Используем переданную ссылку на MainWindow
        mw = getattr(self, "_main_window", None)

        if mw is not None and hasattr(mw, "_saved_settings"):
            new_settings = {
                "ocr": self.ocr_values.get(self.ocr_var.get(), "windows"),
                "provider": self.provider_values.get(self.provider_var.get(), "mymemory"),
                "fallback_provider": self.provider_values.get(self.fallback_provider_var.get(), "argos"),
                "hybrid_enabled": bool(self.hybrid_var.get()),
                "start_hotkey": self.start_hotkey_var.get().strip().lower(),
                "quick_area_hotkey": self.quick_area_hotkey_var.get().strip().lower(),
                "dismiss_mode": self.dismiss_mode_var.get(),
                "dismiss_hotkey": self.dismiss_hotkey_var.get().strip().lower(),
            }

            changed = False
            for key, value in new_settings.items():
                if mw._saved_settings.get(key) != value:
                    mw._saved_settings[key] = value
                    changed = True

            if not changed:
                return

        callback = self._callbacks.get("save_settings")
        if callback is not None:
            callback()