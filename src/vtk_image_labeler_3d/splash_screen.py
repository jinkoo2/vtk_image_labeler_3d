"""Startup splash screen helpers."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen


def create_splash(
    app_name: str = "Image Labeler 3D",
    version: str = "",
    icon: QIcon | None = None,
) -> QSplashScreen:
    """Build a simple branded splash without requiring an image asset."""
    width, height = 460, 280
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(32, 40, 52))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Accent bar
    painter.fillRect(0, 0, width, 6, QColor(43, 176, 199))

    # App icon
    if icon is not None and not icon.isNull():
        icon_pix = icon.pixmap(72, 72)
        if not icon_pix.isNull():
            x = (width - icon_pix.width()) // 2
            painter.drawPixmap(x, 28, icon_pix)

    title_font = QFont()
    title_font.setPointSize(18)
    title_font.setBold(True)
    painter.setFont(title_font)
    painter.setPen(QColor(235, 240, 245))
    painter.drawText(0, 118, width, 40, Qt.AlignHCenter | Qt.AlignVCenter, app_name)

    version_font = QFont()
    version_font.setPointSize(11)
    painter.setFont(version_font)
    painter.setPen(QColor(180, 190, 200))
    version_text = f"Version {version}" if version else ""
    painter.drawText(0, 158, width, 24, Qt.AlignHCenter | Qt.AlignVCenter, version_text)

    painter.setPen(QColor(120, 140, 160))
    painter.drawText(
        0,
        height - 48,
        width,
        24,
        Qt.AlignHCenter | Qt.AlignVCenter,
        "Starting...",
    )
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.WindowStaysOnTopHint)
    return splash


def show_message(splash: QSplashScreen, message: str) -> None:
    if splash is None:
        return
    splash.showMessage(
        message,
        Qt.AlignHCenter | Qt.AlignBottom,
        QColor(210, 220, 230),
    )
    QApplication.processEvents()
