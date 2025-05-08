

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

import reslicer 

class PaintBrush:
    def __init__(self, radius_in_pixel=20, pixel_spacing=(1.0, 1.0), color= (0,255,0), line_thickness= 1, brush_3d=False, viewer=None):
        self.radius_in_pixel = radius_in_pixel
        self.pixel_spacing = pixel_spacing
        self.viewer = viewer

        # Paintbrush setup
        self.enabled = False

        self._brush_3d = brush_3d

        # Brush actor for visualization
        self.brush_actor = vtk.vtkFollower()
        camera = viewer.get_renderer().GetActiveCamera()
        self.brush_actor.SetCamera(camera) # camera to follow
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
    
    def set_enabled(self, enabled):
        self.enabled = enabled
        self.brush_actor.SetVisibility(enabled)  
 
    def set_color(self, color_vtk):
        if hasattr(self, 'brush_actor') and self.brush_actor is not None:
            self.brush_actor.GetProperty().SetColor(color_vtk[0], color_vtk[1], color_vtk[2]) 

    def set_brush_3d(self, flag):
        self._brush_3d = flag
    
    def get_brush_3d(self):
        return self._brush_3d

    def set_radius_in_pixel(self, radius_in_pixel, pixel_spacing=None):
        
        self.radius_in_pixel = radius_in_pixel
        
        if pixel_spacing:
            self.pixel_spacing = pixel_spacing
            radius_in_real = (radius_in_pixel * pixel_spacing[0], radius_in_pixel * pixel_spacing[1])
        else:
            radius_in_real = (radius_in_pixel * self.pixel_spacing[0], radius_in_pixel * self.pixel_spacing[1])

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

    def paint(self, segmentation, x, y, z=0, value=1):
        import reslicer
        axis = self.viewer.reslicer.axis

        if self._brush_3d:
            self.paint_3d(segmentation, x, y, z, value)
        else:
            if axis == reslicer.AXIAL:
                self.paint_ax(segmentation, x, y, z, value)
            elif axis == reslicer.CORONAL:
                self.paint_cr(segmentation, x, y, z, value)
            elif axis == reslicer.SAGITTAL:
                self.paint_sg(segmentation, x, y, z, value)
            else:
                raise Exception(f"Invalid axis: {self.viewer.axis}")

    def paint_ax(self, segmentation, x, y, z, value=1):
        """Draw a circle on the segmentation at (x, y) with the given radius."""
        dims = segmentation.GetDimensions()
        scalars = segmentation.GetPointData().GetScalars()
        extent = segmentation.GetExtent()

        # radius in pixel space
        radius_in_pixel = self.radius_in_pixel

        for i in range(-radius_in_pixel, radius_in_pixel + 1):
            for j in range(-radius_in_pixel, radius_in_pixel + 1):
                for k in [0]:
                
                    # Check if the pixel is within the circle
                    if ((i/radius_in_pixel)**2 + (j/radius_in_pixel)**2) <= 1.0:
                        xi = x + i
                        yj = y + j
                        zk = z + k
                        if extent[0] <= xi <= extent[1] and extent[2] <= yj <= extent[3] and extent[4] <= zk <= extent[5]:
                            idx = (zk - extent[4]) *  (dims[0] * dims[1])+(yj - extent[2]) * dims[0] + (xi - extent[0])
                            scalars.SetTuple1(idx, value)

    def paint_cr(self, segmentation, x, y, z, value=1):
        """Draw a circle on the segmentation at (x, y) with the given radius."""
        dims = segmentation.GetDimensions()
        scalars = segmentation.GetPointData().GetScalars()
        extent = segmentation.GetExtent()

        # radius in pixel space
        radius_in_pixel = self.radius_in_pixel

        for i in range(-radius_in_pixel, radius_in_pixel + 1):
            for j in [0]:
                for k in range(-radius_in_pixel, radius_in_pixel + 1):
                
                    # Check if the pixel is within the circle
                    if ((i/radius_in_pixel)**2 + (k/radius_in_pixel)**2) <= 1.0:
                        xi = x + i
                        yj = y + j
                        zk = z + k
                        if extent[0] <= xi <= extent[1] and extent[2] <= yj <= extent[3] and extent[4] <= zk <= extent[5]:
                            idx = (zk - extent[4]) *  (dims[0] * dims[1])+(yj - extent[2]) * dims[0] + (xi - extent[0])
                            scalars.SetTuple1(idx, value)

    def paint_sg(self, segmentation, x, y, z, value=1):
        """Draw a circle on the segmentation at (x, y) with the given radius."""
        dims = segmentation.GetDimensions()
        scalars = segmentation.GetPointData().GetScalars()
        extent = segmentation.GetExtent()

        # radius in pixel space
        radius_in_pixel = self.radius_in_pixel

        for i in [0]:
            for j in range(-radius_in_pixel, radius_in_pixel + 1):
                for k in range(-radius_in_pixel, radius_in_pixel + 1):
                
                    # Check if the pixel is within the circle
                    if ((j/radius_in_pixel)**2 + (k/radius_in_pixel)**2) <= 1.0:
                        xi = x + i
                        yj = y + j
                        zk = z + k
                        if extent[0] <= xi <= extent[1] and extent[2] <= yj <= extent[3] and extent[4] <= zk <= extent[5]:
                            idx = (zk - extent[4]) *  (dims[0] * dims[1])+(yj - extent[2]) * dims[0] + (xi - extent[0])
                            scalars.SetTuple1(idx, value)


    def paint_3d(self, segmentation, x, y, z, value=1):
        """Draw a circle on the segmentation at (x, y) with the given radius."""
        dims = segmentation.GetDimensions()
        scalars = segmentation.GetPointData().GetScalars()
        extent = segmentation.GetExtent()

        # radius in pixel space
        radius_in_pixel = self.radius_in_pixel

        for i in range(-radius_in_pixel, radius_in_pixel + 1):
            for j in range(-radius_in_pixel, radius_in_pixel + 1):
                for k in range(-radius_in_pixel, radius_in_pixel + 1):
                
                    # Check if the pixel is within the circle
                    if ((i/radius_in_pixel)**2 + (j/radius_in_pixel)**2 + (k/radius_in_pixel)**2) <= 1.0:
                        xi = x + i
                        yj = y + j
                        zk = z + k
                        if extent[0] <= xi <= extent[1] and extent[2] <= yj <= extent[3] and extent[4] <= zk <= extent[5]:
                            idx = (zk - extent[4]) *  (dims[0] * dims[1])+(yj - extent[2]) * dims[0] + (xi - extent[0])
                            scalars.SetTuple1(idx, value)

       
from PyQt5.QtCore import pyqtSignal, QObject

class SegmentationItem(QObject):

    visibility_changed = pyqtSignal(QObject)
    color_changed = pyqtSignal(QObject)
    name_changed = pyqtSignal(str, QObject)
    alpha_changed = pyqtSignal(QObject)

    def __init__(self, segmentation, visible=True, color=np.array([255, 255, 128]), alpha=0.5, actor=None, name="") -> None:
        super().__init__()

        self.segmentation = segmentation
        self._visible = visible
        self._color = color
        self._name = name
        self._alpha = alpha
        self._actor = actor
        self.modified = False

    def set_name(self, name):
        if self._name != name:
            old_value = self._name
            self._name = name
            self.name_changed.emit(old_value, self)
    
    def get_name(self):
        return self._name
    
    def set_color(self, color):
        if self._color != color:
            self._color = color
            self.color_changed.emit(self)
    
    def get_color(self):
        return self._color

    def get_vtk_color(self):
        return [self._color[0]/255, self._color[1]/255, self._color[2]/255]

    def set_visible(self, visible):
        if self._visible != visible:
            self._visible = visible
            self.visibility_changed.emit(self)
    
    def get_visible(self):
        return self._visible

    def set_alpha(self, alpha):
        if self._alpha != alpha:
            self._alpha = alpha
            self.alpha_changed.emit(self)
    
    def get_alpha(self):
        return self._alpha

    def set_actor(self, actor):
        if self._actor != actor:
            self._actor = actor
    
    def get_actor(self):
        return self._actor
    

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
        self.layer_data.set_visible(visibility)


    def get_layer_color_hex(self):
        """Convert the layer's color (numpy array) to a hex color string."""
        color = self.layer_data.get_color()
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        
        """Open a color chooser dialog and update the layer's color."""
        # Get the current color in QColor format
        c256 = self.layer_data.get_color()
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(c256[0], c256[1], c256[2]), self, "Select Layer Color")

        if color.isValid():
            
            c = [color.red(), color.green(), color.blue()]
            # Update layer color
            self.layer_data.set_color(c)

            # Update color patch
            self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")


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

            seg_item = self.layer_data

            # update seg item name
            seg_item.set_name(new_name)
            
            # update list widget name
            self.layer_name = new_name

from PyQt5.QtCore import pyqtSignal, QObject

from color_rotator import ColorRotator

class SegmentationListManager(QObject):
    # Signal to emit log messages
    log_message = pyqtSignal(str, str)  # Format: log_message(type, message)
    layer_added = pyqtSignal(str, QObject)
    layer_modified = pyqtSignal(str, QObject)
    layer_removed = pyqtSignal(str, QObject)

    active_layer_changed = pyqtSignal(str, str, QObject)

    layer_changed = pyqtSignal(str, QObject)
    
    def __init__(self, vtk_viewer, name):
        super().__init__()  # Initialize QObject

        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.name = name

        # segmentation data
        self.segmentation_layers = {}
        self.active_layer_name = None

        self.paint_active = False
        self.paint_brush_color = [0,1,0]

        self.erase_active = False
        self.erase_brush_color = [0, 0.5, 1.0]

        self.paintbrush_3d = False

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

        # 3d or 2d brush
        # Add a checkbox for 3D Brush option
        self.brush_3d_checkbox = QCheckBox("3D Brush")
        self.brush_3d_checkbox.setChecked(False)  # Default: unchecked
        self.brush_3d_checkbox.stateChanged.connect(self.on_brush_3d_toggled)
        main_layout.addWidget(self.brush_3d_checkbox)
        
        # Set layout for the layer manager
        main_widget.setLayout(main_layout)
        
        dock.setWidget(main_widget)

        return dock

    def on_brush_3d_toggled(self, state):
        self.paintbrush_3d = (state == Qt.Checked)
        print(f"3D Brush enabled: {self.paintbrush_3d}")
        
        # if viewers have paintbrushs, update
        for v in self.vtk_viewer.get_viewers_2d():
            if hasattr(v, 'paintbrush') and v.paintbrush is not None:
                v.paintbrush.set_brush_3d(self.paintbrush_3d)

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
                "color": list(layer_data.get_color()),
                "alpha": layer_data.get_alpha(),
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
        self.vtk_viewer.render()

    def on_layer_changed(self, layer_name):
        self._modified = True
        self.render()

    def on_layer_visibility_changed(self, layer_name, visible):
        self._modified = True
        self.render()

    def get_active_layer(self):
        return self.segmentation_layers.get(self.active_layer_name, None)

    def set_active_layer_by_name(self, active_layer_name):
        if self.active_layer_name != active_layer_name:
            old_name = self.active_layer_name
            self.active_layer_name = active_layer_name
            self.active_layer_changed.emit(active_layer_name, old_name, self)

    def enable_paintbrush(self, enabled=True):
        
        for v in self.vtk_viewer.get_viewers_2d():
            if not hasattr(v, 'paintbrush') or v.paintbrush is None:
                v.paintbrush = PaintBrush(viewer=v)
                v.paintbrush.set_radius_in_pixel(radius_in_pixel=20, pixel_spacing=v.vtk_image.GetSpacing())
                v.get_renderer().AddActor(v.paintbrush.get_actor())

            v.paintbrush.set_brush_3d(self.paintbrush_3d)

            v.paintbrush.set_enabled(enabled)

            interactor = v.interactor 
            if enabled:
                v.left_button_press_observer = interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
                v.mouse_move_observer = interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)
                v.left_button_release_observer = interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
            else:    
                interactor.RemoveObserver(v.left_button_press_observer)
                interactor.RemoveObserver(v.mouse_move_observer)
                interactor.RemoveObserver(v.left_button_release_observer)   
        
        self.left_button_is_pressed = False
        self.last_mouse_position = None
        
        print(f"Painbrush mode: {'enabled' if enabled else 'disabled'}")

    def paint_at_mouse_position(self, v2d):
        
        event_data = v2d.get_mouse_event_coordiantes()

        if 'mouse_point' in event_data:
            mouse_pos = event_data['mouse_point']
            print(f"Mouse position: ({mouse_pos[0]:.2f}, {mouse_pos[1]:.2f})")
        else:
            return    
        
        if 'world_point' in event_data:
            world_pos = event_data['world_point']
            print(f"World position: ({world_pos[0]:.2f}, {world_pos[1]:.2f}, {world_pos[2]:.2f})")
        else:
            return

        if 'image_index' in event_data:
            image_index = event_data['image_index']
            print(f"Index: ({image_index[0]:.2f}, {image_index[1]:.2f}, {image_index[2]:.2f})")
        else:
            return

        layer = self.get_active_layer()
        if layer is None:
            print("No active layer selected.")
            return

        # paint or erase
        if self.paint_active:
            value = 1
        else:
            value = 0

        # paint
        v2d.paintbrush.paint(layer.segmentation, image_index[0], image_index[1], image_index[2], value)

        # flag vtkImageData as Modified to update the pipeline.
        layer.segmentation.Modified() 
    
        # flag manager data has been modified (for saving)
        self._modified = True

        # emit event
        self.layer_modified.emit(self.active_layer_name, self)
        
    def _find_viewer_from_interactor(self, interactor):
        for v in self.vtk_viewer.get_viewers():
            if v.get_interactor() == interactor:
                return v
        return None

    def on_left_button_press(self, obj, event):
        # obj is the sender, which is vtkRenderWindowInteractor
        # event = LeftButtonPressEvent string
        v2d = self._find_viewer_from_interactor(obj)
        
        if not v2d:
            return 
        
        if not hasattr(v2d, 'paintbrush') or not v2d.paintbrush.enabled:
            return
        
        self.left_button_is_pressed = True
        self.last_mouse_position = v2d.get_interactor().GetEventPosition()
        
        if self.left_button_is_pressed and v2d.paintbrush.enabled and self.active_layer_name is not None:
            print('paint...')
            self.paint_at_mouse_position(v2d)
       
    def on_mouse_move(self, obj, event):
        # obj is the sender, which is vtkRenderWindowInteractor
        # event = MouseMoveEvent string
        interactor = obj
        
        v2d = self._find_viewer_from_interactor(interactor)
        
        if not v2d:
            return 
        
        if not hasattr(v2d, 'paintbrush') or not v2d.paintbrush.enabled:
            return
        
        paintbrush = v2d.paintbrush
        renderer = v2d.get_renderer()
        if paintbrush.enabled:
            mouse_pos = interactor.GetEventPosition()
            picker = vtk.vtkWorldPointPicker()
            picker.Pick(mouse_pos[0], mouse_pos[1], 0, renderer)

            # Get world position
            world_pos = picker.GetPickPosition()

            # camera
            camera = renderer.GetActiveCamera()
            import vtk_camera_wrapper, numpy as np
            cam = vtk_camera_wrapper.vtk_camera_wrapper(camera)
            w_H_camo = cam.get_w_H_o()
            camo_H_w = cam.get_o_H_w()
            print(f'world_pos={world_pos}')
            print(f'axis={v2d.reslicer.axis}')
            print(f'w_H_camo={w_H_camo}')
            print(f'camo_H_w={camo_H_w}')

            # interaction point in camo
            w_pt_interaction = np.append(np.array(world_pos), 1.0).reshape(4,1)
            camo_pt_interaction = camo_H_w @ w_pt_interaction

            print(f'w_pt_interaction={w_pt_interaction}')
            print(f'camo_pt_interaction={camo_pt_interaction}')

            # project to the camera near plane
            clip_range = cam.get_clip_range()
            z_near = clip_range[0]
            camo_pt_interaction[2,0] = z_near+0.1

            # projected interaction point in w
            w_pt_on_near_plane =  (w_H_camo @ camo_pt_interaction).flatten()[:3]

            print(f'w_pt_on_near_plane={w_pt_on_near_plane}')

            # Update the brush position (ensure Z remains on the image plane + 0.1 to show on top of the image)
            paintbrush.get_actor().SetPosition(w_pt_on_near_plane[0], w_pt_on_near_plane[1], w_pt_on_near_plane[2])
            paintbrush.get_actor().SetVisibility(True)  # Make the brush visible
        
            if self.paint_active:
                paintbrush.set_color(self.paint_brush_color)
            else:
                paintbrush.set_color(self.erase_brush_color)

            # Paint 
            if self.left_button_is_pressed and paintbrush.enabled and self.active_layer_name is not None:
                print('paint...')
                self.paint_at_mouse_position(v2d)
        else:
            paintbrush.get_actor().SetVisibility(False)  # Hide the brush when not painting
       
    def on_left_button_release(self, obj, event):
        interactor = obj
        
        v = self._find_viewer_from_interactor(interactor)
        
        if not v:
            return 
        
        if not hasattr(v,'paintbrush') or not v.paintbrush.enabled:
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
        for v in self.vtk_viewer.get_viewers_2d():
            if hasattr(v, 'paintbrush'):
                v.paintbrush.set_radius_in_pixel(radius_in_pixel=value)

    def list_widget_on_current_item_changed(self, current, previous):
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, SegmentationListItemWidget):
                # Access the layer_name from the custom widget
                layer_name = item_widget.layer_name
                self.set_active_layer_by_name(layer_name)

    def toggle_paint_tool(self, checked):
        
        # no change, just return
        if self.paint_active == checked:
            return 
        
        # turn off both
        self.erase_action.setChecked(False)
        self.paint_action.setChecked(False)

        # activate paint
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
        #self.set_active_layer_by_name(layer_name)
    
    def generate_unique_layer_name(self, base_name="Layer"):
        index = 1
        while f"{base_name} {index}" in self.segmentation_layers:
            index += 1
        return f"{base_name} {index}"
    
    def is_3d(self):
        
        if not self.vtk_viewer:
            return False
        
        vtk_image = self.get_base_image()

        if not vtk_image:
            return False
        
        dims = vtk_image.e.GetDimensions()

        return len(dims) ==3 and dims[2] > 1

    def add_layer(self, segmentation, layer_name, color_vtk, alpha):
        #actor = self.create_segmentation_actor(segmentation, color=color_vtk, alpha=alpha)
        seg_item = SegmentationItem(segmentation=segmentation, color=from_vtk_color(color_vtk), alpha=alpha, name=layer_name)
        self.segmentation_layers[layer_name] = seg_item

        self.add_layer_widget_item(layer_name, seg_item)

        seg_item.name_changed.connect(self.on_layer_name_changed)
        self._modified = True

        # Select the last item in the list widget (to activate it)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

        self.layer_added.emit(layer_name, self)

    def on_layer_name_changed(self, old_name, sender):

        # update the key of the layer dictionary
        seg_item = self.segmentation_layers.pop(old_name)
        new_name = seg_item.get_name()
        self.segmentation_layers[new_name] = seg_item
            
        # if active layer, update the active layer name
        if self.active_layer_name == old_name:
            self.active_layer_name = new_name

        self.on_layer_changed(new_name)

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
            alpha=0.5)
        
        self.print_status(f'A layer added: {layer_name}, and active layer is now {self.active_layer_name}')
        

    def remove_segmentation_by_name(self, layer_name):
        
        if layer_name in self.segmentation_layers:
            # remove actor

            seg_item = self.segmentation_layers[layer_name]
            if seg_item.get_actor():
                self.vtk_viewer.get_renderer().RemoveActor(seg_item.get_actor())

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

            self.vtk_viewer.render()

            # emit
            self.layer_removed.emit(layer_name, self)
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

        # Set the direction matrix 
        # SetDirectionMatrix() function si required
        segmentation.SetDirectionMatrix(direction_matrix)

        #degug
        #import itkvtk
        #itkvtk.fill_square_at_center(segmentation, 100, 1)

        return segmentation  

    def create_segmentation_actor(self, segmentation, color=(1, 0, 0), alpha=0.5):
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
