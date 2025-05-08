from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import ( QSlider, QLabel, QWidget, QHBoxLayout)

from PyQt5.QtCore import pyqtSignal, QObject

class LabeledFloatSlider(QWidget):

    value_changed = pyqtSignal(float, QObject)

    def __init__(self, label_text="Slider", f0=0.0, f1=1.0, initial_value=0.5, float_format_string='{:0.2f}', orientation=Qt.Horizontal):
        super().__init__()

        self.float_format_string = float_format_string

        self.f0 = f0 
        self.f1 = f1
        
        self.min_int = 0
        self.max_int = 100
        self.tick_interval_int = 1
        self.num_of_steps = 100

        # conversion factors (from float to int)
        # i = a * f + b
        self.a = 100 / (self.f1 - self.f0 )
        self.b = self.f0

        # Create the components
        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignRight)  # Align label text to the right
        self.slider = QSlider(orientation)
        self.current_value_label = QLabel(str(initial_value))

        # Set slider properties
        self.slider.setMinimum(self.min_int)
        self.slider.setMaximum(self.max_int)
        self.slider.setTickInterval(self.tick_interval_int)
        self.slider.setValue(self._float_to_int(initial_value))

        # Connect the slider value change signal to the update function
        self.slider.valueChanged.connect(self._on_value_changed)

        # Layout
        main_layout = QHBoxLayout()  # Horizontal layout for label, slider, and value display

        # Add widgets to layouts with margins
        main_layout.addWidget(self.label)
        main_layout.addWidget(self.slider, stretch=1)  # Let slider expand to fill space
        main_layout.addWidget(self.current_value_label)

        # Set margins for better spacing
        main_layout.setContentsMargins(10, 5, 10, 5)  # Left, top, right, bottom

        self.setLayout(main_layout)

    def _int_to_float(self, i):
        f = (i - self.b)/self.a
        return f
    
    def _float_to_int(self, f):
        i = int (self.a * f + self.b + 0.499999999)
        return i

    def _on_value_changed(self, int_value):
        """Update the dynamic value display when the slider changes."""

        f = self._int_to_float(int_value)

        text = self.float_format_string.format(f)
        self.current_value_label.setText(text)

        self.value_changed.emit(f, self)

    def get_value(self):
        """Get the current slider value."""
        return self._int_to_float(self.slider.value())

    def set_value(self, value):
        """Set the slider value."""
        self.slider.setValue(self._float_to_int(value))

    def value(self):
        return self.get_value()