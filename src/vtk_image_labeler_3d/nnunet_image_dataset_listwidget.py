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


class MetaPropertiesDialog(QDialog):
    """Show image/label metadata and allow editing of client-owned fields."""

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

        title = "Image Properties" if meta_kind == "image" else "Label Properties"
        self.setWindowTitle(f"{title} ? case {num}")
        self.resize(620, 560)

        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>Dataset:</b> {dataset_id}<br>"
            f"<b>Split:</b> {images_for}<br>"
            f"<b>Case:</b> {num}"
        )
        layout.addWidget(info)

        edit_group = QGroupBox("Editable Fields")
        edit_form = QFormLayout(edit_group)

        self.status_combo = QComboBox()
        self.status_combo.setEditable(True)
        self.status_combo.addItems(LABEL_STATUS_OPTIONS)
        self.status_combo.setEnabled(meta_kind == "label")
        edit_form.addRow("Status:", self.status_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes?")
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
        wl_enabled = meta_kind == "image"
        self.window_spin.setEnabled(wl_enabled)
        self.level_spin.setEnabled(wl_enabled)
        if wl_enabled:
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Close
        )
        buttons.accepted.connect(self.save_meta)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_meta()

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

    def _load_meta(self):
        try:
            with qt_tools.busy_progress(
                self,
                title="Loading Properties",
                label=f"Fetching {self.meta_kind} metadata for case {self.num}...",
            ):
                response = self._fetch()
        except Exception as e:
            self.error_label.setText(f"Failed to load metadata: {e}")
            self._original_meta = {}
            self.auto_view.setPlainText("{}")
            return

        if response.get("error"):
            self.error_label.setText(
                f"Metadata file exists but could not be parsed/validated:\n{response.get('error')}"
            )

        meta = response.get("meta") if isinstance(response.get("meta"), dict) else {}
        self._original_meta = dict(meta)

        status = str(meta.get("status") or "")
        if status and self.status_combo.findText(status) < 0:
            self.status_combo.addItem(status)
        self.status_combo.setCurrentText(status)
        self.notes_edit.setPlainText(str(meta.get("notes") or ""))

        if self.meta_kind == "image" and hasattr(self, "window_spin"):
            wl = meta.get("window_level") if isinstance(meta.get("window_level"), dict) else {}
            window = wl.get("window", wl.get("width"))
            level = wl.get("level")
            if window is None:
                self.window_spin.setValue(0.0)
            else:
                self.window_spin.setValue(float(window))
            if level is None:
                self.level_spin.setValue(0.0)
            else:
                self.level_spin.setValue(float(level))

        auto_keys = self._auto_fields()
        reserved_editable = {"status", "notes", "window_level"}
        extras = {
            k: v for k, v in meta.items()
            if k not in auto_keys and k not in reserved_editable
        }
        self.extra_edit.setPlainText(
            json.dumps(extras, indent=2) if extras else ""
        )

        auto_only = {k: v for k, v in meta.items() if k in auto_keys}
        if not auto_only and not response.get("exists"):
            self.auto_view.setPlainText("(no metadata file yet)")
        else:
            self.auto_view.setPlainText(json.dumps(auto_only, indent=2))

    def _build_updated_meta(self):
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

        if self.meta_kind == "image" and hasattr(self, "window_spin"):
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

    def save_meta(self):
        try:
            meta = self._build_updated_meta()
            with qt_tools.busy_progress(
                self,
                title="Saving Properties",
                label=f"Saving {self.meta_kind} metadata for case {self.num}...",
            ):
                result = self._save(meta)
            saved = result.get("meta") if isinstance(result, dict) else meta
            if isinstance(saved, dict):
                self._original_meta = dict(saved)
            self.error_label.setText("")
            QMessageBox.information(
                self,
                "Saved",
                f"{self.meta_kind.capitalize()} metadata saved for case {self.num}.",
            )
            self.accept()
        except Exception as e:
            self.error_label.setText(str(e))
            QMessageBox.critical(self, "Save Failed", str(e))


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
        header.setSectionResizeMode(self.COLUMN_STATUS, QHeaderView.ResizeToContents)
        self.table_widget.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table_widget.itemSelectionChanged.connect(self._update_action_buttons)
        layout.addWidget(self.table_widget)

        self.list_widget = self.table_widget

        import flowlayout
        button_layout = flowlayout.FlowLayout()
        self.download_image_button = QPushButton("Load Image")
        self.download_label_button = QPushButton("Load Label")
        self.append_button = QPushButton("Append As New Image Set")
        self.save_label_button = QPushButton("Save Label")
        self.delete_button = QPushButton("Delete")
        self.image_properties_button = QPushButton("Image Properties")
        self.label_properties_button = QPushButton("Label Properties")
        self.renumber_button = QPushButton("Renumber Images")
        self.renumber_button.setToolTip(
            "Renumber cases to sequential 0..N-1 (required by nnU-Net after deletes)."
        )

        # Keep old attribute names used by older call sites/tests if any.
        self.get_button = self.download_image_button
        self.post_button = self.append_button
        self.update_button = self.save_label_button

        for btn in [
            self.download_image_button,
            self.download_label_button,
            self.append_button,
            self.save_label_button,
            self.delete_button,
            self.image_properties_button,
            self.label_properties_button,
            self.renumber_button,
        ]:
            btn.clicked.connect(self.command_button_clicked)
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle("Image Dataset List")
        self._update_action_buttons()

    def on_cell_double_clicked(self, row, column):
        self.download_image_dataset()

    def on_item_double_clicked(self, item):
        self.download_image_dataset()

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
        self.download_label_button.setEnabled(
            has_selection and has_dataset and self._selected_case_has_label()
        )
        self.save_label_button.setEnabled(has_selection and has_dataset)
        self.delete_button.setEnabled(has_selection and has_dataset)
        self.image_properties_button.setEnabled(has_selection and has_dataset)
        self.label_properties_button.setEnabled(has_selection and has_dataset)
        self.append_button.setEnabled(has_dataset)
        self.renumber_button.setEnabled(has_dataset and self.table_widget.rowCount() > 0)

    def _open_meta_dialog(self, meta_kind):
        number = self._selected_image_number()
        if number is None:
            QMessageBox.warning(self, "No Selection", "Please select an image first.")
            return
        if not self._dataset_id:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset first.")
            return

        dialog = MetaPropertiesDialog(
            meta_kind=meta_kind,
            dataset_id=self._dataset_id,
            images_for=self.images_for,
            num=number,
            base_url=self._base_url or nnunet_server_url,
            parent=self,
        )
        if dialog.exec_() == QDialog.Accepted and meta_kind == "label":
            self.update_label_meta_row(number, dialog._original_meta)

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

            status_item = QTableWidgetItem(self._derive_status(meta))
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            self.table_widget.setItem(row, self.COLUMN_STATUS, status_item)

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
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, self.COLUMN_IMAGE)
            if item is None:
                continue
            row_num = item.data(Qt.UserRole)
            if row_num is None or int(row_num) != int(num):
                continue
            status_item = self.table_widget.item(row, self.COLUMN_STATUS)
            if status_item is not None:
                status_item.setText(self._derive_status(meta))

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
            self.download_image_dataset()
        elif sender == self.download_label_button:
            self.download_label_dataset()
        elif sender == self.append_button:
            self.post_image_dataset()
        elif sender == self.save_label_button:
            self.update_image_dataset()
        elif sender == self.delete_button:
            self.delete_image_dataset()
        elif sender == self.image_properties_button:
            self._open_meta_dialog("image")
        elif sender == self.label_properties_button:
            self._open_meta_dialog("label")
        elif sender == self.renumber_button:
            self.renumber_image_dataset()

    def download_image_dataset(self):
        number = self._selected_image_number()
        if number is None:
            print("No image selected.")
            return

        try:
            with qt_tools.busy_progress(
                self,
                title="Loading Image",
                label=f"Downloading image for case {number}...",
            ):
                result = nnunet_service.download_dataset_image(
                    BASE_URL=self._base_url or nnunet_server_url,
                    dataset_id=self._dataset_id,
                    images_for=self.images_for,
                    num=number,
                    out_dir=os.path.join("./_downloads", str(uuid.uuid4())),
                )
                print("Image download complete:", result)
                image_path = result["downloaded_base_image_path"]

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
                self.image_dataset_downloaded.emit(image_path, "", self)
        except Exception as e:
            print("Error downloading image:", str(e))
            QMessageBox.critical(self, "Load Image Failed", str(e))

    def download_label_dataset(self):
        number = self._selected_image_number()
        if number is None:
            print("No image selected.")
            return
        if not self._selected_case_has_label():
            QMessageBox.warning(
                self,
                "No Label",
                f"Case {number} does not have a label file on the server.",
            )
            return

        try:
            with qt_tools.busy_progress(
                self,
                title="Loading Label",
                label=f"Downloading label for case {number}...",
            ):
                result = nnunet_service.download_dataset_label(
                    BASE_URL=self._base_url or nnunet_server_url,
                    dataset_id=self._dataset_id,
                    images_for=self.images_for,
                    num=number,
                    out_dir=os.path.join("./_downloads", str(uuid.uuid4())),
                )
                print("Label download complete:", result)
                labels_path = result["downloaded_labels_image_path"]
                qt_tools.update_busy_progress(label="Applying label layers...")
                self.label_dataset_downloaded.emit(labels_path, self)
        except Exception as e:
            print("Error downloading label:", str(e))
            QMessageBox.critical(self, "Load Label Failed", str(e))

    def get_image_dataset(self):
        """Backward-compatible alias for Download Image. """
        self.download_image_dataset()

    def post_image_dataset(self):
        self.post_dataset_clicked.emit(self._dataset_id, self.images_for, self)

    def update_image_dataset(self):
        number = self._selected_image_number()
        if number is None:
            print("No image selected.")
            return
        self.update_dataset_clicked.emit(self._dataset_id, self.images_for, number, self)

    def delete_image_dataset(self):
        number = self._selected_image_number()
        if number is None:
            print("No image selected.")
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
