

import vtk
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QListWidgetItem, QToolBar, QAction, QToolButton, QVBoxLayout, QPushButton, QLabel, QWidget, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit)
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor

from logger import logger
from color_rotator import ColorRotator

import numpy as np
import math

from vtk_tools import from_vtk_color, to_vtk_color


class PaintBrush:
    def __init__(self, radius_in_pixel=(20,20), pixel_spacing=(1.0, 1.0), color= (0,255,0), line_thickness= 1):
        self.radius_in_pixel = radius_in_pixel
        self.pixel_spacing = pixel_spacing

        # Paintbrush setup
        self.enabled = False

        # Brush actor for visualization
        self.brush_actor = vtk.vtkActor()
        self.brush_actor.SetVisibility(False)  # Initially hidden

        # Create a green brush representation
        # Create a 2D circle for brush visualization
        self.brush_source = vtk.vtkPolyData()
        self.circle_points = vtk.vtkPoints()
        self.circle_lines = vtk.vtkCellArray()


        self.brush_source.SetPoints(self.circle_points)
        self.brush_source.SetLines(self.circle_lines)
        self.brush_mapper = vtk.vtkPolyDataMapper()
        self.brush_mapper.SetInputData(self.brush_source)
        self.brush_actor.SetMapper(self.brush_mapper)
        self.brush_actor.GetProperty().SetColor(color[0], color[1], color[2])  

        self.set_radius_in_pixel(radius_in_pixel, pixel_spacing=(1.0, 1.0))
    def get_actor(self):
        return self.brush_actor
    
    def set_color(self, color_vtk):
        if hasattr(self, 'brush_actor') and self.brush_actor is not None:
            self.brush_actor.GetProperty().SetColor(color_vtk[0], color_vtk[1], color_vtk[2]) 

    def set_radius_in_pixel(self, radius_in_pixel, pixel_spacing):
        
        self.radius_in_pixel = radius_in_pixel
        self.pixel_spacing = pixel_spacing

        radius_in_real = (radius_in_pixel[0] * pixel_spacing[0], radius_in_pixel[1] * pixel_spacing[1])

        self.update_circle_geometry(radius_in_real)

    def update_circle_geometry(self, radius_in_real):
        """Update the circle geometry to reflect the current radius."""
        self.circle_points.Reset()
        self.circle_lines.Reset()

        num_segments = 50  # Number of segments for the circle
        for i in range(num_segments):
            angle = 2.0 * math.pi * i / num_segments
            x = radius_in_real[0] * math.cos(angle)
            y = radius_in_real[1] * math.sin(angle)
            self.circle_points.InsertNextPoint(x, y, 0)

            # Connect the points to form a circle
            if i > 0:
                line = vtk.vtkLine()
                line.GetPointIds().SetId(0, i - 1)
                line.GetPointIds().SetId(1, i)
                self.circle_lines.InsertNextCell(line)

        # Close the circle
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, num_segments - 1)
        line.GetPointIds().SetId(1, 0)
        self.circle_lines.InsertNextCell(line)

        # Notify VTK that the geometry has been updated
        self.circle_points.Modified()
        self.circle_lines.Modified()
        self.brush_source.Modified()


    def paint(self, segmentation, x, y, value=1):
        """Draw a circle on the segmentation at (x, y) with the given radius."""
        dims = segmentation.GetDimensions()
        scalars = segmentation.GetPointData().GetScalars()
        extent = segmentation.GetExtent()

        # radius in pixel space
        radius_in_pixelx = self.radius_in_pixel[0]
        radius_in_pixely = self.radius_in_pixel[1]

        for i in range(-radius_in_pixelx, radius_in_pixelx + 1):
            for j in range(-radius_in_pixely, radius_in_pixely + 1):
                
                # Check if the pixel is within the circle
                if ((i/radius_in_pixelx)**2 + (j/radius_in_pixely)**2) <= 1.0:
                    xi = x + i
                    yj = y + j
                    if extent[0] <= xi <= extent[1] and extent[2] <= yj <= extent[3]:
                        idx = (yj - extent[2]) * dims[0] + (xi - extent[0])
                        scalars.SetTuple1(idx, value)

class SegmentationItem:
    def __init__(self, segmentation, visible=True, color=np.array([255, 255, 128]), alpha=0.5, actor=None) -> None:
        self.segmentation = segmentation
        self.visible = visible
        self.color = color
        self.alpha = alpha
        self.actor = actor
        self.modified = False

from line_edit2 import LineEdit2

class SegmentationListItemWidget(QWidget):
    
    def get_viewer(self):
        return self.manager
    
    def __init__(self, layer_name, layer_data, manager):
        super().__init__()
        self.manager = manager
        self.layer_name = layer_name
        self.layer_data = layer_data

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.visible_checkbox_clicked)
        self.layout.addWidget(self.checkbox)

        # Color patch for layer
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked  # Assign event for color change
        self.layout.addWidget(self.color_patch)

        # Label for the layer name
        self.label = QLabel(layer_name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_editor  # Assign double-click to activate editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = LineEdit2(layer_name)
        self.edit_name.focus_out_callback = self.focusOutEvent
        self.edit_name.setToolTip("Edit the layer name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_editor)  # Commit name on Enter
        self.edit_name.editingFinished.connect(self.deactivate_editor)  # Commit name on losing focus
        self.edit_name.textChanged.connect(self.validate_name)
        self.layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this layer")
        self.remove_button.clicked.connect(self.remove_layer_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def remove_layer_clicked(self):
        """Remove the layer when the 'x' button is clicked."""
        self.manager.remove_segmentation_by_name(self.layer_name)

    def visible_checkbox_clicked(self, state):
        visibility = state == Qt.Checked
        self.layer_data.visible = visibility
        self.layer_data.actor.SetVisibility(visibility)
        self.manager.on_layer_changed(self.layer_name)

    def get_layer_color_hex(self):
        """Convert the layer's color (numpy array) to a hex color string."""
        color = self.layer_data.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        
        """Open a color chooser dialog and update the layer's color."""
        # Get the current color in QColor format
        current_color = QColor(
            self.layer_data.color[0], 
            self.layer_data.color[1], 
            self.layer_data.color[2]
        )
        color = QColorDialog.getColor(current_color, self, "Select Layer Color")

        if color.isValid():
            
            c = [color.red(), color.green(), color.blue()]
            # Update layer color
            self.layer_data.color = c
            # Update color patch
            self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")
            # Notify the viewer to update rendering
            #self.parent_viewer.on_layer_chagned(self.layer_name)
            
            # lookup table of the image actor
            # Create a lookup table for coloring the segmentation
            lookup_table = vtk.vtkLookupTable()
            lookup_table.SetNumberOfTableValues(2)  # For 0 (background) and 1 (segmentation)
            lookup_table.SetTableRange(0, 1)       # Scalar range
            lookup_table.SetTableValue(0, 0, 0, 0, 0)  # Background: Transparent
            lookup_table.SetTableValue(1, c[0]/255, c[1]/255, c[2]/255, self.layer_data.alpha)  # Segmentation: Red with 50% opacity
            lookup_table.Build()
            
            mapper = vtk.vtkImageMapToColors()
            mapper.SetInputData(self.layer_data.segmentation)
            mapper.SetLookupTable(lookup_table)
            mapper.Update()

            actor = self.layer_data.actor
            actor.GetMapper().SetInputConnection(mapper.GetOutputPort())

            self.manager.on_layer_changed(self.layer_name)

            self.manager.print_status(f"Color changed to ({c[0]}, {c[1]}, {c[2]})")



    def focusOutEvent(self, event):
        """Deactivate the editor when it loses focus."""
        if self.edit_name.isVisible():
            self.deactivate_editor()
        super().focusOutEvent(event)

    def activate_editor(self, event):
        """Activate the name editor (QLineEdit) and hide the label."""
        self.label.hide()
        self.edit_name.setText(self.label.text())
        self.edit_name.show()
        self.edit_name.setFocus()
        self.edit_name.selectAll()  # Select all text for easy replacement

    def deactivate_editor(self):
        """Deactivate the editor, validate the name, and show the label."""

        new_name = self.edit_name.text()
        self.validate_name()

        # If valid, update the label and layer name
        if self.edit_name.toolTip() == "":
            self.label.setText(new_name)
            self.layer_name = new_name

        # Show the label and hide the editor
        self.label.show()
        self.edit_name.hide()

    def validate_name(self):
        """Validate the layer name for uniqueness and file system compatibility."""
        new_name = self.edit_name.text()

        # Check for invalid file system characters
        invalid_chars = r'<>:"/\|?*'
        if any(char in new_name for char in invalid_chars) or new_name.strip() == "":
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")  # Radish color
            self.edit_name.setToolTip("Layer name contains invalid characters or is empty.")
            return

        # Check for uniqueness
        existing_names = [name for name in self.manager.segmentation_layers.keys() if name != self.layer_name]
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")  # Radish color
            self.edit_name.setToolTip("Layer name must be unique.")
            return

        # Name is valid
        self.edit_name.setStyleSheet("")  # Reset background
        self.edit_name.setToolTip("")
        self.update_layer_name(new_name)


    def update_layer_name(self, new_name):
        """Update the layer name in the viewer."""
        if new_name != self.layer_name:
            
            self.manager.segmentation_layers[new_name] = self.manager.segmentation_layers.pop(self.layer_name)
            
            # if the current layer is the active layer, update the active layer name as well
            if self.manager.active_layer_name == self.layer_name:
                self.manager.active_layer_name = new_name
            
            self.layer_name = new_name

            self.manager.on_layer_changed(new_name)

from PyQt5.QtCore import pyqtSignal, QObject

from color_rotator import ColorRotator

class SegmentationListManager(QObject):
    # Signal to emit log messages
    log_message = pyqtSignal(str, str)  # Format: log_message(type, message)

    def __init__(self, vtk_viewer, name):
        super().__init__()  # Initialize QObject

        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.active_layer_name = None
        self.name = name

        # segmentation data
        self.segmentation_layers = {}
        self.active_layer_name = None

        self.paint_active = False
        self.paint_brush_color = [0,1,0]

        self.erase_active = False
        self.erase_brush_color = [0, 0.5, 1.0]

        self.paintbrush = None

        self.color_rotator = ColorRotator()

        self._modified = False

        logger.info("SegmentationListManager initialized")

    def get_vtk_viewer(self):
        return self.vtk_viewer
    
    def get_base_vtk_image(self):
        if self.vtk_viewer is None:
            return None
        
        return self.get_vtk_viewer().get_vtk_image()

    def get_segmentation_vtk_images(self):
        vtk_images = []
        for _, layer_data in self.segmentation_layers.items():
            vtk_images.append(layer_data.segmentation)
        return vtk_images
    
    def reset_modified(self):
        self._modified = False
        for _, data in self.segmentation_layers.items():
            data.modified = False
       
    def modified(self):
        if self._modified:
            return True
        
        for _, data in self.segmentation_layers.items():
            if data.modified:
                return True
        
        return False


    def setup_ui(self):   
        toolbar = self.create_toolbar()
        dock = self.create_dock_widget()

        self.toolbar = toolbar
        self.dock_widget = dock

        return None, dock

    def create_toolbar(self):
        
        from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon
        from labeled_slider import LabeledSlider

        # Create a toolbar
        toolbar = QToolBar("PaintBrush Toolbar")
     

        # Add Paint Tool button
        self.paint_action, self.paint_button = self.create_checkable_button("Paint", self.paint_active, toolbar, self.toggle_paint_tool)
        self.erase_action, self.erase_button = self.create_checkable_button("Erase", self.erase_active, toolbar, self.toggle_erase_tool)

        # paintbrush size slider
        self.brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        self.brush_size_slider.slider.setMinimum(3)
        self.brush_size_slider.slider.setMaximum(100)
        self.brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        toolbar.addWidget(self.brush_size_slider)

        return toolbar
    
    def create_dock_widget(self):
        
        # Create a dockable widget
        dock = QDockWidget(self.name)

        # Layer manager layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Layer list
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.list_widget_on_current_item_changed)
       
        # Enable Reordering
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDropIndicatorShown(True)
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
       
        main_layout.addWidget(self.list_widget)

        # Buttons to manage layers
        button_layout = QHBoxLayout()

        add_layer_button = QPushButton("Add Layer")
        add_layer_button.clicked.connect(self.add_layer_clicked)
        button_layout.addWidget(add_layer_button)
        
        # Add Paint Tool button
        self.paint_action, self.paint_button = self.create_checkable_button("Paint", self.paint_active, None, self.toggle_paint_tool)
        button_layout.addWidget(self.paint_button)

        self.erase_action, self.erase_button = self.create_checkable_button("Erase", self.erase_active, None, self.toggle_erase_tool)
        button_layout.addWidget(self.erase_button)

        # Add the button layout 
        main_layout.addLayout(button_layout)
        
        from labeled_slider import LabeledSlider
        brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        brush_size_slider.slider.setMinimum(3)
        brush_size_slider.slider.setMaximum(100)
        brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        main_layout.addWidget(brush_size_slider)
        
        # Set layout for the layer manager
        main_widget.setLayout(main_layout)
        
        dock.setWidget(main_widget)

        return dock

    def get_exclusive_actions(self):
        return [self.paint_action, self.erase_action]
    
    def clear(self):
        
        # remove actors
        for layer_name, layer_data in self.segmentation_layers.items():
            print(f"removing actor of layer {layer_name}")
            actor = layer_data.actor
            self.vtk_renderer.RemoveActor(actor)    
        
        self.vtk_image = None
        self._modified = False
        self.segmentation_layers.clear()
        self.list_widget.clear()


    def save_segmentation_layer(self, segmentation, file_path):
        from itkvtk import save_vtk_image_using_sitk
        save_vtk_image_using_sitk(segmentation, file_path)

    def save_state(self,data_dict, data_dir):
        import os
        # Save segmentation layers as '.mha'
        data_dict["segmentations"] = {}

        for layer_name, layer_data in self.segmentation_layers.items():
            segmentation_file = f"{layer_name}.mha"
            segmentation_path = os.path.join(data_dir, segmentation_file )
            self.save_segmentation_layer(layer_data.segmentation, segmentation_path)

            # Add layer metadata to the workspace data
            data_dict["segmentations"][layer_name] = {
                "file": segmentation_file,
                "color": list(layer_data.color),
                "alpha": layer_data.alpha,
            }

    def load_state(self, data_dict, data_dir, aux_data):
        import os

        self.clear()

        self.vtk_image = aux_data['base_image']

        # Load segmentation layers
        from itkvtk import load_vtk_image_using_sitk
        for layer_name, layer_metadata in data_dict.get("segmentations", {}).items():
            seg_path = os.path.join(data_dir, layer_metadata["file"])
            if os.path.exists(seg_path):
                try:
                    vtk_seg = load_vtk_image_using_sitk(seg_path)

                    self.add_layer(
                        segmentation=vtk_seg,
                        layer_name=layer_name,
                        color_vtk=to_vtk_color(layer_metadata["color"]),
                        alpha=layer_metadata["alpha"]
                    )
                    
                except Exception as e:
                    self.print_status(f"Failed to load segmentation layer {layer_name}: {e}")
            else:
                self.print_status(f"Segmentation file for layer {layer_name} not found.")

    def render(self):
        self.vtk_renderer.GetRenderWindow().Render()

    def on_layer_changed(self, layer_name):
        self._modified = True
        self.render()

    def get_active_layer(self):
        return self.segmentation_layers.get(self.active_layer_name, None)

    def enable_paintbrush(self, enabled=True):
        
        if self.paintbrush is None:
            self.paintbrush = PaintBrush()
            self.paintbrush.set_radius_in_pixel(radius_in_pixel=(20, 20), pixel_spacing=self.vtk_viewer.vtk_image.GetSpacing())
            self.vtk_viewer.get_renderer().AddActor(self.paintbrush.get_actor())

        self.paintbrush.enabled = enabled

        interactor = self.vtk_viewer.interactor 
        if enabled:
            self.left_button_press_observer = interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
            self.mouse_move_observer = interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)
            self.left_button_release_observer = interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        else:    
            interactor.RemoveObserver(self.left_button_press_observer)
            interactor.RemoveObserver(self.mouse_move_observer)
            interactor.RemoveObserver(self.left_button_release_observer)   
        
        self.left_button_is_pressed = False
        self.last_mouse_position = None
        
        print(f"Painbrush mode: {'enabled' if enabled else 'disabled'}")


    def paint_at_mouse_position(self):
        
        vtk_viewer = self.vtk_viewer
        vtk_image = vtk_viewer.vtk_image
        
        mouse_pos = vtk_viewer.interactor.GetEventPosition()
        picker = vtk.vtkWorldPointPicker()
        picker.Pick(mouse_pos[0], mouse_pos[1], 0, vtk_viewer.get_renderer())
        world_pos = picker.GetPickPosition()

        print(f"World position: ({world_pos[0]:.2f}, {world_pos[1]:.2f}, {world_pos[2]:.2f})"
              f"Mouse position: ({mouse_pos[0]:.2f}, {mouse_pos[1]:.2f})")
        
        dims = vtk_image.GetDimensions()
        spacing = vtk_image.GetSpacing()
        origin = vtk_image.GetOrigin()

        print(f"Image dimensions: {dims}")
        print(f"Image spacing: {spacing}")
        print(f"Image origin: {origin}")

        x = int((world_pos[0] - origin[0]) / spacing[0] + 0.49999999)
        y = int((world_pos[1] - origin[1]) / spacing[1] + 0.49999999)


        if not (0 <= x < dims[0] and 0 <= y < dims[1]):
            print(f"Point ({x}, {y}) is outside the image bounds.")
            return

        layer = self.get_active_layer()
        if layer is None:
            print("No active layer selected.")
            return

        segmentation = layer.segmentation
        
        # paint or erase
        if self.paint_active:
            value = 1
        else:
            value = 0

        self.paintbrush.paint(segmentation, x, y, value)
        
        segmentation.Modified() # flag vtkImageData as Modified to update the pipeline.
        
        self._modified = True
        self.render()

    def on_left_button_press(self, obj, event):
        if not self.paintbrush.enabled:
            return
        
        self.left_button_is_pressed = True
        self.last_mouse_position = self.vtk_viewer.interactor.GetEventPosition()
        
        if self.left_button_is_pressed and self.paintbrush.enabled and self.active_layer_name is not None:
            print('paint...')
            self.paint_at_mouse_position()
       
    def on_mouse_move(self, obj, event):
        if not self.paintbrush.enabled:
            return

        if self.paintbrush.enabled:
            mouse_pos = self.vtk_viewer.interactor.GetEventPosition()
            picker = vtk.vtkWorldPointPicker()
            picker.Pick(mouse_pos[0], mouse_pos[1], 0, self.vtk_viewer.get_renderer())

            # Get world position
            world_pos = picker.GetPickPosition()

            # Update the brush position (ensure Z remains on the image plane + 0.1 to show on top of the image)
            self.paintbrush.get_actor().SetPosition(world_pos[0], world_pos[1], world_pos[2] + 0.1)
            self.paintbrush.get_actor().SetVisibility(True)  # Make the brush visible

            if self.paint_active:
                self.paintbrush.set_color(self.paint_brush_color)
            else:
                self.paintbrush.set_color(self.erase_brush_color)

            # Paint 
            if self.left_button_is_pressed and self.paintbrush.enabled and self.active_layer_name is not None:
                print('paint...')
                self.paint_at_mouse_position()
        else:
            self.paintbrush.get_actor().SetVisibility(False)  # Hide the brush when not painting
       
    def on_left_button_release(self, obj, event):
        if not self.paintbrush.enabled:
            return
        
        self.left_button_is_pressed = False
        self.last_mouse_position = None

    def create_checkable_button(self, label, checked, toolbar, on_toggled_fn):
        action = QAction(label)
        action.setCheckable(True)  # Make it togglable
        action.setChecked(checked)  # Sync with initial state
        #action.triggered.connect(on_click_fn)
        action.toggled.connect(on_toggled_fn)

        # Create a QToolButton for the action
        button = QToolButton(toolbar)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setDefaultAction(action)

        # add to the toolbar
        if toolbar is not None:
            toolbar.addWidget(button)

        return action, button
 
    def update_button_style(self, button, checked):
        """Update the button's style to dim or brighten the icon."""
        if checked:
            button.setStyleSheet("QToolButton { opacity: 1.0; }")  # Normal icon
        else:
            button.setStyleSheet("QToolButton { opacity: 0.5; }")  # Dimmed icon

    def update_brush_size(self, value):
        self.paintbrush.set_radius_in_pixel(
            radius_in_pixel=(value, value), 
            pixel_spacing=self.get_base_image().GetSpacing())


    def list_widget_on_current_item_changed(self, current, previous):
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, SegmentationListItemWidget):
                # Access the layer_name from the custom widget
                layer_name = item_widget.layer_name
                if self.active_layer_name != layer_name:
                    self.active_layer_name = layer_name
                    self.print_status(f"Layer {layer_name} selected")
                    

    def toggle_paint_tool(self, checked):
        
        # no change, just return
        if self.paint_active == checked:
            return 
        
        # turn off both
        self.erase_action.setChecked(False)
        self.paint_action.setChecked(False)

        self.paint_active = checked
        self.paint_action.setChecked(checked)
        
        if self.paint_active:
            self.print_status("Paint tool activated")
        else:
            self.print_status("Paint tool deactivated")

        self.enable_paintbrush(self.paint_active or self.erase_active)

    def toggle_erase_tool(self, checked):
        
        # no change, just return
        if self.erase_active == checked:
            return 

        # turn off both
        self.erase_action.setChecked(False)
        self.paint_action.setChecked(False)

        self.erase_active = checked
        self.erase_action.setChecked(checked)

        if self.erase_active:
            self.print_status("Erase tool activated")
        else:
            self.print_status("Erase tool deactivated")    

        self.enable_paintbrush(self.paint_active or self.erase_active)

    def get_status_bar(self):
        return self._mainwindow.status_bar
    
    def print_status(self, msg):
        #if self.get_status_bar() is not None:
        #    self.get_status_bar().showMessage(msg)
    
        """
        Emit a log message with the specified type.
        log_type can be INFO, WARNING, ERROR, etc.
        """
        log_type = "INFO"
        self.log_message.emit(log_type, msg)

    def add_layer_widget_item(self, layer_name, layer_data):

        # Create a custom widget for the layer
        layer_item_widget = SegmentationListItemWidget(layer_name, layer_data, self)
        layer_item = QListWidgetItem(self.list_widget)
        layer_item.setSizeHint(layer_item_widget.sizeHint())
        self.list_widget.addItem(layer_item)
        self.list_widget.setItemWidget(layer_item, layer_item_widget) # This replaces the default text-based display with the custom widget that includes the checkbox and label.

        # set the added as active (do I need to indicate this in the list widget?)
        self.active_layer_name = layer_name
    
    def generate_unique_layer_name(self, base_name="Layer"):
        index = 1
        while f"{base_name} {index}" in self.segmentation_layers:
            index += 1
        return f"{base_name} {index}"
    
    def add_layer(self, segmentation, layer_name, color_vtk, alpha):
        actor = self.create_segmentation_actor(segmentation, color=color_vtk, alpha=alpha)
        layer_data = SegmentationItem(segmentation=segmentation, color=from_vtk_color(color_vtk), alpha=alpha, actor=actor)
        self.segmentation_layers[layer_name] = layer_data
        self.vtk_renderer.AddActor(actor)
        self.vtk_renderer.GetRenderWindow().Render()

        self.add_layer_widget_item(layer_name, layer_data)

        # Select the last item in the list widget (to activate it)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

        self._modified = True

    def add_layer_clicked(self):

        # Generate a random bright color for the new layer
        layer_color = self.color_rotator.next()

        # add layer data        
        layer_name = self.generate_unique_layer_name()
        
        # empty segmentation
        segmentation = self.create_empty_segmentation()

        self.add_layer(
            segmentation=segmentation, 
            layer_name=layer_name, 
            color_vtk=[layer_color[0]/255, layer_color[1]/255, layer_color[2]/255],
            alpha=0.8)
        
        self.print_status(f'A layer added: {layer_name}, and active layer is now {self.active_layer_name}')
        

    def remove_segmentation_by_name(self, layer_name):
        
        if layer_name in self.segmentation_layers:
            # remove actor
            actor = self.segmentation_layers[layer_name].actor
            self.vtk_renderer.RemoveActor(actor)

            # Remove from the data list
            del self.segmentation_layers[layer_name]

            # Remove from the list widget
            item, _ = self.find_list_widget_item_by_text(layer_name)
            if item is not None:
                self.list_widget.takeItem(self.list_widget.row(item))
            else:
                logger.error(f'Internal error! List item of {layer_name} is not found!')

            # Select the last item in the list widget (to activate it)
            if layer_name == self.active_layer_name and self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(self.list_widget.count() - 1)

            self._modified = True

            self.vtk_renderer.GetRenderWindow().Render()
        else:
            logger.error(f'Remove layer failed. the name {layer_name} given is not in the segmentation layer list')
    
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

            if item_widget.layer_name == text:
                return item, item_widget
        return None

    def remove_layer_clicked(self):
        #if len(self.list_widget) == 1:
        #        self.print_status("At least 1 layer is required.")
        #        return 

        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            widget = self.list_widget.itemWidget(item)
            layer_name = widget.layer_name
            self.remove_layer(layer_name)

        # render
        self.vtk_renderer.GetRenderWindow().Render()    

        self._modified = True

        self.print_status(f"Selected layers removed successfully. The acive layer is now {self.active_layer_name}")


    def toggle_visibility(self):
        """Toggle the visibility of the selected layer."""
        current_item = self.list_widget.currentItem()
        if current_item:
            layer_name = current_item.text()
            actor = self.segments[layer_name]['actor']
            visibility = actor.GetVisibility()
            actor.SetVisibility(not visibility)
            print(f"Toggled visibility for layer: {layer_name} (Visible: {not visibility})")

    def get_base_image(self):
        return self.vtk_viewer.vtk_image
    
    def create_empty_segmentation(self):
        """Create an empty segmentation as vtkImageData with the same geometry as the base image."""
        
        image_data = self.get_base_image() 
        
        if image_data is None:
            raise ValueError("Base image data is not loaded. Cannot create segmentation.")

        # Get properties from the base image
        dims = image_data.GetDimensions()
        spacing = image_data.GetSpacing()
        origin = image_data.GetOrigin()
        direction_matrix = image_data.GetDirectionMatrix()

        # Create a new vtkImageData object for the segmentation
        segmentation = vtk.vtkImageData()
        segmentation.SetDimensions(dims)
        segmentation.SetSpacing(spacing)
        segmentation.SetOrigin(origin)
        segmentation.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)  # Single component for segmentation
        segmentation.GetPointData().GetScalars().Fill(0)  # Initialize with zeros

        # Set the direction matrix if supported
        if hasattr(segmentation, 'SetDirectionMatrix') and direction_matrix is not None:
            segmentation.SetDirectionMatrix(direction_matrix)

        return segmentation

    def create_segmentation_actor(self, segmentation, color=(1, 0, 0), alpha=0.8):
        """Create a VTK actor for a segmentation layer."""
        # Create a lookup table for coloring the segmentation
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(2)  # For 0 (background) and 1 (segmentation)
        lookup_table.SetTableRange(0, 1)       # Scalar range
        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # Background: Transparent
        lookup_table.SetTableValue(1, color[0], color[1], color[2], alpha)  # Segmentation: Red with 50% opacity
        lookup_table.Build()
        
        mapper = vtk.vtkImageMapToColors()
        mapper.SetInputData(segmentation)
        mapper.SetLookupTable(lookup_table)
        mapper.Update()

        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
              
        return actor
