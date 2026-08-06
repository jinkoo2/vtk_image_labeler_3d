"""In-app Feature Request / Bug Report dialog that opens a GitHub Issue."""

from __future__ import annotations

import platform
import sys
import webbrowser
from urllib.parse import quote, urlencode

from PyQt5.QtCore import Qt, QUrl
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
    QTextEdit,
    QVBoxLayout,
)

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


def collect_environment_block() -> str:
    return (
        "### Environment\n"
        f"- App version: `{get_version()}`\n"
        f"- OS: `{platform.platform()}`\n"
        f"- Python: `{sys.version.split()[0]}`\n"
        f"- Platform: `{platform.system()} {platform.release()}`\n"
    )


class FeedbackDialog(QDialog):
    """Collect a title/message and open a prefilled GitHub issue page."""

    def __init__(self, kind: str = "bug", parent=None):
        super().__init__(parent)
        if kind not in FEEDBACK_KINDS:
            raise ValueError(f"Unknown feedback kind: {kind}")
        self.kind = kind
        self.meta = FEEDBACK_KINDS[kind]

        self.setWindowTitle(self.meta["window_title"])
        self.setModal(True)
        self.setMinimumWidth(460)
        self.resize(520, 420)

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
        layout.addLayout(form)

        note = QLabel(
            "Send opens GitHub Issues in your browser with this text filled in. "
            "Sign in to GitHub if needed, then click Submit new issue."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #666;")
        layout.addWidget(note)

        buttons = QDialogButtonBox()
        self.send_button = buttons.addButton("Send", QDialogButtonBox.AcceptRole)
        self.send_button.setDefault(True)
        buttons.addButton(QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_send)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_send(self):
        title = (self.title_edit.text() or "").strip()
        details = (self.body_edit.toPlainText() or "").strip()
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

        full_title = self.meta["title_prefix"] + title
        body = (
            details
            + "\n\n---\n"
            + collect_environment_block()
            + "\n_Submitted from Image Labeler 3D in-app feedback._\n"
        )

        url = github_new_issue_url(full_title, body, self.meta["label"])
        # Keep URLs under common browser/OS limits.
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
        self.accept()


def show_feedback_dialog(kind: str, parent=None) -> None:
    dialog = FeedbackDialog(kind=kind, parent=parent)
    dialog.exec_()
