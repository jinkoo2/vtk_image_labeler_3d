from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QApplication
import sys

class ListWidgetWithTitle(QWidget):
    def __init__(self, title="My Item List"):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add a title bar using QLabel
        self.title_label_widget = QLabel(title)
        self.title_label_widget.setStyleSheet("padding: 0;")
        self.title_label_widget.setContentsMargins(0, 0, 0, 0)

        # Create the list widget
        self.list_widget = QListWidget()

        # Add widgets to the layout
        layout.addWidget( self.title_label_widget)
        layout.addWidget(self.list_widget)

        self.setLayout(layout)
        self.setWindowTitle("QListWidget with Title")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ListWidgetWithTitle()
    window.show()
    sys.exit(app.exec_())
