
import vtk
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QListWidgetItem, QVBoxLayout, QPushButton, QLabel, QWidget, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit)
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor

from logger import logger
from color_rotator import ColorRotator

class PointItem:
    def __init__(self, coordinates, color=[255, 0, 0], visible=True, renderer=None, interactor=None):
        self.coordinates = coordinates
        self.color = color
        self.visible = visible
        self.modified = False
        self.renderer = renderer

        # Create a handle representation
        self.representation = vtk.vtkPointHandleRepresentation3D()
        self.representation.SetWorldPosition(self.coordinates)
        self.representation.SetHandleSize(20.0)
        self.representation.GetProperty().SetLineWidth(3.0)
        self.representation.GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

        # Create a handle widget
        self.widget = vtk.vtkHandleWidget()
        self.widget.SetRepresentation(self.representation)

        # Add observer for position change
        self.widget.AddObserver("InteractionEvent", self.on_position_changed)

        # Add the widget to the interactor
        if interactor:
            self.widget.SetInteractor(interactor)
            self.widget.EnabledOn()

    def destroy(self):
        # Disable and delete the widget
        from vtk_tools import remove_widget
        remove_widget(self.widget, self.renderer)

        # Delete the representation
        if self.representation:
            self.representation = None

        # Clear attributes to help garbage collection
        self.coordinates = None
        self.color = None
        self.visible = None

        print("PointItem successfully destroyed.")
        
    def set_highlight(self, highlighted):
        if highlighted:
            #self.representation.SetHandleSize(20.0)
            self.representation.GetProperty().SetLineWidth(6.0)
        else: 
            #self.representation.SetHandleSize(10.0)
            self.representation.GetProperty().SetLineWidth(3.0)

    def set_visibility(self, visible):
        self.widget.EnabledOn() if visible else self.widget.EnabledOff()

    def on_position_changed(self, obj, event):
        self.coordinates = list(self.representation.GetWorldPosition())
        self.modified = True
        print(f"Point moved to: {self.coordinates}")


class PointListItemWidget(QWidget):
    def __init__(self, name, point, manager):
        super().__init__()
        self.manager = manager
        self.point = point
        self.name = name

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.point.visible)
        self.checkbox.stateChanged.connect(self.toggle_visibility)
        self.layout.addWidget(self.checkbox)

        # Color patch for the point
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked
        self.layout.addWidget(self.color_patch)

        # Label for the point name
        self.label = QLabel(name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_name_editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = QLineEdit(name)
        self.edit_name.setToolTip("Edit the point name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_name_editor)
        self.edit_name.editingFinished.connect(self.deactivate_name_editor)
        self.edit_name.textChanged.connect(self.validate_name)
        self.layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this point")
        self.remove_button.clicked.connect(self.remove_point_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def remove_point_clicked(self):
        """Remove the layer when the 'x' button is clicked."""
        self.manager.remove_point_by_name(self.name)

    def toggle_visibility(self, state):
        self.point.visible = state == Qt.Checked
        self.point.set_visibility(self.point.visible)
        self.manager.on_point_changed(self.name)

    def get_color_hex_string(self):
        color = self.point.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        current_color = QColor(self.point.color[0], self.point.color[1], self.point.color[2])
        color = QColorDialog.getColor(current_color, self, "Select Point Color")

        if color.isValid():
            c = [color.red(), color.green(), color.blue()]
            self.point.color = c
            self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
            self.point.representation.GetProperty().SetColor(c[0] / 255, c[1] / 255, c[2] / 255)
            self.manager.on_point_changed(self.name)

    def activate_name_editor(self, event):
        self.label.hide()
        self.edit_name.setText(self.label.text())
        self.edit_name.show()
        self.edit_name.setFocus()
        self.edit_name.selectAll()

    def deactivate_name_editor(self):
        new_name = self.edit_name.text()
        self.validate_name()

        if self.edit_name.toolTip() == "":
            self.label.setText(new_name)
            self.name = new_name

        self.label.show()
        self.edit_name.hide()

    def validate_name(self):
        print('==== validate_name() ====')
        new_name = self.edit_name.text()

        print(f'new_name={new_name}')
        invalid_chars = r'<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars) or new_name.strip() == "":
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Point name contains invalid characters or is empty.")
            print("Point name contains invalid characters or is empty.")
            return

        existing_names = [name for name in self.manager.points.keys() if name != self.name]
        print(f'existing_names={existing_names}')
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Point name must be unique.")
            return

        self.edit_name.setStyleSheet("")
        self.edit_name.setToolTip("")

        self.update_point_name(new_name)
        self.name = new_name
        self.label.setText(new_name)
    
    def update_point_name(self, new_name):
        """Update the layer name in the viewer."""
        if new_name != self.name:
            
            self.manager.points[new_name] = self.manager.points.pop(self.name)
            
            # if the current layer is the active layer, update the active layer name as well
            if self.manager.active_point_name == self.name:
                self.manager.active_point_name = new_name
            
            self.name = new_name

            self.manager.on_point_changed(new_name)


class PointListManager(QObject):
    log_message = pyqtSignal(str, str)  # For emitting log messages

    def __init__(self, vtk_viewer, name):
        super().__init__()
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.points = {}  # List of Point objects
        self.active_point_name = None
        self.name = name

        self._modified = False

        self.color_rotator = ColorRotator()

    def reset_modified(self):
        self._modified = False
        for _, data in self.points.items():
            data.modified = False


    def modified(self):
        if self._modified:
            return True

        for name, point in self.points.items():
            if point.modified:
                return True
            
        return False

    def setup_ui(self):
        """Set up the UI with a dockable widget."""
        dock = QDockWidget(self.name)
        widget = QWidget()
        layout = QVBoxLayout()

        # List widget for points
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_current_item_changed)
        layout.addWidget(self.list_widget)

        # Buttons to manage points
        button_layout = QHBoxLayout()
        add_point_button = QPushButton("Add Point")
        add_point_button.clicked.connect(self.add_point_clicked)
        button_layout.addWidget(add_point_button)

        edit_point_button = QPushButton("Edit Points")
        edit_point_button.clicked.connect(self.edit_points_clicked)
        button_layout.addWidget(edit_point_button)

        layout.addLayout(button_layout)
        widget.setLayout(layout)
        dock.setWidget(widget)

        # no toolbar
        toolbar = None

        self.toolbar = None
        self.dock_widget = dock

        return toolbar, dock

    def get_exclusive_actions(self):
        return []

    def generate_unique_name(self, base_name="Point"):
        index = 1
        while f"{base_name} {index}" in self.points:
            index += 1
        return f"{base_name} {index}"
    
    def add_point(self, coordinates, color=[255, 0, 0], visible=True, name=None):
        """Add a new editable point."""
        editable_point = PointItem(
            coordinates=coordinates,
            color=color,
            visible=visible,
            renderer=self.vtk_renderer,
            interactor=self.vtk_viewer.interactor
        )

        if name is None:
            name = self.generate_unique_name()

        self.points[name]= editable_point

        item_widget = PointListItemWidget(name, editable_point, self)
        item = QListWidgetItem()
        item.data = editable_point
        item.setSizeHint(item_widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        self.list_widget.setCurrentItem(item)
        
        self._modified = True

        self.log_message.emit("INFO", f"Added point at {coordinates}")

    def edit_points_clicked(self):
        """Toggle editing mode for points."""
        self.editing_points_enabled = not self.editing_points_enabled
        for point in self.points:
            point.set_visibility(self.editing_points_enabled)
        self.log_message.emit("INFO", f"Point editing {'enabled' if self.editing_points_enabled else 'disabled'}.")

    def on_point_changed(self, name):
        self._modified = True
        self.vtk_renderer.GetRenderWindow().Render()

    def edit_point(self, index, new_coordinates=None, new_color=None, new_visibility=None):
        """Edit a point's properties."""
        if index is not None and 0 <= index < len(self.points):
            point = self.points[index]

            if new_coordinates:
                point.coordinates = new_coordinates
                point.actor.SetPosition(*new_coordinates)

            if new_color:
                point.color = new_color
                point.actor.GetProperty().SetColor(new_color[0] / 255, new_color[1] / 255, new_color[2] / 255)

            if new_visibility is not None:
                point.visible = new_visibility
                point.actor.SetVisibility(new_visibility)

            point.modified = True
            self._modified = True
            self.vtk_viewer.get_render_window().Render()
            self.log_message.emit("INFO", f"Edited point {index}")


    def on_current_item_changed(self, current, previous):
        """Handle point selection in the list widget."""
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, PointListItemWidget):

                point = item_widget.point
                name = item_widget.name

                # turn off all others    
                for key in self.points:
                    if name is not key:
                        self.points[key].set_highlight(False)
                    
                # turn on the selected point
                point.set_highlight(True)

                if self.active_point_name != name:
                    self.active_point_name = name
                    print(f"Point {name} selected")

                self.vtk_renderer.GetRenderWindow().Render()

    def add_point_clicked(self):
        """Handle the 'Add Point' button click."""
        # Add a point at the center of the current view
        camera = self.vtk_renderer.GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        
        # move closer to camera, so that it's visible.
        focal_point = [focal_point[0], focal_point[1], focal_point[2]+1.0]
        
        name = self.generate_unique_name()

        self.add_point(coordinates=focal_point, color=self.color_rotator.next(), visible=True, name=name)

        self._modified = True

    

    def remove_point_by_name(self, name):
        
        if name in self.points:
            
            item, item_widget = self.find_list_widget_item_by_text(name)

            if item is not None:
                point = item_widget.point

                # Disable the point's widget and remove it
                #from vtk_tools import remove_widget
                #remove_widget(point.widget, self.vtk_renderer)
                #point.widget.EnabledOff()
                point.destroy()

                # Remove from the data list
                del self.points[name]

                # Remove from the list widget
                self.list_widget.takeItem(self.list_widget.row(item))

                # Select the last item in the list widget (to activate it)
                if name == self.active_point_name and self.list_widget.count() > 0:
                    self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            
                self._modified = True
            else:
                logger.error(f'List item of name {name} not found!')
        else:
            logger.error(f'Remove point failed. the point with name {name} in the point list')
    
    def find_list_widget_item_by_text(self, text):
        """
        Find a QListWidgetItem in the list widget based on its text.

        :param list_widget: The QListWidget instance.
        :param text: The text of the item to find.
        :return: The matching QListWidgetItem or None if not found.
        """
        list_widget = self.list_widget

        for index in range(list_widget.count()):
            item = list_widget.item(index)
            item_widget = list_widget.itemWidget(item)

            if item_widget.name == text:
                return item, item_widget
        return None

    def save_state(self, data_dict, data_dir):
        """Save points to the state dictionary."""
        points_data = []
        for name in self.points:
            point = self.points[name]
            points_data.append({
                "name": name,
                "coordinates": point.coordinates,
                "color": point.color,
            })
        data_dict["points"] = points_data

    def load_state(self, data_dict, data_dir, aux_data):
        """Load points from the state dictionary."""
        self.clear()
        for point_data in data_dict.get("points", []):
            self.add_point(
                coordinates=point_data["coordinates"],
                color=point_data["color"],
                visible= True,
                name=point_data["name"]
            )
        
    def clear(self):
        if len(self.points) == 0:
            return 
        
        """Clear all points."""
        for name in self.points:
            point = self.points[name]
            # Disable the point's widget and remove it
            point.widget.EnabledOff()

        self.points = {}
        self._modified = False
        self.list_widget.clear()
        self.vtk_viewer.get_render_window().Render()