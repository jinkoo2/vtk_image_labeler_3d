"""Edit -> Preferences dialog for settings.json."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
)

from config import get_config, get_nnunet_server_url, get_nnunet_server_urls, save_settings, settings_path


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(620)
        self.setWindowModality(Qt.ApplicationModal)

        conf = get_config()

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.log_dir_edit = QLineEdit(str(conf.get("log_dir", "")))
        self.temp_dir_edit = QLineEdit(str(conf.get("temp_dir", "")))

        urls = get_nnunet_server_urls(conf)
        self.server_urls_edit = QPlainTextEdit("\n".join(urls))
        self.server_urls_edit.setPlaceholderText(
            "One nnU-Net server URL per line\n"
            "https://nnunet-server-01.apps.myphysics.net/api/v3"
        )
        self.server_urls_edit.setMinimumHeight(90)

        self.keycloak_url_edit = QLineEdit(str(conf.get("keycloak_url", "")))
        self.keycloak_realm_edit = QLineEdit(str(conf.get("keycloak_realm", "")))
        self.registration_url_edit = QLineEdit(str(conf.get("keycloak_registration_url", "")))
        self.feedback_api_url_edit = QLineEdit(str(conf.get("feedback_api_url", "")))
        self.feedback_api_key_edit = QLineEdit(str(conf.get("feedback_api_key", "")))
        self.feedback_api_key_edit.setEchoMode(QLineEdit.Password)

        form.addRow("Log directory:", self._path_row(self.log_dir_edit))
        form.addRow("Temp directory:", self._path_row(self.temp_dir_edit))
        form.addRow("nnU-Net server URLs:", self.server_urls_edit)
        form.addRow("Keycloak URL:", self.keycloak_url_edit)
        form.addRow("Keycloak realm:", self.keycloak_realm_edit)
        form.addRow("Registration URL:", self.registration_url_edit)
        form.addRow("Feedback API URL:", self.feedback_api_url_edit)
        form.addRow("Feedback API key:", self.feedback_api_key_edit)

        path_label = QLabel(f"Settings file: {settings_path()}")
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #666; font-size: 11px;")

        note = QLabel(
            "Log/temp directory changes take effect after restart. "
            "Server URLs, Keycloak, and Feedback API settings apply immediately. "
            "Enter one nnU-Net server URL per line; use the dashboard dropdown to switch. "
            "Feedback API URL is the CapRover origin only (no path)."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #666; font-size: 11px;")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(path_label)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def _path_row(self, edit: QLineEdit):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        browse = QPushButton("Browse...")
        browse.setFixedWidth(80)
        browse.clicked.connect(lambda: self._browse_dir(edit))
        row.addWidget(edit, 1)
        row.addWidget(browse)
        return row

    def _browse_dir(self, edit: QLineEdit):
        start = edit.text().strip() or "."
        path = QFileDialog.getExistingDirectory(self, "Select directory", start)
        if path:
            edit.setText(path)

    def _parse_server_urls(self) -> list:
        text = self.server_urls_edit.toPlainText() or ""
        urls = []
        seen = set()
        for line in text.splitlines():
            url = line.strip().rstrip("/")
            if not url or url.startswith("#") or url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def values(self) -> dict:
        urls = self._parse_server_urls()
        previous_selected = get_nnunet_server_url()
        selected = previous_selected if previous_selected in urls else (urls[0] if urls else "")
        return {
            "log_dir": self.log_dir_edit.text().strip(),
            "temp_dir": self.temp_dir_edit.text().strip(),
            "nnunet_server_url_list": urls,
            "nnunet_selected_server_url": selected,
            "keycloak_url": self.keycloak_url_edit.text().strip(),
            "keycloak_realm": self.keycloak_realm_edit.text().strip(),
            "keycloak_registration_url": self.registration_url_edit.text().strip(),
            "feedback_api_url": self.feedback_api_url_edit.text().strip().rstrip("/"),
            "feedback_api_key": self.feedback_api_key_edit.text().strip(),
        }

    def accept(self):
        vals = self.values()
        if not vals["nnunet_server_url_list"]:
            QMessageBox.warning(
                self,
                "Preferences",
                "At least one nnU-Net server URL is required (one URL per line).",
            )
            return
        try:
            save_settings(vals)
        except Exception as exc:
            QMessageBox.critical(self, "Preferences", f"Failed to save settings:\n{exc}")
            return
        super().accept()
