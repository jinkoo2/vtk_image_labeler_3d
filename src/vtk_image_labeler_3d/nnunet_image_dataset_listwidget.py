from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QApplication,
    QWidget,
    QDialog,
    QTextEdit,
    QComboBox,
    QFormLayout,
    QDialogButtonBox,
    QGroupBox,
    QMessageBox,
    QTabWidget,
)
import sys
import json
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import uuid
import os
import nnunet_service
import qt_tools

from config import get_config
conf = get_config()

def extract_image_number(filename):
    import re
    match = re.match(r'^.*?_(\d+)_\d+\.(nii\.gz|mha|mhd)$', filename)
    if match:
        return int(match.group(1))
    raise ValueError(f"Could not extract number from filename: {filename}")

nnunet_server_url = conf['nnunet_server_url']

LABEL_AUTO_FIELDS = {
    "filename", "shape", "spacing", "label_stats", "error", "modified_at", "modified_by"
}
IMAGE_AUTO_FIELDS = {
    "channels", "modified_at", "modified_by"
}

LABEL_STATUS_OPTIONS = [
    "",
    "inprogress",
    "complete",
    "reviewed",
    "labeled",
    "empty",
]


class MetaPropertiesPanel(QWidget):
    """Editable image or label metadata panel (used inside the Properties tabs)."""

    def __init__(
        self,
        meta_kind,
        dataset_id,
        images_for,
        num,
        base_url,
        parent=None,
    ):
        super().__init__(parent)
        self.meta_kind = meta_kind  # "image" or "label"
        self.dataset_id = dataset_id
        self.images_for = images_for
        self.num = num
        self.base_url = base_url
        self._original_meta = {}
        self._exists = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)

        edit_group = QGroupBox("Editable Fields")
        edit_form = QFormLayout(edit_group)

        self.status_combo = QComboBox()
        self.status_combo.setEditable(True)
        self.status_combo.addItems(LABEL_STATUS_OPTIONS)
        self.status_combo.setEnabled(meta_kind == "label")
        if meta_kind == "label":
            edit_form.addRow("Status:", self.status_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes")
        self.notes_edit.setMaximumHeight(100)
        edit_form.addRow("Notes:", self.notes_edit)

        from PyQt5.QtWidgets import QDoubleSpinBox
        self.window_spin = QDoubleSpinBox()
        self.window_spin.setDecimals(2)
        self.window_spin.setRange(0.0, 1e7)
        self.window_spin.setSingleStep(10.0)
        self.window_spin.setSpecialValueText("(not set)")
        self.window_spin.setValue(0.0)
        self.level_spin = QDoubleSpinBox()
        self.level_spin.setDecimals(2)
        self.level_spin.setRange(-1e7, 1e7)
        self.level_spin.setSingleStep(10.0)
        if meta_kind == "image":
            edit_form.addRow("Window:", self.window_spin)
            edit_form.addRow("Level:", self.level_spin)

        self.extra_edit = QTextEdit()
        self.extra_edit.setPlaceholderText(
            'Optional extra JSON fields, e.g. {"reviewed": true}'
        )
        self.extra_edit.setMaximumHeight(120)
        edit_form.addRow("Extra JSON:", self.extra_edit)

        layout.addWidget(edit_group)

        auto_group = QGroupBox("Auto-managed Fields (read-only)")
        auto_layout = QVBoxLayout(auto_group)
        self.auto_view = QTextEdit()
        self.auto_view.setReadOnly(True)
        self.auto_view.setFontFamily("Consolas")
        auto_layout.addWidget(self.auto_view)
        layout.addWidget(auto_group)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    def _auto_fields(self):
        return IMAGE_AUTO_FIELDS if self.meta_kind == "image" else LABEL_AUTO_FIELDS

    def _fetch(self):
        if self.meta_kind == "image":
            return nnunet_service.get_image_meta(
                self.base_url, self.dataset_id, self.images_for, self.num
            )
        return nnunet_service.get_label_meta(
            self.base_url, self.dataset_id, self.images_for, self.num
        )

    def _save(self, meta):
        if self.meta_kind == "image":
            return nnunet_service.update_image_meta(
                self.base_url, self.dataset_id, self.images_for, self.num, meta
            )
        return nnunet_service.update_label_meta(
            self.base_url, self.dataset_id, self.images_for, self.num, meta
        )

    def load_meta(self):
        try:
            response = self._fetch()
        except Exception as e:
            self.error_label.setText(f"Failed to load metadata: {e}")
            self._original_meta = {}
            self._exists = False
            self.auto_view.setPlainText("{}")
            return

        if response.get("error"):
            self.error_label.setText(
                f"Metadata file exists but could not be parsed/validated:\n{response.get('error')}"
            )
        else:
            self.error_label.setText("")

        self._exists = bool(response.get("exists"))
        meta = response.get("meta") if isinstance(response.get("meta"), dict) else {}
        self._original_meta = dict(meta)

        status = str(meta.get("status") or "")
        if status and self.status_combo.findText(status) < 0:
            self.status_combo.addItem(status)
        self.status_combo.setCurrentText(status)
        self.notes_edit.setPlainText(str(meta.get("notes") or ""))

        if self.meta_kind == "image":
            wl = meta.get("window_level") if isinstance(meta.get("window_level"), dict) else {}
            window = wl.get("window", wl.get("width"))
            level = wl.get("level")
            self.window_spin.setValue(0.0 if window is None else float(window))
            self.level_spin.setValue(0.0 if level is None else float(level))

        auto_keys = self._auto_fields()
        reserved_editable = {"status", "notes", "window_level"}
        extras = {
            k: v for k, v in meta.items()
            if k not in auto_keys and k not in reserved_editable
        }
        self.extra_edit.setPlainText(json.dumps(extras, indent=2) if extras else "")

        auto_only = {k: v for k, v in meta.items() if k in auto_keys}
        if not auto_only and not self._exists:
            self.auto_view.setPlainText("(no metadata file yet)")
        else:
            self.auto_view.setPlainText(json.dumps(auto_only, indent=2))

    def build_updated_meta(self):
        meta = dict(self._original_meta)

        notes = self.notes_edit.toPlainText().strip()
        if notes:
            meta["notes"] = notes
        else:
            meta.pop("notes", None)

        if self.meta_kind == "label":
            status = self.status_combo.currentText().strip()
            if status:
                meta["status"] = status
            else:
                meta.pop("status", None)

        if self.meta_kind == "image":
            window = float(self.window_spin.value())
            level = float(self.level_spin.value())
            if window > 0:
                meta["window_level"] = {"window": window, "level": level}
            else:
                meta.pop("window_level", None)

        extra_text = self.extra_edit.toPlainText().strip()
        extras = {}
        if extra_text:
            try:
                extras = json.loads(extra_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Extra JSON is invalid: {e}") from e
            if not isinstance(extras, dict):
                raise ValueError("Extra JSON must be an object/dictionary.")

        auto_keys = self._auto_fields()
        reserved_editable = {"status", "notes", "window_level"}

        for key in list(meta.keys()):
            if key not in auto_keys and key not in reserved_editable:
                del meta[key]

        for key, value in extras.items():
            if key in auto_keys or key in reserved_editable:
                raise ValueError(
                    f"'{key}' is reserved and cannot be set via Extra JSON."
                )
            meta[key] = value

        return meta

    def is_modified(self):
        try:
            return self.build_updated_meta() != self._original_meta
        except Exception:
            # Invalid edits count as pending changes that need attention on Save.
            return True

    def save_if_modified(self):
        """Save this panel's meta when changed. Returns (saved, meta_or_none)."""
        if not self.is_modified():
            return False, None

        meta = self.build_updated_meta()
        result = self._save(meta)
        saved = result.get("meta") if isinstance(result, dict) else meta
        if isinstance(saved, dict):
            self._original_meta = dict(saved)
            self._exists = True
            # Refresh auto fields view after save.
            auto_keys = self._auto_fields()
            auto_only = {k: v for k, v in self._original_meta.items() if k in auto_keys}
            self.auto_view.setPlainText(
                json.dumps(auto_only, indent=2) if auto_only else "(no auto fields)"
            )
        self.error_label.setText("")
        return True, saved if isinstance(saved, dict) else meta


class CasePropertiesDialog(QDialog):
    """Combined Properties dialog with Label and Image tabs."""

    def __init__(
        self,
        dataset_id,
        images_for,
        num,
        base_url,
        parent=None,
    ):
        super().__init__(parent)
        self.dataset_id = dataset_id
        self.images_for = images_for
        self.num = num
        self.base_url = base_url
        self.saved_label_meta = None
        self.saved_image_meta = None

        self.setWindowTitle(f"Properties - case {num}")
        self.resize(640, 600)

        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>Dataset:</b> {dataset_id}<br>"
            f"<b>Split:</b> {images_for}<br>"
            f"<b>Case:</b> {num}"
        )
        layout.addWidget(info)

        self.tabs = QTabWidget()
        self.label_panel = MetaPropertiesPanel(
            "label", dataset_id, images_for, num, base_url, parent=self
        )
        self.image_panel = MetaPropertiesPanel(
            "image", dataset_id, images_for, num, base_url, parent=self
        )
        self.tabs.addTab(self.label_panel, "Label")
        self.tabs.addTab(self.image_panel, "Image")
        layout.addWidget(self.tabs)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Save).clicked.connect(self.save_all)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_all()

    def _load_all(self):
        try:
            with qt_tools.busy_progress(
                self,
                title="Loading Properties",
                label=f"Fetching metadata for case {self.num}...",
            ):
                self.label_panel.load_meta()
                self.image_panel.load_meta()
        except Exception as e:
            self.error_label.setText(f"Failed to load metadata: {e}")

    def save_all(self):
        try:
            label_dirty = self.label_panel.is_modified()
            image_dirty = self.image_panel.is_modified()
            if not label_dirty and not image_dirty:
                QMessageBox.information(
                    self,
                    "No Changes",
                    "There are no modified properties to save.",
                )
                return

            with qt_tools.busy_progress(
                self,
                title="Saving Properties",
                label=f"Saving metadata for case {self.num}...",
            ):
                saved_parts = []
                if label_dirty:
                    qt_tools.update_busy_progress(label="Saving label metadata...")
                    saved, meta = self.label_panel.save_if_modified()
                    if saved:
                        self.saved_label_meta = meta
                        saved_parts.append("Label")
                if image_dirty:
                    qt_tools.update_busy_progress(label="Saving image metadata...")
                    saved, meta = self.image_panel.save_if_modified()
                    if saved:
                        self.saved_image_meta = meta
                        saved_parts.append("Image")

            self.error_label.setText("")
            QMessageBox.information(
                self,
                "Saved",
                f"Saved {' and '.join(saved_parts)} metadata for case {self.num}.",
            )
        except Exception as e:
            self.error_label.setText(str(e))
            QMessageBox.critical(self, "Save Failed", str(e))


# Backward-compatible alias used by older call sites.
class MetaPropertiesDialog(CasePropertiesDialog):
    def __init__(
        self,
        meta_kind=None,
        dataset_id=None,
        images_for=None,
        num=None,
        base_url=None,
        parent=None,
        **kwargs,
    ):
        # Older callers passed meta_kind; ignore it and show both tabs.
        super().__init__(
            dataset_id=dataset_id,
            images_for=images_for,
            num=num,
            base_url=base_url,
            parent=parent,
        )

from base_widget import BaseWidget
class nnUnetImageDataSetListWidget(BaseWidget):

    image_dataset_downloaded = pyqtSignal(str, str, QObject)
    label_dataset_downloaded = pyqtSignal(str, QObject)
    post_dataset_clicked = pyqtSignal(str, str, QObject)
    update_dataset_clicked = pyqtSignal(str, str, int, QObject)
    delete_dataset_clicked = pyqtSignal(str, str, int, QObject)
    renumber_dataset_clicked = pyqtSignal(str, str, QObject)

    COLUMN_IMAGE = 0
    COLUMN_STATUS = 1

    def __init__(self, images_for:str):
        super().__init__()

        if images_for != 'train' and images_for != 'test':
            raise Exception('images_for must be either TRAIN(=0) or TEST(=1)')

        self.images_for = images_for
        self._dataset_id = None
        self._base_url = nnunet_server_url
        self._label_nums = set()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_label_widget = QLabel(f'{images_for.upper()} Images')
        self.title_label_widget.setStyleSheet("padding: 0;")
        self.title_label_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_label_widget)

        self.table_widget = QTableWidget(0, 2)
        self.table_widget.setHorizontalHeaderLabels(["Image", "Status"])
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setAlternatingRowColors(True)
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(self.COLUMN_IMAGE, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COLUMN_STATUS, QHeaderView.Fixed)
        self.table_widget.setColumnWidth(self.COLUMN_STATUS, 160)
        self.table_widget.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table_widget.itemSelectionChanged.connect(self._update_action_buttons)
        layout.addWidget(self.table_widget)

        self.list_widget = self.table_widget

        import flowlayout
        button_layout = flowlayout.FlowLayout()
        self.download_image_button = QPushButton("Load")
        self.download_image_button.setToolTip(
            "Load the selected case image and its label (if available)."
        )
        # Kept for backward compatibility; not shown in the UI.
        self.download_label_button = None
        self.append_button = QPushButton("Append As New Image Set")
        self.save_label_button = QPushButton("Save")
        self.save_label_button.setToolTip(
            "Save modified label data and related metadata (e.g. window/level) for the selected case."
        )
        self.delete_button = QPushButton("Delete")
        self.properties_button = QPushButton("Properties")
        self.properties_button.setToolTip(
            "View and edit image and label metadata for the selected case."
        )
        self.image_properties_button = self.properties_button
        self.label_properties_button = self.properties_button
        self.renumber_button = QPushButton("Renumber Images")
        self.renumber_button.setToolTip(
            "Renumber cases to sequential 0..N-1 (required by nnU-Net after deletes)."
        )

        # Keep old attribute names used by older call sites/tests if any.
        self.get_button = self.download_image_button
        self.post_button = self.append_button
        self.update_button = self.save_label_button

        for btn in [
            self.download_image_button,  # Load
            self.save_label_button,      # Save
            self.delete_button,          # Delete
            self.properties_button,      # Properties
            self.append_button,          # Append As New Image Set
            self.renumber_button,        # Renumber Images
        ]:
            btn.clicked.connect(self.command_button_clicked)
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle("Image Dataset List")
        self._update_action_buttons()

    def on_cell_double_clicked(self, row, column):
        if column == self.COLUMN_IMAGE:
            self.table_widget.selectRow(row)
            self.load_selected_case()

    def on_item_double_clicked(self, item):
        self.load_selected_case()

    @staticmethod
    def _derive_status(meta):
        if not meta:
            return ""
        explicit = meta.get("status")
        if explicit:
            return str(explicit)

        label_stats = meta.get("label_stats")
        if isinstance(label_stats, dict) and label_stats:
            any_labeled = False
            for entry in label_stats.values():
                if not isinstance(entry, dict):
                    continue
                count = entry.get("voxel_count", entry.get("num_of_pixels", 0)) or 0
                if count > 0:
                    any_labeled = True
                    break
            return "labeled" if any_labeled else "empty"

        if meta.get("modified_by") or meta.get("modified_at"):
            return "labeled"
        return ""

    def _fetch_label_meta(self, base_url, dataset_id, num):
        try:
            response = nnunet_service.get_label_meta(
                base_url, dataset_id, self.images_for, num
            )
            if response.get("exists") and isinstance(response.get("meta"), dict):
                return response["meta"]
        except Exception as e:
            print(f"Failed to fetch label meta for num={num}: {e}")
        return {}

    def _selected_case_has_label(self):
        number = self._selected_image_number()
        if number is None:
            return False
        return int(number) in self._label_nums

    def _update_action_buttons(self):
        has_selection = self._selected_image_number() is not None
        has_dataset = bool(self._dataset_id)

        self.download_image_button.setEnabled(has_selection and has_dataset)
        self.save_label_button.setEnabled(has_selection and has_dataset)
        self.delete_button.setEnabled(has_selection and has_dataset)
        self.properties_button.setEnabled(has_selection and has_dataset)
        self.append_button.setEnabled(has_dataset)
        self.renumber_button.setEnabled(has_dataset and self.table_widget.rowCount() > 0)

    def _open_meta_dialog(self, meta_kind=None, num=None):
        number = num if num is not None else self._selected_image_number()
        if number is None:
            QMessageBox.warning(self, "No Selection", "Please select an image first.")
            return
        if not self._dataset_id:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset first.")
            return

        dialog = CasePropertiesDialog(
            dataset_id=self._dataset_id,
            images_for=self.images_for,
            num=number,
            base_url=self._base_url or nnunet_server_url,
            parent=self,
        )
        dialog.exec_()
        if dialog.saved_label_meta is not None:
            self.update_label_meta_row(number, dialog.saved_label_meta)

    def set_dataset(self, dataset_id, image_list, base_url=None, label_list=None):
        self.table_widget.setRowCount(0)
        self._dataset_id = dataset_id
        self._base_url = base_url or nnunet_server_url

        self._label_nums = set()
        for label_item in (label_list or []):
            if isinstance(label_item, dict) and label_item.get("num") is not None:
                self._label_nums.add(int(label_item["num"]))

        items = list(image_list or [])
        total = len(items)
        meta_cache = {}
        for i, item in enumerate(items):
            filename = item["filename"]
            num = item.get("num")
            if num is None:
                num = extract_image_number(filename)
            num = int(num)

            if num not in meta_cache:
                qt_tools.update_busy_progress(
                    label=f"Loading {self.images_for} status {i + 1}/{total}..."
                )
                meta_cache[num] = self._fetch_label_meta(self._base_url, dataset_id, num)
            meta = meta_cache[num] or {}

            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)

            image_item = QTableWidgetItem(filename)
            image_item.setData(Qt.UserRole, num)
            image_item.setData(Qt.UserRole + 1, num in self._label_nums)
            image_item.setFlags(image_item.flags() & ~Qt.ItemIsEditable)
            self.table_widget.setItem(row, self.COLUMN_IMAGE, image_item)

            self._set_row_status_combo(row, num, self._derive_status(meta))

        self._update_action_buttons()

    def mark_label_exists(self, num):
        """Record that a label file now exists for this case and refresh button state."""
        self._label_nums.add(int(num))
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, self.COLUMN_IMAGE)
            if item is None:
                continue
            row_num = item.data(Qt.UserRole)
            if row_num is not None and int(row_num) == int(num):
                item.setData(Qt.UserRole + 1, True)
        self._update_action_buttons()

    def update_label_meta_row(self, num, meta):
        """Update the Status column for a case number."""
        meta = meta or {}
        status = self._derive_status(meta)
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, self.COLUMN_IMAGE)
            if item is None:
                continue
            row_num = item.data(Qt.UserRole)
            if row_num is None or int(row_num) != int(num):
                continue
            combo = self.table_widget.cellWidget(row, self.COLUMN_STATUS)
            if isinstance(combo, QComboBox):
                combo.blockSignals(True)
                if status and combo.findText(status) < 0:
                    combo.addItem(status)
                combo.setCurrentText(status)
                combo.setProperty("last_saved_status", status)
                combo.blockSignals(False)
            else:
                self._set_row_status_combo(row, int(num), status)

    def currentItem(self):
        row = self.table_widget.currentRow()
        if row < 0:
            return None
        return self.table_widget.item(row, self.COLUMN_IMAGE)

    def _selected_image_number(self):
        item = self.currentItem()
        if not item:
            return None
        num = item.data(Qt.UserRole)
        if num is not None:
            return int(num)
        return extract_image_number(item.text())

    def command_button_clicked(self):
        sender = self.sender()
        if sender == self.download_image_button:
            self.load_selected_case()
        elif sender == self.append_button:
            self.post_image_dataset()
        elif sender == self.save_label_button:
            self.update_image_dataset()
        elif sender == self.delete_button:
            self.delete_image_dataset()
        elif sender == self.properties_button:
            self._open_meta_dialog()
        elif sender == self.renumber_button:
            self.renumber_image_dataset()

    def load_selected_case(self):
        """Load selected case image and label (when available)."""
        number = self._selected_image_number()
        if number is None:
            print("No image selected.")
            return

        try:
            with qt_tools.busy_progress(
                self,
                title="Loading",
                label=f"Downloading image for case {number}...",
            ):
                out_dir = os.path.join("./_downloads", str(uuid.uuid4()))
                result = nnunet_service.download_dataset_image(
                    BASE_URL=self._base_url or nnunet_server_url,
                    dataset_id=self._dataset_id,
                    images_for=self.images_for,
                    num=number,
                    out_dir=out_dir,
                )
                print("Image download complete:", result)
                image_path = result["downloaded_base_image_path"]
                labels_path = ""

                if self._selected_case_has_label():
                    try:
                        qt_tools.update_busy_progress(
                            label=f"Downloading label for case {number}..."
                        )
                        label_result = nnunet_service.download_dataset_label(
                            BASE_URL=self._base_url or nnunet_server_url,
                            dataset_id=self._dataset_id,
                            images_for=self.images_for,
                            num=number,
                            out_dir=out_dir,
                        )
                        print("Label download complete:", label_result)
                        labels_path = label_result.get("downloaded_labels_image_path") or ""
                    except Exception as label_err:
                        print(f"Error downloading label for case {number}: {label_err}")
                        QMessageBox.warning(
                            self,
                            "Load Label Failed",
                            f"Image will still load, but label download failed:\n{label_err}",
                        )

                self._pending_load_window_level = None
                self._pending_load_case = {
                    "dataset_id": self._dataset_id,
                    "images_for": self.images_for,
                    "num": number,
                    "base_url": self._base_url or nnunet_server_url,
                }
                try:
                    qt_tools.update_busy_progress(label="Fetching image display settings...")
                    meta_response = nnunet_service.get_image_meta(
                        self._base_url or nnunet_server_url,
                        self._dataset_id,
                        self.images_for,
                        number,
                    )
                    meta = meta_response.get("meta") if isinstance(meta_response.get("meta"), dict) else {}
                    wl = meta.get("window_level")
                    if isinstance(wl, dict):
                        self._pending_load_window_level = wl
                except Exception as meta_err:
                    print(f"Could not fetch image meta for window/level: {meta_err}")

                qt_tools.update_busy_progress(label="Opening image in viewer...")
                self.image_dataset_downloaded.emit(image_path, labels_path, self)
        except Exception as e:
            print("Error loading case:", str(e))
            QMessageBox.critical(self, "Load Failed", str(e))

    def download_image_dataset(self):
        """Backward-compatible alias for Load. """
        self.load_selected_case()

    def download_label_dataset(self):
        """ Backward-compatible alias: Load now includes label when available. """
        self.load_selected_case()

    def get_image_dataset(self):
        """ Backward-compatible alias for Load. """
        self.load_selected_case()

    def post_image_dataset(self):
        self.post_dataset_clicked.emit(self._dataset_id, self.images_for, self)

    def update_image_dataset(self):
        number = self._selected_image_number()
        if number is None:
            print("No image selected.")
            return
        self.update_dataset_clicked.emit(self._dataset_id, self.images_for, number, self)

    def _set_row_status_combo(self, row, num, status):
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(LABEL_STATUS_OPTIONS)
        status = str(status or "")
        if status and combo.findText(status) < 0:
            combo.addItem(status)
        combo.setCurrentText(status)
        combo.setProperty("case_num", int(num))
        combo.setProperty("last_saved_status", status)
        combo.setToolTip("Change label status for this case")
        # Save on dropdown choice or when finished editing custom text (not every keystroke).
        combo.activated[str].connect(
            lambda text, n=int(num), c=combo: self._on_row_status_changed(n, text, c)
        )
        if combo.lineEdit() is not None:
            combo.lineEdit().editingFinished.connect(
                lambda n=int(num), c=combo: self._on_row_status_changed(n, c.currentText(), c)
            )
        self.table_widget.setCellWidget(row, self.COLUMN_STATUS, combo)

    def _on_row_status_changed(self, num, status_text, combo):
        if not self._dataset_id:
            return
        new_status = (status_text or "").strip()
        last_saved = str(combo.property("last_saved_status") or "")
        if new_status == last_saved:
            return
        try:
            with qt_tools.busy_progress(
                self,
                title="Saving Status",
                label=f"Updating status for case {num}...",
            ):
                response = nnunet_service.get_label_meta(
                    self._base_url or nnunet_server_url,
                    self._dataset_id,
                    self.images_for,
                    num,
                )
                meta = response.get("meta") if isinstance(response.get("meta"), dict) else {}
                meta = dict(meta)
                if new_status:
                    meta["status"] = new_status
                else:
                    meta.pop("status", None)
                result = nnunet_service.update_label_meta(
                    self._base_url or nnunet_server_url,
                    self._dataset_id,
                    self.images_for,
                    num,
                    meta,
                )
                saved = result.get("meta") if isinstance(result, dict) else meta
                if isinstance(saved, dict):
                    self.update_label_meta_row(num, saved)
                combo.setProperty("last_saved_status", new_status)
        except Exception as e:
            QMessageBox.critical(self, "Status Update Failed", str(e))
            try:
                meta = self._fetch_label_meta(
                    self._base_url or nnunet_server_url, self._dataset_id, num
                )
                self.update_label_meta_row(num, meta)
            except Exception:
                pass

    def delete_image_dataset(self, num=None):
        number = num if num is not None else self._selected_image_number()
        if number is None:
            print("No image selected.")
            return
        if not self._dataset_id:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset first.")
            return

        nl = chr(10)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            (
                f"Delete case {number} from dataset '{self._dataset_id}' ({self.images_for})?"
                + nl + nl
                + "This cannot be undone."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.delete_dataset_clicked.emit(self._dataset_id, self.images_for, number, self)

    def renumber_image_dataset(self):
        if not self._dataset_id:
            print("No dataset selected.")
            return
        self.renumber_dataset_clicked.emit(self._dataset_id, self.images_for, self)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = nnUnetImageDataSetListWidget(images_for='train')
    window.show()
    sys.exit(app.exec_())
