from contextlib import contextmanager

from PyQt5.QtCore import Qt, QEvent, QObject, QSettings
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog, QWidget

_busy_state = {"depth": 0, "dialog": None}


def app_qsettings() -> QSettings:
    """Shared INI settings file used across the app (``_settings.conf``)."""
    return QSettings("_settings.conf", QSettings.IniFormat)


def restore_widget_geometry(widget: QWidget, key: str) -> bool:
    """Restore size/position previously saved under ``window_geometry/<key>``."""
    if widget is None or not key:
        return False
    try:
        geom = app_qsettings().value(f"window_geometry/{key}")
        if geom is None:
            return False
        return bool(widget.restoreGeometry(geom))
    except Exception as e:
        print(f"Failed to restore geometry for '{key}': {e}")
        return False


def save_widget_geometry(widget: QWidget, key: str) -> None:
    """Persist size/position under ``window_geometry/<key>``."""
    if widget is None or not key:
        return
    try:
        settings = app_qsettings()
        settings.setValue(f"window_geometry/{key}", widget.saveGeometry())
        settings.sync()
    except Exception as e:
        print(f"Failed to save geometry for '{key}': {e}")


class _GeometryPersistenceFilter(QObject):
    """Save geometry on hide/close; restore once on first show if not restored yet."""

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self.key = key
        self._restored = False

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype == QEvent.Show:
            if not self._restored:
                restore_widget_geometry(obj, self.key)
                self._restored = True
        elif etype in (QEvent.Hide, QEvent.Close):
            # Prediction Tool uses Hide (closeEvent ignored); other dialogs Close.
            save_widget_geometry(obj, self.key)
        return False


def persist_widget_geometry(widget: QWidget, key: str) -> None:
    """Restore geometry now (if available) and auto-save on hide/close.

    Call after the widget's default ``resize`` / ``setGeometry`` so a saved
    layout overrides the defaults.
    """
    if widget is None or not key:
        return
    # Prefer immediate restore so size is correct before first paint.
    restored = restore_widget_geometry(widget, key)
    filt = _GeometryPersistenceFilter(key, parent=widget)
    filt._restored = restored
    widget.installEventFilter(filt)
    # Keep a strong ref so the filter is not GC'd.
    widget._geometry_persistence_filter = filt


@contextmanager
def busy_progress(parent=None, title="Please wait", label="Working..."):
    """Show an indeterminate progress dialog + wait cursor for blocking work.

    Nested calls reuse the same dialog and only close it when the outermost
    context exits.
    """
    if _busy_state["depth"] == 0:
        dialog = QProgressDialog(label, None, 0, 0, parent)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setMinimumDuration(0)
        dialog.setCancelButton(None)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setMinimumWidth(360)
        dialog.show()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        _busy_state["dialog"] = dialog
    else:
        dialog = _busy_state["dialog"]
        if dialog is not None:
            dialog.setWindowTitle(title)
            dialog.setLabelText(label)
            QApplication.processEvents()

    _busy_state["depth"] += 1
    try:
        yield dialog
    finally:
        _busy_state["depth"] -= 1
        if _busy_state["depth"] <= 0:
            _busy_state["depth"] = 0
            QApplication.restoreOverrideCursor()
            if _busy_state["dialog"] is not None:
                _busy_state["dialog"].close()
                _busy_state["dialog"].deleteLater()
                _busy_state["dialog"] = None
            QApplication.processEvents()


def update_busy_progress(label=None, title=None):
    """Update the active busy dialog label/title, if any."""
    dialog = _busy_state.get("dialog")
    if dialog is None:
        return
    if title is not None:
        dialog.setWindowTitle(title)
    if label is not None:
        dialog.setLabelText(label)
    QApplication.processEvents()


def show_msgbox_yes_no(title:str="Confirm", msg:str="", parent: QWidget = None):
    reply = QMessageBox.question(
        parent,
        title,
        msg,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes  # Default button
    )

    if reply == QMessageBox.Yes:
        print("User clicked Yes")
        return True
    else:
        print("User clicked No")
        return False


def show_msgbox_error(title:str="Error", msg:str="something went wrong!", parent: QWidget = None):
    QMessageBox.critical(parent, title, msg)

def show_msgbox_warning(title:str="Warning", msg:str="something went wrong!", parent: QWidget = None):
    QMessageBox.warning(parent, title, msg)

def show_msgbox_info(title:str="Information", msg:str="something went wrong!", parent: QWidget = None):
    QMessageBox.information(parent, title, msg)


def show_select_options_dlg(title, label, options, parent: QWidget = None):
    from PyQt5.QtWidgets import QInputDialog
    item, ok = QInputDialog.getItem(parent, title, label, options, 0, False)
    if ok and item:
        print(f"User selected: {item}")
        return item
    return None
