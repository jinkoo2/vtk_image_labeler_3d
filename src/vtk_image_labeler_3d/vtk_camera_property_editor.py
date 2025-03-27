from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5.QtCore import pyqtSignal, QObject

class VTKCameraPropertyEditor(QTreeWidget):

    property_changed = pyqtSignal(str, QObject)

    def __init__(self, camera, parent=None):
        super().__init__(parent)
        self.camera = camera  # Store reference to the VTK camera

        self.setColumnCount(2)
        self.setHeaderLabels(["Property", "Value"])
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.populate_camera_properties()

        # Allow editing and detect changes
        self.itemChanged.connect(self.update_camera_property)

    def populate_camera_properties(self):
        """Populate the widget with VTK camera properties."""
        self.clear()

        # Define camera properties
        properties = {
            "Position": self.camera.GetPosition(),
            "Focal Point": self.camera.GetFocalPoint(),
            "View Up": self.camera.GetViewUp(),
            "Clipping Range": self.camera.GetClippingRange(),
            "View Angle": [self.camera.GetViewAngle()],  # Single value in list
            "Parallel Scale": [self.camera.GetParallelScale()]  # Single value in list
        }

        # Create items
        for prop, value in properties.items():
            item = QTreeWidgetItem(self, [prop, ", ".join(map(str, value))])
            item.setFlags(item.flags() | Qt.ItemIsEditable)  # Make editable
            item.setData(0, Qt.UserRole, prop)  # Store property name

    def update_camera_property(self, item, column):
        """Update the VTK camera when a value is changed."""
        if column == 1:  # Only process edits in the Value column
            prop_name = item.data(0, Qt.UserRole)
            new_value = item.text(1)

            # Convert input string back to tuple or float
            try:
                if "," in new_value:  # Convert comma-separated values to tuple
                    new_value = tuple(map(float, new_value.split(",")))
                else:
                    new_value = float(new_value)
            except ValueError:
                return  # Ignore invalid input

            # Apply changes to VTK camera
            if prop_name == "Position":
                self.camera.SetPosition(new_value)
                self.property_changed.emit(prop_name, self)
            elif prop_name == "Focal Point":
                self.camera.SetFocalPoint(new_value)
                self.property_changed.emit(prop_name, self)
            elif prop_name == "View Up":
                self.camera.SetViewUp(new_value)
                self.property_changed.emit(prop_name, self)
            elif prop_name == "Clipping Range":
                self.camera.SetClippingRange(new_value)
                self.property_changed.emit(prop_name, self)
            elif prop_name == "View Angle":
                self.camera.SetViewAngle(new_value)
                self.property_changed.emit(prop_name, self)
            elif prop_name == "Parallel Scale":
                self.camera.SetParallelScale(new_value)
                self.property_changed.emit(prop_name, self)


class VTKViewer2D(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the layout
        layout = QVBoxLayout(self)

        # Create VTK Widget
        self.vtkWidget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtkWidget)

        # Setup VTK Renderer
        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)

        # Create VTK Camera
        self.camera = self.ren.GetActiveCamera()

        # Create Camera Property Editor
        self.camera_editor = VTKCameraPropertyEditor(self.camera)
        layout.addWidget(self.camera_editor)

        # Initialize Interactor
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.iren.Initialize()

        self.show()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    viewer = VTKViewer2D()
    sys.exit(app.exec_())
