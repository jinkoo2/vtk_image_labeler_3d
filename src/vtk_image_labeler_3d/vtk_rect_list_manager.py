import vtk
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (QListWidgetItem, QVBoxLayout, QPushButton, QLabel, QWidget, QDockWidget, QListWidget, QHBoxLayout, QCheckBox, QLineEdit, QColorDialog)
from PyQt5.QtGui import QColor

from logger import logger
from color_rotator import ColorRotator

class RectItem:
    def __init__(self, corner1, corner2, min_size=[1.0, 1.0], color=[255, 0, 0], visible=True, renderer=None, interactor=None):
        self.corner1 = corner1
        self.corner2 = corner2
        self.min_size = min_size
        self.color = color
        self.visible = visible
        self.modified = False
        self.renderer = renderer
        self.interactor = interactor

        # Compute initial rectangle corners
        self.corners = self.calculate_corners(corner1, corner2)

        # Create handles for corners
        self.handles = [self.create_handle(i, corner, color, renderer, interactor) for i, corner in enumerate(self.corners)]

        # Create center handle
        self.center_handle = self.create_center_handle(color, renderer, interactor)


        # Store renderer and interactor for updates
        self.renderer = renderer
        self.interactor = interactor

        # Create rectangle actor
        self.rect_actor = self.create_rectangle_actor()

        self.set_color(self.color)

        renderer.AddActor(self.rect_actor)

    def destroy(self):
        # Remove handles from the renderer
        if self.renderer:
            for handle in self.handles:
                # Remove the handle representation if attached to the renderer
                if handle.GetRepresentation():
                    self.renderer.RemoveActor(handle.GetRepresentation())
                # Disconnect the handle widget from the interactor
                handle.SetInteractor(None)
                handle = None  # Clear the reference to the handle
            
            # Remove the center handle representation
            if self.center_handle.GetRepresentation():
                self.renderer.RemoveActor(self.center_handle.GetRepresentation())
            self.center_handle.SetInteractor(None)
            self.center_handle = None  # Clear the reference to the center handle

            # Remove rectangle actor
            if self.rect_actor:
                self.renderer.RemoveActor(self.rect_actor)
                self.rect_actor = None  # Clear the reference to the rectangle actor

        # Clear references to renderer and interactor
        self.renderer = None
        self.interactor = None

        # Reset other attributes (optional)
        self.handles = []
        self.center_handle = None

        print("RectItem successfully destroyed.")

    def create_center_handle(self, color, renderer, interactor):
        """Create a handle at the rectangle's center."""
        center = self.calculate_center()
        handle_rep = vtk.vtkPointHandleRepresentation3D()
        handle_rep.SetWorldPosition(center)
        handle_rep.GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

        handle_widget = vtk.vtkHandleWidget()
        handle_widget.SetRepresentation(handle_rep)
        handle_widget.SetInteractor(interactor)
        handle_widget.On()

        handle_widget.AddObserver("InteractionEvent", self.update_center)

        return handle_widget

    def update_center(self, obj, event):
        """Update the position of the rectangle when the center handle is moved."""
        new_center = self.center_handle.GetRepresentation().GetWorldPosition()
        old_center = self.calculate_center()

        dx = new_center[0] - old_center[0]
        dy = new_center[1] - old_center[1]

        # Update all corners
        for i, corner in enumerate(self.corners):
            self.corners[i] = [corner[0] + dx, corner[1] + dy, corner[2]]

        # Update handle positions
        for i, handle in enumerate(self.handles):
            handle.GetRepresentation().SetWorldPosition(self.corners[i])

        # Update rectangle actor
        self.update_rectangle()


    def calculate_center(self):
        """Calculate the center of the rectangle."""
        x_center = (self.corners[0][0] + self.corners[2][0]) / 2.0
        y_center = (self.corners[0][1] + self.corners[2][1]) / 2.0
        z_center = self.corners[0][2]  # Assuming 2D rectangle in the same Z-plane
        return [x_center, y_center, z_center]

    def calculate_corners(self, corner1, corner2):
        """Calculate all four corners of the rectangle given two diagonal corners."""
        x_min, x_max = min(corner1[0], corner2[0]), max(corner1[0], corner2[0])
        y_min, y_max = min(corner1[1], corner2[1]), max(corner1[1], corner2[1])
        z = corner1[2]  # Assuming a 2D rectangle in the same Z-plane

        # Enforce minimum size constraint
        if (x_max - x_min) < self.min_size[0]:
            x_center = (x_min + x_max) / 2.0
            x_min = x_center - self.min_size[0] / 2.0
            x_max = x_center + self.min_size[0] / 2.0

        if (y_max - y_min) < self.min_size[1]:
            y_center = (y_min + y_max) / 2.0
            y_min = y_center - self.min_size[1] / 2.0
            y_max = y_center + self.min_size[1] / 2.0

        return [
            [x_min, y_min, z],  # Bottom-left
            [x_max, y_min, z],  # Bottom-right
            [x_max, y_max, z],  # Top-right
            [x_min, y_max, z],  # Top-left
        ]

    def create_handle(self, index, position, color, renderer, interactor):
        """Create a handle at a given position."""
        handle_rep = vtk.vtkPointHandleRepresentation3D()
        handle_rep.SetWorldPosition(position)
        handle_rep.GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

        handle_widget = vtk.vtkHandleWidget()
        handle_widget.SetRepresentation(handle_rep)
        handle_widget.SetInteractor(interactor)
        handle_widget.On()

        # Attach different interaction event handlers based on corner index
        if index == 0:  # Bottom-left
            handle_widget.AddObserver("InteractionEvent", self.update_bottom_left)
        elif index == 1:  # Bottom-right
            handle_widget.AddObserver("InteractionEvent", self.update_bottom_right)
        elif index == 2:  # Top-right
            handle_widget.AddObserver("InteractionEvent", self.update_top_right)
        elif index == 3:  # Top-left
            handle_widget.AddObserver("InteractionEvent", self.update_top_left)

        return handle_widget

    def create_rectangle_actor(self):
        """Create the rectangle's outline using vtkPolyData."""
        points = vtk.vtkPoints()
        for corner in self.corners:
            points.InsertNextPoint(corner)

        # Create lines to form a rectangle
        lines = vtk.vtkCellArray()
        for i in range(4):
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, i)
            line.GetPointIds().SetId(1, (i + 1) % 4)  # Wrap around to the first point
            lines.InsertNextCell(line)

        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetLines(lines)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly_data)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self.color[0] / 255, self.color[1] / 255, self.color[2] / 255)
        return actor

    def update_bottom_left(self, obj, event):
        """Update rectangle when bottom-left corner is moved."""
        self.corners[0] = self.handles[0].GetRepresentation().GetWorldPosition()
        self.corners[1][1] = self.corners[0][1]  # Adjust bottom-right Y
        self.corners[3][0] = self.corners[0][0]  # Adjust top-left X
        self.update_rectangle()
       

    def update_bottom_right(self, obj, event):
        """Update rectangle when bottom-right corner is moved."""
        self.corners[1] = self.handles[1].GetRepresentation().GetWorldPosition()
        self.corners[0][1] = self.corners[1][1]  # Adjust bottom-left Y
        self.corners[2][0] = self.corners[1][0]  # Adjust top-right X
        self.update_rectangle()
        

    def update_top_right(self, obj, event):
        """Update rectangle when top-right corner is moved."""
        self.corners[2] = self.handles[2].GetRepresentation().GetWorldPosition()
        self.corners[1][0] = self.corners[2][0]  # Adjust bottom-right X
        self.corners[3][1] = self.corners[2][1]  # Adjust top-left Y
        self.update_rectangle()
        

    def update_top_left(self, obj, event):
        """Update rectangle when top-left corner is moved."""
        self.corners[3] = self.handles[3].GetRepresentation().GetWorldPosition()
        self.corners[0][0] = self.corners[3][0]  # Adjust bottom-left X
        self.corners[2][1] = self.corners[3][1]  # Adjust top-right Y
        self.update_rectangle()
        

    def update_rectangle(self):
        """Update rectangle shape and reposition handles."""
        # Enforce minimum size constraint and recalculate corners
        bottom_left = self.corners[0]
        top_right = self.corners[2]
        self.corners = self.calculate_corners(bottom_left, top_right)

        # Update handle positions
        for i, handle in enumerate(self.handles):
            handle.GetRepresentation().SetWorldPosition(self.corners[i])

        # Update the rectangle actor
        points = vtk.vtkPoints()
        for corner in self.corners:
            points.InsertNextPoint(corner)

        poly_data = self.rect_actor.GetMapper().GetInput()
        poly_data.SetPoints(points)
        poly_data.Modified()

        self.modified = True

        # Update center handle
        self.center_handle.GetRepresentation().SetWorldPosition(self.calculate_center())


    def set_visibility(self, visible):
        self.visible = visible
        for handle in self.handles:
            handle.EnabledOn() if visible else handle.EnabledOff()
        self.rect_actor.SetVisibility(visible)

    def set_color(self, color):
        self.color = color
        self.rect_actor.GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)
        for handle in self.handles:
            handle.GetRepresentation().GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

    def set_highlight(self, highlighted):
        """Highlight or unhighlight the rectangle by changing line width or color."""
        width = 3.0 if highlighted else 1.0  # Thicker lines for highlighting
        #color = [0, 255, 0] if highlighted else self.color  # Green for highlighting
        self.rect_actor.GetProperty().SetLineWidth(width)
        #self.set_color(color)


class RectListItemWidget(QWidget):
    def __init__(self, name, rect, manager):
        super().__init__()
        self.manager = manager
        self.rect = rect
        self.name = name

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.rect.visible)
        self.checkbox.stateChanged.connect(self.toggle_visibility)
        self.layout.addWidget(self.checkbox)

        # Color patch for the rectangle
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked
        self.layout.addWidget(self.color_patch)

        # Label for the rectangle name
        self.label = QLabel(name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_name_editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = QLineEdit(name)
        self.edit_name.setToolTip("Edit the rectangle name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_name_editor)
        self.edit_name.editingFinished.connect(self.deactivate_name_editor)
        self.edit_name.textChanged.connect(self.validate_name)
        self.layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this rectangle")
        self.remove_button.clicked.connect(self.remove_rect_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def toggle_visibility(self, state):
        self.rect.set_visibility(state == Qt.Checked)
        self.manager.on_rect_changed(self.name)

    def get_color_hex_string(self):
        color = self.rect.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        current_color = QColor(self.rect.color[0], self.rect.color[1], self.rect.color[2])
        color = QColorDialog.getColor(current_color, self, "Select Rectangle Color")

        if color.isValid():
            c = [color.red(), color.green(), color.blue()]
            self.rect.set_color(c)
            self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
            self.manager.on_rect_changed(self.name)

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
            self.edit_name.setToolTip("Rectangle name contains invalid characters or is empty.")
            return

        existing_names = [name for name in self.manager.rects.keys() if name != self.name]
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Rectangle name must be unique.")
            return

        self.edit_name.setStyleSheet("")
        self.edit_name.setToolTip("")
        self.manager.update_rect_name(self.name, new_name)

    def remove_rect_clicked(self):
        self.manager.remove_rect_by_name(self.name)
        

class RectListManager(QObject):
    log_message = pyqtSignal(str, str)  # For emitting log messages

    def __init__(self, vtk_viewer, name):
        super().__init__()
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.rects = {}  # Dictionary of RectItem objects
        self.active_rect_name = None
        self.name = name

        self._modified = False

    def clear(self):
        if len(self.rects) == 0:
            return 

        """Clear all rectangles and their widgets."""
        for name, rect in list(self.rects.items()):
            self.remove_rect_by_name(name)

        self.rects.clear()
        self.list_widget.clear()
        self.vtk_renderer.GetRenderWindow().Render()
        self.log_message.emit("INFO", "All rectangles cleared.")
        

    def setup_ui(self):
        """Set up the UI with a dockable widget."""
        dock = QDockWidget(self.name)
        widget = QWidget()
        layout = QVBoxLayout()

        # List widget for rectangles
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_current_item_changed)
        layout.addWidget(self.list_widget)

        # Buttons to manage rectangles
        button_layout = QHBoxLayout()

        add_rect_button = QPushButton("Add Rectangle")
        add_rect_button.clicked.connect(self.add_rect_clicked)
        button_layout.addWidget(add_rect_button)

        layout.addLayout(button_layout)
        widget.setLayout(layout)
        dock.setWidget(widget)

        self.toolbar = None
        self.dock_widget = dock

        return None, dock

    def on_current_item_changed(self, current, previous):
        if current:
            item_widget = self.list_widget.itemWidget(current)
            if item_widget:
                rect = item_widget.rect
                name = item_widget.name

                for key in self.rects:
                    if key is not name:
                        self.rects[key].set_highlight(False)

                rect.set_highlight(True)
                self.active_rect_name = name
                self.vtk_renderer.GetRenderWindow().Render()

    def get_exclusive_actions(self):
        return []

    def generate_unique_name(self, base_name="Rect"):
        index = 1
        while f"{base_name} {index}" in self.rects:
            index += 1
        return f"{base_name} {index}"

    def add_rect_clicked(self):
        renderer = self.vtk_viewer.get_renderer()
        camera = renderer.GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        view_extent = camera.GetParallelScale()

        corner1 = [
            focal_point[0] - view_extent / 4,
            focal_point[1] - view_extent / 4,
            focal_point[2]+0.1,
        ]
        corner2 = [
            focal_point[0] + view_extent / 4,
            focal_point[1] + view_extent / 4,
            focal_point[2]+0.1,
        ]

        rect_name = self.generate_unique_name()

        if not hasattr(self, 'color_rotator'):
            self.color_rotator = ColorRotator()
        
        self.add_rect(corner1=corner1, corner2=corner2, name=rect_name, color=self.color_rotator.next())

    def add_rect(self, corner1, corner2, color=[255, 0, 0], visible=True, name=None):
        rect = RectItem(corner1=corner1, corner2=corner2, color=color, visible=visible, renderer=self.vtk_renderer, interactor=self.vtk_viewer.interactor)
        if name is None:
            name = self.generate_unique_name()

        self.rects[name] = rect

        item_widget = RectListItemWidget(name, rect, self)
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())

        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        self.list_widget.setCurrentItem(item)

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

    def remove_rect_by_name(self, name):
        if name in self.rects:
            item, item_widget = self.find_list_widget_item_by_text(name)

            if item is not None:
                rect = item_widget.rect

                # Disable the line widget and remove it
                #from vtk_tools import remove_widget
                #remove_widget(line.widget, self.vtk_renderer)
                rect.destroy()

                # Remove from the data list
                del self.rects[name]

                # Remove from the list widget
                self.list_widget.takeItem(self.list_widget.row(item))

                # Select the last item in the list widget (to activate it)
                if name == self.active_rect_name and self.list_widget.count() > 0:
                    self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            
                self.vtk_renderer.GetRenderWindow().Render()  # Refresh the renderer
                
                self._modified = True
            else:
                logger.error(f'Rect item of name {name} not found!')
        else:
            logger.error(f'Remove rect failed. the line with name {name} in the line list')
    

    def update_rect_name(self, old_name, new_name):
        if old_name in self.rects:
            self.rects[new_name] = self.rects.pop(old_name)

    def on_rect_changed(self, name):
        self.vtk_renderer.GetRenderWindow().Render()

    def save_state(self, data_dict, data_dir):
        """Save the state of all rectangles to the workspace."""
        rects_data = []
        for name, rect in self.rects.items():
            rects_data.append({
                "name": name,
                "corner1": list(rect.corner1),
                "corner2": list(rect.corner2),
                "color": rect.color,
            })
        data_dict["rects"] = rects_data
        self.reset_modified()  # Reset modified state after saving
        self.log_message.emit("INFO", "Rectangles state saved successfully.")


    def load_state(self, data_dict, data_dir, aux_data):
        """Load the state of all rectangles from the workspace."""
        self.clear()  # Clear existing rectangles before loading new ones

        if "rects" not in data_dict:
            self.log_message.emit("WARNING", "No rectangles found in workspace to load.")
            return

        for rect_data in data_dict["rects"]:
            try:
                name = rect_data["name"]
                corner1 = rect_data["corner1"]
                corner2 = rect_data["corner2"]
                color = rect_data["color"]
                visible = True

                # Add the rectangle to the manager
                self.add_rect(corner1=corner1, corner2=corner2, color=color, visible=visible, name=name)

            except Exception as e:
                self.log_message.emit("ERROR", f"Failed to load rectangle {rect_data.get('name', 'Unnamed')}: {str(e)}")

        self._modified = False  # Reset modified state after loading
        self.log_message.emit("INFO", "Rectangles state loaded successfully.")

    def reset_modified(self):
        self._modified = False
        for _, rect in self.rects.items():
            rect.modified = False

    def modified(self):
        if self._modified:
            return True

        for _, rect in self.rects.items():
            if rect.modified:
                return True

        return False
