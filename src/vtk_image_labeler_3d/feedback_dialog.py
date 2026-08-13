"""In-app Feature Request / Bug Report dialog.

Posts to the CapRover feedback API (GitHub Issues via bot token).

Requires `feedback_api_url` and `feedback_api_key` in settings.json
(Edit -> Preferences).
"""

from __future__ import annotations

import json
import platform
import sys
import webbrowser
from urllib.parse import quote, urlencode

import requests
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from config import get_config
from version_info import GITHUB_OWNER, GITHUB_REPO, get_version


FEEDBACK_KINDS = {
    "bug": {
        "window_title": "Bug Report",
        "heading": "Describe the bug",
        "title_placeholder": "Short summary of the problem",
        "body_placeholder": (
            "What happened?\n"
            "What did you expect?\n"
            "Steps to reproduce:\n"
            "1. ...\n"
            "2. ..."
        ),
        "label": "bug",
        "title_prefix": "[Bug] ",
    },
    "feature": {
        "window_title": "Feature Request",
        "heading": "Describe the feature",
        "title_placeholder": "Short summary of the idea",
        "body_placeholder": (
            "What would you like to do?\n"
            "Why is it useful?\n"
            "Any suggested workflow or UI?"
        ),
        "label": "enhancement",
        "title_prefix": "[Feature] ",
    },
}


def github_new_issue_url(title: str, body: str, label: str = "") -> str:
    base = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues/new"
    params = {"title": title, "body": body}
    if label:
        params["labels"] = label
    return f"{base}?{urlencode(params, quote_via=quote)}"


def collect_environment_fields() -> dict:
    return {
        "app_version": get_version(),
        "os": platform.platform(),
        "python_version": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
    }


def collect_environment_block() -> str:
    env = collect_environment_fields()
    return (
        "### Environment\n"
        f"- App version: `{env['app_version']}`\n"
        f"- OS: `{env['os']}`\n"
        f"- Python: `{env['python_version']}`\n"
        f"- Platform: `{env['platform']}`\n"
    )


class FeedbackDialog(QDialog):
    """Collect feedback and submit via API (preferred) or GitHub browser fallback."""

    def __init__(self, kind: str = "bug", parent=None):
        super().__init__(parent)
        if kind not in FEEDBACK_KINDS:
            raise ValueError(f"Unknown feedback kind: {kind}")
        self.kind = kind
        self.meta = FEEDBACK_KINDS[kind]

        conf = get_config()
        self._api_url = str(conf.get("feedback_api_url") or "").strip().rstrip("/")
        self._api_key = str(conf.get("feedback_api_key") or "").strip()

        self.setWindowTitle(self.meta["window_title"])
        self.setModal(True)
        self.setMinimumWidth(460)
        self.resize(520, 460)

        layout = QVBoxLayout(self)

        heading = QLabel(self.meta["heading"])
        heading.setWordWrap(True)
        layout.addWidget(heading)

        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(self.meta["title_placeholder"])
        form.addRow("Title:", self.title_edit)

        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText(self.meta["body_placeholder"])
        self.body_edit.setAcceptRichText(False)
        form.addRow("Details:", self.body_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Optional — so we can follow up")
        form.addRow("Email:", self.email_edit)
        layout.addLayout(form)

        if self._api_configured():
            note_text = (
                "Send posts to the feedback service (no GitHub account needed). "
                "Your report becomes a GitHub Issue for the maintainers / AI agents."
            )
            note_style = "color: #666;"
        else:
            note_text = (
                "Feedback API is not configured. Set Feedback API URL and Feedback API key "
                "in Edit -> Preferences before sending."
            )
            note_style = "color: #b71c1c;"
        note = QLabel(note_text)
        note.setWordWrap(True)
        note.setStyleSheet(note_style)
        layout.addWidget(note)

        buttons = QDialogButtonBox()
        self.send_button = buttons.addButton("Send", QDialogButtonBox.AcceptRole)
        self.send_button.setDefault(True)
        cancel = buttons.addButton(QDialogButtonBox.Cancel)
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        buttons.accepted.connect(self._on_send)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if not self._api_configured():
            # Nudge immediately; Send will warn again if they ignore it.
            self._prompt_configure_preferences()

    def _api_configured(self) -> bool:
        return bool(self._api_url) and bool(self._api_key)

    def _prompt_configure_preferences(self) -> None:
        QMessageBox.warning(
            self,
            self.meta["window_title"],
            "Feedback API URL and Feedback API key are not set.\n\n"
            "Open Edit -> Preferences, fill in:\n"
            "  - Feedback API URL\n"
            "  - Feedback API key\n\n"
            "Then try Send again.",
        )

    def _on_send(self):
        if not self._api_configured():
            self._prompt_configure_preferences()
            return

        title = (self.title_edit.text() or "").strip()
        details = (self.body_edit.toPlainText() or "").strip()
        email = (self.email_edit.text() or "").strip()
        if not title:
            QMessageBox.warning(self, self.meta["window_title"], "Please enter a title.")
            self.title_edit.setFocus()
            return
        if not details:
            QMessageBox.warning(
                self, self.meta["window_title"], "Please enter some details."
            )
            self.body_edit.setFocus()
            return

        ok = self._submit_via_api(title, details, email)
        if ok:
            self.accept()

    def _submit_via_api(self, title: str, details: str, email: str) -> bool:
        url = f"{self._api_url}/api/v1/feedback"
        env = collect_environment_fields()
        payload = {
            "kind": self.kind,
            "title": title,
            "details": details,
            "contact_email": email or None,
            **env,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["X-Feedback-Key"] = self._api_key

        self.send_button.setEnabled(False)
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        except requests.RequestException as exc:
            self.send_button.setEnabled(True)
            QMessageBox.critical(
                self,
                self.meta["window_title"],
                f"Could not reach the feedback service:\n{exc}",
            )
            return False
        finally:
            self.send_button.setEnabled(True)

        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            QMessageBox.critical(
                self,
                self.meta["window_title"],
                f"Feedback service error ({resp.status_code}):\n{detail}",
            )
            return False

        try:
            data = resp.json()
        except Exception:
            data = {}
        issue_url = data.get("html_url") or data.get("issue_url") or ""
        number = data.get("issue_number")
        msg = "Thanks - your feedback was submitted."
        if number:
            msg += f"\nIssue #{number} was created for the maintainers."
        if issue_url:
            msg += f"\n\n{issue_url}"
        QMessageBox.information(self, self.meta["window_title"], msg)
        return True

    def _submit_via_github_browser(self, title: str, details: str) -> None:
        full_title = self.meta["title_prefix"] + title
        body = (
            details
            + "\n\n---\n"
            + collect_environment_block()
            + "\n_Submitted from Image Labeler 3D in-app feedback._\n"
        )
        url = github_new_issue_url(full_title, body, self.meta["label"])
        if len(url) > 6500:
            short_body = (
                details[:1500]
                + "\n\n_(Details truncated for URL length; please paste the rest.)_\n\n---\n"
                + collect_environment_block()
            )
            url = github_new_issue_url(full_title, short_body, self.meta["label"])
            try:
                from PyQt5.QtWidgets import QApplication

                QApplication.clipboard().setText(details)
            except Exception:
                pass
            QMessageBox.information(
                self,
                self.meta["window_title"],
                "The message was long, so the full details were copied to the clipboard.\n"
                "Paste them into the GitHub issue if needed.",
            )

        ok = QDesktopServices.openUrl(QUrl(url))
        if not ok:
            webbrowser.open(url)


def show_feedback_dialog(kind: str, parent=None) -> None:
    dialog = FeedbackDialog(kind=kind, parent=parent)
    dialog.exec_()
