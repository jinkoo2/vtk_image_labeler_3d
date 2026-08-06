"""Resolve and load the application icon."""

from __future__ import annotations

import os

from PyQt5.QtGui import QIcon


def app_icon_path(resource_dir: str | None = None) -> str:
    """Return path to app.ico/app.png (or legacy brush.png)."""
    base = resource_dir or os.path.dirname(os.path.abspath(__file__))
    icons = os.path.join(base, "icons")
    for name in ("app.ico", "app.png", "brush.png"):
        path = os.path.join(icons, name)
        if os.path.isfile(path):
            return path
    return os.path.join(icons, "app.png")


def load_app_icon(resource_dir: str | None = None) -> QIcon:
    path = app_icon_path(resource_dir)
    icon = QIcon(path)
    return icon
