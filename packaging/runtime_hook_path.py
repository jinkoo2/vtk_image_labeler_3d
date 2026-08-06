"""Ensure frozen app can resolve bare package imports and resource paths."""

import os
import sys


def _ensure_path():
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and meipass not in sys.path:
            sys.path.insert(0, meipass)
        # Prefer launching cwd for settings.json / logs next to the exe folder.
        exe_dir = os.path.dirname(sys.executable)
        if exe_dir and os.path.isdir(exe_dir):
            try:
                os.chdir(exe_dir)
            except OSError:
                pass


_ensure_path()
