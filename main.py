import ctypes
import os
import sys
import traceback
from pathlib import Path


def _enable_windows_dpi_awareness() -> None:
    if os.name != "nt":
        return
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return
    try:
        getattr(windll.shcore, "SetProcessDpiAwareness")(2)
    except Exception:
        try:
            getattr(windll.user32, "SetProcessDPIAware")()
        except Exception:
            pass


def _setup_console_logging() -> None:
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "ui_debug.log"

    def write_line(text: str) -> None:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass
        print(text, flush=True)

    def excepthook(exc_type, exc_value, exc_tb):
        msg = "\n!!! ГЛОБАЛЬНАЯ ОШИБКА !!!\n"
        msg += "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        write_line(msg)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = excepthook


    import tkinter as tk
    original_report = tk.Tk.report_callback_exception
    def report_callback_exception(self, exc, val, tb):
        msg = "\n!!! ОШИБКА В TKINTER CALLBACK !!!\n"
        msg += "".join(traceback.format_exception(exc, val, tb))
        write_line(msg)
        try:
            original_report(self, exc, val, tb)
        except Exception:
            pass

    tk.Tk.report_callback_exception = report_callback_exception



def main() -> None:
    _enable_windows_dpi_awareness()
    _setup_console_logging()
    from core.application import Application

    Application().run()


if __name__ == "__main__":
    main()