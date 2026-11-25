"""PromptPersona 启动入口：双击 启动.bat 或运行 python main.py。"""

from __future__ import annotations

import os
import sys
import traceback


def _enable_dpi_awareness():
    """Windows 高分屏下避免界面发糊。"""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def _log_dir():
    """崩溃日志要落在用户能找到的地方：打包后是 exe 同目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    _enable_dpi_awareness()
    try:
        from app.ui import App

        App().mainloop()
        return 0
    except Exception:
        detail = traceback.format_exc()
        try:
            with open(os.path.join(_log_dir(), "startup-error.log"), "w", encoding="utf-8") as handle:
                handle.write(detail)
        except OSError:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("PromptPersona", detail[-1500:])
            root.destroy()
        except Exception:
            print(detail, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
