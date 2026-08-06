"""Keycloak login dialog for the nnU-Net server."""

from __future__ import annotations

import webbrowser

from PyQt5.QtCore import Qt, QSettings, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


def default_registration_url(keycloak_url: str, realm: str) -> str:
    """
    Keycloak self-registration page (when realm registration is enabled).

    Uses the built-in account-console client so the confidential nnunet-server
    client secret is never needed in the desktop app.
    """
    base = (keycloak_url or "").rstrip("/")
    realm = realm or "myphysics"
    redirect = f"{base}/realms/{realm}/account/"
    return (
        f"{base}/realms/{realm}/protocol/openid-connect/registrations"
        f"?client_id=account-console"
        f"&response_type=code"
        f"&scope=openid"
        f"&redirect_uri={redirect}"
    )


class NnUNetLoginDialog(QDialog):
    """Modal email/password login with a Register link."""

    def __init__(
        self,
        server_url: str,
        registration_url: str = "",
        parent=None,
        initial_email: str = "",
    ):
        super().__init__(parent)
        self.server_url = server_url
        self.registration_url = registration_url
        self._login_result = None

        self.setWindowTitle("nnU-Net Server Login")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Sign in with your myphysics account to connect to the nnU-Net server."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("you@example.com")
        if initial_email:
            self.email_edit.setText(initial_email)
        form.addRow("Email:", self.email_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Password")
        form.addRow("Password:", self.password_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._login_button = buttons.button(QDialogButtonBox.Ok)
        self._login_button.setText("Login")
        self._login_button.setDefault(True)
        self._login_button.setAutoDefault(True)
        buttons.accepted.connect(self._on_login_clicked)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Registration at the bottom; never autoDefault so Enter logs in, not Register.
        reg_row = QHBoxLayout()
        reg_label = QLabel("Don't have an account?")
        self.register_button = QPushButton("Register")
        self.register_button.setFlat(True)
        self.register_button.setAutoDefault(False)
        self.register_button.setDefault(False)
        self.register_button.setCursor(Qt.PointingHandCursor)
        self.register_button.setStyleSheet("QPushButton { color: #1565c0; text-align: left; }")
        self.register_button.setToolTip("Open account registration in your browser")
        self.register_button.clicked.connect(self._on_register_clicked)
        if not registration_url:
            self.register_button.setEnabled(False)
            self.register_button.setToolTip("Registration URL is not configured")
        reg_row.addWidget(reg_label)
        reg_row.addWidget(self.register_button)
        reg_row.addStretch(1)
        layout.addLayout(reg_row)

        # Do not also connect password returnPressed -> login: Enter would fire
        # both returnPressed and the default Login button, showing errors twice.
        self.email_edit.returnPressed.connect(self.password_edit.setFocus)
        self._login_in_progress = False

    def login_result(self):
        return self._login_result

    def _on_register_clicked(self):
        url = self.registration_url
        if not url:
            QMessageBox.information(
                self,
                "Registration",
                "No registration URL is configured.\n"
                "Ask an administrator to create your account.",
            )
            return
        ok = QDesktopServices.openUrl(QUrl(url))
        if not ok:
            webbrowser.open(url)

    def _on_login_clicked(self):
        import nnunet_service
        import qt_tools

        # Guard against re-entrancy (Enter / default-button / processEvents).
        if getattr(self, "_login_in_progress", False):
            return
        self._login_in_progress = True
        try:
            email = self.email_edit.text().strip()
            password = self.password_edit.text()
            if not email or not password:
                QMessageBox.warning(self, "Login", "Enter both email and password.")
                return

            try:
                with qt_tools.busy_progress(
                    self,
                    title="Login",
                    label="Signing in...",
                ):
                    result = nnunet_service.login(self.server_url, email, password)
            except Exception as e:
                QMessageBox.critical(self, "Login Failed", str(e))
                return

            self._login_result = result
            # Remember last email for convenience
            settings = QSettings("vtk_image_labeler_3d", "nnunet")
            settings.setValue("last_login_email", email)
            self.accept()
        finally:
            self._login_in_progress = False
