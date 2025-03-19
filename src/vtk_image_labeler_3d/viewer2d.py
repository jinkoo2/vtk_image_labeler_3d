import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSlider, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, 
    QFileDialog, QVBoxLayout, QSlider, QPushButton, QLabel, QWidget, QMenuBar, QAction, QToolBar, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit
)
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QListWidgetItem, QColorDialog
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon

from logger import logger


class Panning:
    def __init__(self, viewer=None):
        self.viewer = viewer
        self.interactor = viewer.interactor
        self.left_button_is_pressed = False
        self.last_mouse_position = None
        self.enabled = False

    def enable(self, enabled=True):
        self.enabled = enabled

        if enabled:
            self.left_button_press_observer = self.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
            self.mouse_move_observer = self.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)
            self.left_button_release_observer = self.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        else:    
            self.interactor.RemoveObserver(self.left_button_press_observer)
            self.interactor.RemoveObserver(self.mouse_move_observer)
            self.interactor.RemoveObserver(self.left_button_release_observer)   
            self.last_mouse_position = None

        if enabled:
            self.viewer.setCursor(Qt.OpenHandCursor)  # Change cursor for panning mode
        else:
            self.viewer.setCursor(Qt.ArrowCursor)  # Reset cursor
        
        print(f"Panning mode: {'enabled' if enabled else 'disabled'}")
    
    def on_left_button_press(self, obj, event):
        if not self.enabled:
            return
        
        self.left_button_is_pressed = True
        self.last_mouse_position = self.interactor.GetEventPosition()

    def on_mouse_move(self, obj, event):
        if not self.enabled:
            return

        if self.left_button_is_pressed:
            self.perform_panning()

        self.viewer.render_window.Render()

    def on_left_button_release(self, obj, event):
        if not self.enabled:
            return
        
        self.left_button_is_pressed = False
        self.last_mouse_position = None

    def perform_panning(self):
        """Perform panning based on mouse movement, keeping the pointer fixed on the same point in the image."""
        current_mouse_position = self.interactor.GetEventPosition()

        if self.last_mouse_position:
            
            renderer = self.viewer.get_renderer()
            
            # Get the camera and renderer
            camera = renderer.GetActiveCamera()

            # Convert mouse positions to world coordinates
            picker = vtk.vtkWorldPointPicker()

            # Pick world coordinates for the last mouse position
            picker.Pick(self.last_mouse_position[0], self.last_mouse_position[1], 0, renderer)
            last_world_position = picker.GetPickPosition()

            # Pick world coordinates for the current mouse position
            picker.Pick(current_mouse_position[0], current_mouse_position[1], 0, renderer)
            current_world_position = picker.GetPickPosition()

            # Compute the delta in world coordinates
            delta_world = [
                last_world_position[0] - current_world_position[0],
                last_world_position[1] - current_world_position[1],
                last_world_position[2] - current_world_position[2],
            ]

            # Update the camera position and focal point
            camera.SetFocalPoint(
                camera.GetFocalPoint()[0] + delta_world[0],
                camera.GetFocalPoint()[1] + delta_world[1],
                camera.GetFocalPoint()[2] + delta_world[2],
            )
            camera.SetPosition(
                camera.GetPosition()[0] + delta_world[0],
                camera.GetPosition()[1] + delta_world[1],
                camera.GetPosition()[2] + delta_world[2],
            )

            # Render the updated scene
            self.viewer.render_window.Render()

        # Update the last mouse position
        self.last_mouse_position = current_mouse_position
        
from PyQt5.QtCore import pyqtSignal, QObject

class Zooming(QObject):

    zoomChanged = pyqtSignal(str, QObject)

    def __init__(self, viewer=None):
        super().__init__()

        self.viewer = viewer
        self.interactor = viewer.interactor
        self.enabled = False
        self.zoom_in_factor = 1.2
        self.zoom_out_factor = 0.8

    def enable(self, enabled=True):
        self.enabled = enabled

        if enabled:
            self.mouse_wheel_forward_observer = self.interactor.AddObserver("MouseWheelForwardEvent", self.on_mouse_wheel_forward)
            self.on_mouse_wheel_backward_observer = self.interactor.AddObserver("MouseWheelBackwardEvent", self.on_mouse_wheel_backward)
        else:    
            self.interactor.RemoveObserver(self.mouse_wheel_forward_observer)
            self.interactor.RemoveObserver(self.on_mouse_wheel_backward_observer)   

        print(f"Zooming mode: {'enabled' if enabled else 'disabled'}")
    
    def on_mouse_wheel_forward(self, obj, event):
        if not self.enabled:
            return

        self.zoom_in()        

        self.viewer.render_window.Render()

    def on_mouse_wheel_backward(self, obj, event):
        if not self.enabled:
            return

        self.zoom_out()

        self.viewer.render_window.Render()

    def zoom(self, type, emit_event=True):
        camera = self.viewer.get_renderer().GetActiveCamera()
        if type == 'in':
            camera.Zoom(self.zoom_in_factor)  
        elif type == 'out':
            camera.Zoom(self.zoom_out_factor)  
        elif type == 'reset':
            if camera.GetParallelProjection():
                # Reset parallel projection scale
                self.viewer.get_renderer().ResetCamera()
            else:
                # Reset perspective projection parameters
                camera.SetPosition(0.0, 0.0, 1000.0)
                camera.SetFocalPoint(0.0, 0.0, 0.0)
                camera.SetViewUp(0.0, 1.0, 0.0)
                self.viewer.get_renderer().ResetCameraClippingRange()
        else:
            raise Exception(f'Unknown zoom type {type}!')

        if emit_event:
            self.zoomChanged.emit(type, self)

        self.viewer.get_render_window().Render()

    def zoom_in(self, emit_event=True):
        self.zoom('in', emit_event)

    def zoom_out(self, emit_event=True):
        self.zoom('out', emit_event)

    def zoom_reset(self, emit_event=True):
        self.zoom('reset', emit_event)

class LineWidget:
    def __init__(self, vtk_image, pt1_w, pt2_w, line_color_vtk=[1,0,0], line_width=2, renderer=None):
        # Create a ruler using vtkLineWidget2
        widget = vtk.vtkLineWidget2()
        representation = vtk.vtkLineRepresentation()
        widget.SetRepresentation(representation)

        # Set initial position of the ruler
        representation.SetPoint1WorldPosition(pt1_w)
        representation.SetPoint2WorldPosition(pt2_w)
        representation.GetLineProperty().SetColor(line_color_vtk[0],line_color_vtk[1],line_color_vtk[2])  
        representation.GetLineProperty().SetLineWidth(line_width)
        representation.SetVisibility(True)

        representation.text_actor = vtk.vtkTextActor()
        representation.text_actor.GetTextProperty().SetFontSize(12)
        representation.text_actor.GetTextProperty().SetColor(1, 1, 1)  # White color
        
        renderer.AddActor2D(representation.text_actor)

        interactor = renderer.GetRenderWindow().GetInteractor()

        # Set interactor and enable interaction
        if interactor:
            widget.SetInteractor(interactor)

        self.widget = widget
        self.representation = representation
        self.interactor = interactor
        self.renderer = renderer
        self.color_vtk = line_color_vtk
        self.line_width = line_width
        self.vtk_image = vtk_image

        # Attach a callback to update distance when the ruler is moved
        widget.AddObserver("InteractionEvent", lambda obj, event: self.update_ruler_distance())

        # Attach the camera observer
        self.renderer.GetActiveCamera().AddObserver("ModifiedEvent", lambda obj, event: self.update_ruler_distance())

        # Attach the window resize observer
        self.renderer.GetRenderWindow().AddObserver("WindowResizeEvent", lambda obj, event: self.update_ruler_distance())

        self.update_ruler_distance()
    
    def world_to_display(self, renderer, world_coordinates):
        """Convert world coordinates to display coordinates."""
        display_coordinates = [0.0, 0.0, 0.0]
        renderer.SetWorldPoint(*world_coordinates, 1.0)
        renderer.WorldToDisplay()
        display_coordinates = renderer.GetDisplayPoint()
        return display_coordinates

    def update_ruler_distance(self):

        representation = self.representation

        # Calculate the distance
        point1 = representation.GetPoint1WorldPosition()
        point2 = representation.GetPoint2WorldPosition()
        distance = ((point2[0] - point1[0]) ** 2 +
                    (point2[1] - point1[1]) ** 2 +
                    (point2[2] - point1[2]) ** 2) ** 0.5

        print(f"Ruler Distance: {distance:.2f} mm")

        # Update the text actor position 
        midpoint_w = [(point1[i] + point2[i]) / 2 for i in range(3)]
        midpoint_screen = self.world_to_display(self.renderer, midpoint_w)
        representation.text_actor.SetInput(f"{distance:.2f} mm")
        representation.text_actor.SetPosition(midpoint_screen[0], midpoint_screen[1])       

background_color = (0.5, 0.5, 0.5)
background_color_active = (0.6, 0.6, 0.6)

class VTKViewer2D(QWidget):
    zoom_changed = pyqtSignal(str, QObject)

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
    
        self.main_window = main_window

        # Create a VTK Renderer
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetLayer(0)
        self.renderer.SetBackground(*background_color)  # Set background to gray
        self.renderer.GetActiveCamera().SetParallelProjection(True)
        self.renderer.SetInteractive(True)

        # Create a VTK Renderer for the brush actor
        #self.brush_renderer = vtk.vtkRenderer()
        #self.brush_renderer.SetLayer(1)  # Higher layer index
        #self.brush_renderer.SetBackground(*background_color)  # Transparent background

        # Create a QVTKRenderWindowInteractor
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.render_window = self.vtk_widget.GetRenderWindow()  # Retrieve the render window
        #self.render_window.SetNumberOfLayers(2)
        self.render_window.AddRenderer(self.renderer)
        #self.render_window.AddRenderer(self.brush_renderer)

        # Set up interactor style
        self.interactor = self.render_window.GetInteractor()
        self.interactor_style = vtk.vtkInteractorStyleUser()
        self.interactor.SetInteractorStyle(self.interactor_style)

        # Layout for embedding the VTK widget
        layout = QVBoxLayout()
        layout.addWidget(self.vtk_widget)
        self.setLayout(layout)

        # Connect mouse events
        self.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
        self.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        self.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)

        self.rulers = []
        self.vtk_image = None

        self.zooming = Zooming(viewer=self)
        self.zooming.zoomChanged.connect(self.on_zoom_changed_event)

        self.panning = Panning(viewer=self)  

        self.set_active(False)

    def set_active(self, active=True):
        self.active = active
        if active:
            self.renderer.SetBackground(*background_color_active)  # Set background to gray
        else:
            self.renderer.SetBackground(*background_color)  # Set background to gray
        self.render()

    def on_zoom_changed_event(self, zoom_type, sender):
        self.zoom_changed.emit(zoom_type, self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'render_window') and self.render_window is not None:
            self.render_window.SetSize(self.width(), self.height())
            self.render_window.Render()

    def cleanup_vtk(self, event):
        if hasattr(self, 'interactor') and self.interactor is not None:
            self.interactor.Disable()
            self.interactor.TerminateApp()
            del self.interactor

        if hasattr(self, 'render_window') and self.render_window is not None:
            self.render_window.Finalize()
            del self.render_window


    def clear(self):
        # Remove the previous image actor if it exists
        if hasattr(self, 'image_actor') and self.image_actor is not None:
            self.get_renderer().RemoveActor(self.image_actor)
            self.image_actor = None

        self.vtk_image = None

        self.render()

    def print_status(self, msg):
        if self.main_window is not None:
            self.main_window.print_status(msg)

    def get_vtk_image(self):
        return self.vtk_image
    
    def set_vtk_image(self, vtk_image, window, level):

        # reset first
        self.clear()

        self.vtk_image = vtk_image
                
        # Connect reader to window/level filter
        self.window_level_filter = vtk.vtkImageMapToWindowLevelColors()
        #self.window_level_filter.SetOutputFormatToRGB()
        self.window_level_filter.SetInputData(vtk_image)
        self.window_level_filter.SetWindow(window)
        self.window_level_filter.SetLevel(level)
        self.window_level_filter.Update()

        self.image_actor = vtk.vtkImageActor()
        self.image_actor.GetMapper().SetInputConnection(self.window_level_filter.GetOutputPort())

        self.get_renderer().AddActor(self.image_actor)
        
        self.get_renderer().ResetCamera()

        self.get_render_window().Render()

    def set_window_level(self, window, level):
        if self.window_level_filter:
            self.window_level_filter.SetWindow(window)
            self.window_level_filter.SetLevel(level)
            self.window_level_filter.Update()
            self.get_render_window().Render()

    def get_renderer(self):
        return self.renderer
    
    def get_render_window(self):
        return self.render_window
    
    def get_camera_info(self):
        """Retrieve the camera's position and direction in the world coordinate system."""
        camera = self.renderer.GetActiveCamera()

        # Get the camera origin (position in world coordinates)
        camera_position = camera.GetPosition()

        # Get the focal point (the point the camera is looking at in world coordinates)
        focal_point = camera.GetFocalPoint()

        # Compute the view direction (vector from camera position to focal point)
        view_direction = [
            focal_point[0] - camera_position[0],
            focal_point[1] - camera_position[1],
            focal_point[2] - camera_position[2],
        ]

        # Normalize the view direction
        magnitude = (view_direction[0] ** 2 + view_direction[1] ** 2 + view_direction[2] ** 2) ** 0.5
        view_direction = [component / magnitude for component in view_direction]

        print(f"Camera Position (Origin): {camera_position}")
        print(f"Focal Point: {focal_point}")
        print(f"View Direction: {view_direction}")

        return camera_position, focal_point, view_direction


    def print_camera_viewport_info(self):
        """Print the viewport and camera information."""
        # Get the renderer and camera
        renderer = self.renderer
        camera = renderer.GetActiveCamera()

        # Viewport settings
        viewport = renderer.GetViewport()
        print(f"Viewport: {viewport}")  # Returns (xmin, ymin, xmax, ymax)

        # Camera position and orientation
        position = camera.GetPosition()
        focal_point = camera.GetFocalPoint()
        view_up = camera.GetViewUp()

        print(f"Camera Position: {position}")
        print(f"Focal Point: {focal_point}")
        print(f"View Up Vector: {view_up}")

        # Parallel scale (if in parallel projection mode)
        if camera.GetParallelProjection():
            parallel_scale = camera.GetParallelScale()
            print(f"Parallel Scale: {parallel_scale}")

        # Clipping range (near and far clipping planes)
        clipping_range = camera.GetClippingRange()
        print(f"Clipping Range: {clipping_range}")

    def add_ruler(self):
        """Add a ruler to the center of the current view and enable interaction."""
        camera = self.get_renderer().GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        view_extent = camera.GetParallelScale()  # Approximate size of the visible area

        # Calculate ruler start and end points
        start_point = [focal_point[0] - view_extent / 6, focal_point[1], focal_point[2]+0.1]
        end_point = [focal_point[0] + view_extent / 6, focal_point[1], focal_point[2]+0.1]

        # Create a ruler using vtkLineWidget2
        line_widget = LineWidget(
            vtk_image=self.vtk_image,
            pt1_w=start_point, 
            pt2_w=end_point, 
            line_color_vtk=[1,0,0], 
            line_width=2, 
            renderer=self.get_renderer())
        
        line_widget.widget.On()

        # Add the ruler to the list for management
        self.rulers.append(line_widget)

        self.get_render_window().Render()

    def on_left_button_press(self, obj, event):
        self.left_button_is_pressed = True

    def on_mouse_move(self, obj, event):
        self.print_mouse_coordiantes()
        self.render_window.Render()

    def print_mouse_coordiantes(self):
        """Update brush position and print mouse position details when inside the image."""
        mouse_pos = self.interactor.GetEventPosition()

        # Use a picker to get world coordinates
        picker = vtk.vtkWorldPointPicker()
        picker.Pick(mouse_pos[0], mouse_pos[1], 0, self.get_renderer())

        # Get world position
        world_pos = picker.GetPickPosition()

        # Check if the world position is valid
        if not picker.GetPickPosition():
            print("Mouse is outside the render area.")
            return

        # Get the image data
        vtk_image = self.vtk_image
        if not vtk_image:
            #print("No image loaded.")
            return

        # Get image properties
        dims = vtk_image.GetDimensions()
        spacing = vtk_image.GetSpacing()
        origin = vtk_image.GetOrigin()

        # Convert world coordinates to image index
        image_index = [
            int((world_pos[0] - origin[0]) / spacing[0] + 0.5),
            int((world_pos[1] - origin[1]) / spacing[1] + 0.5),
            int((world_pos[2] - origin[2]) / spacing[2] + 0.5)
        ]

        # Check if the index is within bounds
        if not (0 <= image_index[0] < dims[0] and 0 <= image_index[1] < dims[1] and 0 <= image_index[2] < dims[2]):
            # Print details
            self.print_status(f"Point - World: ({world_pos[0]:.2f}, {world_pos[1]:.2f}))")
            return

        # Get the pixel value
        scalars = vtk_image.GetPointData().GetScalars()
        flat_index = image_index[2] * dims[0] * dims[1] + image_index[1] * dims[0] + image_index[0]
        pixel_value = scalars.GetTuple1(flat_index)

        # Print details
        self.print_status(f"Point - World: ({world_pos[0]:.2f}, {world_pos[1]:.2f}) Index: ({image_index[0]}, {image_index[1]}), Value: {pixel_value} )")
        
        

    def on_left_button_release(self, obj, event):
        self.left_button_is_pressed = False

    def center_image(self):
        
        dims = self.vtk_image.GetDimensions()
        spacing = self.vtk_image.GetSpacing()
        original_origin = self.vtk_image.GetOrigin()

        # Calculate the center of the image in world coordinates
        center = [
            original_origin[0] + (dims[0] * spacing[0]) / 2.0,
            original_origin[1] + (dims[1] * spacing[1]) / 2.0,
            original_origin[2] + (dims[2] * spacing[2]) / 2.0,
        ]

        # Shift the origin to center the image in the world coordinate system
        new_origin = [
            original_origin[0] - center[0],
            original_origin[1] - center[1],
            0.0,
        ]
        self.vtk_image.SetOrigin(new_origin)
        
        print('new_origin: ', new_origin)

        self.image_original_origin = original_origin


    def print_properties(self):
        """Print the properties of the camera, image, and line widgets."""
        # Camera properties
        camera = self.renderer.GetActiveCamera()
        print("Camera Properties:")
        print(f"  Position: {camera.GetPosition()}")
        print(f"  Focal Point: {camera.GetFocalPoint()}")
        print(f"  View Up: {camera.GetViewUp()}")
        print(f"  Clipping Range: {camera.GetClippingRange()}")
        print(f"  Parallel Scale: {camera.GetParallelScale()}")
        print()

        # Image properties
        if self.vtk_image:
            dims = self.vtk_image.GetDimensions()
            spacing = self.vtk_image.GetSpacing()
            origin = self.vtk_image.GetOrigin()
            print("Image Properties:")
            print(f"  Dimensions: {dims}")
            print(f"  Spacing: {spacing}")
            print(f"  Origin: {origin}")
            print()

        # Line widget properties
        if self.rulers:
            print("Line Widget Properties:")
            for idx, line_widget in enumerate(self.rulers, start=1):
                representation = line_widget.GetRepresentation()
                point1 = representation.GetPoint1WorldPosition()
                point2 = representation.GetPoint2WorldPosition()
                print(f"  Line Widget {idx}:")
                print(f"    Point 1: {point1}")
                print(f"    Point 2: {point2}")
                print()
        else:
            print("No Line Widgets Present.")

    def reset_camera_parameters(self):
        """Align the camera viewport center to the center of the loaded image."""
        if self.vtk_image is None:
            print("No image data loaded.")
            return

        # Get the image center
        dims = self.vtk_image.GetDimensions()
        spacing = self.vtk_image.GetSpacing()
        origin = self.vtk_image.GetOrigin()

        # Calculate the center of the image in world coordinates
        image_center = [
            origin[0] + (dims[0] * spacing[0]) / 2.0,
            origin[1] + (dims[1] * spacing[1]) / 2.0,
            origin[2] + (dims[2] * spacing[2]) / 2.0,
        ]

        # Set the camera parameters
        camera = self.renderer.GetActiveCamera()

        # Position the camera at the center of the image, slightly offset in Z
        camera.SetPosition(image_center[0], image_center[1], image_center[2] + 100)  # Adjust Z for visibility

        # Set the focal point to the center of the image
        camera.SetFocalPoint(image_center)

        # Set the view-up vector
        camera.SetViewUp(0.0, -1.0, 0.0)  # Y-axis up in world coordinates

        # Adjust the parallel scale to fit the image height
        camera.SetParallelScale((dims[1] * spacing[1]) / 2.0)

        # Reset the clipping range for visibility
        camera.SetClippingRange(1, 1000)

        print(f"Camera aligned to image center: {image_center}")
        print(f"Camera Position: {camera.GetPosition()}")
        print(f"Camera Focal Point: {camera.GetFocalPoint()}")
        print(f"Camera View Up: {camera.GetViewUp()}")

        # Render the changes
        self.render_window.Render()
            
    def toggle_base_image(self, visible):
        """Toggle the visibility of the base image."""
        self.base_image_visible = visible
        self.image_actor.SetVisibility(self.base_image_visible)
        self.render_window.Render()

    def toggle_panning_mode(self, checked):
        """Enable or disable panning mode."""
        self.panning.enable(checked)

    def toggle_zooming_mode(self, checked):
        """Enable or disable panning mode."""
        self.zooming.enable(checked)
  
    def toggle_paintbrush(self, enabled):
        """Enable or disable the paintbrush tool."""
        self.painting_enabled = enabled
        self.brush_actor.SetVisibility(enabled)  # Show brush if enabled
        self.render_window.Render()

    def zoom(self, type, emit_event=True):
        if not self.vtk_image:
            return 
        
        self.zooming.zoom(type, emit_event)

    def render(self):
        self.get_render_window().Render()


from PyQt5.QtWidgets import QWidget, QVBoxLayout
import os

# Construct paths to the icons
current_dir = os.path.dirname(__file__)
brush_icon_path = os.path.join(current_dir, "icons", "brush.png")
eraser_icon_path = os.path.join(current_dir, "icons", "eraser.png")
reset_zoom_icon_path = os.path.join(current_dir, "icons", "reset_zoom.png")


def is_dicom(file_path):
    import pydicom 

    """Check if the file is a valid DICOM file using pydicom."""
    try:
        # Attempt to read the file as a DICOM
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        # If no exception occurs, it's a valid DICOM
        return True
    except pydicom.errors.InvalidDicomError:
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

from PyQt5.QtWidgets import QMessageBox

from PyQt5.QtCore import QSettings
settings = QSettings("_settings.conf", QSettings.IniFormat)


from vtk_segmentation_list_manager import SegmentationListManager
from vtk_point_list_manager import PointListManager
from vtk_line_list_manager import LineListManager
from vtk_rect_list_manager import RectListManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # exclusive QActions
        self.exclusive_actions = []
        self.managers = []
        self.vtk_image = None

        ### init ui ###    
        self.setWindowTitle("Image Labeler 2D")
        self.setGeometry(100, 100, 1024, 786)

        self.main_widget = QWidget()
        self.layout = QVBoxLayout()

        # VTK Viewer
        self.vtk_viewer = VTKViewer2D(parent = self, main_window = self)
        self.layout.addWidget(self.vtk_viewer)

        self.main_widget.setLayout(self.layout)
        self.setCentralWidget(self.main_widget)

        # Add the menus and toolbars
        self.create_menu()
        self.create_file_toolbar()
        self.create_view_toolbar()

        ##########################
        # Segmentation List Manager
        self.segmentation_list_manager = SegmentationListManager(self.vtk_viewer, "Segmentations")
        toolbar, dock = self.segmentation_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.add_exclusive_actions(self.segmentation_list_manager.get_exclusive_actions()) 
        self.segmentation_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.segmentation_list_manager)
        self.segmentation_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.segmentation_list_manager, True)
        

        ##########################
        # Point List Manager
        self.point_list_manager = PointListManager(self.vtk_viewer, "Points")
        toolbar, dock = self.point_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.point_list_manager.get_exclusive_actions())
        self.point_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.point_list_manager)
        self.point_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.point_list_manager, True)

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.point_list_dock_widget)

        ##########################
        # Line List Manager
        self.line_list_manager = LineListManager(self.vtk_viewer, "Lines")
        toolbar, dock = self.line_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.line_list_manager.get_exclusive_actions())
        self.line_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.line_list_manager)
        self.line_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.line_list_manager, True)

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.line_list_dock_widget)

        ##########################
        # Rect List Manager
        self.rect_list_manager = RectListManager(self.vtk_viewer, "Rects")
        toolbar, dock = self.rect_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.rect_list_manager.get_exclusive_actions())
        self.rect_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.rect_list_manager)
        self.rect_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.rect_list_manager, True)

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.rect_list_dock_widget)

        ##########################
        # nnUNet client manager
        from nnunet_client_manager import nnUNetDatasetManager
        self.nnunet_client_manager = nnUNetDatasetManager(self.segmentation_list_manager, "nnUNet Dashboard")
        toolbar, dock = self.nnunet_client_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        self.add_exclusive_actions(self.nnunet_client_manager.get_exclusive_actions())
        self.nnunet_client_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.nnunet_client_manager)
        self.nnunet_client_manager_widget = dock
        self.add_manager_visibility_toggle_menu(self.nnunet_client_manager, True)

        #self.tabifyDockWidget(self.nnunet_client_manager, self.rect_list_dock_widget)

        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")  # Initial message

        logger.info("MainWindow initialized")

        # Load a sample DICOM file
        #dicom_file = "./data/jaw_cal.dcm"
        #self.load_dicom(dicom_file)



    def add_manager_visibility_toggle_menu(self, manager, visible):
        toggle_action = QAction(manager.name, self)
        toggle_action.setCheckable(True)
        toggle_action.setChecked(visible)
        toggle_action.triggered.connect(lambda checked, m=manager: self.toggle_dock_widget(m.dock_widget, checked))
        if visible:
            manager.dock_widget.show()
        else: 
            manager.dock_widget.hide()

        self.managers_menu.addAction(toggle_action)
        

    def closeEvent(self, event):
        """
        Override the closeEvent to log application or window close.
        """
        logger.info("MainWindow is closing.")

        

        super().closeEvent(event)  # Call the base class method to ensure proper behavior

       

        

    def handle_log_message(self, log_type, message):
        """
        Handle log messages emitted by SegmentationListManager.
        """
        if log_type == "INFO":
            self.status_bar.showMessage(message)
            logger.info(message)  # Log the message
        elif log_type == "WARNING":
            self.status_bar.showMessage(f"WARNING: {message}")
            logger.warning(message)  # Log the warning
            self.show_popup("Warning", message, QMessageBox.Warning)
        elif log_type == "ERROR":
            self.status_bar.showMessage(f"ERROR: {message}")
            logger.error(message)  # Log the error
            self.show_popup("Error", message, QMessageBox.Critical)
        else:
            logger.debug(f"{log_type}: {message}")
            self.status_bar.showMessage(f"{log_type}: {message}")

    def show_popup(self, title, message, icon=None):
        """
        Display a QMessageBox with the specified title, message, and icon.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if icon is None:
            icon = QMessageBox.Information
            
        msg_box.setIcon(icon)
        
        msg_box.exec_()

    def on_exclusiave_action_clicked(self):
        
        sender = self.sender()

        # Check if the sender is a QAction and retrieve its text
        if isinstance(sender, QAction):
            print(f"Exclusive action clicked: {sender.text()}")
        else:
            print("The sender is not a QAction.")

        # Get the QAction that triggered this signal
        sender = self.sender()

        # uncheck all other actions
        for action in self.exclusive_actions:
            if action is not sender:
                action.setChecked(False)

    def add_exclusive_actions(self, actions):
        for action in actions:
            self.exclusive_actions.append(action)
            action.triggered.connect(self.on_exclusiave_action_clicked)

    def print_status(self, msg):
        self.status_bar.showMessage(msg)

    def create_menu(self):
        # Create a menu bar
        menubar = self.menuBar()

        # Add the File menu
        file_menu = menubar.addMenu("File")
        self.create_file_menu(file_menu)

        # Add View menu
        view_menu = menubar.addMenu("View")
        self.create_view_menu(view_menu)

    def create_file_menu(self, file_menu):
        
        from PyQt5.QtWidgets import QAction
        
        # Add Open Image action
        open_image_action = QAction("Import Image", self)
        open_image_action.triggered.connect(self.import_image_clicked)
        file_menu.addAction(open_image_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.open_workspace)
        file_menu.addAction(open_workspace_action)

        # Add Save Workspace action
        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        file_menu.addAction(save_workspace_action)

        # Add Open Image action
        close_image_action = QAction("Close Workspace", self)
        close_image_action.triggered.connect(self.close_workspace)
        file_menu.addAction(close_image_action)

        # Print Object Properties Button
        print_objects_action = QAction("Print Object Properties", self)
        print_objects_action.triggered.connect(self.vtk_viewer.print_properties)
        file_menu.addAction(print_objects_action)
        
    def create_managers_menu(self, view_menu):
        self.managers_menu = view_menu.addMenu("Managers")

    def create_view_menu(self, view_menu):
        
        # Zoom In
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.vtk_viewer.zooming.zoom_in)
        view_menu.addAction(zoom_in_action)

        # Zoom Out
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zooming.zoom_out)
        view_menu.addAction(zoom_out_action)

        # Zoom Reset
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zooming.zoom_reset)
        view_menu.addAction(zoom_reset_action)
        
        self.create_managers_menu(view_menu)

        # Add Toggle Button
        toggle_image_button = QAction("Toggle Base Image", self)
        toggle_image_button.setCheckable(True)
        toggle_image_button.setChecked(True)
        toggle_image_button.triggered.connect(self.vtk_viewer.toggle_base_image)
        view_menu.addAction(toggle_image_button)


    def create_file_toolbar(self):
        # Create a toolbar
        toolbar = QToolBar("File Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add actions to the toolbar
        # Add Open DICOM action
        open_image_action = QAction("Import Image", self)
        open_image_action.triggered.connect(self.import_image_clicked)
        toolbar.addAction(open_image_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.open_workspace)
        toolbar.addAction(open_workspace_action)

        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        toolbar.addAction(save_workspace_action)

        close_image_action = QAction("Close Workspace", self)
        close_image_action.triggered.connect(self.close_workspace)
        toolbar.addAction(close_image_action)

    def create_view_toolbar(self):
        from labeled_slider import LabeledSlider
        from rangeslider import RangeSlider

        # Create a toolbar
        toolbar = QToolBar("View Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add a label for context
        toolbar.addWidget(QLabel("Window/Level:", self))

        # Replace two QSliders with a RangeSlider for window and level
        self.range_slider = RangeSlider(self)
        self.range_slider.setFixedWidth(200)  # Adjust size for the toolbar
        self.range_slider.rangeChanged.connect(self.update_window_level)
        toolbar.addWidget(self.range_slider)
        
        # zoom in action
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.vtk_viewer.zooming.zoom_in)
        toolbar.addAction(zoom_in_action)    
        
         # zoom out action
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zooming.zoom_out)
        toolbar.addAction(zoom_out_action)    

        # zoom reset button
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zooming.zoom_reset)
        toolbar.addAction(zoom_reset_action)        

        # zoom toggle button
        zoom_action = QAction("Zoom", self)
        zoom_action.setCheckable(True)
        zoom_action.toggled.connect(self.vtk_viewer.toggle_zooming_mode)
        toolbar.addAction(zoom_action)        

        # pan toggle button
        pan_action = QAction("Pan", self)
        pan_action.setCheckable(True)
        pan_action.toggled.connect(self.vtk_viewer.toggle_panning_mode)
        toolbar.addAction(pan_action)        

        # rotate plus 90 deg (x-->y)
        rot_plus_90_action = QAction("Rot +90", self)
        rot_plus_90_action.triggered.connect(self.rotate_plus_90_clicked)
        toolbar.addAction(rot_plus_90_action)        

        # rotate minus 90 deg (y-->x)
        rot_minus_90_action = QAction("Rot -90", self)
        rot_minus_90_action.triggered.connect(self.rotate_minus_90_clicked)
        toolbar.addAction(rot_minus_90_action)        

        # flip x
        flip_x_action = QAction("Flip X", self)
        flip_x_action.triggered.connect(self.flip_x_clicked)
        toolbar.addAction(flip_x_action)      

        # flip y
        flip_y_action = QAction("Flip Y", self)
        flip_y_action.triggered.connect(self.flip_y_clicked)
        toolbar.addAction(flip_y_action)      

        # pad is an exclusive
        self.add_exclusive_actions([pan_action])
        
        # Add ruler toggle action
        add_ruler_action = QAction("Add Ruler", self)
        add_ruler_action.triggered.connect(self.vtk_viewer.add_ruler)
        toolbar.addAction(add_ruler_action)

    def rotate_plus_90_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # Get image properties
        # dims = self.vtk_image.GetDimensions()
        # spacing = self.vtk_image.GetSpacing()
        # original_origin = self.vtk_image.GetOrigin()
        # direction = self.vtk_image.GetDirectionMatrix()
        # print('dims: ', dims)
        # print('spacing: ', spacing)
        # print('original_origin: ', original_origin)
        # print('direction: ', direction)

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import rot90
        sitk_image_rotated = rot90(sitk_image, plus=True)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_rotated)

       # Get image properties
        # dims = self.vtk_image.GetDimensions()
        # spacing = self.vtk_image.GetSpacing()
        # original_origin = self.vtk_image.GetOrigin()
        # direction = self.vtk_image.GetDirectionMatrix()
        # print('dims: ', dims)
        # print('spacing: ', spacing)
        # print('original_origin: ', original_origin)
        # print('direction: ', direction)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()

    def rotate_minus_90_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import rot90
        sitk_image_rotated = rot90(sitk_image, plus=False)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_rotated)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()

    def flip_x_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import flip_x
        sitk_image_flipped = flip_x(sitk_image)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_flipped)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()


    def flip_y_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import flip_y
        sitk_image_flipped = flip_y(sitk_image)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_flipped)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()



    def update_window_level(self):
        if self.vtk_image is not None:
            # Update the window and level using the RangeSlider values
            window = self.range_slider.get_width()
            level = self.range_slider.get_center()

            self.vtk_viewer.window_level_filter.SetWindow(window)
            self.vtk_viewer.window_level_filter.SetLevel(level)
            self.vtk_viewer.get_render_window().Render()

            self.print_status(f"Window: {window}, Level: {level}")

    def get_list_dir(self):
        if settings.contains('last_directory'):
            return settings.value('last_directory')
        else:
            return '.'

    def import_image_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", self.get_list_dir(), "Medical Image Files (*.dcm *.mhd *.mha);;DICOM Files (*.dcm);;MetaImage Files (*.mhd *.mha);;All Files (*)")
        
        if file_path == '':
            return 
        
        # save to last_directory
        settings.setValue("last_directory", os.path.dirname(file_path))

        try:
            logger.info(f"Loading image from {file_path}")
            self.image_path = file_path 

            _,file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()

            print(f"File extension: {file_extension}")  # Output: .mha      

            image_type = ""
            from itkvtk import load_vtk_image_using_sitk
            if file_extension == ".dcm" or is_dicom(file_path):
                # NOTE: this did not work for RTImage reading. So, using sitk to read images.
                #reader = vtk.vtkDICOMImageReader()
                self.vtk_image = load_vtk_image_using_sitk(file_path)
                image_type = "dicom"
            elif file_extension == ".mhd" or file_extension == ".mha":
                self.vtk_image = load_vtk_image_using_sitk(file_path)
                image_type = "meta"
            else:
                raise Exception("Only dicom or meta image formats are supported at the moment.")

            # Extract correct spacing for RTImage using pydicom
            if image_type == "dicom":
                
                import pydicom
                dicom_dataset = pydicom.dcmread(file_path)
                if hasattr(dicom_dataset, "Modality") and dicom_dataset.Modality == "RTIMAGE":

                    # Extract necessary tags
                    if hasattr(dicom_dataset, "ImagePlanePixelSpacing"):
                        pixel_spacing = dicom_dataset.ImagePlanePixelSpacing  # [row spacing, column spacing]
                    else:
                        raise ValueError("RTImage is missing ImagePlanePixelSpacing")

                    if hasattr(dicom_dataset, "RadiationMachineSAD"):
                        SAD = float(dicom_dataset.RadiationMachineSAD)
                    else:
                        raise ValueError("RTImage is missing RadiationMachineSAD")

                    if hasattr(dicom_dataset, "RTImageSID"):
                        SID = float(dicom_dataset.RTImageSID)
                    else:
                        raise ValueError("RTImage is missing RTImageSID")

                    # Scale pixel spacing to SAD scale
                    scaling_factor = SAD / SID
                    scaled_spacing = [spacing * scaling_factor for spacing in pixel_spacing]

                    # Update spacing in vtkImageData
                    self.vtk_image.SetSpacing(scaled_spacing[1], scaled_spacing[0], 1.0)  # Column, Row, Depth

                    # Print the updated spacing
                    print(f"Updated Spacing: {self.vtk_image.GetSpacing()}")
            
            self.image_type = image_type

            # align the center of the image to the center of the world coordiante system
            # Get image properties
            dims = self.vtk_image.GetDimensions()
            spacing = self.vtk_image.GetSpacing()
            original_origin = self.vtk_image.GetOrigin()

            print('dims: ', dims)
            print('spacing: ', spacing)
            print('original_origin: ', original_origin)

            # Get the scalar range (pixel intensity range)
            scalar_range = self.vtk_image.GetScalarRange()

            self.range_slider.range_min = scalar_range[0]
            self.range_slider.range_max = scalar_range[1]
            self.range_slider.low_value = scalar_range[0]
            self.range_slider.high_value = scalar_range[1]
            self.range_slider.update()  
            
            self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())


            self.setWindowTitle(f"Image Labeler 2D - {os.path.basename(file_path)}")
            
            logger.info("Image loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load image:{e}") 
            self.show_popup("Load Image", f"Error: Load Image Failed, {str(e)}", QMessageBox.Critical)


    def modified(self):
        for manager in self.managers:
            if manager.modified():
                return True
        return False
    
    def show_yes_no_question_dialog(self, title, msg):
        # Create a message box
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)  # Set the icon to a question mark
        msg_box.setWindowTitle(title)  # Set the title of the dialog
        msg_box.setText(msg)  # Set the main message
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)  # Add Yes and No buttons
        
        # Set the default button to Yes
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        # Show the dialog and get the user's response
        response = msg_box.exec_()
        
        if response == QMessageBox.Yes:
            return True
        elif response == QMessageBox.No:
            return False
            
    def close_workspace(self):

        if self.vtk_image is None:
            self.show_popup("Close Image", "No image has been loaded.")
            return 

        if self.modified():
            yes = self.show_yes_no_question_dialog("Save Workspace", "There are modified objects. Do you want to save the workspace?")

            if yes:
                self.save_workspace()
        
        for manager in self.managers:
            manager.clear()

        self.vtk_viewer.clear()

     

        self.image_path = None
        self.vtk_image = None
        self.image_type = None



    def save_workspace(self):
        import json
        import os
        from PyQt5.QtWidgets import QFileDialog

        """Save the current workspace to a folder."""
        if self.vtk_image is None:
            self.print_status("No image loaded. Cannot save workspace.")
            return

        # workspace json file
        workspace_json_path, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "Json (*.json)")
        if not workspace_json_path:
            logger.info("Save workspace operation canceled by user.")
            return 
        
        # save to last_directory
        settings.setValue("last_directory", os.path.dirname(workspace_json_path))

        try:
            # data folder for the workspace
            data_dir = workspace_json_path+".data"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.debug(f"Created data directory: {data_dir}")

            # Create a metadata dictionary
            workspace_data = {
                "window_settings": {
                    "level": self.range_slider.get_center(),
                    "width": self.range_slider.get_width(),
                    "range_min" : self.range_slider.range_min,
                    "range_max" : self.range_slider.range_max
                }
            }

            # Save input image as '.mha'
            from itkvtk import save_vtk_image_using_sitk
            input_image_path = os.path.join(data_dir, "input_image.mhd")
            save_vtk_image_using_sitk(self.vtk_image, input_image_path)
            logger.info(f"Saved input image to {input_image_path}")
            
            logger.info('Saving manager states')
            for manager in self.managers:
                logger.info(f'{manager} - Saving state')
                manager.save_state(workspace_data, data_dir)

            # Save metadata as 'workspace.json'
            with open(workspace_json_path, "w") as f:
                json.dump(workspace_data, f, indent=4)
            
            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()
            
            logger.info(f"Workspace metadata saved to {workspace_json_path}.")
            self.print_status(f"Workspace saved to {workspace_json_path}.")
            self.show_popup("Save Workspace", "Workspace saved successfully.", QMessageBox.Information)
        except Exception as e:
            logger.error(f"Failed to save workspace: {e}", exc_info=True)
            self.print_status("Failed to save workspace. Check logs for details.")
            self.show_popup("Save Workspace", f"Error saving workspace: {str(e)}", QMessageBox.Critical)      

    def open_workspace(self):
        import json
        import os

        """Load a workspace from a folder."""
        workspace_json_path, _ = QFileDialog.getOpenFileName(self, "Select Workspace File", self.get_list_dir(), "JSON Files (*.json)")
        if not workspace_json_path:
           logger.info("Load workspace operation canceled by user.")
           return

        # save to last dir
        settings.setValue('last_directory', os.path.dirname(workspace_json_path))

        data_path = workspace_json_path+".data"
        if not os.path.exists(data_path):
            msg = "Workspace data folder not found."
            logger.error(msg)
            self.print_status(msg)
            return

        try:
            with open(workspace_json_path, "r") as f:
                workspace_data = json.load(f)

            logger.info(f"Loaded workspace metadata from {workspace_json_path}.")

            # Clear existing workspace
            self.vtk_image = None
            #self.point_list_manager.points.clear()

            from itkvtk import load_vtk_image_using_sitk

            # Load input image
            input_image_path = os.path.join(data_path, "input_image.mhd")
            if os.path.exists(input_image_path):
                self.vtk_image = load_vtk_image_using_sitk(input_image_path)
                logger.info(f"Loaded input image from {input_image_path}.")
            else:
                raise FileNotFoundError(f"Input image file not found at {input_image_path}")

            # Restore window settings
            window_settings = workspace_data.get("window_settings", {})
            window = window_settings.get("width", 1)
            level = window_settings.get("level", 0)

            # Get the scalar range (pixel intensity range)
            scalar_range = self.vtk_image.GetScalarRange()

            self.range_slider.range_min = scalar_range[0]
            self.range_slider.range_max = scalar_range[1]
            self.range_slider.low_value = level-window/2
            self.range_slider.high_value = level+window/2
            self.range_slider.update()  

            self.vtk_viewer.set_vtk_image(self.vtk_image, window, level)

            logger.info('loading manager states')
            for manager in self.managers:
                logger.info(f'{manager} - Loading state')
                manager.load_state(workspace_data, data_path, {'base_image': self.vtk_image})

            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()

            self.print_status(f"Workspace loaded from {data_path}.")
            logger.info("Loaded workspace successfully.")

        except Exception as e:
            logger.error(f"Failed to load workspace: {e}", exc_info=True)
            self.print_status("Failed to load workspace. Check logs for details.")
  
    def toggle_dock_widget(self, dock_widget, checked):
        # Toggle the visibility of the dock widget based on the checked state
        if checked:
            dock_widget.show()
        else:
            dock_widget.hide()

        


if __name__ == "__main__":
    import sys
    
    logger.info("Application started")

    app = QApplication(sys.argv)
    
    app.setWindowIcon(QIcon(brush_icon_path))  # Set application icon

    app.aboutToQuit.connect(lambda: logger.info("Application is quitting."))

    main_window = MainWindow()
    #main_window.show()
    main_window.showMaximized()
    sys.exit(app.exec_())
