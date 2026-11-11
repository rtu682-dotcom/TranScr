from __future__ import annotations

import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

DEFAULT_COLOR = "#1b2a4a"


THEMES = {
    "Синий": ("#1b2a4a", "#0f1626"),
    "Графит": ("#2b2b2b", "#111111"),
    "Изумруд": ("#0f3d2e", "#06170f"),
    "Бордовый": ("#3d0f1f", "#17060c"),
}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def gradient_image(width: int, height: int, top: str, bottom: str) -> Image.Image:
    width = max(1, int(width))
    height = max(1, int(height))
    top_rgb = _hex_to_rgb(top)
    bottom_rgb = _hex_to_rgb(bottom)
    column = Image.new("RGB", (1, height))
    pixels = column.load()
    for y in range(height):
        t = y / max(1, height - 1)
        pixels[0, y] = tuple(
            round(top_rgb[i] * (1 - t) + bottom_rgb[i] * t) for i in range(3)
        )
    return column.resize((width, height))


class BackgroundPainter:
    def __init__(self, canvas: tk.Canvas) -> None:
        self.canvas = canvas
        self._image_item = canvas.create_image(0, 0, anchor="nw")
        self._photo: ImageTk.PhotoImage | None = None
        self._source: Image.Image | None = None
        self._last_size: tuple[int, int] = (0, 0)
        self._kind = "default"
        self._theme = "Синий"
        self._path: str | None = None

    def configure(self, kind: str, theme: str | None = None, path: str | None = None) -> None:
        self._kind = "image" if kind == "image" and path else "theme"
        self._theme = theme or self._theme
        self._path = path
        self._source = None
        self._last_size = (0, 0)
        self.repaint()

    def repaint(self) -> None:
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        if self._kind == "image" and self._path:
            source = self._load_image()
        else:
            top, bottom = THEMES.get(self._theme, THEMES["Синий"])
            source = gradient_image(width, height, top, bottom)

        self._photo = ImageTk.PhotoImage(source, master=self.canvas)
        self.canvas.itemconfigure(self._image_item, image=self._photo)
        self.canvas.coords(self._image_item, 0, 0)
        self._last_size = (width, height)

    def _load_image(self) -> Image.Image:
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if self._source is None:
            try:
                self._source = Image.open(self._path).convert("RGB")
            except Exception:
                self._kind = "theme"
                top, bottom = THEMES[self._theme]
                return gradient_image(width, height, top, bottom)
        return self._cover(self._source, width, height)

    @staticmethod
    def _cover(image: Image.Image, width: int, height: int) -> Image.Image:
        width = max(1, width)
        height = max(1, height)
        src_ratio = image.width / image.height
        dst_ratio = width / height
        if src_ratio > dst_ratio:
            new_height = height
            new_width = round(height * src_ratio)
        else:
            new_width = width
            new_height = round(width / src_ratio)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        return resized.crop((left, top, left + width, top + height))


def describe_background(settings: dict) -> str:
    background = settings.get("background") or {}
    if background.get("kind") == "image" and background.get("path"):
        return f"Картинка: {Path(background['path']).name}"
    theme = background.get("theme") or "Синий"
    return f"Тема: {theme}"