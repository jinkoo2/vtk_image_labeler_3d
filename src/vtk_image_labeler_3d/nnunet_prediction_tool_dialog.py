"""nnU-Net Prediction Tool dialog: run approved models on the currently open case."""

from __future__ import annotations

import os
import tempfile
import uuid

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

import nnunet_service
import qt_tools


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
    if not isinstance(dataset_json, dict):
        return 1
    channel_names = dataset_json.get("channel_names") or dataset_json.get("modality") or {}
    if isinstance(channel_names, dict) and channel_names:
        return len(channel_names)
    if isinstance(channel_names, (list, tuple)) and channel_names:
        return len(channel_names)
    return 1


def _labels_from_dataset_json(dataset_json: dict) -> dict:
    if not isinstance(dataset_json, dict):
        return {}
    labels = dataset_json.get("labels") or {}
    return labels if isinstance(labels, dict) else {}


class NnUNetPredictionToolDialog(QDialog):
    """Floating tool to run an approved nnU-Net model on the open image set."""

    def __init__(self, segmentation_list_manager, get_context_fn, parent=None):
        super().__init__(parent)
        self.segmentation_list_manager = segmentation_list_manager
        self.get_context_fn = get_context_fn

        self._models = []
        self._model_detail = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_job_status)
        self._active_job = None

        self.setWindowTitle("nnUNet Prediction Tool")
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(420, 360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Approved prediction models from the nnU-Net server")
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        form.addRow("Model:", self.model_combo)

        self.input_dataset_label = QLabel("-")
        self.input_dataset_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Input Dataset:", self.input_dataset_label)

        self.input_case_label = QLabel("-")
        self.input_case_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Input Image Set:", self.input_case_label)

        self.channels_label = QLabel("-")
        form.addRow("Model Channels:", self.channels_label)

        layout.addLayout(form)

        self.status_view = QTextEdit()
        self.status_view.setReadOnly(True)
        self.status_view.setMaximumHeight(140)
        self.status_view.setPlaceholderText("Status / progress will appear here.")
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_view)

        btn_row = QHBoxLayout()
        self.run_button = QPushButton("Run Auto Segment")
        self.run_button.clicked.connect(self._on_run_clicked)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        btn_row.addWidget(self.run_button)
        btn_row.addStretch(1)
        btn_row.addWidget(self.close_button)
        layout.addLayout(btn_row)

        self._refresh_context_labels()
        self._load_approved_models()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_context_labels()

    def closeEvent(self, event):
        self._poll_timer.stop()
        super().closeEvent(event)

    def _append_status(self, msg: str):
        self.status_view.append(msg)
        sb = self.status_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_status(self, msg: str):
        self.status_view.setPlainText(msg)

    def _context(self):
        if not callable(self.get_context_fn):
            return {}
        try:
            ctx = self.get_context_fn() or {}
            return ctx if isinstance(ctx, dict) else {}
        except Exception as e:
            self._append_status(f"Context error: {e}")
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
        has_case = case.get("dataset_id") is not None and case.get("num") is not None
        self.run_button.setEnabled(bool(has_image and has_case and self.model_combo.count() > 0 and self._selected_model()))

    def _model_display_name(self, model: dict) -> str:
        return (
            f"{model.get('dataset_id', '?')} | "
            f"{model.get('configuration', '?')} | "
            f"{model.get('trainer', '?')}"
        )

    def _load_approved_models(self):
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self._models = []
        ctx = self._context()
        base_url = ctx.get("server_url")
        if not base_url:
            self._set_status("No nnU-Net server URL available. Connect to the server first.")
            self.model_combo.blockSignals(False)
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
            if not self._models:
                self.model_combo.addItem("(no approved models)")
                self._set_status("No approved models found on the server.")
            else:
                for m in self._models:
                    self.model_combo.addItem(self._model_display_name(m), m)
                self._set_status(f"Loaded {len(self._models)} approved model(s).")
                self.model_combo.setCurrentIndex(0)
                self._on_model_changed(0)
        except Exception as e:
            self.model_combo.addItem("(failed to load models)")
            self._set_status(f"Failed to load approved models:\n{e}")
        finally:
            self.model_combo.blockSignals(False)
            self._refresh_context_labels()

    def _selected_model(self):
        data = self.model_combo.currentData()
        return data if isinstance(data, dict) else None

    def _on_model_changed(self, index):
        model = self._selected_model()
        self._model_detail = None
        if not model:
            self.channels_label.setText("-")
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
            n_ch = _channel_count_from_dataset_json(dataset_json or {})
            labels = _labels_from_dataset_json(dataset_json or {})
            label_names = [f"{k}={v}" for k, v in labels.items() if int(v) > 0] if labels else []
            self.channels_label.setText(str(n_ch))
            self._append_status(
                f"Selected model needs {n_ch} channel(s). "
                f"Labels: {', '.join(label_names) if label_names else '(none)'}"
            )
        except Exception as e:
            self.channels_label.setText("?")
            self._append_status(f"Failed to fetch model detail: {e}")
        self._refresh_context_labels()

    def _download_case_channels(self, base_url, case, num_channels, out_dir):
        paths = []
        for ch in range(num_channels):
            qt_tools.update_busy_progress(
                label=f"Downloading input channel {ch}/{max(num_channels - 1, 0)}..."
            )
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
            self._append_status(f"Downloaded channel {ch}: {os.path.basename(path)}")
        return paths

    def _on_run_clicked(self):
        if self._poll_timer.isActive():
            QMessageBox.information(self, "Busy", "A prediction job is already running.")
            return

        ctx = self._context()
        base_url = ctx.get("server_url")
        case = ctx.get("case") or {}
        model = self._selected_model()

        if self.segmentation_list_manager.get_base_vtk_image() is None:
            QMessageBox.warning(self, "No Image", "Open an image in the viewer first.")
            return
        if not base_url:
            QMessageBox.warning(self, "No Server", "Connect to the nnU-Net server first.")
            return
        if not case.get("dataset_id") or case.get("num") is None:
            QMessageBox.warning(
                self,
                "No Case",
                "Load a case from the Train/Test list so the input image set is known.",
            )
            return
        if not model:
            QMessageBox.warning(self, "No Model", "Select an approved prediction model.")
            return

        dataset_json = {}
        if isinstance(self._model_detail, dict):
            dataset_json = self._model_detail.get("dataset_json") or {}
        num_channels = _channel_count_from_dataset_json(dataset_json)
        labels = _labels_from_dataset_json(dataset_json)

        if num_channels > 1:
            self._append_status(
                f"Model requires {num_channels} channels; downloading all channels "
                f"for case {case['num']}..."
            )

        out_dir = os.path.join(tempfile.gettempdir(), f"nnunet_pred_{uuid.uuid4().hex}")
        os.makedirs(out_dir, exist_ok=True)

        try:
            with qt_tools.busy_progress(
                self,
                title="Auto Segment",
                label="Preparing input images...",
            ):
                channel_paths = self._download_case_channels(
                    base_url, case, num_channels, out_dir
                )
                qt_tools.update_busy_progress(label="Submitting prediction job...")
                image_id = f"{case['dataset_id']}_{case['images_for']}_{case['num']}"
                submit = nnunet_service.post_prediction(
                    BASE_URL=base_url,
                    model_dataset_id=model["dataset_id"],
                    image_id=image_id,
                    channel_image_paths=channel_paths,
                    trainer=model.get("trainer", "nnUNetTrainer"),
                    plans=model.get("plans", "nnUNetPlans"),
                    configuration=model.get("configuration", "3d_lowres"),
                )
        except Exception as e:
            QMessageBox.critical(self, "Prediction Failed", str(e))
            self._append_status(f"Submit failed: {e}")
            return

        job_id = submit.get("job_id")
        req_id = submit.get("req_id")
        if not job_id or not req_id:
            QMessageBox.critical(
                self,
                "Prediction Failed",
                f"Unexpected submit response (missing job_id/req_id):\n{submit}",
            )
            return

        self._active_job = {
            "job_id": job_id,
            "req_id": req_id,
            "model_dataset_id": model["dataset_id"],
            "labels": labels,
            "base_url": base_url,
            "out_dir": out_dir,
        }
        ahead = submit.get("number_of_jobs_ahead", "?")
        self._append_status(
            f"Job queued. req_id={req_id}, job_id={job_id}, jobs ahead={ahead}"
        )
        self.run_button.setEnabled(False)
        self._poll_timer.start()

    def _poll_job_status(self):
        job = self._active_job
        if not job:
            self._poll_timer.stop()
            return

        try:
            status = nnunet_service.get_prediction_job_status(
                job["base_url"], job["job_id"]
            )
        except Exception as e:
            self._append_status(f"Status check failed: {e}")
            return

        state = str(status.get("status", "")).lower()
        progress = status.get("progress", "")
        ahead = status.get("number_of_jobs_ahead", "")
        self._append_status(f"Status: {state}  progress={progress}  ahead={ahead}")

        if state in ("finished", "completed", "success"):
            self._poll_timer.stop()
            self._on_job_finished()
        elif state in ("failed", "stopped", "canceled", "cancelled"):
            self._poll_timer.stop()
            self.run_button.setEnabled(True)
            err = status.get("error") or state
            self._append_status(f"Prediction failed: {err}")
            QMessageBox.critical(self, "Prediction Failed", str(err))

    def _on_job_finished(self):
        job = self._active_job
        self._active_job = None
        if not job:
            self.run_button.setEnabled(True)
            self._refresh_context_labels()
            return

        try:
            with qt_tools.busy_progress(
                self,
                title="Auto Segment",
                label="Downloading prediction result...",
            ):
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
                    raise RuntimeError(
                        f"Prediction finished but ZIP was not found: {result}"
                    )
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

                qt_tools.update_busy_progress(label="Adding result layers...")
                added = self._add_prediction_layers(labels_path, job.get("labels") or {})
        except Exception as e:
            self.run_button.setEnabled(True)
            self._refresh_context_labels()
            self._append_status(f"Failed to apply result: {e}")
            QMessageBox.critical(self, "Result Failed", str(e))
            return

        self.run_button.setEnabled(True)
        self._refresh_context_labels()
        self._append_status(
            f"Done. Added layer(s): {', '.join(added) if added else '(none)'}"
        )
        if added:
            QMessageBox.information(
                self,
                "Auto Segment Complete",
                "Prediction finished.\nAdded layers:\n- " + "\n- ".join(added),
            )
        else:
            QMessageBox.information(
                self,
                "Auto Segment Complete",
                "Prediction finished, but no label layers were added.",
            )

    def _add_prediction_layers(self, labels_path, labels_map):
        """Split composite label into layers; never replace existing layers."""
        import itkvtk
        import vtk_tools

        mgr = self.segmentation_list_manager
        base = mgr.get_base_vtk_image()
        if base is None:
            raise RuntimeError("No base image in the viewer.")

        composite = itkvtk.load_vtk_image_using_sitk(labels_path)
        vtk_tools.copy_image_origin_spacing_direction_matrix(base, composite)

        label_items = []
        for name, value in (labels_map or {}).items():
            try:
                iv = int(value)
            except (TypeError, ValueError):
                continue
            if iv <= 0:
                continue
            label_items.append((str(name), iv))

        if not label_items:
            label_items = [("Prediction", 1)]

        from color_rotator import ColorRotator
        from vtk_tools import to_vtk_color

        # Prefer the shared app rotator when available so colors stay consistent.
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
            self._append_status(f"Added layer '{layer_name}' (class {label_value})")

        return added_names