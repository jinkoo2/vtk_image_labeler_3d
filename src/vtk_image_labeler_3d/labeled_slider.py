from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import ( QSlider, QLabel, QWidget, QHBoxLayout)

class LabeledSlider(QWidget):
    def __init__(self, label_text="Slider", min_value=0, max_value=100, initial_value=50, orientation=Qt.Horizontal):
        super().__init__()

        # Create the components
        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignRight)  # Align label text to the right
        self.slider = QSlider(orientation)
        self.current_value_label = QLabel(str(initial_value))

        # Set slider properties
        self.slider.setMinimum(min_value)
        self.slider.setMaximum(max_value)
        self.slider.setValue(initial_value)

        # Connect the slider value change signal to the update function
        self.slider.valueChanged.connect(self.update_value_label)

        # Layout
        main_layout = QHBoxLayout()  # Horizontal layout for label, slider, and value display

        # Add widgets to layouts with margins
        main_layout.addWidget(self.label)
        main_layout.addWidget(self.slider, stretch=1)  # Let slider expand to fill space
        main_layout.addWidget(self.current_value_label)

        # Set margins for better spacing
        main_layout.setContentsMargins(10, 5, 10, 5)  # Left, top, right, bottom

        self.setLayout(main_layout)

    def update_value_label(self, value):
        """Update the dynamic value display when the slider changes."""
        self.current_value_label.setText(str(value))

    def get_value(self):
        """Get the current slider value."""
        return self.slider.value()

    def set_value(self, value):
        """Set the slider value."""
        self.slider.setValue(value)

    def setMinimum(self, min):
        self.slider.setMinimum(min)
            
    def setMaximum(self, min):
        self.slider.setMaximum(min)

    def setTickInterval(self, min):
        self.slider.setTickInterval(min)

    def setValue(self, min):
        self.slider.setValue(min)
    
    def value(self):
        return self.slider.value()
    