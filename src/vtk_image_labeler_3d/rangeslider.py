from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRect

from PyQt5.QtCore import pyqtSignal

class RangeSlider(QWidget):

    # Signal emitted when the range values change
    rangeChanged = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.low_value = 20
        self.high_value = 80
        self.range_min = 0
        self.range_max = 100
        self.slider_width = 10
        self.active_handle = None
        self.bar_dragging = False
        self.last_mouse_position = None

    def get_center(self):
        return (self.low_value+self.high_value)/2
    def get_width(self):
        return (self.high_value-self.low_value)

    def paintEvent(self, event):
        painter = QPainter(self)
        width = self.width()
        height = self.height()

        # Draw background bar
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(0, height // 2 - 5, width, 10)

        # Draw range
        low_pos = int(self.value_to_pos(self.low_value))
        high_pos = int(self.value_to_pos(self.high_value))
        painter.setBrush(QColor(150, 150, 150))
        painter.drawRect(low_pos, height // 2 - 5, high_pos - low_pos, 10)

        # Draw handles
        painter.setBrush(QColor(100, 100, 100))
        painter.drawEllipse(
            low_pos - self.slider_width // 2,
            height // 2 - self.slider_width // 2,
            self.slider_width,
            self.slider_width,
        )
        painter.drawEllipse(
            high_pos - self.slider_width // 2,
            height // 2 - self.slider_width // 2,
            self.slider_width,
            self.slider_width,
        )

    def mousePressEvent(self, event):
        pos = event.x()
        low_pos = self.value_to_pos(self.low_value)
        high_pos = self.value_to_pos(self.high_value)

        if abs(pos - low_pos) < self.slider_width:  # Clicked near low handle
            self.active_handle = "low"
        elif abs(pos - high_pos) < self.slider_width:  # Clicked near high handle
            self.active_handle = "high"
        elif low_pos < pos < high_pos:  # Clicked inside the bar
            self.bar_dragging = True
            self.last_mouse_position = pos


    def mouseMoveEvent(self, event):
        pos = event.x()

        if self.active_handle:  # Moving a single handle
            value = self.pos_to_value(pos)
            if self.active_handle == "low":
                new_low_value = max(self.range_min, min(self.high_value, value))
                if new_low_value != self.low_value:
                    self.low_value = new_low_value
                    self.rangeChanged.emit(self.low_value, self.high_value)
            elif self.active_handle == "high":
                new_high_value = min(self.range_max, max(self.low_value, value))
                if new_high_value != self.high_value:
                    self.high_value = new_high_value
                    self.rangeChanged.emit(self.low_value, self.high_value)

        elif self.bar_dragging:  # Moving the entire range
            delta = pos - self.last_mouse_position
            step = self.pos_to_value(delta) - self.range_min  # Convert pixel movement to value
            new_low_value = self.low_value + step
            new_high_value = self.high_value + step

            # Ensure the bar stays within bounds
            if self.range_min <= new_low_value and new_high_value <= self.range_max:
                self.low_value = new_low_value
                self.high_value = new_high_value
                self.rangeChanged.emit(self.low_value, self.high_value)

            self.last_mouse_position = pos

        self.update()


    def mouseReleaseEvent(self, event):
        self.active_handle = None
        self.bar_dragging = False
        self.last_mouse_position = None

    def value_to_pos(self, value):
        return (value - self.range_min) / (self.range_max - self.range_min) * self.width()

    def pos_to_value(self, pos):
        return int(pos / self.width() * (self.range_max - self.range_min) + self.range_min)

if __name__ == "__main__":
    app = QApplication([])
    window = RangeSlider()
    window.resize(400, 100)
    window.show()
    app.exec_()
