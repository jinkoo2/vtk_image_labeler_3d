from PyQt5.QtWidgets import (QLineEdit)

class LineEdit2(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.focus_out_callback = None  # Placeholder for the callback

    def focusOutEvent(self, event):
        if self.focus_out_callback:
            self.focus_out_callback(event)  # Call the assigned function
        super().focusOutEvent(event)  # Ensure default behavior