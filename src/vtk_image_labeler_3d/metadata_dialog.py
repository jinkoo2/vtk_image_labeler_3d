from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton

class MetadataDialog(QDialog):
    def __init__(self, metadata, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Request Metadata")

        self.edits = {}

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)  # Adds padding around all content
        self.resize(400, 250)
        
        form_layout = QFormLayout()

        # Create line edits for each metadata field
        for key, value in metadata.items():
            edit = QLineEdit(str(value))
            form_layout.addRow(key, edit)
            self.edits[key] = edit

        layout.addLayout(form_layout)

        # OK and Cancel buttons
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        layout.addWidget(btn_ok)
        layout.addWidget(btn_cancel)

        self.setLayout(layout)

    def get_metadata(self):
        return {key: edit.text() for key, edit in self.edits.items()}
