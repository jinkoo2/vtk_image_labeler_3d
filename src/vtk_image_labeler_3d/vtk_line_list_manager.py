
import vtk
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QListWidgetItem, QVBoxLayout, QPushButton, QLabel, QWidget, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit)
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor

from logger import logger
from color_rotator import ColorRotator

class LineItem:
    def __init__(self, point1_w, point2_w, color=[255, 0, 0], width=1.0, visible=True, renderer=None, interactor=None):
        self.point1_w = point1_w
        self.point2_w = point2_w
        self.color = color
        self.visible = visible
        self.modified = False
        self.width = width
        self.renderer = renderer

        # Create a line representation
        self.representation = vtk.vtkLineRepresentation()
        self.representation.SetPoint1WorldPosition(self.point1_w)
        self.representation.SetPoint2WorldPosition(self.point2_w)
        self.representation.GetLineProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)
        self.representation.GetLineProperty().SetLineWidth(self.width)

        # Create a line widget
        self.widget = vtk.vtkLineWidget2()
        self.widget.SetRepresentation(self.representation)

        # Add observer for interaction
        self.on_interaction_observer_id = self.widget.AddObserver("InteractionEvent", self.on_interaction)

        # Add the widget to the interactor
        if interactor:
            self.widget.SetInteractor(interactor)
            self.widget.On()

    def destroy(self):
        from vtk_tools import remove_widget
        remove_widget(self.widget, self.renderer)

        # Delete the representation
        if self.representation:
            self.representation = None

        # Clear attributes to help garbage collection
        self.point1_w = None
        self.point2_w = None
        self.color = None
        self.width = None
        self.visible = None

        print("LineItem successfully destroyed.")
        
    def set_highlight(self, highlighted):
        """Highlight or unhighlight the line."""
        representation = self.widget.GetRepresentation()
        if highlighted:
            representation.GetLineProperty().SetLineWidth(self.width * 2.0)  # Increase width for highlighting
        else:
            representation.GetLineProperty().SetLineWidth(self.width)
            
    def set_visibility(self, visible):
        self.visible = visible
        self.widget.EnabledOn() if visible else self.widget.EnabledOff()

    def set_color(self, color):
        self.color = color
        self.modified = True
        self.representation.GetLineProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

    def on_interaction(self, obj, event):
        self.point1_w = self.representation.GetPoint1WorldPosition()
        self.point2_w = self.representation.GetPoint2WorldPosition()
        self.modified = True


class LineListItemWidget(QWidget):
    def __init__(self, name, line, manager):
        super().__init__()
        self.manager = manager
        self.line = line
        self.name = name

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.line.visible)
        self.checkbox.stateChanged.connect(self.toggle_visibility)
        self.layout.addWidget(self.checkbox)

        # Color patch for the line
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked
        self.layout.addWidget(self.color_patch)

        # Label for the line name
        self.label = QLabel(name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_name_editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = QLineEdit(name)
        self.edit_name.setToolTip("Edit the line name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_name_editor)
        self.edit_name.editingFinished.connect(self.deactivate_name_editor)
        self.edit_name.textChanged.connect(self.validate_name)
        self.layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this line")
        self.remove_button.clicked.connect(self.remove_line_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def toggle_visibility(self, state):
        self.line.set_visibility(state == Qt.Checked)
        self.manager.on_line_changed(self.name)

    def get_color_hex_string(self):
        color = self.line.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        current_color = QColor(self.line.color[0], self.line.color[1], self.line.color[2])
        color = QColorDialog.getColor(current_color, self, "Select Line Color")

        if color.isValid():
            c = [color.red(), color.green(), color.blue()]
            self.line.set_color(c)
            self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
            self.manager.on_line_changed(self.name)

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
        new_name = self.edit_name.text()
        invalid_chars = r'<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars) or new_name.strip() == "":
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Line name contains invalid characters or is empty.")
            return

        existing_names = [name for name in self.manager.lines.keys() if name != self.name]
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Line name must be unique.")
            return

        self.edit_name.setStyleSheet("")
        self.edit_name.setToolTip("")
        self.manager.update_line_name(self.name, new_name)

    def remove_line_clicked(self):
        self.manager.remove_line_by_name(self.name)


class LineListManager(QObject):
    log_message = pyqtSignal(str, str)  # For emitting log messages

    def __init__(self, vtk_viewer, name):
        super().__init__()
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.lines = {}  # Dictionary of LineItem objects
        self.active_line_name = None
        self.name = name

        self.color_rotator = ColorRotator()

        self._modified = False

    def clear(self):

        if len(self.lines) == 0:
            return 

        """Clear all lines and their widgets."""
        for name, line in list(self.lines.items()):  # Use list to avoid mutation during iteration
            self.remove_line_by_name(name)  # Properly remove each line

        self.lines.clear()  # Clear the dictionary
        self.list_widget.clear()  # Clear the list widget
        self._modified = False  # Reset the modified flag
        self.vtk_renderer.GetRenderWindow().Render()  # Refresh the renderer

        self.log_message.emit("INFO", "All lines cleared.")

    def setup_ui(self):
        """Set up the UI with a dockable widget."""
        dock = QDockWidget(self.name)
        widget = QWidget()
        layout = QVBoxLayout()

        # List widget for lines
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_current_item_changed)
        layout.addWidget(self.list_widget)

        # Buttons to manage lines
        button_layout = QHBoxLayout()

        add_line_button = QPushButton("Add Line")
        add_line_button.clicked.connect(self.add_line_clicked)
        button_layout.addWidget(add_line_button)

        layout.addLayout(button_layout)
        widget.setLayout(layout)
        dock.setWidget(widget)

        self.toolbar = None
        self.dock_widget = dock

        return None, dock

    def get_exclusive_actions(self):
        """Return an empty list of exclusive actions."""
        return []

    def on_current_item_changed(self, current, previous):
        """Handle line selection in the list widget."""
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, LineListItemWidget):
                # Get the line and name from the widget
                line = item_widget.line
                name = item_widget.name

                # Deselect all other lines
                for name2 in self.lines:
                    if name is not name2:
                        self.lines[name2].set_highlight(False)
                        
                # Highlight and enable the selected line
                line.widget.On()  # Enable interaction for the selected line
                line.set_highlight(True)

                # Update the active line name
                self.active_line_name = name
                print(f"Line {name} selected")

                # Render the updated scene
                self.vtk_viewer.get_render_window().Render()
                
    def generate_unique_name(self, base_name="Line"):
        index = 1
        while f"{base_name} {index}" in self.lines:
            index += 1
        return f"{base_name} {index}"

    def add_line_clicked(self):
        """Handle the 'Add Line' button click."""
        # Determine the center of the current view
        renderer = self.vtk_viewer.get_renderer()
        camera = renderer.GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        view_extent = camera.GetParallelScale()  # Approximate size of the visible area

        # Calculate start and end points for the new line
        point1_w = [
            focal_point[0] - view_extent / 6,
            focal_point[1],
            focal_point[2] + 1.0,  # Slightly above the focal plane
        ]
        point2_w = [
            focal_point[0] + view_extent / 6,
            focal_point[1],
            focal_point[2] + 1.0,  # Slightly above the focal plane
        ]

        # Generate a unique name for the new line
        line_name = self.generate_unique_name()

        # Add the new line
        self.add_line(
            point1_w=point1_w,
            point2_w=point2_w,
            color=self.color_rotator.next(),  # Generate a new color
            name=line_name,
        )

        # Log the addition
        self.log_message.emit("INFO", f"Added line {line_name}")
        
    def add_line(self, point1_w, point2_w, color=[255, 0, 0], visible=True, width=1.0, name=None):
        line = LineItem(point1_w=point1_w, point2_w=point2_w, color=color, width=width, visible=visible, renderer=self.vtk_renderer, interactor=self.vtk_viewer.interactor)
        if name is None:
            name = self.generate_unique_name()

        self.lines[name] = line

        item_widget = LineListItemWidget(name, line, self)
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        self.list_widget.setCurrentItem(item)
        
        self._modified = True

        self.log_message.emit("INFO", f"Added line: pt1={point1_w}, pt2={point2_w}")

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

    def remove_line_by_name(self, name):
        
        if name in self.lines:
            
            item, item_widget = self.find_list_widget_item_by_text(name)

            if item is not None:
                line = item_widget.line

                # Disable the line widget and remove it
                #from vtk_tools import remove_widget
                #remove_widget(line.widget, self.vtk_renderer)
                line.destroy()

                # Remove from the data list
                del self.lines[name]

                # Remove from the list widget
                self.list_widget.takeItem(self.list_widget.row(item))

                # Select the last item in the list widget (to activate it)
                if name == self.active_line_name and self.list_widget.count() > 0:
                    self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            
                self._modified = True
            else:
                logger.error(f'List item of name {name} not found!')
        else:
            logger.error(f'Remove line failed. the line with name {name} in the line list')
    

    def on_line_changed(self, name):
        self.vtk_renderer.GetRenderWindow().Render()

    def update_line_name(self, old_name, new_name):
        if old_name in self.lines:
            self.lines[new_name] = self.lines.pop(old_name)

    def save_state(self, data_dict, data_dir):
        """Save the state of all lines to the workspace."""
        lines_data = []
        for name, line in self.lines.items():
            lines_data.append({
                "name": name,
                "point1_w": list(line.representation.GetPoint1WorldPosition()),
                "point2_w": list(line.representation.GetPoint2WorldPosition()),
                "color": line.color,
                "width": line.width,
                "visible": line.visible,
            })
        data_dict["lines"] = lines_data
        self.reset_modified()  # Reset modified state after saving
        self.log_message.emit("INFO", "Lines state saved successfully.")

    def load_state(self, data_dict, data_dir, aux_data):
        """Load the state of all lines from the workspace."""
        self.clear()  # Clear existing lines before loading new ones

        if "lines" not in data_dict:
            self.log_message.emit("WARNING", "No lines found in workspace to load.")
            return

        for line_data in data_dict["lines"]:
            try:
                name = line_data["name"]
                point1_w = line_data["point1_w"]
                point2_w = line_data["point2_w"]
                color = line_data["color"]
                width = line_data["width"]
                visible = line_data["visible"]

                # Add the line to the manager
                self.add_line(point1_w=point1_w, point2_w=point2_w, color=color, width=width, visible=True, name=name)

            except Exception as e:
                self.log_message.emit("ERROR", f"Failed to load line {line_data.get('name', 'Unnamed')}: {str(e)}")

        self._modified = False  # Reset modified state after loading
        self.log_message.emit("INFO", "Lines state loaded successfully.")

    def reset_modified(self):
        self._modified = False
        for _, data in self.lines.items():
            data.modified = False

    def modified(self):
        if self._modified:
            return True

        for _, line in self.lines.items():
            if line.modified:
                return True
            
        return False
    