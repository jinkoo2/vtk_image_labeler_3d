"""nnU-Net Prediction Tool dialog: run approved models on the currently open case."""

from __future__ import annotations

import os
import tempfile
import time
import uuid
from urllib.parse import urlsplit

from PyQt5.QtCore import Qt, QSettings, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import nnunet_service
import qt_tools
from config import get_nnunet_server_url, get_nnunet_server_urls

_PREDICTION_TOOL_SETTINGS_GROUP = "nnunet_prediction_tool"
_NEXT_AVAILABLE_SERVER = "Next Available Server"


def _unique_layer_name(segmentation_layers, base_name: str) -> str:
    """Return base_name, or base_name_2 / _3 / ... if already taken."""
    base = (base_name or "Label").strip() or "Label"
    if segmentation_layers.get_layer_by_name(base) is None:
        return base
    index = 2
    while segmentation_layers.get_layer_by_name(f"{base}_{index}") is not None:
        index += 1
    return f"{base}_{index}"


def _channel_count_from_dataset_json(dataset_json: dict) -> int:
    names = _channel_names_from_dataset_json(dataset_json)
    return max(1, len(names)) if names else 1


def _channel_names_from_dataset_json(dataset_json: dict) -> list:
    """Return ordered channel/modality names from dataset_json."""
    if not isinstance(dataset_json, dict):
        return []
    channel_names = dataset_json.get("channel_names") or dataset_json.get("modality") or {}
    if isinstance(channel_names, dict) and channel_names:
        def _sort_key(key):
            try:
                return (0, int(key))
            except (TypeError, ValueError):
                return (1, str(key))

        return [str(channel_names[k]) for k in sorted(channel_names.keys(), key=_sort_key)]
    if isinstance(channel_names, (list, tuple)) and channel_names:
        return [str(name) for name in channel_names]
    return []


def _format_channel_names(channel_names) -> str:
    """Format channel names for UI, e.g. ``[CT]`` or ``[CT, MR]``."""
    names = [str(n).strip() for n in (channel_names or []) if str(n).strip()]
    if not names:
        return "-"
    return "[" + ", ".join(names) + "]"


def _labels_from_dataset_json(dataset_json: dict) -> dict:
    if not isinstance(dataset_json, dict):
        return {}
    labels = dataset_json.get("labels") or {}
    return labels if isinstance(labels, dict) else {}


def _importable_label_items(labels_map) -> list:
    """Return ``[(name, int_value), ...]`` excluding background (value <= 0)."""
    items = []
    for name, value in (labels_map or {}).items():
        try:
            iv = int(value)
        except (TypeError, ValueError):
            continue
        if iv <= 0:
            continue
        items.append((str(name), iv))
    items.sort(key=lambda pair: (pair[1], pair[0].lower()))
    return items


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _short_host(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    return parsed.netloc or str(url or "?")


def _prediction_tool_qsettings() -> QSettings:
    return QSettings("_settings.conf", QSettings.IniFormat)


def _load_persisted_prediction_prefs():
    """Return ``(filter_text, preferred_model_dict_or_None)``."""
    settings = _prediction_tool_qsettings()
    settings.beginGroup(_PREDICTION_TOOL_SETTINGS_GROUP)
    filter_text = str(settings.value("filter", "") or "")
    dataset_id = str(settings.value("model_dataset_id", "") or "").strip()
    trainer = str(settings.value("model_trainer", "") or "").strip()
    plans = str(settings.value("model_plans", "") or "").strip()
    configuration = str(settings.value("model_configuration", "") or "").strip()
    settings.endGroup()
    preferred = None
    if dataset_id:
        preferred = {
            "dataset_id": dataset_id,
            "trainer": trainer or None,
            "plans": plans or None,
            "configuration": configuration or None,
        }
    return filter_text, preferred


class NnUNetPredictionToolDialog(QDialog):
    """Floating tool to run approved nnU-Net models on the open image set."""

    def __init__(self, segmentation_list_manager, get_context_fn, parent=None):
        super().__init__(parent)
        self.segmentation_list_manager = segmentation_list_manager
        self.get_context_fn = get_context_fn

        self._models = []
        self._model_detail = None
        self._jobs = {}  # uid -> job dict
        self._job_seq = 0
        self._allow_close = False
        self._restoring_prefs = False
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_all_jobs)
        self._filter_debounce_timer = QTimer(self)
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.setInterval(300)
        self._filter_debounce_timer.timeout.connect(self._apply_model_filter)

        persisted_filter, self._preferred_model = _load_persisted_prediction_prefs()

        self.setWindowTitle("nnUNet Prediction Tool")
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(520, 620)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.model_filter_edit = QLineEdit()
        self.model_filter_edit.setPlaceholderText(
            "Filter by organ, configuration, description, model name…"
        )
        self.model_filter_edit.setClearButtonEnabled(True)
        self.model_filter_edit.setToolTip(
            "Case-insensitive filter over model fields "
            "(dataset, configuration, trainer, plans, description, name, organ, etc.)."
        )
        if persisted_filter:
            self.model_filter_edit.setText(persisted_filter)
        self.model_filter_edit.textChanged.connect(self._on_model_filter_changed)
        form.addRow("Filter:", self.model_filter_edit)

        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Approved prediction models from the nnU-Net server")
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)

        self.model_docs_button = QPushButton("Model Info")
        self.model_docs_button.setToolTip(
            "Open this model's documentation (expected input, output labels, training dataset)"
        )
        self.model_docs_button.setEnabled(False)
        self.model_docs_button.clicked.connect(self._open_model_docs)

        model_row = QHBoxLayout()
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.model_docs_button)
        form.addRow("Model:", model_row)

        self.input_dataset_label = QLabel("-")
        self.input_dataset_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Input Dataset:", self.input_dataset_label)

        self.input_case_label = QLabel("-")
        self.input_case_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Input Image Set:", self.input_case_label)

        self.channels_label = QLabel("-")
        form.addRow("Model Channels:", self.channels_label)

        labels_panel = QWidget()
        labels_layout = QVBoxLayout(labels_panel)
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.setSpacing(4)

        labels_btn_row = QHBoxLayout()
        self.select_all_labels_button = QPushButton("Select All")
        self.select_all_labels_button.setToolTip("Check all labels for import")
        self.select_all_labels_button.clicked.connect(self._select_all_import_labels)
        self.clear_all_labels_button = QPushButton("Clear All")
        self.clear_all_labels_button.setToolTip("Uncheck all labels")
        self.clear_all_labels_button.clicked.connect(self._clear_all_import_labels)
        labels_btn_row.addWidget(self.select_all_labels_button)
        labels_btn_row.addWidget(self.clear_all_labels_button)
        labels_btn_row.addStretch(1)
        labels_layout.addLayout(labels_btn_row)

        self.import_labels_list = QListWidget()
        self.import_labels_list.setToolTip(
            "Checked labels will be imported into segmentation layers after prediction."
        )
        self.import_labels_list.setMinimumHeight(120)
        self.import_labels_list.setMaximumHeight(200)
        self.import_labels_list.setSelectionMode(QListWidget.NoSelection)
        labels_layout.addWidget(self.import_labels_list)

        form.addRow("Labels to Import:", labels_panel)
        layout.addLayout(form)

        layout.addWidget(QLabel("Status:"))
        self.status_tabs = QTabWidget()
        self.status_tabs.setTabsClosable(False)
        self.general_status_view = QTextEdit()
        self.general_status_view.setReadOnly(True)
        self.general_status_view.setPlaceholderText(
            "General messages and load-balancing notes appear here. "
            "Each Run Auto Segment adds a job tab."
        )
        self.status_tabs.addTab(self.general_status_view, "General")
        layout.addWidget(self.status_tabs, 1)

        btn_row = QHBoxLayout()
        self.run_button = QPushButton("Run Auto Segment")
        self.run_button.clicked.connect(self._on_run_clicked)
        self.prediction_server_combo = QComboBox()
        self.prediction_server_combo.setMinimumWidth(220)
        self.prediction_server_combo.setToolTip(
            "Where to run the prediction.\n"
            f"“{_NEXT_AVAILABLE_SERVER}” load-balances among configured servers "
            "that have the selected model.\n"
            "Pick a specific server to send the job there."
        )
        self._reload_prediction_server_combo()
        btn_row.addWidget(self.run_button)
        btn_row.addWidget(QLabel("Server:"))
        btn_row.addWidget(self.prediction_server_combo, 1)
        self.hide_button = QPushButton("Hide")
        self.hide_button.setToolTip("Hide this tool; prediction jobs keep running.")
        self.hide_button.clicked.connect(self._on_hide_clicked)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setToolTip(
            "Cancel all active prediction jobs on their servers and close this tool."
        )
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        btn_row.addStretch(1)
        btn_row.addWidget(self.hide_button)
        btn_row.addWidget(self.cancel_button)
        layout.addLayout(btn_row)

        self._refresh_context_labels()
        self._load_approved_models()

    def showEvent(self, event):
        super().showEvent(event)
        self._reload_prediction_server_combo()
        self._refresh_context_labels()

    def closeEvent(self, event):
        # Window X behaves like Hide so background jobs keep running,
        # unless Cancel explicitly allows a real close.
        self._flush_pending_model_filter()
        self._persist_prediction_prefs()
        if self._allow_close:
            self._poll_timer.stop()
            event.accept()
            return
        event.ignore()
        self.hide()

    def _on_hide_clicked(self):
        self._flush_pending_model_filter()
        self._persist_prediction_prefs()
        self.hide()

    def _flush_pending_model_filter(self):
        if self._filter_debounce_timer.isActive():
            self._filter_debounce_timer.stop()
            self._apply_model_filter()

    def _persist_prediction_prefs(self):
        """Save filter text and selected model identity to ``_settings.conf``."""
        if self._restoring_prefs:
            return
        try:
            settings = _prediction_tool_qsettings()
            settings.beginGroup(_PREDICTION_TOOL_SETTINGS_GROUP)
            settings.setValue("filter", self.model_filter_edit.text() or "")
            model = self._selected_model()
            if isinstance(model, dict) and model.get("dataset_id"):
                settings.setValue("model_dataset_id", model.get("dataset_id") or "")
                settings.setValue("model_trainer", model.get("trainer") or "")
                settings.setValue("model_plans", model.get("plans") or "")
                settings.setValue("model_configuration", model.get("configuration") or "")
                self._preferred_model = {
                    "dataset_id": model.get("dataset_id"),
                    "trainer": model.get("trainer"),
                    "plans": model.get("plans"),
                    "configuration": model.get("configuration"),
                }
            settings.endGroup()
            settings.sync()
        except Exception as e:
            print(f"Failed to persist prediction-tool prefs: {e}")

    def _append_general(self, msg: str):
        self.general_status_view.append(msg)
        sb = self.general_status_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _append_job(self, job, msg: str):
        view = job.get("status_view") if isinstance(job, dict) else None
        if view is None:
            self._append_general(msg)
            return
        view.append(msg)
        sb = view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_status(self, msg: str):
        """Replace General tab text (used when loading models)."""
        self.general_status_view.setPlainText(msg)

    def _append_status(self, msg: str):
        """Compatibility helper: general log."""
        self._append_general(msg)

    def _context(self):
        if not callable(self.get_context_fn):
            return {}
        try:
            ctx = self.get_context_fn() or {}
            return ctx if isinstance(ctx, dict) else {}
        except Exception as e:
            self._append_general(f"Context error: {e}")
            return {}

    def _refresh_context_labels(self):
        ctx = self._context()
        case = ctx.get("case") or {}
        dataset = ctx.get("dataset") or {}
        dataset_id = case.get("dataset_id") or dataset.get("id") or "-"
        images_for = case.get("images_for") or "-"
        num = case.get("num")
        case_txt = f"{images_for} / case {num}" if num is not None else "-"
        self.input_dataset_label.setText(str(dataset_id))
        self.input_case_label.setText(case_txt)

        has_image = self.segmentation_list_manager.get_base_vtk_image() is not None
        has_server = bool(ctx.get("server_url"))
        self.run_button.setEnabled(
            bool(
                has_image
                and has_server
                and self.model_combo.count() > 0
                and self._selected_model()
            )
        )

    def _model_license_tag(self, model: dict) -> str:
        license_ = model.get("license")
        if not license_:
            return ""
        if model.get("required_scope"):
            return " [research-only]"
        return " [open license]"

    def _model_tooltip(self, model: dict) -> str:
        license_ = model.get("license")
        if not license_:
            return "No external license — locally trained model."
        lines = [f"License: {license_}"]
        scope = model.get("required_scope")
        if scope:
            lines.append(f"Requires the '{scope}' scope/role on your account.")
        return "\n".join(lines)

    def _model_display_name(self, model: dict) -> str:
        dataset = (
            model.get("dataset_id")
            or model.get("dataset")
            or model.get("name")
            or model.get("model_name")
            or model.get("folder")
            or "?"
        )
        config = model.get("configuration") or model.get("config") or "?"
        trainer = model.get("trainer") or "?"
        return (
            f"{dataset} | {config} | {trainer}"
            f"{self._model_license_tag(model)}"
        )

    def _model_search_text(self, model: dict) -> str:
        def _collect(obj, depth=0):
            if depth > 5:
                return
            if isinstance(obj, str):
                yield obj
            elif isinstance(obj, dict):
                for v in obj.values():
                    yield from _collect(v, depth + 1)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    yield from _collect(v, depth + 1)

        return " ".join(_collect(model))

    def _filtered_models(self):
        query = (self.model_filter_edit.text() or "").strip().lower()
        if not query:
            return list(self._models)
        return [m for m in self._models if query in self._model_search_text(m).lower()]

    def _populate_model_combo(self, preferred_model=None):
        previous = (
            preferred_model
            if isinstance(preferred_model, dict)
            else (self._preferred_model if isinstance(self._preferred_model, dict) else None)
        )
        if previous is None:
            previous = self._selected_model()
        self._restoring_prefs = True
        self.model_combo.blockSignals(True)
        try:
            self.model_combo.clear()
            filtered = self._filtered_models()
            if not self._models:
                self.model_combo.addItem("(no approved models)")
            elif not filtered:
                self.model_combo.addItem("(no matching models)")
            else:
                select_index = 0
                for i, m in enumerate(filtered):
                    self.model_combo.addItem(self._model_display_name(m), m)
                    idx = self.model_combo.count() - 1
                    self.model_combo.setItemData(idx, self._model_tooltip(m), Qt.ToolTipRole)
                    if previous and (
                        previous.get("dataset_id") == m.get("dataset_id")
                        and (
                            not previous.get("trainer")
                            or previous.get("trainer") == m.get("trainer")
                        )
                        and (
                            not previous.get("plans")
                            or previous.get("plans") == m.get("plans")
                        )
                        and (
                            not previous.get("configuration")
                            or previous.get("configuration") == m.get("configuration")
                        )
                    ):
                        select_index = i
                self.model_combo.setCurrentIndex(select_index)
        finally:
            self.model_combo.blockSignals(False)
            self._restoring_prefs = False

        selected = self._selected_model()
        same_as_previous = bool(
            previous
            and selected
            and previous.get("dataset_id") == selected.get("dataset_id")
            and (
                not previous.get("trainer")
                or previous.get("trainer") == selected.get("trainer")
            )
            and (
                not previous.get("plans")
                or previous.get("plans") == selected.get("plans")
            )
            and (
                not previous.get("configuration")
                or previous.get("configuration") == selected.get("configuration")
            )
        )
        if selected and not same_as_previous:
            self._on_model_changed(self.model_combo.currentIndex())
        elif not selected:
            self._model_detail = None
            self.model_docs_button.setEnabled(False)
            self.channels_label.setText("-")
            self._clear_import_labels_list()
        else:
            # Restored selection: still refresh detail/labels once if needed.
            if self._model_detail is None:
                self._on_model_changed(self.model_combo.currentIndex())
            else:
                self.model_docs_button.setEnabled(
                    bool(selected.get("docs_url") or (self._model_detail or {}).get("docs_url"))
                )
        self._refresh_context_labels()
        self._persist_prediction_prefs()

    def _on_model_filter_changed(self, _text: str = ""):
        # Debounce so filtering/persist wait until typing pauses.
        self._filter_debounce_timer.start()

    def _apply_model_filter(self):
        self._persist_prediction_prefs()
        if not self._models:
            return
        self._populate_model_combo()

    def _load_approved_models(self):
        self._models = []
        ctx = self._context()
        base_url = ctx.get("server_url")
        if not base_url:
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.addItem("(no server)")
            self.model_combo.blockSignals(False)
            self._set_status("No nnU-Net server URL available. Connect to the server first.")
            self._refresh_context_labels()
            return

        try:
            with qt_tools.busy_progress(
                self,
                title="Loading Models",
                label="Fetching approved prediction models...",
            ):
                models = nnunet_service.get_approved_models(base_url)
            self._models = models or []
            self._populate_model_combo()
            query = (self.model_filter_edit.text() or "").strip()
            matched = len(self._filtered_models())
            if not self._models:
                self._set_status("No approved models found on the server.")
            elif query:
                self._set_status(
                    f"Loaded {len(self._models)} approved model(s); "
                    f"showing {matched} matching “{query}”."
                )
            else:
                self._set_status(f"Loaded {len(self._models)} approved model(s).")
        except Exception as e:
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.addItem("(failed to load models)")
            self.model_combo.blockSignals(False)
            self._set_status(f"Failed to load approved models:\n{e}")
            self._refresh_context_labels()

    def _selected_model(self):
        data = self.model_combo.currentData()
        return data if isinstance(data, dict) else None

    def _open_model_docs(self):
        model = self._selected_model()
        if not model:
            return
        docs_url = (self._model_detail or {}).get("docs_url") or model.get("docs_url")
        if not docs_url:
            return
        ctx = self._context()
        base_url = ctx.get("server_url") or ""
        parsed = urlsplit(base_url)
        host_root = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        QDesktopServices.openUrl(QUrl(host_root + docs_url))

    def _clear_import_labels_list(self):
        self.import_labels_list.clear()
        self.select_all_labels_button.setEnabled(False)
        self.clear_all_labels_button.setEnabled(False)

    def _populate_import_labels_list(self, labels_map, checked=True):
        self.import_labels_list.clear()
        items = _importable_label_items(labels_map)
        state = Qt.Checked if checked else Qt.Unchecked
        for name, value in items:
            item = QListWidgetItem(f"{name}  (class {value})")
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            item.setCheckState(state)
            item.setData(Qt.UserRole, {"name": name, "value": value})
            self.import_labels_list.addItem(item)
        enabled = bool(items)
        self.select_all_labels_button.setEnabled(enabled)
        self.clear_all_labels_button.setEnabled(enabled)

    def _set_all_import_labels_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.import_labels_list.count()):
            self.import_labels_list.item(i).setCheckState(state)

    def _select_all_import_labels(self):
        self._set_all_import_labels_checked(True)

    def _clear_all_import_labels(self):
        self._set_all_import_labels_checked(False)

    def _checked_import_labels(self) -> dict:
        selected = {}
        for i in range(self.import_labels_list.count()):
            item = self.import_labels_list.item(i)
            if item.checkState() != Qt.Checked:
                continue
            data = item.data(Qt.UserRole) or {}
            name = data.get("name")
            value = data.get("value")
            if name is None or value is None:
                continue
            selected[str(name)] = int(value)
        return selected

    def _on_model_changed(self, index):
        model = self._selected_model()
        self._model_detail = None
        self.model_docs_button.setEnabled(bool(model and model.get("docs_url")))
        if not model:
            self.channels_label.setText("-")
            self._clear_import_labels_list()
            self._refresh_context_labels()
            return

        ctx = self._context()
        base_url = ctx.get("server_url")
        if not base_url:
            return

        try:
            with qt_tools.busy_progress(
                self,
                title="Model Detail",
                label="Fetching model channel/label info...",
            ):
                detail = nnunet_service.get_model_detail(
                    base_url,
                    model["dataset_id"],
                    model["trainer"],
                    model["plans"],
                    model["configuration"],
                )
            self._model_detail = detail
            dataset_json = detail.get("dataset_json") if isinstance(detail, dict) else {}
            channel_names = _channel_names_from_dataset_json(dataset_json or {})
            n_ch = max(1, len(channel_names)) if channel_names else 1
            labels = _labels_from_dataset_json(dataset_json or {})
            importable = _importable_label_items(labels)
            self.channels_label.setText(_format_channel_names(channel_names))
            self._populate_import_labels_list(labels, checked=True)
            self._append_general(
                f"Selected model channels: {_format_channel_names(channel_names)} "
                f"({n_ch}). Labels to import: {len(importable)}"
            )
        except Exception as e:
            self.channels_label.setText("?")
            self._clear_import_labels_list()
            self._append_general(f"Failed to fetch model detail: {e}")
        self._refresh_context_labels()
        self._persist_prediction_prefs()

    def _create_job_tab(self, title: str):
        view = QTextEdit()
        view.setReadOnly(True)
        index = self.status_tabs.addTab(view, title)
        self.status_tabs.setCurrentIndex(index)
        return view

    def _set_job_tab_title(self, job, title: str):
        view = job.get("status_view")
        if view is None:
            return
        idx = self.status_tabs.indexOf(view)
        if idx >= 0:
            self.status_tabs.setTabText(idx, title)

    def _active_jobs(self):
        return [
            j
            for j in self._jobs.values()
            if j.get("state") in ("preparing", "queued", "running", "importing")
        ]

    def _ensure_poll_timer(self):
        if self._active_jobs():
            if not self._poll_timer.isActive():
                self._poll_timer.start()
        else:
            self._poll_timer.stop()

    def _reload_prediction_server_combo(self):
        """Fill Server combo from settings; keep prior selection when possible."""
        combo = getattr(self, "prediction_server_combo", None)
        if combo is None:
            return
        previous = combo.currentData()
        urls = list(get_nnunet_server_urls() or [])
        preferred = get_nnunet_server_url()
        if preferred and preferred not in urls:
            urls = [preferred] + urls

        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItem(_NEXT_AVAILABLE_SERVER, None)
            for url in urls:
                host = _short_host(url)
                label = f"{host}  ({url})" if host and host != url else str(url)
                combo.addItem(label, url)

            select_index = 0
            if previous:
                idx = combo.findData(previous)
                if idx >= 0:
                    select_index = idx
            combo.setCurrentIndex(select_index)
        finally:
            combo.blockSignals(False)

    def _selected_prediction_server_url(self):
        """Return explicit server URL, or None for Next Available Server."""
        combo = getattr(self, "prediction_server_combo", None)
        if combo is None:
            return None
        data = combo.currentData()
        return str(data).strip() if data else None

    def _pick_prediction_server(self, model, log_fn):
        """Choose a prediction server: explicit pick, or least-loaded available."""
        forced_url = self._selected_prediction_server_url()
        if forced_url:
            return self._validate_prediction_server(forced_url, model, log_fn)

        urls = get_nnunet_server_urls()
        preferred = get_nnunet_server_url()
        if preferred and preferred not in urls:
            urls = [preferred] + list(urls)

        candidates = []
        for url in urls:
            host = _short_host(url)
            try:
                load = self._probe_prediction_server(url, model, log_fn)
            except Exception as e:
                log_fn(f"Skip {host}: {e}")
                continue
            if load is None:
                continue
            jobs_ahead = load.get("jobs_ahead")
            wait = load.get("estimated_wait_seconds")
            try:
                jobs_ahead_n = float(jobs_ahead) if jobs_ahead is not None else 1e9
            except (TypeError, ValueError):
                jobs_ahead_n = 1e9
            try:
                wait_n = float(wait) if wait is not None else jobs_ahead_n
            except (TypeError, ValueError):
                wait_n = jobs_ahead_n
            candidates.append((wait_n, jobs_ahead_n, url, load))

        if not candidates:
            raise RuntimeError(
                "No configured server both has the selected model and reported queue load."
            )

        candidates.sort(key=lambda row: (row[0], row[1], row[2]))
        chosen = candidates[0][2]
        log_fn(f"Selected prediction server (next available): {_short_host(chosen)}")
        return chosen

    def _validate_prediction_server(self, url, model, log_fn):
        """Ensure a user-picked server can run the selected model."""
        host = _short_host(url)
        log_fn(f"Using selected prediction server: {host}")
        load = self._probe_prediction_server(url, model, log_fn, require_inferencing=True)
        if load is None:
            raise RuntimeError(
                f"Selected server {_short_host(url)} cannot run this model "
                "(missing model, inferencing disabled, or queue load unavailable)."
            )
        return url

    def _probe_prediction_server(self, url, model, log_fn, require_inferencing=True):
        """
        Return queue-load dict if the server has the model and can accept jobs.
        Returns None when the server should be skipped (and logs the reason).
        """
        host = _short_host(url)
        try:
            if not nnunet_service.server_has_approved_model(url, model):
                log_fn(f"Skip {host}: selected model not available.")
                return None
        except Exception as e:
            log_fn(f"Skip {host}: could not list approved models ({e}).")
            return None

        try:
            load = nnunet_service.get_prediction_queue_load(
                url,
                dataset_id=model.get("dataset_id"),
                configuration=model.get("configuration"),
            )
        except Exception as e:
            log_fn(f"Skip {host}: /predictions/load failed ({e}).")
            return None

        jobs_ahead = load.get("jobs_ahead")
        wait = load.get("estimated_wait_seconds")
        inferencing = load.get("inferencing_enabled", True)
        log_fn(
            f"{host}: model OK, jobs_ahead={jobs_ahead}, "
            f"estimated_wait_s={wait}, inferencing_enabled={inferencing}"
        )
        if require_inferencing and inferencing is False:
            log_fn(f"Skip {host}: inferencing disabled.")
            return None
        return load

    def _download_case_channels(self, base_url, case, num_channels, out_dir, log_fn):
        paths = []
        for ch in range(num_channels):
            log_fn(f"Downloading input channel {ch}/{max(num_channels - 1, 0)}...")
            QApplication.processEvents()
            result = nnunet_service.download_dataset_image(
                BASE_URL=base_url,
                dataset_id=case["dataset_id"],
                images_for=case["images_for"],
                num=case["num"],
                out_dir=out_dir,
                ch_number=ch,
            )
            path = result.get("downloaded_base_image_path")
            if not path or not os.path.exists(path):
                raise RuntimeError(f"Failed to download channel {ch} for case {case['num']}.")
            paths.append(path)
            log_fn(f"Downloaded channel {ch}: {os.path.basename(path)}")
            QApplication.processEvents()
        return paths

    def _export_viewer_volume(self, out_dir, log_fn):
        """Write the in-memory viewer volume to a temp .mha for prediction upload."""
        vtk_image = self.segmentation_list_manager.get_base_vtk_image()
        if vtk_image is None:
            raise RuntimeError("No image is loaded in the viewer.")
        from itkvtk import save_vtk_image_using_sitk

        path = os.path.join(out_dir, "viewer_channel_0.mha")
        log_fn("Exporting in-memory viewer volume...")
        QApplication.processEvents()
        save_vtk_image_using_sitk(vtk_image, path)
        if not os.path.exists(path):
            raise RuntimeError("Failed to export the viewer volume.")
        log_fn(f"Exported viewer volume: {os.path.basename(path)}")
        return path

    def _on_run_clicked(self):
        ctx = self._context()
        case_base_url = ctx.get("server_url")
        case = ctx.get("case") or {}
        model = self._selected_model()

        if self.segmentation_list_manager.get_base_vtk_image() is None:
            QMessageBox.warning(self, "No Image", "Open an image in the viewer first.")
            return
        if not case_base_url:
            QMessageBox.warning(self, "No Server", "Connect to the nnU-Net server first.")
            return
        if not model:
            QMessageBox.warning(self, "No Model", "Select an approved prediction model.")
            return

        dataset_json = {}
        if isinstance(self._model_detail, dict):
            dataset_json = self._model_detail.get("dataset_json") or {}
        num_channels = _channel_count_from_dataset_json(dataset_json)
        all_labels = _labels_from_dataset_json(dataset_json)
        selected_labels = self._checked_import_labels()

        if self.import_labels_list.count() > 0 and not selected_labels:
            QMessageBox.warning(
                self,
                "No Labels Selected",
                "Select at least one label to import into segmentation layers.",
            )
            return

        has_case = case.get("dataset_id") is not None and case.get("num") is not None
        use_downloaded_case = False
        if num_channels > 1:
            if not has_case:
                QMessageBox.warning(
                    self,
                    "Multi-Channel Model",
                    f"This model requires {num_channels} input channels, but the viewer "
                    "holds only one image.\n\n"
                    "Load a case from the Train/Test list so the full image set can be "
                    "downloaded from the server.",
                )
                return
            reply = QMessageBox.question(
                self,
                "Download Case Image Set?",
                f"This model requires {num_channels} input channels, but the viewer "
                "holds only one image.\n\n"
                f"Download the full case image set "
                f"({case.get('images_for')} / case {case.get('num')}) from the "
                "logged-on server and use it for prediction?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return
            use_downloaded_case = True

        labels = selected_labels if selected_labels else all_labels

        self._job_seq += 1
        job_uid = uuid.uuid4().hex
        model_label = (
            model.get("dataset_id")
            or model.get("name")
            or model.get("model_name")
            or f"Job {self._job_seq}"
        )
        tab_title = f"#{self._job_seq} {model_label}"
        status_view = self._create_job_tab(tab_title)

        job = {
            "uid": job_uid,
            "seq": self._job_seq,
            "tab_title": tab_title,
            "status_view": status_view,
            "state": "preparing",
            "job_id": None,
            "req_id": None,
            "base_url": None,
            "case_base_url": case_base_url,
            "model_dataset_id": model.get("dataset_id"),
            "labels": labels,
            "out_dir": None,
            "submitted_at": time.monotonic(),
            "model": dict(model),
        }
        self._jobs[job_uid] = job

        def log(msg):
            self._append_job(job, msg)

        log(
            f"Will import "
            f"{len(selected_labels) if selected_labels else len(_importable_label_items(labels))} "
            f"label layer(s) after prediction."
        )
        QApplication.processEvents()

        out_dir = os.path.join(tempfile.gettempdir(), f"nnunet_pred_{job_uid}")
        os.makedirs(out_dir, exist_ok=True)
        job["out_dir"] = out_dir

        try:
            if self._selected_prediction_server_url():
                log("Validating selected prediction server...")
            else:
                log("Choosing next available prediction server (model + queue load)...")
            QApplication.processEvents()
            predict_url = self._pick_prediction_server(model, log)

            if use_downloaded_case:
                log(
                    f"Downloading {num_channels} input channels for case {case['num']} "
                    f"from {_short_host(case_base_url)}..."
                )
                QApplication.processEvents()
                channel_paths = self._download_case_channels(
                    case_base_url, case, num_channels, out_dir, log
                )
                image_id = f"{case['dataset_id']}_{case['images_for']}_{case['num']}"
            else:
                channel_paths = [self._export_viewer_volume(out_dir, log)]
                if has_case:
                    image_id = f"{case['dataset_id']}_{case['images_for']}_{case['num']}"
                else:
                    image_id = f"viewer_{job_uid}"

            log(f"Submitting prediction to {_short_host(predict_url)}...")
            QApplication.processEvents()
            submit = nnunet_service.post_prediction(
                BASE_URL=predict_url,
                model_dataset_id=model["dataset_id"],
                image_id=image_id,
                channel_image_paths=channel_paths,
                trainer=model.get("trainer", "nnUNetTrainer"),
                plans=model.get("plans", "nnUNetPlans"),
                configuration=model.get("configuration", "3d_lowres"),
            )
        except Exception as e:
            job["state"] = "failed"
            self._set_job_tab_title(job, f"{tab_title} ✕")
            log(f"Submit failed: {e}")
            self._ensure_poll_timer()
            return

        job_id = submit.get("job_id")
        req_id = submit.get("req_id")
        if not job_id or not req_id:
            job["state"] = "failed"
            self._set_job_tab_title(job, f"{tab_title} ✕")
            log(f"Submit failed: unexpected response (missing job_id/req_id): {submit}")
            self._ensure_poll_timer()
            return

        job["job_id"] = job_id
        job["req_id"] = req_id
        job["base_url"] = predict_url
        job["state"] = "queued"
        job["submitted_at"] = time.monotonic()
        ahead = submit.get("number_of_jobs_ahead", "?")
        log(
            f"Job queued on {_short_host(predict_url)}. "
            f"req_id={req_id}, job_id={job_id}, jobs ahead={ahead}"
        )
        self._ensure_poll_timer()

    def _poll_all_jobs(self):
        active = self._active_jobs()
        if not active:
            self._poll_timer.stop()
            return

        for job in list(active):
            if job.get("state") not in ("queued", "running"):
                continue
            if not job.get("job_id") or not job.get("base_url"):
                continue
            try:
                status = nnunet_service.get_prediction_job_status(
                    job["base_url"], job["job_id"]
                )
            except Exception as e:
                self._append_job(job, f"Status check failed: {e}")
                continue

            state = str(status.get("status", "")).lower()
            progress = status.get("progress", "")
            ahead = status.get("number_of_jobs_ahead", "")
            self._append_job(
                job, f"Status: {state}  progress={progress}  ahead={ahead}"
            )

            if state in ("finished", "completed", "success"):
                job["state"] = "importing"
                self._on_job_finished(job)
            elif state in ("failed", "stopped", "canceled", "cancelled"):
                job["state"] = "failed" if state == "failed" else "canceled"
                self._set_job_tab_title(job, f"{job.get('tab_title')} ✕")
                err = status.get("error") or state
                self._append_job(job, f"Prediction ended: {err}")

        self._ensure_poll_timer()

    def _on_job_finished(self, job):
        if not job:
            return
        try:
            self._append_job(job, "Downloading prediction result...")
            QApplication.processEvents()
            result = nnunet_service.download_prediction_images_and_labels(
                BASE_URL=job["base_url"],
                dataset_id=job["model_dataset_id"],
                req_id=job["req_id"],
                image_number=0,
                out_dir=job["out_dir"],
            )
            import zip_tools

            zip_path = result.get("zip_path")
            label_name = result.get("label_name") or ""
            if not zip_path or not os.path.exists(str(zip_path)):
                raise RuntimeError(f"Prediction finished but ZIP was not found: {result}")
            zip_tools.unzip_to_folder(zip_path, job["out_dir"])
            labels_path = os.path.join(job["out_dir"], label_name) if label_name else ""
            if not labels_path or not os.path.exists(str(labels_path)):
                for name in os.listdir(job["out_dir"]):
                    lower = name.lower()
                    if lower.endswith((".mha", ".mhd", ".nii", ".nii.gz")) and (
                        "label" in lower or "seg" in lower or "pred" in lower
                    ):
                        labels_path = os.path.join(job["out_dir"], name)
                        break
            if not labels_path or not os.path.exists(str(labels_path)):
                raise RuntimeError(
                    f"Prediction finished but label file was not found: {result}"
                )

            self._append_job(job, "Adding result layers...")
            QApplication.processEvents()
            added = self._add_prediction_layers(
                labels_path, job.get("labels") or {}, log_fn=lambda m: self._append_job(job, m)
            )
        except Exception as e:
            job["state"] = "failed"
            self._set_job_tab_title(job, f"{job.get('tab_title')} ✕")
            self._append_job(job, f"Failed to apply result: {e}")
            self._ensure_poll_timer()
            return

        elapsed = time.monotonic() - job.get("submitted_at", time.monotonic())
        elapsed_str = _format_duration(elapsed)
        job["state"] = "finished"
        self._set_job_tab_title(job, f"{job.get('tab_title')} ✓")
        if added:
            self._append_job(
                job,
                f"Done in {elapsed_str}. Added {len(added)} layer(s): {', '.join(added)}",
            )
        else:
            self._append_job(job, f"Done in {elapsed_str}, but no label layers were added.")
        self._ensure_poll_timer()

    def _add_prediction_layers(self, labels_path, labels_map, log_fn=None):
        """Split composite label into layers; never replace existing layers."""
        import itkvtk
        import vtk_tools

        log = log_fn or self._append_general
        mgr = self.segmentation_list_manager
        base = mgr.get_base_vtk_image()
        if base is None:
            raise RuntimeError("No base image in the viewer.")

        composite = itkvtk.load_vtk_image_using_sitk(labels_path)
        vtk_tools.copy_image_origin_spacing_direction_matrix(base, composite)

        label_items = _importable_label_items(labels_map)
        if not label_items:
            label_items = [("Prediction", 1)]

        from color_rotator import ColorRotator
        from vtk_tools import to_vtk_color

        try:
            from vtk_segmentation_list_manager import color_rotator1 as _rotator
        except Exception:
            _rotator = ColorRotator()

        added_names = []
        layers = mgr.get_segmentation_layer_list()

        for label_name, label_value in label_items:
            layer_name = _unique_layer_name(layers, label_name)
            label_image = itkvtk.extract_binary_label_image_from_composit_labels_image(
                composite, label_value
            )
            color_vtk = to_vtk_color(_rotator.next())
            mgr.add_layer(
                segmentation=label_image,
                layer_name=layer_name,
                color_vtk=color_vtk,
                alpha=0.5,
            )
            added_names.append(layer_name)
            log(f"Added layer '{layer_name}' (class {label_value})")

        return added_names

    def _on_cancel_clicked(self):
        active = self._active_jobs()
        if active:
            reply = QMessageBox.question(
                self,
                "Cancel Predictions",
                f"Cancel {len(active)} active prediction job(s) and close this tool?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self._poll_timer.stop()
        for job in list(active):
            job_id = job.get("job_id")
            base_url = job.get("base_url")
            if job_id and base_url:
                try:
                    result = nnunet_service.cancel_prediction_job(base_url, job_id)
                    self._append_job(
                        job,
                        f"Cancel requested: {result.get('status')} — {result.get('message', '')}",
                    )
                except Exception as e:
                    self._append_job(job, f"Cancel request failed: {e}")
            job["state"] = "canceled"
            self._set_job_tab_title(job, f"{job.get('tab_title')} ✕")

        self._append_general("Canceled active jobs; closing prediction tool.")
        self._poll_timer.stop()
        self._flush_pending_model_filter()
        self._persist_prediction_prefs()
        self._allow_close = True
        self.accept()
