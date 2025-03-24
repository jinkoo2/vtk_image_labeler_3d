from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QPushButton, QLabel, QWidget


class WidgetDialog(QDialog):
    def __init__(self, widget, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Custom Modal Dialog")
        self.setModal(True)  # Set the dialog to be modal

        # Create layout
        layout = QVBoxLayout(self)

        # Central Widget (Can be replaced with any custom QWidget)
        self.central_widget = widget
        self.central_widget.setStyleSheet("background-color: lightgray; min-height: 100px;")  # Placeholder
        layout.addWidget(self.central_widget)

        # OK Button
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.accept)  # Close dialog on click
        layout.addWidget(self.ok_button)

        self.setLayout(layout)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    # Create and show the dialog
    dialog = WidgetDialog(QLabel("Hello World!"))
    dialog.exec_()  # Show modal dialog

    sys.exit(app.exec_())
