"""Light Material-inspired Qt theme helpers."""

from __future__ import annotations

from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QApplication


MATERIAL_LIGHT_QSS = """
QWidget {
    font-size: 13px;
    color: #212121;
}
QMainWindow, QDialog {
    background: #FAFAFA;
    color: #212121;
}
QLabel {
    color: #212121;
}
QMenuBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
    padding: 2px 4px;
    color: #212121;
}
QMenuBar::item {
    padding: 6px 10px;
    border-radius: 4px;
    color: #212121;
}
QMenuBar::item:selected {
    background: #E3F2FD;
}
QMenu {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    padding: 4px;
    color: #212121;
}
QMenu::item {
    padding: 6px 28px 6px 28px;
    border-radius: 4px;
    color: #212121;
}
QMenu::item:selected {
    background: #E3F2FD;
    color: #0D47A1;
}
QMenu::item:checked {
    background: #E8F5E9;
    color: #1B5E20;
    font-weight: 600;
}
QMenu::indicator {
    width: 14px;
    height: 14px;
    margin-left: 6px;
}
QMenu::indicator:non-exclusive:checked {
    background: #2E7D32;
    border-radius: 2px;
}
QMenu::indicator:non-exclusive:unchecked {
    background: transparent;
    border: 1px solid #B0BEC5;
    border-radius: 2px;
}
QToolBar {
    background: #FFFFFF;
    border: none;
    border-bottom: 1px solid #EEEEEE;
    spacing: 4px;
    padding: 4px;
}
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 8px;
    color: #37474F;
}
QToolButton:hover {
    background: #F5F5F5;
    border-color: #EEEEEE;
}
QToolButton:checked, QToolButton:pressed {
    background: #E3F2FD;
    border-color: #BBDEFB;
    color: #0D47A1;
}
QPushButton {
    background: #FFFFFF;
    border: 1px solid #CFD8DC;
    border-radius: 6px;
    padding: 6px 12px;
    color: #37474F;
}
QPushButton:hover {
    background: #F5F5F5;
    border-color: #90A4AE;
}
QPushButton:pressed {
    background: #E3F2FD;
}
QPushButton:disabled {
    color: #B0BEC5;
    background: #FAFAFA;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QListWidget {
    background: #FFFFFF;
    color: #212121;
    border: 1px solid #CFD8DC;
    border-radius: 6px;
    padding: 4px 6px;
    selection-background-color: #BBDEFB;
    selection-color: #0D47A1;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    color: #212121;
    selection-background-color: #E3F2FD;
    selection-color: #0D47A1;
}
QDockWidget {
    titlebar-close-icon: none;
    color: #37474F;
}
QDockWidget::title {
    background: #ECEFF1;
    padding: 6px;
    border-bottom: 1px solid #CFD8DC;
    color: #37474F;
}
QStatusBar {
    background: #FFFFFF;
    border-top: 1px solid #EEEEEE;
    color: #212121;
}
QTabWidget::pane {
    border: 1px solid #E0E0E0;
    background: #FFFFFF;
    border-radius: 4px;
}
QTabBar::tab {
    background: #ECEFF1;
    border: 1px solid #E0E0E0;
    border-bottom: none;
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #212121;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #0D47A1;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #CFD8DC;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 14px;
    margin: -6px 0;
    background: #1976D2;
    border-radius: 7px;
}
"""


def _light_palette() -> QPalette:
    """Force a light Fusion palette so macOS Dark Mode cannot invert text."""
    palette = QPalette()
    window = QColor("#FAFAFA")
    base = QColor("#FFFFFF")
    text = QColor("#212121")
    disabled = QColor("#B0BEC5")
    highlight = QColor("#BBDEFB")
    highlighted_text = QColor("#0D47A1")
    button = QColor("#FFFFFF")
    button_text = QColor("#37474F")

    palette.setColor(QPalette.Window, window)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.AlternateBase, QColor("#F5F5F5"))
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.PlaceholderText, QColor("#90A4AE"))
    palette.setColor(QPalette.Button, button)
    palette.setColor(QPalette.ButtonText, button_text)
    palette.setColor(QPalette.BrightText, QColor("#FFFFFF"))
    palette.setColor(QPalette.Highlight, highlight)
    palette.setColor(QPalette.HighlightedText, highlighted_text)
    palette.setColor(QPalette.ToolTipBase, base)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Link, QColor("#1565C0"))

    palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled)
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled)
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor("#ECEFF1"))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, disabled)
    return palette


def apply_material_theme(app: QApplication) -> None:
    """Apply Fusion style + a light Material-inspired stylesheet."""
    app.setStyle("Fusion")
    app.setPalette(_light_palette())
    font = QFont("Segoe UI")
    if not font.exactMatch():
        # Prefer readable system UI fonts on macOS/Linux.
        for family in ("Helvetica Neue", "Arial", ".AppleSystemUIFont", "Sans Serif"):
            font = QFont(family)
            if font.exactMatch() or family == "Sans Serif":
                break
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(MATERIAL_LIGHT_QSS)
