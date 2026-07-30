

import vtk
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QListWidgetItem, QToolBar, QAction, QToolButton, QVBoxLayout, QPushButton, QLabel, QWidget, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit)
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor

from logger import logger
import color_rotator

color_rotator1 = color_rotator.ColorRotator()

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

class SegmentationLayer(QObject):

    visibility_changed = pyqtSignal(QObject)
    color_changed = pyqtSignal(QObject)
    name_changed = pyqtSignal(str, QObject)
    alpha_changed = pyqtSignal(QObject)
    image_changed = pyqtSignal(QObject)

    def __init__(self, segmentation, visible=True, color=np.array([255, 255, 128]), alpha=0.5, actor=None, name="") -> None:
        super().__init__()

        self._segmentation_image = segmentation
        self._visible = visible
        self._color = color
        self._name = name.strip()
        self._alpha = alpha
        #self._actor = actor

        self._parent_list: SegmentationLayerList = None

        self._modified = False

    def set_parent_list(self, list):
        self._parent_list = list
    
    def get_parent_list(self):
        return self._parent_list
        
    def get_modified(self):
        return self._modified

    def set_modified(self, flag):
        self._modified = flag

    def get_image(self):
        return self._segmentation_image
    
    def set_image(self, image):
        if image is not self._segmentation_image:
            self._modified = True
            self._segmentation_image = image
            self.image_changed.emit(self)

    def set_name(self, name):
        
        name_trimmed = name.strip()

        if self._name != name_trimmed:
            old_value = self._name
            self._name = name_trimmed
            self._modified = True
            self.name_changed.emit(old_value, self)
    
    def get_name(self):
        return self._name
    
    def set_color(self, color):
        if self._color != color:
            self._color = color
            self._modified = True
            self.color_changed.emit(self)
    
    def get_color(self):
        return self._color

    def get_vtk_color(self):
        return [self._color[0]/255, self._color[1]/255, self._color[2]/255]

    def set_visible(self, visible):
        if self._visible != visible:
            self._visible = visible
            self._modified = True
            self.visibility_changed.emit(self)
    
    def get_visible(self):
        return self._visible

    def set_alpha(self, alpha):
        if self._alpha != alpha:
            self._alpha = alpha
            self._modified = True
            self.alpha_changed.emit(self)
    
    def get_alpha(self):
        return self._alpha

    @staticmethod
    def deep_copy(layer):
        import vtk_tools
        return SegmentationLayer(segmentation=vtk_tools.deep_copy_image(layer.get_image()), 
                                                                        color=layer.get_color(),
                                                                        alpha=layer.get_alpha(),
                                                                        name=layer.get_name())

    # def set_actor(self, actor):
    #     if self._actor != actor:
    #         self._actor = actor
    
    # def get_actor(self):
    #     return self._actor

from typing import List

class SegmentationLayerList(QObject):

    layer_added = pyqtSignal(QObject, QObject)
    layer_removed = pyqtSignal(QObject, QObject)

    def __init__(self):
        super().__init__()
        self._layers: List[SegmentationLayer] = []
    
    def clear(self):
        if len(self._layers) == 0:
            return 
        
        self.remove_all_layers()
        self._layers.clear()

    def get_layer_by_name(self, name):
        for layer in self._layers:
            if layer.get_name() == name:
                return layer
        return None

    def add_layer(self, layer):
        
        # add list as parent
        layer.set_parent_list(self)

        # add to the list
        self._layers.append(layer)

        # emit event
        self.layer_added.emit(layer, self)
    
    def remove_layer_by_name(self,name):
        layer = self.get_layer_by_name(name)
        if layer:

            layer.set_parent_list(None)

            self._layers.remove(layer)

            # emit event
            self.layer_removed.emit(layer, self)

            return layer
        
        return None

    def remove_all_layers(self):
        for layer in self._layers:
            self.remove_layer_by_name(layer.get_name())
        
    def pop(self, name):
        return self.remove_layer_by_name(name)
    
    def get_layers(self):
        return self._layers
    
    def get_layer_names(self):
        return [layer.get_name() for layer in self.get_layers()]

    def modified(self):
        for layer in self.get_layers():
            if layer.get_modified():
                return True
        return False

    def reset_modified(self):
        for layer in self.get_layers():
            layer.set_modified(False)

    def __getitem__(self, key):
        return self.get_layer_by_name(key)

    def __delitem__(self, key):
        self.remove_layer_by_name(key)

    def __setitem__(self, key, value):
        # if exists, remove first
        self.remove_layer_by_name(key)

        # add layer
        self.add_layer(value)

from line_edit2 import LineEdit2
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QLabel, QLineEdit, QSlider, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt


class SegmentationListItemWidget(QWidget):
    
    # def get_viewer(self):
    #     return self.manager
    
    def __init__(self, layer: SegmentationLayer):
        super().__init__()
        
        # data
        self.layer = layer

        self._setup_ui()

    def _setup_ui(self):
        
        #main layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        #header widget
        self.header_widget = self._create_header_widget()
        self.main_layout.addWidget(self.header_widget)

        #details widget
        self.details_widget = self._create_details_widget()
        self.main_layout.addWidget(self.details_widget)

        self.setLayout(self.main_layout)        

    def _create_header_widget(self):
        
        widget = QWidget()

        # === Header Layout ===
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.visible_checkbox_clicked)
        layout.addWidget(self.checkbox)

        # Color patch for layer
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked  # Assign event for color change
        layout.addWidget(self.color_patch)

        # Label for the layer name
        self.label = QLabel(self.layer.get_name())
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_editor  # Assign double-click to activate editor
        layout.addWidget(self.label)

        # Editable name field
        self.edit_name = LineEdit2(self.layer.get_name())
        self.edit_name.focus_out_callback = self.focusOutEvent
        self.edit_name.setToolTip("Edit the layer name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_editor)  # Commit name on Enter
        self.edit_name.editingFinished.connect(self.deactivate_editor)  # Commit name on losing focus
        self.edit_name.textChanged.connect(self.validate_name)
        layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setFixedSize(20, 20)
        #self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this layer")
        self.remove_button.clicked.connect(self.remove_layer_clicked)
        layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.toggle_button = QPushButton("▼")
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.toggle_details)
        layout.addWidget(self.toggle_button)
        
        widget.setLayout(layout)

        return widget

    def _create_command_buttoms_widget(self):
        
        widget = QWidget()

        import flowlayout
        layout = flowlayout.FlowLayout()

        # Clear layer contents (keep the layer)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setToolTip("Clear this layer (set all voxels to empty)")
        self.clear_button.clicked.connect(self.clear_layer_clicked)
        layout.addWidget(self.clear_button)

        # Duplicate layer
        self.duplicate_button = QPushButton("Duplicate")
        self.duplicate_button.setToolTip("Duplicate")
        self.duplicate_button.clicked.connect(self.duplicate_layer_clicked)
        layout.addWidget(self.duplicate_button)

        # Extract the largest 
        self.extract_the_largest_component_button = QPushButton("Extract Largest Compoments")
        self.extract_the_largest_component_button.setToolTip("Split into connected components and extract the largest one")
        self.extract_the_largest_component_button.clicked.connect(self.extract_the_largest_component_clicked)
        layout.addWidget(self.extract_the_largest_component_button)

        # # Extract a compoment
        # self.extract_a_component_button = QPushButton("Extract a Compoment")
        # self.extract_a_component_button.setToolTip("Mouse pick a component")
        # self.extract_a_component_button.clicked.connect(self.extract_a_component_using_mouse_clicked)
        # layout.addWidget(self.extract_a_component_button)

        # Interpolate sparse labels
        self.make_convex_hull_label_button = QPushButton("Make Enclusure Segmentation")
        self.make_convex_hull_label_button.setToolTip("Make a convex hull semgmentation")
        self.make_convex_hull_label_button.clicked.connect(self.make_convex_hull_label_button_clicked)
        layout.addWidget(self.make_convex_hull_label_button)


        widget.setLayout(layout)

        return widget

    def _create_details_widget(self):
        widget = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)

        # Alpha slider as an example
        from labeled_float_slider import LabeledFloatSlider
        self.alpha_slider = LabeledFloatSlider(label_text="Alpha", f0=0.0, f1=1.0, initial_value=0.5, float_format_string='{:0.2f}', orientation=Qt.Horizontal)
        self.alpha_slider.value_changed.connect(self.alpha_changed)
        layout.addWidget(self.alpha_slider)

        widget.setLayout(layout)
        widget.setVisible(False)  # Initially collapsed

        # command buttons
        layout.addWidget(self._create_command_buttoms_widget())

        return widget


    def toggle_details(self):
        is_expanded = self.toggle_button.isChecked()
        self.toggle_button.setText("▲" if is_expanded else "▼")
        self.details_widget.setVisible(is_expanded)      

        # Resize list item properly
        self.list_widget_item.setSizeHint(self.sizeHint())  # Use widget's own updated size
        self.list_widget.doItemsLayout()

    def clear_layer_clicked(self):
        """Zero voxel values in-place; keep the same vtkImageData and geometry."""
        image = self.layer.get_image()
        if image is None:
            return
        scalars = image.GetPointData().GetScalars()
        if scalars is None:
            return

        # Fill existing buffer so origin/spacing/direction and viewer
        # reslicer input pointers stay unchanged.
        scalars.Fill(0)
        scalars.Modified()
        image.Modified()
        self.layer.set_modified(True)
        manager = getattr(self, "manager", None)
        if manager is not None:
            manager._modified = True
        # Emit last so 3D surface refresh (image_changed -> timer 0) is not
        # overridden by the paint debounce path (layer_image_modified -> 1000ms).
        self.layer.image_changed.emit(self.layer)

    def duplicate_layer_clicked(self):
        layer_copy = SegmentationLayer.deep_copy(self.layer)
        layer_copy.set_name(self.layer.get_name()+"_copy")
        layer_copy.set_color(color_rotator1.next())
        self.layer.get_parent_list().add_layer(layer_copy)

    def extract_the_largest_component_clicked(self):
        import vtk_tools
        blob_images = vtk_tools.extract_largest_components(self.layer.get_image(), 1)
        largest_image = blob_images[0]
        layer_largest = SegmentationLayer(segmentation=largest_image, name=f'{self.layer.get_name()}-largest', color = color_rotator1.next())
        self.layer.get_parent_list().add_layer(layer_largest)

    # def extract_a_component_using_mouse_clicked(self):

    #     from PyQt5.QtWidgets import QDialog, QComboBox, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFormLayout
    #     from PyQt5.QtCore import Qt
        
    #     dialog = QDialog()
    #     dialog.setWindowTitle("Extract a Component")
    #     dialog.setModal(False)  # Modeless dialog

    #     layout = QVBoxLayout()

    #     label = QLabel()
    #     label.setText("Please move your cross hair to the compoenent you want to extract and click 'Extract' button. ")

    #     # Run button
    #     run_button = QPushButton("Extract")
    #     layout.addWidget(run_button, alignment=Qt.AlignRight)
    #     dialog.setLayout(layout)

    #     def run_operation():
            
    #         # get the focus point from the viewer

    #         # extract the picked compoment
    #         import vtk_tools
    #         blob_images = vtk_tools.extract_largest_components(self.layer.get_image(), 1)
    #         largest_image = blob_images[0]
    #         layer_largest = SegmentationLayer(segmentation=largest_image, name=f'{self.layer.get_name()}-largest', color = color_rotator1.next())
            
    #         # add the layer
    #         self.layer.get_parent_list().add_layer(layer_largest)

    #         self.print_status(f"Boolean operation {op} applied. New layer: {new_name}")
    #         dialog.close()

    #     run_button.clicked.connect(run_operation)
    #     dialog.show()

    def make_convex_hull_label_button_clicked(self):
        import itk_tools
        import itkvtk

        # convert to itk image
        itk_seg = itkvtk.vtk_to_sitk(self.layer.get_image())

        # interpolate
        itk_interpolated = itk_tools.make_convex_label(itk_seg)

        # convert back to vtk image
        vtk_interpolated = itkvtk.sitk_to_vtk(itk_interpolated)
        
        # add layer
        layer_largest = SegmentationLayer(segmentation=vtk_interpolated, name=f'{self.layer.get_name()}-interpolated', color = color_rotator1.next())
        self.layer.get_parent_list().add_layer(layer_largest)

    def remove_layer_clicked(self):
        """Remove the layer when the 'x' button is clicked."""
        semgneation_list : SegmentationLayerList =  self.layer.get_parent_list()

        semgneation_list.remove_layer_by_name(self.layer.get_name())

    def visible_checkbox_clicked(self, state):
        visibility = state == Qt.Checked
        self.layer.set_visible(visibility)

    def get_layer_color_hex(self):
        """Convert the layer's color (numpy array) to a hex color string."""
        color = self.layer.get_color()
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        
        """Open a color chooser dialog and update the layer's color."""
        # Get the current color in QColor format
        c256 = self.layer.get_color()
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(c256[0], c256[1], c256[2]), self, "Select Layer Color")

        if color.isValid():
            
            c = [color.red(), color.green(), color.blue()]
            # Update layer color
            self.layer.set_color(c)

            # Update color patch
            self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")

    def alpha_changed(self, value, sender):
        self.layer.set_alpha(value)

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
        if self.validate_name():
            self.label.setText(new_name)
            self.update_layer_name(new_name)
        else:
            self.label.setText(self.layer.get_name())

        # Show the label and hide the editor
        self.label.show()

        self.edit_name.setText('')
        self.edit_name.hide()


    def validate_name(self):
        """Validate the layer name for uniqueness and file system compatibility."""
        new_name = self.edit_name.text()

        # Check for invalid file system characters
        invalid_chars = r'<>:"/\|?*'
        if any(char in new_name for char in invalid_chars) or new_name.strip() == "":
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")  # Radish color
            self.edit_name.setToolTip("Layer name contains invalid characters or is empty.")
            return False

        # Check for uniqueness
        existing_names = [name for name in self.layer.get_parent_list().get_layer_names() if name != self.layer.get_name()]
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")  # Radish color
            self.edit_name.setToolTip("Layer name must be unique.")
            return False
        else:
            # Name is valid
            self.edit_name.setStyleSheet("")  # Reset background
            self.edit_name.setToolTip("")
            return True


    def update_layer_name(self, new_name):
        """Update the layer name in the viewer."""
        if new_name != self.layer.get_name():

            # update seg item name
            self.layer.set_name(new_name)
           

from PyQt5.QtCore import pyqtSignal, QObject




        
class SegmentationListManager(QObject):
    # Signal to emit log messages
    log_message = pyqtSignal(str, str)  # Format: log_message(type, message)
    layer_added = pyqtSignal(str, QObject)
    layer_image_modified = pyqtSignal(QObject, QObject)
    layer_removed = pyqtSignal(str, QObject)

    active_layer_changed = pyqtSignal(QObject)

    layer_changed = pyqtSignal(str, QObject)
    
    def __init__(self, vtk_viewer, name):
        super().__init__()  # Initialize QObject

        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.name = name

        # segmentation data
        self.segmentation_layers = SegmentationLayerList()
        self.segmentation_layers.layer_added.connect(self.segmentation_layer_added)
        self.segmentation_layers.layer_removed.connect(self.segmentation_layer_removed)

        self._active_layer = None

        self.paint_active = False
        self.paint_brush_color = [0,1,0]

        self.erase_active = False
        self.erase_brush_color = [0, 0.5, 1.0]

        self.paintbrush_3d = False
        self.paint_tool_dialog = None
        self._paint_target_layer_name = None
        self._paint_target_layer = None
        self._closing_paint_tool = False
        self._brush_color_is_erase = None  # cache last brush color mode

        self.pencil_active = False
        self.pencil_erase_active = False
        self.pencil_tool_dialog = None
        self._pencil_target_layer_name = None
        self._pencil_target_layer = None
        self._closing_pencil_tool = False
        self._pencil_points_ijk = []
        self._pencil_points_world = []
        self._pencil_viewer = None
        self._pencil_axis = None
        self._pencil_fixed_coord = None
        self._pencil_cursor_world = None
        self._pencil_left_button_down = False
        self._pencil_min_drag_spacing_px = 2  # min image-index distance between drag samples

        self._modified = False

        self.nnunet_prediction_tool_dialog = None
        self.nnunet_prediction_tool_button = None
        self.get_nnunet_prediction_context = None  # optional callback set by MainWindow

        # Scribble Tool (GraphCut + Histogram)
        self.scribble_active = False
        self.scribble_action = None
        self.scribble_button = None
        self.scribble_tool_dialog = None
        self._closing_scribble_tool = False
        self.scribble_mode = "foreground"  # "foreground" | "background"
        self.scribble_erase_active = False
        self._scribble_target_layer_name = None
        self._scribble_target_layer = None
        self.scribble_fg_layer_name = "Scribble FG"
        self.scribble_bg_layer_name = "Scribble BG"
        self.scribble_fg_brush_color = [0.0, 1.0, 0.0]
        self.scribble_bg_brush_color = [1.0, 0.0, 0.0]
        self.scribble_lamda = 1.0
        self.scribble_sigma = 0.1
        self.scribble_num_bins = 64

        self.interpolation_tool_dialog = None
        self.interpolation_tool_button = None

        logger.info("SegmentationListManager initialized")

    def get_segmentation_layer_list(self) -> SegmentationLayerList:
        return self.segmentation_layers
    
    def get_vtk_viewer(self):
        return self.vtk_viewer
    
    def get_base_vtk_image(self):
        if self.vtk_viewer is None:
            return None
        
        return self.get_vtk_viewer().get_vtk_image()

    def get_segmentation_vtk_images(self):
        return [layer.get_image() for layer in self.segmentation_layers.get_layers()]
    
    def reset_modified(self):
        self._modified = False
        self.segmentation_layers.reset_modified()
       
    def modified(self):
        return self._modified or self.segmentation_layers.modified()

    def setup_ui(self):   
        toolbar = self.create_toolbar()
        dock = self.create_dock_widget()

        self.toolbar = toolbar
        self.dock_widget = dock

        return None, dock

    def create_toolbar(self):
        
        # Create a toolbar
        toolbar = QToolBar("PaintBrush Toolbar")
     

        # Add Paint Tool button (controls live in the floating Paint Tool window)
        self.paint_action, self.paint_button = self.create_checkable_button(
            "Paint Tool", self.paint_active, toolbar, self.toggle_paint_tool
        )
        self.pencil_action, self.pencil_button = self.create_checkable_button(
            "Pencil Tool", self.pencil_active, toolbar, self.toggle_pencil_tool
        )

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
        
        # Add Paint Tool button (opens floating tool window)
        self.paint_action, self.paint_button = self.create_checkable_button(
            "Paint Tool", self.paint_active, None, self.toggle_paint_tool
        )
        button_layout.addWidget(self.paint_button)

        self.pencil_action, self.pencil_button = self.create_checkable_button(
            "Pencil Tool", self.pencil_active, None, self.toggle_pencil_tool
        )
        button_layout.addWidget(self.pencil_button)

        boolean_tool_button = QPushButton("Boolean Tool")
        boolean_tool_button.clicked.connect(self.show_boolean_tool_clicked)
        button_layout.addWidget(boolean_tool_button)

        self.nnunet_prediction_tool_button = QPushButton("nnUNet Prediction Tool")
        self.nnunet_prediction_tool_button.setEnabled(False)
        self.nnunet_prediction_tool_button.setToolTip(
            "Run an approved nnU-Net model on the currently open image set"
        )
        self.nnunet_prediction_tool_button.clicked.connect(
            self.show_nnunet_prediction_tool_clicked
        )
        button_layout.addWidget(self.nnunet_prediction_tool_button)

        self.scribble_action, self.scribble_button = self.create_checkable_button(
            "Scribble Tool", self.scribble_active, None, self.toggle_scribble_tool
        )
        self.scribble_button.setToolTip(
            "Draw FG/BG scribbles and run GraphCut+Histogram to update the target layer"
        )
        button_layout.addWidget(self.scribble_button)

        self.interpolation_tool_button = QPushButton("Interpolation Tool")
        self.interpolation_tool_button.setToolTip(
            "Fill between sparsely painted slices (morphological contour interpolation)"
        )
        self.interpolation_tool_button.clicked.connect(
            self.show_interpolation_tool_clicked
        )
        button_layout.addWidget(self.interpolation_tool_button)

        # Add the button layout 
        main_layout.addLayout(button_layout)

        # Set layout for the layer manager
        main_widget.setLayout(main_layout)
        
        dock.setWidget(main_widget)

        return dock


    def update_nnunet_prediction_tool_button_state(self):
        """Enable Prediction Tool when a base image is open in the viewer."""
        btn = getattr(self, "nnunet_prediction_tool_button", None)
        if btn is None:
            return
        btn.setEnabled(self.get_base_vtk_image() is not None)

    def show_nnunet_prediction_tool_clicked(self):
        if self.get_base_vtk_image() is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.dock_widget,
                "nnUNet Prediction Tool",
                "Open an image in the viewer first.",
            )
            return

        if (
            self.nnunet_prediction_tool_dialog is not None
            and self.nnunet_prediction_tool_dialog.isVisible()
        ):
            self.nnunet_prediction_tool_dialog.raise_()
            self.nnunet_prediction_tool_dialog.activateWindow()
            return

        from nnunet_prediction_tool_dialog import NnUNetPredictionToolDialog

        get_ctx = self.get_nnunet_prediction_context
        dialog = NnUNetPredictionToolDialog(
            segmentation_list_manager=self,
            get_context_fn=get_ctx,
            parent=self.dock_widget,
        )
        self.nnunet_prediction_tool_dialog = dialog
        dialog.show()

    # ------------------------------------------------------------------
    # Scribble Tool: FG/BG paintbrush + GraphCut+Histogram
    # ------------------------------------------------------------------

    def get_scribble_target_layer(self):
        if self._scribble_target_layer is not None:
            return self._scribble_target_layer
        if self._scribble_target_layer_name:
            layer = self.segmentation_layers.get_layer_by_name(self._scribble_target_layer_name)
            if layer is not None:
                self._scribble_target_layer = layer
                return layer
        return self.get_active_layer()

    def get_scribble_paint_layer(self):
        """Layer currently being painted by scribble strokes (FG or BG overlay)."""
        self._ensure_scribble_layers()
        name = (
            self.scribble_bg_layer_name
            if self.scribble_mode == "background"
            else self.scribble_fg_layer_name
        )
        return self.segmentation_layers.get_layer_by_name(name)

    def _ensure_scribble_layers(self):
        """Create Scribble FG/BG overlay layers if missing."""
        if self.get_base_vtk_image() is None:
            return

        specs = [
            (self.scribble_fg_layer_name, (0, 255, 0), 0.35),
            (self.scribble_bg_layer_name, (255, 0, 0), 0.35),
        ]
        for name, color, alpha in specs:
            if self.segmentation_layers.get_layer_by_name(name) is not None:
                continue
            empty = self.create_empty_segmentation_image()
            self.add_layer(
                segmentation=empty,
                layer_name=name,
                color_vtk=[c / 255.0 for c in color],
                alpha=alpha,
            )

    def _refresh_scribble_target_layers(self, preferred_name=None):
        if not hasattr(self, "scribble_target_combo") or self.scribble_target_combo is None:
            return
        skip = {self.scribble_fg_layer_name, self.scribble_bg_layer_name}
        names = [n for n in self.segmentation_layers.get_layer_names() if n not in skip]
        current = preferred_name or self.scribble_target_combo.currentText()
        self.scribble_target_combo.blockSignals(True)
        self.scribble_target_combo.clear()
        self.scribble_target_combo.addItems(names)
        if current in names:
            self.scribble_target_combo.setCurrentText(current)
        elif names:
            self.scribble_target_combo.setCurrentIndex(0)
        self.scribble_target_combo.blockSignals(False)
        self._on_scribble_target_layer_changed(self.scribble_target_combo.currentText())

    def _on_scribble_target_layer_changed(self, name):
        self._scribble_target_layer_name = name or None
        self._scribble_target_layer = (
            self.segmentation_layers.get_layer_by_name(name) if name else None
        )

    def _ensure_scribble_tool_dialog(self):
        if self.scribble_tool_dialog is not None:
            return self.scribble_tool_dialog

        from PyQt5.QtWidgets import (
            QDialog,
            QComboBox,
            QFormLayout,
            QVBoxLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QRadioButton,
            QButtonGroup,
            QDoubleSpinBox,
            QSpinBox,
            QCheckBox,
        )
        from labeled_slider import LabeledSlider

        dialog = QDialog(self.dock_widget)
        dialog.setWindowTitle("Scribble Tool (GraphCut+Histogram)")
        dialog.setModal(False)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WA_ShowWithoutActivating, True)
        dialog.resize(360, 340)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        self.scribble_target_combo = QComboBox(dialog)
        self.scribble_target_combo.setToolTip(
            "Foreground / target layer updated when you press Run"
        )
        self.scribble_target_combo.currentTextChanged.connect(
            self._on_scribble_target_layer_changed
        )
        form.addRow("Target Layer:", self.scribble_target_combo)

        mode_row = QHBoxLayout()
        self.scribble_fg_radio = QRadioButton("Foreground")
        self.scribble_bg_radio = QRadioButton("Background")
        self.scribble_fg_radio.setChecked(True)
        self.scribble_mode_group = QButtonGroup(dialog)
        self.scribble_mode_group.addButton(self.scribble_fg_radio)
        self.scribble_mode_group.addButton(self.scribble_bg_radio)
        # Connect both radios: only the checked=True transition updates mode.
        self.scribble_fg_radio.toggled.connect(self._on_scribble_mode_toggled)
        self.scribble_bg_radio.toggled.connect(self._on_scribble_mode_toggled)
        mode_row.addWidget(self.scribble_fg_radio)
        mode_row.addWidget(self.scribble_bg_radio)
        form.addRow("Paint:", mode_row)

        self.scribble_brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        self.scribble_brush_size_slider.slider.setMinimum(3)
        self.scribble_brush_size_slider.slider.setMaximum(100)
        self.scribble_brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        form.addRow(self.scribble_brush_size_slider)

        self.scribble_brush_3d_checkbox = QCheckBox("3D Brush")
        self.scribble_brush_3d_checkbox.setChecked(bool(self.paintbrush_3d))
        self.scribble_brush_3d_checkbox.stateChanged.connect(self.on_brush_3d_toggled)
        form.addRow("", self.scribble_brush_3d_checkbox)

        self.scribble_erase_checkbox = QCheckBox("Erase")
        self.scribble_erase_checkbox.setToolTip("Erase scribbles from the active FG/BG overlay")
        self.scribble_erase_checkbox.toggled.connect(self._on_scribble_erase_toggled)
        form.addRow("", self.scribble_erase_checkbox)

        self.scribble_lamda_spin = QDoubleSpinBox()
        self.scribble_lamda_spin.setRange(0.01, 100.0)
        self.scribble_lamda_spin.setSingleStep(0.1)
        self.scribble_lamda_spin.setValue(self.scribble_lamda)
        self.scribble_lamda_spin.setToolTip("GraphCut smoothness weight (lambda)")
        form.addRow("Lambda:", self.scribble_lamda_spin)

        self.scribble_sigma_spin = QDoubleSpinBox()
        self.scribble_sigma_spin.setRange(0.001, 10.0)
        self.scribble_sigma_spin.setDecimals(3)
        self.scribble_sigma_spin.setSingleStep(0.01)
        self.scribble_sigma_spin.setValue(self.scribble_sigma)
        self.scribble_sigma_spin.setToolTip("Intensity std for pairwise term (sigma)")
        form.addRow("Sigma:", self.scribble_sigma_spin)

        self.scribble_bins_spin = QSpinBox()
        self.scribble_bins_spin.setRange(8, 256)
        self.scribble_bins_spin.setValue(self.scribble_num_bins)
        form.addRow("Histogram Bins:", self.scribble_bins_spin)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear Scribbles")
        clear_btn.clicked.connect(self.clear_scribble_layers)
        run_btn = QPushButton("Run")
        run_btn.setToolTip("Run GraphCut+Histogram and update the Target Layer")
        run_btn.clicked.connect(self.run_scribble_graphcut)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(run_btn)
        layout.addLayout(btn_row)

        hint = QLabel(
            "Paint FG (green) and BG (red) scribbles, then Run.\n"
            "Review, add more scribbles, and Run again until satisfied."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        dialog.finished.connect(self._on_scribble_tool_dialog_finished)
        self.scribble_tool_dialog = dialog
        return dialog

    def _on_scribble_mode_toggled(self, checked):
        if not checked:
            return
        self.scribble_mode = "foreground" if self.scribble_fg_radio.isChecked() else "background"
        self._brush_color_is_erase = None
        self._update_scribble_brush_colors()
        # Keep the active scribble overlay visible so the stroke color is obvious.
        layer = self.get_scribble_paint_layer()
        if layer is not None and not layer.get_visible():
            layer.set_visible(True)
        self.print_status(f"Scribble mode: {self.scribble_mode}")

    def _update_scribble_brush_colors(self):
        """Apply FG/BG/erase brush color immediately on all 2D viewers."""
        if self.scribble_erase_active:
            color = self.erase_brush_color
            key = "erase"
        elif self.scribble_mode == "background":
            color = self.scribble_bg_brush_color
            key = "bg"
        else:
            color = self.scribble_fg_brush_color
            key = "fg"
        self._brush_color_is_erase = key
        if self.vtk_viewer is None:
            return
        for v in self.vtk_viewer.get_viewers_2d():
            if hasattr(v, "paintbrush") and v.paintbrush is not None:
                v.paintbrush.set_color(color)

    def _on_scribble_erase_toggled(self, checked):
        self.scribble_erase_active = bool(checked)
        self._brush_color_is_erase = None
        self._update_scribble_brush_colors()
        self.print_status("Scribble erase " + ("on" if checked else "off"))

    def _on_scribble_tool_dialog_finished(self, result):
        if self._closing_scribble_tool:
            return
        if self.scribble_active:
            self.toggle_scribble_tool(False)

    def open_scribble_tool(self):
        if self.paint_active or self.erase_active:
            self.toggle_paint_tool(False)
        if self.pencil_active:
            self.toggle_pencil_tool(False)

        if self.get_base_vtk_image() is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.dock_widget,
                "Scribble Tool",
                "Open an image in the viewer first.",
            )
            if self.scribble_action is not None:
                self.scribble_action.blockSignals(True)
                self.scribble_action.setChecked(False)
                self.scribble_action.blockSignals(False)
            return

        dialog = self._ensure_scribble_tool_dialog()
        active = self.get_active_layer()
        preferred = None
        if active is not None and active.get_name() not in (
            self.scribble_fg_layer_name,
            self.scribble_bg_layer_name,
        ):
            preferred = active.get_name()
        self._ensure_scribble_layers()
        self._refresh_scribble_target_layers(preferred_name=preferred)

        self.scribble_erase_active = False
        if hasattr(self, "scribble_erase_checkbox") and self.scribble_erase_checkbox is not None:
            self.scribble_erase_checkbox.blockSignals(True)
            self.scribble_erase_checkbox.setChecked(False)
            self.scribble_erase_checkbox.blockSignals(False)

        self.scribble_active = True
        self.scribble_action.blockSignals(True)
        self.scribble_action.setChecked(True)
        self.scribble_action.blockSignals(False)
        if self.scribble_button is not None:
            self.scribble_button.blockSignals(True)
            self.scribble_button.setChecked(True)
            self.scribble_button.blockSignals(False)

        self._brush_color_is_erase = None
        dialog.show()
        dialog.raise_()
        self.enable_paintbrush(True)
        self._update_scribble_brush_colors()
        self.print_status("Scribble tool activated")

    def close_scribble_tool(self):
        self._closing_scribble_tool = True
        try:
            self.scribble_active = False
            self.scribble_erase_active = False
            if self.scribble_action is not None:
                self.scribble_action.blockSignals(True)
                self.scribble_action.setChecked(False)
                self.scribble_action.blockSignals(False)
            if self.scribble_button is not None:
                self.scribble_button.blockSignals(True)
                self.scribble_button.setChecked(False)
                self.scribble_button.blockSignals(False)
            if hasattr(self, "scribble_erase_checkbox") and self.scribble_erase_checkbox is not None:
                self.scribble_erase_checkbox.blockSignals(True)
                self.scribble_erase_checkbox.setChecked(False)
                self.scribble_erase_checkbox.blockSignals(False)
            if self.scribble_tool_dialog is not None and self.scribble_tool_dialog.isVisible():
                self.scribble_tool_dialog.hide()
            self.enable_paintbrush(False)
            self.print_status("Scribble tool deactivated")
        finally:
            self._closing_scribble_tool = False

    def toggle_scribble_tool(self, checked):
        dialog_visible = (
            self.scribble_tool_dialog is not None and self.scribble_tool_dialog.isVisible()
        )
        if checked and self.scribble_active and dialog_visible:
            return
        if (not checked) and (not self.scribble_active) and (not dialog_visible):
            return
        if checked:
            self.open_scribble_tool()
        else:
            self.close_scribble_tool()

    def clear_scribble_layers(self):
        import vtk_tools

        for name in (self.scribble_fg_layer_name, self.scribble_bg_layer_name):
            layer = self.segmentation_layers.get_layer_by_name(name)
            if layer is None:
                continue
            empty = self.create_empty_segmentation_image()
            layer.set_image(empty)
            self.layer_image_modified.emit(layer, self)
        self.print_status("Scribble overlays cleared")

    def run_scribble_graphcut(self):
        from PyQt5.QtWidgets import QMessageBox
        import qt_tools
        from graphcut_histogram import vtk_arrays_histogram_graphcut

        base = self.get_base_vtk_image()
        if base is None:
            QMessageBox.warning(self.dock_widget, "Scribble Tool", "No image is open.")
            return

        self._ensure_scribble_layers()
        fg_layer = self.segmentation_layers.get_layer_by_name(self.scribble_fg_layer_name)
        bg_layer = self.segmentation_layers.get_layer_by_name(self.scribble_bg_layer_name)
        target = self.get_scribble_target_layer()
        if fg_layer is None or bg_layer is None:
            QMessageBox.warning(self.dock_widget, "Scribble Tool", "Scribble layers are missing.")
            return
        if target is None:
            QMessageBox.warning(
                self.dock_widget,
                "Scribble Tool",
                "Select a Target Layer (foreground) to update.",
            )
            return
        if target.get_name() in (self.scribble_fg_layer_name, self.scribble_bg_layer_name):
            QMessageBox.warning(
                self.dock_widget,
                "Scribble Tool",
                "Target Layer must be a real label layer, not a scribble overlay.",
            )
            return

        if hasattr(self, "scribble_lamda_spin"):
            self.scribble_lamda = float(self.scribble_lamda_spin.value())
            self.scribble_sigma = float(self.scribble_sigma_spin.value())
            self.scribble_num_bins = int(self.scribble_bins_spin.value())

        try:
            with qt_tools.busy_progress(
                self.dock_widget,
                title="Scribble Tool",
                label="Running GraphCut+Histogram...",
            ):
                result = vtk_arrays_histogram_graphcut(
                    base_vtk_image=base,
                    fg_scribble_vtk=fg_layer.get_image(),
                    bg_scribble_vtk=bg_layer.get_image(),
                    num_bins=self.scribble_num_bins,
                    lamda=self.scribble_lamda,
                    sigma=self.scribble_sigma,
                )
            target.set_image(result)
            self._modified = True
            self.layer_image_modified.emit(target, self)
            self.print_status(
                f"Scribble GraphCut updated target layer '{target.get_name()}'"
            )
        except Exception as e:
            QMessageBox.critical(self.dock_widget, "Scribble Tool Failed", str(e))
            self.print_status(f"Scribble GraphCut failed: {e}")

    # ------------------------------------------------------------------
    # Interpolation Tool: fill between sparse slices (Slicer Fill between slices)
    # ------------------------------------------------------------------

    def show_interpolation_tool_clicked(self):
        if self.get_base_vtk_image() is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.dock_widget,
                "Interpolation Tool",
                "Open an image in the viewer first.",
            )
            return

        if (
            self.interpolation_tool_dialog is not None
            and self.interpolation_tool_dialog.isVisible()
        ):
            self.interpolation_tool_dialog.raise_()
            self.interpolation_tool_dialog.activateWindow()
            self._refresh_interpolation_target_layers()
            return

        dialog = self._ensure_interpolation_tool_dialog()
        active = self.get_active_layer()
        preferred = active.get_name() if active is not None else None
        # Prefer a real label layer, not scribble overlays.
        if preferred in (
            getattr(self, "scribble_fg_layer_name", None),
            getattr(self, "scribble_bg_layer_name", None),
        ):
            preferred = None
        self._refresh_interpolation_target_layers(preferred_name=preferred)
        dialog.show()
        dialog.raise_()

    def _ensure_interpolation_tool_dialog(self):
        if self.interpolation_tool_dialog is not None:
            return self.interpolation_tool_dialog

        from PyQt5.QtWidgets import (
            QDialog,
            QComboBox,
            QFormLayout,
            QVBoxLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
        )

        dialog = QDialog(self.dock_widget)
        dialog.setWindowTitle("Interpolation Tool (Fill Between Slices)")
        dialog.setModal(False)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WA_ShowWithoutActivating, True)
        dialog.resize(400, 260)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        self.interpolation_target_combo = QComboBox(dialog)
        self.interpolation_target_combo.setToolTip(
            "Layer with sparse slice labels to fill between"
        )
        self.interpolation_target_combo.currentTextChanged.connect(
            self._on_interpolation_target_changed
        )
        form.addRow("Target Layer:", self.interpolation_target_combo)

        self.interpolation_axis_combo = QComboBox(dialog)
        # Values match ITK MorphologicalContourInterpolator axes.
        self.interpolation_axis_combo.addItem("Auto (all axes)", -1)
        self.interpolation_axis_combo.addItem("Axial (Z)", 2)
        self.interpolation_axis_combo.addItem("Coronal (Y)", 1)
        self.interpolation_axis_combo.addItem("Sagittal (X)", 0)
        self.interpolation_axis_combo.setCurrentIndex(1)  # Axial default for CT workflows
        self.interpolation_axis_combo.setToolTip(
            "Slice axis to interpolate along. Axial is typical for sparse axial paintings."
        )
        form.addRow("Axis:", self.interpolation_axis_combo)

        layout.addLayout(form)

        hint = QLabel(
            "Paint complete contours on selected slices with the Paint Tool, "
            "leaving at least one empty neighbor slice between painted slices. "
            "Then click Run to fill the empty slices "
            "(morphological contour interpolation, same as Slicer "
            "\"Fill between slices\")."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        run_btn = QPushButton("Run")
        run_btn.setToolTip("Fill empty slices between painted contours")
        run_btn.clicked.connect(self.run_interpolation_fill_between_slices)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        btn_row.addWidget(run_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.interpolation_tool_dialog = dialog
        return dialog

    def _on_interpolation_target_changed(self, name):
        self._interpolation_target_layer_name = name or None

    def _refresh_interpolation_target_layers(self, preferred_name=None):
        if (
            not hasattr(self, "interpolation_target_combo")
            or self.interpolation_target_combo is None
        ):
            return
        skip = {
            getattr(self, "scribble_fg_layer_name", None),
            getattr(self, "scribble_bg_layer_name", None),
        }
        skip.discard(None)
        names = [n for n in self.segmentation_layers.get_layer_names() if n not in skip]
        current = preferred_name or self.interpolation_target_combo.currentText()
        self.interpolation_target_combo.blockSignals(True)
        self.interpolation_target_combo.clear()
        self.interpolation_target_combo.addItems(names)
        if current in names:
            self.interpolation_target_combo.setCurrentText(current)
        elif names:
            self.interpolation_target_combo.setCurrentIndex(0)
        self.interpolation_target_combo.blockSignals(False)
        self._on_interpolation_target_changed(
            self.interpolation_target_combo.currentText()
        )

    def get_interpolation_target_layer(self):
        name = getattr(self, "_interpolation_target_layer_name", None)
        if name:
            layer = self.segmentation_layers.get_layer_by_name(name)
            if layer is not None:
                return layer
        return self.get_active_layer()

    def run_interpolation_fill_between_slices(self):
        from PyQt5.QtWidgets import QMessageBox
        import qt_tools
        from fill_between_slices import fill_between_slices_vtk, write_zyx_into_vtk_image

        target = self.get_interpolation_target_layer()
        if target is None:
            QMessageBox.warning(
                self.dock_widget,
                "Interpolation Tool",
                "Select a Target Layer that has sparse slice paintings.",
            )
            return

        image = target.get_image()
        if image is None:
            QMessageBox.warning(
                self.dock_widget,
                "Interpolation Tool",
                "Target layer has no image data.",
            )
            return

        axis = int(self.interpolation_axis_combo.currentData())
        try:
            with qt_tools.busy_progress(
                self.dock_widget,
                title="Interpolation Tool",
                label="Filling between slices...",
            ):
                filled = fill_between_slices_vtk(image, axis=axis, label=0)
                write_zyx_into_vtk_image(image, filled)
            target.set_modified(True)
            self._modified = True
            # Emit image_changed last so 3D surface uses the prompt (0ms) refresh path.
            target.image_changed.emit(target)
            self.print_status(
                f"Fill between slices applied to '{target.get_name()}' (axis={axis})"
            )
        except Exception as e:
            QMessageBox.critical(self.dock_widget, "Interpolation Failed", str(e))
            self.print_status(f"Interpolation failed: {e}")

    def show_boolean_tool_clicked(self):
        from PyQt5.QtWidgets import QDialog, QComboBox, QPushButton, QVBoxLayout, QFormLayout

        dialog = QDialog(self.dock_widget)
        dialog.setWindowTitle("Boolean Tool")
        dialog.setModal(False)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WA_ShowWithoutActivating, True)
        dialog.resize(320, 220)

        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        layer_names = self.segmentation_layers.get_layer_names()

        comboA = QComboBox()
        comboA.addItems(layer_names)

        comboB = QComboBox()
        comboB.addItems(layer_names)

        operation_combo = QComboBox()
        # Display labels with math-style symbols; item data keeps API op codes.
        for label, op_code in (
            ("A ∩ B", "AND"),  # intersection
            ("A ∪ B", "OR"),
            ("A - B", "SUB"),
        ):
            operation_combo.addItem(label, op_code)

        target_combo = QComboBox()
        target_combo.addItems(layer_names)
        target_combo.setToolTip("Layer that will receive the boolean result")

        active = self.get_active_layer()
        if active is not None:
            active_name = active.get_name()
            if active_name in layer_names:
                target_combo.setCurrentText(active_name)

        form_layout.addRow("Image A:", comboA)
        form_layout.addRow("Operation:", operation_combo)
        form_layout.addRow("Image B:", comboB)
        form_layout.addRow("Target Layer:", target_combo)

        layout.addLayout(form_layout)

        run_button = QPushButton("Run")
        layout.addWidget(run_button, alignment=Qt.AlignRight)

        def run_operation():
            nameA = comboA.currentText()
            nameB = comboB.currentText()
            op = operation_combo.currentData()
            target_name = target_combo.currentText()

            if not nameA or not nameB or not target_name:
                self.print_status("Select Image A, Image B, and Target Layer.")
                return

            if nameA == nameB:
                self.print_status("Image A and B must be different.")
                return

            layerA = self.segmentation_layers.get_layer_by_name(nameA)
            layerB = self.segmentation_layers.get_layer_by_name(nameB)
            target_layer = self.segmentation_layers.get_layer_by_name(target_name)
            if layerA is None or layerB is None or target_layer is None:
                self.print_status("One or more selected layers no longer exist.")
                return

            import vtk_tools
            result = vtk_tools.perform_boolean_operation(layerA.get_image(), layerB.get_image(), op)
            if result is None:
                self.print_status("Operation failed.")
                return

            target_layer.set_image(result)
            self._modified = True
            self.layer_image_modified.emit(target_layer, self)

            self.print_status(
                f"Boolean {op} applied to target layer '{target_name}' ({nameA} {op} {nameB})"
            )

        run_button.clicked.connect(run_operation)
        dialog.show()
        dialog.raise_()


    def on_brush_3d_toggled(self, state):
        self.paintbrush_3d = (state == Qt.Checked)
        print(f"3D Brush enabled: {self.paintbrush_3d}")
        
        # if viewers have paintbrushs, update
        for v in self.vtk_viewer.get_viewers_2d():
            if hasattr(v, 'paintbrush') and v.paintbrush is not None:
                v.paintbrush.set_brush_3d(self.paintbrush_3d)

    def get_exclusive_actions(self):
        actions = [self.paint_action, self.pencil_action]
        if getattr(self, "scribble_action", None) is not None:
            actions.append(self.scribble_action)
        return actions
    
    def clear(self):       
        
        # deactivate editing
        self.toggle_erase_tool(False)
        self.toggle_paint_tool(False)
        self.toggle_pencil_tool(False)
        if getattr(self, "scribble_active", False):
            self.toggle_scribble_tool(False)

        # reset rgw color rotator
        color_rotator1.reset()

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
        segmentations = []
        import itkvtk
        for layer in self.segmentation_layers.get_layers():
            segmentation_file = f"{layer.get_name()}.mha"
            segmentation_path = os.path.join(data_dir, segmentation_file )
            itkvtk.save_vtk_image_using_sitk(layer.get_image(), segmentation_path)

            # Add layer metadata to the workspace data
            segmentations.append({
                "name" : layer.get_name(),
                "color": list(layer.get_color()),
                "alpha": layer.get_alpha(),
                "file": segmentation_file
            })
        data_dict["segmentations"] = segmentations


    def load_state(self, data_dict, data_dir, aux_data):
        import os

        self.clear()

        self.vtk_image = aux_data['base_image']

        # Load segmentation layers
        from itkvtk import load_vtk_image_using_sitk

        for segmentation in data_dict.get("segmentations", {}):
            seg_path = os.path.join(data_dir, segmentation["file"])
            layer_name = segmentation["name"]
            if os.path.exists(seg_path):
                try:
                    vtk_seg = load_vtk_image_using_sitk(seg_path)

                    import vtk_tools
                    vtk_tools.copy_image_origin_spacing_direction_matrix(self.vtk_image, vtk_seg)

                    self.add_layer(
                        segmentation=vtk_seg,
                        layer_name=segmentation["name"],
                        color_vtk=to_vtk_color(segmentation["color"]),
                        alpha=segmentation["alpha"]
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
        return self._active_layer

    def set_active_layer(self, layer):
        if self._active_layer is not layer:
            self._active_layer = layer
            self.active_layer_changed.emit(self)

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
        if 'image_index' not in event_data:
            return

        image_index = event_data['image_index']
        if getattr(self, "scribble_active", False):
            layer = self.get_scribble_paint_layer()
            erase = bool(self.scribble_erase_active)
        else:
            layer = self.get_paint_target_layer()
            erase = bool(self.erase_active)
        if layer is None:
            return

        if not layer.get_visible():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Warning", "The layer being editted is not visible. Please turn it on first.")
            return

        value = 0 if erase else 1
        v2d.paintbrush.paint(layer.get_image(), image_index[0], image_index[1], image_index[2], value)

        # flag vtkImageData as Modified to update the pipeline.
        layer.get_image().Modified()

        # flag manager data has been modified (for saving)
        self._modified = True

        # emit event (other views update; painted view renders immediately below)
        self.layer_image_modified.emit(layer, self)

        # Always refresh the view under the cursor right away. Opening the Paint
        # Tool window can leave VTK views "inactive", which otherwise uses a
        # 1000ms delayed render and feels very laggy while dragging.
        v2d.render()
        
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

        # Mark this view active immediately so slice updates render without delay.
        if hasattr(self.vtk_viewer, 'activate_viewer'):
            self.vtk_viewer.activate_viewer(obj)
        
        self.left_button_is_pressed = True
        self.last_mouse_position = v2d.get_interactor().GetEventPosition()
        
        target_layer = self.get_paint_target_layer()
        if self.left_button_is_pressed and v2d.paintbrush.enabled and target_layer is not None:
            if target_layer.get_visible():
                self.paint_at_mouse_position(v2d)
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(None, "Warning", "The layer being editted is not visible. Please turn it on first.")
                self.left_button_is_pressed = False
                return 
       
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

            # interaction point in camo
            w_pt_interaction = np.append(np.array(world_pos), 1.0).reshape(4,1)
            camo_pt_interaction = camo_H_w @ w_pt_interaction

            # project to the camera near plane
            clip_range = cam.get_clip_range()
            z_near = clip_range[0]
            camo_pt_interaction[2,0] = z_near+0.1

            # projected interaction point in w
            w_pt_on_near_plane =  (w_H_camo @ camo_pt_interaction).flatten()[:3]

            # Update the brush position (ensure Z remains on the image plane + 0.1 to show on top of the image)
            paintbrush.get_actor().SetPosition(w_pt_on_near_plane[0], w_pt_on_near_plane[1], w_pt_on_near_plane[2])
            paintbrush.get_actor().SetVisibility(True)  # Make the brush visible

            # Only update brush color when erase mode changes.
            if getattr(self, "scribble_active", False):
                if self.scribble_erase_active:
                    desired = ("erase", self.erase_brush_color)
                elif self.scribble_mode == "background":
                    desired = ("bg", self.scribble_bg_brush_color)
                else:
                    desired = ("fg", self.scribble_fg_brush_color)
                if self._brush_color_is_erase != desired[0]:
                    paintbrush.set_color(desired[1])
                    self._brush_color_is_erase = desired[0]
            elif self._brush_color_is_erase != self.erase_active:
                if self.erase_active:
                    paintbrush.set_color(self.erase_brush_color)
                else:
                    paintbrush.set_color(self.paint_brush_color)
                self._brush_color_is_erase = self.erase_active

            # Paint 
            target_layer = self.get_paint_target_layer()
            if self.left_button_is_pressed and paintbrush.enabled and target_layer is not None:
                if target_layer.get_visible():
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
                self.set_active_layer(item_widget.layer)

    def get_paint_target_layer(self):
        """Layer currently targeted by the Paint Tool dropdown."""
        if self._paint_target_layer is not None:
            return self._paint_target_layer
        if self._paint_target_layer_name:
            layer = self.segmentation_layers.get_layer_by_name(self._paint_target_layer_name)
            if layer is not None:
                self._paint_target_layer = layer
                return layer
        return self.get_active_layer()

    def _ensure_paint_tool_dialog(self):
        if self.paint_tool_dialog is not None:
            return self.paint_tool_dialog

        from PyQt5.QtWidgets import (
            QDialog, QComboBox, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel,
        )
        from labeled_slider import LabeledSlider

        dialog = QDialog(self.dock_widget)
        dialog.setWindowTitle("Paint Tool")
        dialog.setModal(False)
        # Tool + stay-on-top, but do not activate on show so VTK keeps focus/active view.
        dialog.setWindowFlags(dialog.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WA_ShowWithoutActivating, True)
        dialog.resize(320, 180)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        self.paint_target_combo = QComboBox(dialog)
        self.paint_target_combo.setToolTip("Layer that painting/erasing will modify")
        self.paint_target_combo.currentTextChanged.connect(self._on_paint_target_layer_changed)
        form.addRow("Target Layer:", self.paint_target_combo)

        self.brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        self.brush_size_slider.slider.setMinimum(3)
        self.brush_size_slider.slider.setMaximum(100)
        self.brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        form.addRow(self.brush_size_slider)

        self.brush_3d_checkbox = QCheckBox("3D Brush")
        self.brush_3d_checkbox.setChecked(bool(self.paintbrush_3d))
        self.brush_3d_checkbox.stateChanged.connect(self.on_brush_3d_toggled)
        form.addRow("", self.brush_3d_checkbox)

        self.erase_checkbox = QCheckBox("Erase")
        self.erase_checkbox.setToolTip("When checked, brush strokes erase instead of paint")
        self.erase_checkbox.setChecked(False)
        self.erase_checkbox.stateChanged.connect(self._on_erase_checkbox_changed)
        form.addRow("", self.erase_checkbox)

        layout.addLayout(form)
        hint = QLabel("Close this window to leave paint/erase mode.")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)

        dialog.finished.connect(self._on_paint_tool_dialog_finished)
        self.paint_tool_dialog = dialog
        return dialog

    def _refresh_paint_target_layers(self, preferred_name=None):
        if not hasattr(self, 'paint_target_combo') or self.paint_target_combo is None:
            return

        preferred = preferred_name or self._paint_target_layer_name
        if not preferred:
            active = self.get_active_layer()
            if active is not None:
                preferred = active.get_name()

        names = self.segmentation_layers.get_layer_names()
        self.paint_target_combo.blockSignals(True)
        self.paint_target_combo.clear()
        self.paint_target_combo.addItems(names)
        if preferred and preferred in names:
            self.paint_target_combo.setCurrentText(preferred)
            self._paint_target_layer_name = preferred
        elif names:
            self.paint_target_combo.setCurrentIndex(0)
            self._paint_target_layer_name = names[0]
        else:
            self._paint_target_layer_name = None
        self._paint_target_layer = (
            self.segmentation_layers.get_layer_by_name(self._paint_target_layer_name)
            if self._paint_target_layer_name else None
        )
        self.paint_target_combo.blockSignals(False)

    def _on_paint_target_layer_changed(self, name):
        self._paint_target_layer_name = name or None
        self._paint_target_layer = (
            self.segmentation_layers.get_layer_by_name(self._paint_target_layer_name)
            if self._paint_target_layer_name else None
        )

    def _on_erase_checkbox_changed(self, state):
        self.toggle_erase_tool(state == Qt.Checked)

    def _on_paint_tool_dialog_finished(self, result=0):
        if self._closing_paint_tool:
            return
        # Closing the floating window ends paint/erase mode.
        self.toggle_paint_tool(False)

    def open_paint_tool(self):
        if self.pencil_active:
            self.toggle_pencil_tool(False)
        if getattr(self, "scribble_active", False):
            self.toggle_scribble_tool(False)

        dialog = self._ensure_paint_tool_dialog()
        active = self.get_active_layer()
        preferred = active.get_name() if active is not None else None
        self._refresh_paint_target_layers(preferred_name=preferred)

        if hasattr(self, 'erase_checkbox') and self.erase_checkbox is not None:
            self.erase_checkbox.blockSignals(True)
            self.erase_checkbox.setChecked(False)
            self.erase_checkbox.blockSignals(False)

        self.erase_active = False
        self.paint_active = True
        self.paint_action.blockSignals(True)
        self.paint_action.setChecked(True)
        self.paint_action.blockSignals(False)
        if hasattr(self, 'paint_button') and self.paint_button is not None:
            self.paint_button.blockSignals(True)
            self.paint_button.setChecked(True)
            self.paint_button.blockSignals(False)

        dialog.show()
        dialog.raise_()
        # Intentionally do not activateWindow(): keep VTK view focus/active for responsive painting.
        self.enable_paintbrush(True)
        self.print_status("Paint tool activated")

    def close_paint_tool(self):
        self._closing_paint_tool = True
        try:
            self.paint_active = False
            self.erase_active = False
            self.paint_action.blockSignals(True)
            self.paint_action.setChecked(False)
            self.paint_action.blockSignals(False)
            if hasattr(self, 'paint_button') and self.paint_button is not None:
                self.paint_button.blockSignals(True)
                self.paint_button.setChecked(False)
                self.paint_button.blockSignals(False)

            if hasattr(self, 'erase_checkbox') and self.erase_checkbox is not None:
                self.erase_checkbox.blockSignals(True)
                self.erase_checkbox.setChecked(False)
                self.erase_checkbox.blockSignals(False)

            if self.paint_tool_dialog is not None and self.paint_tool_dialog.isVisible():
                self.paint_tool_dialog.hide()

            self.enable_paintbrush(False)
            self.print_status("Paint tool deactivated")
        finally:
            self._closing_paint_tool = False

    def toggle_paint_tool(self, checked):
        # Ignore no-op toggles, but still open if action is checked while dialog hidden.
        dialog_visible = (
            self.paint_tool_dialog is not None and self.paint_tool_dialog.isVisible()
        )
        if checked and self.paint_active and dialog_visible:
            return
        if (not checked) and (not self.paint_active) and (not self.erase_active) and (not dialog_visible):
            return

        if checked:
            self.open_paint_tool()
        else:
            self.close_paint_tool()

    def toggle_erase_tool(self, checked):
        """Enable/disable erase mode while the Paint Tool session is open."""
        checked = bool(checked)
        if self.erase_active == checked:
            return

        self.erase_active = checked
        self._brush_color_is_erase = None  # force brush color refresh on next move
        # Keep paint session flagged while erasing so brush stays enabled.
        if checked:
            self.paint_active = True

        if hasattr(self, 'erase_checkbox') and self.erase_checkbox is not None:
            if self.erase_checkbox.isChecked() != checked:
                self.erase_checkbox.blockSignals(True)
                self.erase_checkbox.setChecked(checked)
                self.erase_checkbox.blockSignals(False)

        if checked:
            self.print_status("Erase mode activated")
        else:
            self.print_status("Paint mode activated")

        self.enable_paintbrush(self.paint_active or self.erase_active)

    # ------------------------------------------------------------------
    # Pencil Tool: click-to-draw polygon, right-click to close & fill
    # ------------------------------------------------------------------

    def get_pencil_target_layer(self):
        """Layer currently targeted by the Pencil Tool dropdown."""
        if self._pencil_target_layer is not None:
            return self._pencil_target_layer
        if self._pencil_target_layer_name:
            layer = self.segmentation_layers.get_layer_by_name(self._pencil_target_layer_name)
            if layer is not None:
                self._pencil_target_layer = layer
                return layer
        return self.get_active_layer()

    def _ensure_pencil_tool_dialog(self):
        if self.pencil_tool_dialog is not None:
            return self.pencil_tool_dialog

        from PyQt5.QtWidgets import (
            QDialog, QComboBox, QFormLayout, QVBoxLayout, QLabel,
        )

        dialog = QDialog(self.dock_widget)
        dialog.setWindowTitle("Pencil Tool")
        dialog.setModal(False)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WA_ShowWithoutActivating, True)
        dialog.resize(320, 160)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        self.pencil_target_combo = QComboBox(dialog)
        self.pencil_target_combo.setToolTip("Layer that pencil fill/erase will modify")
        self.pencil_target_combo.currentTextChanged.connect(self._on_pencil_target_layer_changed)
        form.addRow("Target Layer:", self.pencil_target_combo)

        self.pencil_erase_checkbox = QCheckBox("Erase")
        self.pencil_erase_checkbox.setToolTip(
            "When checked, the closed area erases instead of painting"
        )
        self.pencil_erase_checkbox.setChecked(False)
        self.pencil_erase_checkbox.stateChanged.connect(self._on_pencil_erase_checkbox_changed)
        form.addRow("", self.pencil_erase_checkbox)

        layout.addLayout(form)
        hint = QLabel(
            "Click or drag with left mouse to draw. Right-click to close and fill.\n"
            "Close this window to leave pencil mode."
        )
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)

        dialog.finished.connect(self._on_pencil_tool_dialog_finished)
        self.pencil_tool_dialog = dialog
        return dialog

    def _refresh_pencil_target_layers(self, preferred_name=None):
        if not hasattr(self, "pencil_target_combo") or self.pencil_target_combo is None:
            return

        preferred = preferred_name or self._pencil_target_layer_name
        if not preferred:
            active = self.get_active_layer()
            if active is not None:
                preferred = active.get_name()

        names = self.segmentation_layers.get_layer_names()
        self.pencil_target_combo.blockSignals(True)
        self.pencil_target_combo.clear()
        self.pencil_target_combo.addItems(names)
        if preferred and preferred in names:
            self.pencil_target_combo.setCurrentText(preferred)
            self._pencil_target_layer_name = preferred
        elif names:
            self.pencil_target_combo.setCurrentIndex(0)
            self._pencil_target_layer_name = names[0]
        else:
            self._pencil_target_layer_name = None
        self._pencil_target_layer = (
            self.segmentation_layers.get_layer_by_name(self._pencil_target_layer_name)
            if self._pencil_target_layer_name else None
        )
        self.pencil_target_combo.blockSignals(False)

    def _on_pencil_target_layer_changed(self, name):
        self._pencil_target_layer_name = name or None
        self._pencil_target_layer = (
            self.segmentation_layers.get_layer_by_name(self._pencil_target_layer_name)
            if self._pencil_target_layer_name else None
        )

    def _on_pencil_erase_checkbox_changed(self, state):
        self.pencil_erase_active = (state == Qt.Checked)
        self._update_pencil_overlay_style()
        if self.pencil_erase_active:
            self.print_status("Pencil erase mode")
        else:
            self.print_status("Pencil paint mode")

    def _on_pencil_tool_dialog_finished(self, result=0):
        if self._closing_pencil_tool:
            return
        self.toggle_pencil_tool(False)

    def open_pencil_tool(self):
        if self.paint_active or self.erase_active:
            self.toggle_paint_tool(False)
        if getattr(self, "scribble_active", False):
            self.toggle_scribble_tool(False)

        dialog = self._ensure_pencil_tool_dialog()
        active = self.get_active_layer()
        preferred = active.get_name() if active is not None else None
        self._refresh_pencil_target_layers(preferred_name=preferred)

        if hasattr(self, "pencil_erase_checkbox") and self.pencil_erase_checkbox is not None:
            self.pencil_erase_checkbox.blockSignals(True)
            self.pencil_erase_checkbox.setChecked(False)
            self.pencil_erase_checkbox.blockSignals(False)

        self.pencil_erase_active = False
        self.pencil_active = True
        self.pencil_action.blockSignals(True)
        self.pencil_action.setChecked(True)
        self.pencil_action.blockSignals(False)
        if hasattr(self, "pencil_button") and self.pencil_button is not None:
            self.pencil_button.blockSignals(True)
            self.pencil_button.setChecked(True)
            self.pencil_button.blockSignals(False)

        dialog.show()
        dialog.raise_()
        self.enable_pencil_tool(True)
        self.print_status("Pencil tool activated")

    def close_pencil_tool(self):
        self._closing_pencil_tool = True
        try:
            self.pencil_active = False
            self.pencil_erase_active = False
            self.pencil_action.blockSignals(True)
            self.pencil_action.setChecked(False)
            self.pencil_action.blockSignals(False)
            if hasattr(self, "pencil_button") and self.pencil_button is not None:
                self.pencil_button.blockSignals(True)
                self.pencil_button.setChecked(False)
                self.pencil_button.blockSignals(False)

            if hasattr(self, "pencil_erase_checkbox") and self.pencil_erase_checkbox is not None:
                self.pencil_erase_checkbox.blockSignals(True)
                self.pencil_erase_checkbox.setChecked(False)
                self.pencil_erase_checkbox.blockSignals(False)

            if self.pencil_tool_dialog is not None and self.pencil_tool_dialog.isVisible():
                self.pencil_tool_dialog.hide()

            self.enable_pencil_tool(False)
            self.print_status("Pencil tool deactivated")
        finally:
            self._closing_pencil_tool = False

    def toggle_pencil_tool(self, checked):
        dialog_visible = (
            self.pencil_tool_dialog is not None and self.pencil_tool_dialog.isVisible()
        )
        if checked and self.pencil_active and dialog_visible:
            return
        if (not checked) and (not self.pencil_active) and (not dialog_visible):
            return

        if checked:
            self.open_pencil_tool()
        else:
            self.close_pencil_tool()

    def enable_pencil_tool(self, enabled=True):
        for v in self.vtk_viewer.get_viewers_2d():
            interactor = v.interactor
            v.suppress_context_menu = bool(enabled)

            if enabled:
                if not hasattr(v, "pencil_overlay_actor") or v.pencil_overlay_actor is None:
                    self._create_pencil_overlay(v)

                v.pencil_left_press_observer = interactor.AddObserver(
                    "LeftButtonPressEvent", self.on_pencil_left_button_press
                )
                v.pencil_left_release_observer = interactor.AddObserver(
                    "LeftButtonReleaseEvent", self.on_pencil_left_button_release
                )
                v.pencil_right_press_observer = interactor.AddObserver(
                    "RightButtonPressEvent", self.on_pencil_right_button_press
                )
                v.pencil_mouse_move_observer = interactor.AddObserver(
                    "MouseMoveEvent", self.on_pencil_mouse_move
                )
            else:
                for attr in (
                    "pencil_left_press_observer",
                    "pencil_left_release_observer",
                    "pencil_right_press_observer",
                    "pencil_mouse_move_observer",
                ):
                    tag = getattr(v, attr, None)
                    if tag is not None:
                        interactor.RemoveObserver(tag)
                        setattr(v, attr, None)

                self._clear_pencil_overlay(v)

        self._reset_pencil_drawing()

    def _create_pencil_overlay(self, v2d):
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()
        poly = vtk.vtkPolyData()
        poly.SetPoints(points)
        poly.SetLines(lines)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly)
        # Keep lines from losing the depth fight against the slice image.
        mapper.SetResolveCoincidentTopologyToPolygonOffset()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(3)
        actor.GetProperty().SetColor(0.0, 1.0, 0.0)
        actor.GetProperty().SetLighting(False)
        actor.SetVisibility(False)

        v2d.get_renderer().AddActor(actor)
        v2d.pencil_overlay_points = points
        v2d.pencil_overlay_lines = lines
        v2d.pencil_overlay_poly = poly
        v2d.pencil_overlay_actor = actor

    def _pencil_overlay_color(self):
        if self.pencil_erase_active:
            return (0.0, 0.5, 1.0)
        return (0.0, 1.0, 0.0)

    def _update_pencil_overlay_style(self):
        color = self._pencil_overlay_color()
        for v in self.vtk_viewer.get_viewers_2d():
            actor = getattr(v, "pencil_overlay_actor", None)
            if actor is not None:
                actor.GetProperty().SetColor(*color)
                if self._pencil_viewer is v:
                    v.render()

    def _clear_pencil_overlay(self, v2d):
        actor = getattr(v2d, "pencil_overlay_actor", None)
        if actor is None:
            return
        points = v2d.pencil_overlay_points
        lines = v2d.pencil_overlay_lines
        points.Reset()
        lines.Reset()
        v2d.pencil_overlay_poly.Modified()
        actor.SetVisibility(False)
        v2d.render()

    def _reset_pencil_drawing(self):
        if self._pencil_viewer is not None:
            self._clear_pencil_overlay(self._pencil_viewer)
        self._pencil_points_ijk = []
        self._pencil_points_world = []
        self._pencil_viewer = None
        self._pencil_axis = None
        self._pencil_fixed_coord = None
        self._pencil_cursor_world = None
        self._pencil_left_button_down = False

    def _fixed_coord_for_axis(self, image_index, axis):
        import reslicer
        if axis == reslicer.AXIAL:
            return int(round(image_index[2]))
        if axis == reslicer.CORONAL:
            return int(round(image_index[1]))
        if axis == reslicer.SAGITTAL:
            return int(round(image_index[0]))
        raise ValueError(f"Invalid axis: {axis}")

    def _project_world_in_front_of_slice(self, v2d, world_pos):
        """Shift a world point toward the camera so overlay lines draw above the slice."""
        import numpy as np
        import vtk_camera_wrapper

        camera = v2d.get_renderer().GetActiveCamera()
        cam = vtk_camera_wrapper.vtk_camera_wrapper(camera)
        w_H_camo = cam.get_w_H_o()
        camo_H_w = cam.get_o_H_w()

        w_pt = np.append(np.array(world_pos, dtype=float), 1.0).reshape(4, 1)
        camo_pt = camo_H_w @ w_pt
        # Same trick as the paintbrush cursor: pull to just in front of the near plane.
        z_near = cam.get_clip_range()[0]
        camo_pt[2, 0] = z_near + 0.1
        return (w_H_camo @ camo_pt).flatten()[:3]

    def _refresh_pencil_overlay(self):
        v2d = self._pencil_viewer
        if v2d is None or not hasattr(v2d, "pencil_overlay_actor"):
            return

        points = v2d.pencil_overlay_points
        lines = v2d.pencil_overlay_lines
        points.Reset()
        lines.Reset()

        world_pts = list(self._pencil_points_world)
        if self._pencil_cursor_world is not None and world_pts:
            world_pts = world_pts + [self._pencil_cursor_world]

        for wp in world_pts:
            disp = self._project_world_in_front_of_slice(v2d, wp)
            points.InsertNextPoint(float(disp[0]), float(disp[1]), float(disp[2]))

        n = points.GetNumberOfPoints()
        if n >= 2:
            for i in range(n - 1):
                line = vtk.vtkLine()
                line.GetPointIds().SetId(0, i)
                line.GetPointIds().SetId(1, i + 1)
                lines.InsertNextCell(line)

        points.Modified()
        lines.Modified()
        v2d.pencil_overlay_poly.Modified()
        actor = v2d.pencil_overlay_actor
        actor.GetProperty().SetColor(*self._pencil_overlay_color())
        actor.SetVisibility(n > 0)
        v2d.render()

    def _try_add_pencil_point(self, v2d, image_index, world_point, require_spacing=False):
        """Append a polyline vertex if view/slice/layer checks pass.

        When require_spacing is True (drag sampling), skip points closer than
        _pencil_min_drag_spacing_px in image-index space to avoid oversampling.
        """
        axis = v2d.reslicer.axis
        fixed = self._fixed_coord_for_axis(image_index, axis)

        if self._pencil_viewer is None:
            self._pencil_viewer = v2d
            self._pencil_axis = axis
            self._pencil_fixed_coord = fixed
        else:
            if v2d is not self._pencil_viewer:
                if not require_spacing:
                    self.print_status("Pencil: finish or cancel on the same view")
                return False
            if fixed != self._pencil_fixed_coord:
                if not require_spacing:
                    self.print_status("Pencil: stay on the same slice while drawing")
                return False

        layer = self.get_pencil_target_layer()
        if layer is None:
            if not require_spacing:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(None, "Warning", "No target layer selected for the Pencil Tool.")
            return False
        if not layer.get_visible():
            if not require_spacing:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    None, "Warning", "The layer being edited is not visible. Please turn it on first."
                )
            return False

        ijk = (
            int(round(float(image_index[0]))),
            int(round(float(image_index[1]))),
            int(round(float(image_index[2]))),
        )

        if require_spacing and self._pencil_points_ijk:
            last = self._pencil_points_ijk[-1]
            import reslicer
            if axis == reslicer.AXIAL:
                dist = ((ijk[0] - last[0]) ** 2 + (ijk[1] - last[1]) ** 2) ** 0.5
            elif axis == reslicer.CORONAL:
                dist = ((ijk[0] - last[0]) ** 2 + (ijk[2] - last[2]) ** 2) ** 0.5
            else:  # SAGITTAL
                dist = ((ijk[1] - last[1]) ** 2 + (ijk[2] - last[2]) ** 2) ** 0.5
            if dist < self._pencil_min_drag_spacing_px:
                return False

        self._pencil_points_ijk.append(ijk)
        self._pencil_points_world.append(
            (float(world_point[0]), float(world_point[1]), float(world_point[2]))
        )
        self._pencil_cursor_world = None
        self._refresh_pencil_overlay()
        return True

    def on_pencil_left_button_press(self, obj, event):
        if not self.pencil_active:
            return

        v2d = self._find_viewer_from_interactor(obj)
        if not v2d:
            return

        if hasattr(self.vtk_viewer, "activate_viewer"):
            self.vtk_viewer.activate_viewer(obj)

        event_data = v2d.get_mouse_event_coordiantes()
        if "image_index" not in event_data or "world_point" not in event_data:
            return

        self._pencil_left_button_down = True
        added = self._try_add_pencil_point(
            v2d, event_data["image_index"], event_data["world_point"], require_spacing=False
        )
        if added:
            self.print_status(f"Pencil: point {len(self._pencil_points_ijk)}")

    def on_pencil_left_button_release(self, obj, event):
        if not self.pencil_active:
            return
        self._pencil_left_button_down = False

    def on_pencil_mouse_move(self, obj, event):
        if not self.pencil_active:
            return

        v2d = self._find_viewer_from_interactor(obj)
        if not v2d:
            return

        # Hold-and-drag: append polyline samples while LMB is down.
        if self._pencil_left_button_down:
            event_data = v2d.get_mouse_event_coordiantes()
            if "image_index" not in event_data or "world_point" not in event_data:
                return
            added = self._try_add_pencil_point(
                v2d,
                event_data["image_index"],
                event_data["world_point"],
                require_spacing=True,
            )
            if added:
                self.print_status(f"Pencil: point {len(self._pencil_points_ijk)}")
            return

        # Rubber-band preview from last point to cursor when not dragging.
        if self._pencil_viewer is None or not self._pencil_points_world:
            return
        if v2d is not self._pencil_viewer:
            return

        event_data = v2d.get_mouse_event_coordiantes()
        if "world_point" not in event_data:
            return

        world_point = event_data["world_point"]
        self._pencil_cursor_world = (
            float(world_point[0]), float(world_point[1]), float(world_point[2])
        )
        self._refresh_pencil_overlay()

    def on_pencil_right_button_press(self, obj, event):
        if not self.pencil_active:
            return

        v2d = self._find_viewer_from_interactor(obj)
        if not v2d:
            return

        # Closing with fewer than 3 points cancels the current polyline.
        if len(self._pencil_points_ijk) < 3:
            self._reset_pencil_drawing()
            self.print_status("Pencil: drawing cancelled")
            return

        if self._pencil_viewer is not None and v2d is not self._pencil_viewer:
            self.print_status("Pencil: right-click on the same view to close")
            return

        self._close_and_fill_pencil_polygon(v2d)

    def _close_and_fill_pencil_polygon(self, v2d):
        layer = self.get_pencil_target_layer()
        if layer is None:
            self._reset_pencil_drawing()
            return
        if not layer.get_visible():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                None, "Warning", "The layer being edited is not visible. Please turn it on first."
            )
            self._reset_pencil_drawing()
            return

        value = 0 if self.pencil_erase_active else 1
        self._fill_polygon_on_slice(
            layer.get_image(),
            self._pencil_points_ijk,
            self._pencil_axis,
            value,
        )

        layer.get_image().Modified()
        self._modified = True
        self.layer_image_modified.emit(layer, self)
        v2d.render()

        n = len(self._pencil_points_ijk)
        self._reset_pencil_drawing()
        mode = "erased" if value == 0 else "filled"
        self.print_status(f"Pencil: {mode} polygon ({n} points)")

    def _fill_polygon_on_slice(self, segmentation, points_ijk, axis, value):
        """Fill the polygon on the slice plane defined by axis using OpenCV."""
        import cv2
        import numpy as np
        import reslicer
        from vtk.util import numpy_support

        if len(points_ijk) < 3:
            return

        dims = segmentation.GetDimensions()
        extent = segmentation.GetExtent()
        scalars = segmentation.GetPointData().GetScalars()
        arr = numpy_support.vtk_to_numpy(scalars)
        # VTK layout matches paintbrush indexing: z, y, x
        vol = arr.reshape((dims[2], dims[1], dims[0]))

        if axis == reslicer.AXIAL:
            z = int(round(points_ijk[0][2]))
            zi = z - extent[4]
            if not (0 <= zi < dims[2]):
                return
            pts = np.array(
                [[[int(round(p[0] - extent[0])), int(round(p[1] - extent[2]))] for p in points_ijk]],
                dtype=np.int32,
            )
            mask = np.zeros((dims[1], dims[0]), dtype=np.uint8)
            cv2.fillPoly(mask, pts, 1)
            vol[zi][mask > 0] = value

        elif axis == reslicer.CORONAL:
            y = int(round(points_ijk[0][1]))
            yi = y - extent[2]
            if not (0 <= yi < dims[1]):
                return
            pts = np.array(
                [[[int(round(p[0] - extent[0])), int(round(p[2] - extent[4]))] for p in points_ijk]],
                dtype=np.int32,
            )
            mask = np.zeros((dims[2], dims[0]), dtype=np.uint8)
            cv2.fillPoly(mask, pts, 1)
            slice2d = vol[:, yi, :]
            slice2d[mask > 0] = value

        elif axis == reslicer.SAGITTAL:
            x = int(round(points_ijk[0][0]))
            xi = x - extent[0]
            if not (0 <= xi < dims[0]):
                return
            pts = np.array(
                [[[int(round(p[1] - extent[2])), int(round(p[2] - extent[4]))] for p in points_ijk]],
                dtype=np.int32,
            )
            mask = np.zeros((dims[2], dims[1]), dtype=np.uint8)
            cv2.fillPoly(mask, pts, 1)
            slice2d = vol[:, :, xi]
            slice2d[mask > 0] = value
        else:
            raise ValueError(f"Invalid axis: {axis}")

        scalars.Modified()


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

    def add_layer_widget_item(self, layer_data):

        # Create a custom widget for the layer
        layer_item_widget = SegmentationListItemWidget(layer_data)
        layer_item = QListWidgetItem(self.list_widget)
        
        # add references for resizing / manager callbacks
        layer_item_widget.list_widget_item = layer_item
        layer_item_widget.list_widget = self.list_widget
        layer_item_widget.manager = self
        
        layer_item.setSizeHint(layer_item_widget.sizeHint())
        self.list_widget.addItem(layer_item)
        self.list_widget.setItemWidget(layer_item, layer_item_widget) # This replaces the default text-based display with the custom widget that includes the checkbox and label.

        # set the added as active (do I need to indicate this in the list widget?)
        #self.set_active_layer_by_name(layer_name)
    
    def generate_unique_layer_name(self, base_name="Layer"):
        index = 1
        while self.segmentation_layers.get_layer_by_name(f"{base_name} {index}"):
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

    def add_layer(self, segmentation, layer_name, color_vtk=None, alpha=0.5):

        if color_vtk is None:
            color_vtk = to_vtk_color(color_rotator1.next())

        layer = SegmentationLayer(segmentation=segmentation, color=from_vtk_color(color_vtk), alpha=alpha, name=layer_name)

        self.segmentation_layers.add_layer(layer)

        self._modified = True # flag manager has been modified (something to be saved)


    def add_layer_clicked(self):

        # Generate a random bright color for the new layer
        layer_color = color_rotator1.next()

        # add layer data        
        layer_name = self.generate_unique_layer_name()
        
        # empty segmentation
        segmentation = self.create_empty_segmentation_image()

        self.add_layer(
            segmentation=segmentation, 
            layer_name=layer_name, 
            color_vtk=[layer_color[0]/255, layer_color[1]/255, layer_color[2]/255],
            alpha=0.5)
        
        self.print_status(f'A layer added: {layer_name}')

    def select_the_last_item_on_the_list(self):
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def segmentation_layer_added(self, layer, segmentation_layers):
        
        # add widget for the added layer        
        self.add_layer_widget_item(layer)

        # Select the last item in the list widget (to activate it)
        self.select_the_last_item_on_the_list()
        self._refresh_paint_target_layers()
        if getattr(self, "scribble_tool_dialog", None) is not None:
            self._refresh_scribble_target_layers()
        if getattr(self, "interpolation_tool_dialog", None) is not None:
            self._refresh_interpolation_target_layers()

    def segmentation_layer_removed(self, layer, segmentation_layers):
        
        # Remove from the list widget
        layer_name = layer.get_name()
        item, _ = self.find_list_widget_item_by_text(layer_name)
        if item is not None:
            self.list_widget.takeItem(self.list_widget.row(item))
        else:
            logger.error(f'Internal error! List item of {layer_name} is not found!')

        # Select the last item in the list widget (to activate it)
        if layer is self._active_layer:
                self.select_the_last_item_on_the_list()

        if self._paint_target_layer_name == layer_name:
            self._paint_target_layer_name = None
        self._refresh_paint_target_layers()

        self._modified = True


    # def remove_segmentation_by_name(self, layer_name):
        
    #     layer = self.segmentation_layers.get_layer_by_name(layer_name)
    #     if layer:

    #         self.segmentation_layers.remove_layer_by_name(layer_name)

    #         # Remove from the list widget
    #         item, _ = self.find_list_widget_item_by_text(layer_name)
    #         if item is not None:
    #             self.list_widget.takeItem(self.list_widget.row(item))
    #         else:
    #             logger.error(f'Internal error! List item of {layer_name} is not found!')



    #         self.vtk_viewer.render()

    #         # emit
            
    #     else:
    #         logger.error(f'Remove layer failed. the name {layer_name} given is not in the segmentation layer list')

    
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

            if item_widget.layer.get_name() == text:
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

        self.print_status(f"Selected layers removed.")

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
    
    def create_empty_segmentation_image(self):
        """Create an empty segmentation as vtkImageData with the same geometry as the base image."""
        base_image = self.get_base_image() 
        if base_image is None:
            raise ValueError("Base image data is not loaded. Cannot create segmentation.")

        import vtk_tools
        segmentation = vtk_tools.create_uchar_image_based_on_image(base_image, 0)
        return segmentation  

    # def create_segmentation_actor(self, segmentation, color=(1, 0, 0), alpha=0.5):
    #     """Create a VTK actor for a segmentation layer."""
    #     # Create a lookup table for coloring the segmentation
    #     lookup_table = vtk.vtkLookupTable()
    #     lookup_table.SetNumberOfTableValues(2)  # For 0 (background) and 1 (segmentation)
    #     lookup_table.SetTableRange(0, 1)       # Scalar range
    #     lookup_table.SetTableValue(0, 0, 0, 0, 0)  # Background: Transparent
    #     lookup_table.SetTableValue(1, color[0], color[1], color[2], alpha)  # Segmentation: Red with 50% opacity
    #     lookup_table.Build()
        
    #     mapper = vtk.vtkImageMapToColors()
    #     mapper.SetInputData(segmentation)
    #     mapper.SetLookupTable(lookup_table)
    #     mapper.Update()

    #     actor = vtk.vtkImageActor()
    #     actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
              
    #     return actor
