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

from logger import logger, _info, _err

import viewer3d

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

class MainWindow3D(QMainWindow):
    


    def __init__(self):
        super().__init__()

        # exclusive QActions
        self.exclusive_actions = []
        self.managers = []
        self.vtk_image = None

        ### init ui ###    
        self.setWindowTitle("Image Labeler 3D")
        self.setGeometry(100, 100, 1024, 786)

        self.main_widget = QWidget()
        self.layout = QVBoxLayout()

        # VTK Viewer
        self.vtk_viewer = viewer3d.VTKViewer3D(parent = self, main_window = self)
        self.vtk_viewer.status_message.connect(self.on_status_message_from_viewer)
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
        self.segmentation_list_manager.layer_added.connect(self.on_segmentation_layer_added) 
        self.segmentation_list_manager.layer_removed.connect(self.on_segmentation_layer_removed) 
        self.segmentation_list_manager.active_layer_changed.connect(self.on_active_segmentation_layer_changed) 

        self.managers.append(self.segmentation_list_manager)
        self.segmentation_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.segmentation_list_manager, True)

        self.vtk_viewer.set_segmentation_layers(self.segmentation_list_manager.segmentation_layers)

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
        self.add_manager_visibility_toggle_menu(self.nnunet_client_manager, False)

        #self.tabifyDockWidget(self.nnunet_client_manager, self.rect_list_dock_widget)

        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")  # Initial message

        _info("MainWindow initialized")

        # Load a sample DICOM file
        #dicom_file = "./data/jaw_cal.dcm"
        #self.load_dicom(dicom_file)

    def on_segmentation_layer_added(self, layer_name, sender):
        self.vtk_viewer.on_segmentation_layer_added(layer_name, sender)

    def on_segmentation_layer_removed(self, layer_name, sender):
        self.vtk_viewer.on_segmentation_layer_removed(layer_name, sender)

    def on_active_segmentation_layer_changed(self, new_layer_name, old_layer_name, sender):
        self.vtk_viewer.on_active_segmentation_layer_changed(new_layer_name, old_layer_name, sender)

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
        _info("MainWindow is closing.")

        self.vtk_viewer.cleanup_vtk(event)  # explicitly clean VTK resources

        super().closeEvent(event)  # Call the base class method to ensure proper behavior

       

        

    def handle_log_message(self, log_type, message):
        """
        Handle log messages emitted by SegmentationListManager.
        """
        if log_type == "INFO":
            self.status_bar.showMessage(message)
            _info(message)  # Log the message
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

    def on_status_message_from_viewer(self, msg, sender):
        self.status_bar.showMessage(msg)

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
        zoom_in_action.triggered.connect(self.vtk_viewer.zoom_in)
        view_menu.addAction(zoom_in_action)

        # Zoom Out
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zoom_out)
        view_menu.addAction(zoom_out_action)

        # Zoom Reset
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zoom_reset)
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
        zoom_in_action.triggered.connect(self.vtk_viewer.zoom_in)
        toolbar.addAction(zoom_in_action)    
        
         # zoom out action
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zoom_out)
        toolbar.addAction(zoom_out_action)    

        # zoom reset button
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zoom_reset)
        toolbar.addAction(zoom_reset_action)        

        # zoom toggle button
        zoom_action = QAction("Zoom", self)
        zoom_action.setCheckable(True)
        zoom_action.toggled.connect(self.zoom_clicked)
        toolbar.addAction(zoom_action)        

        # pan toggle button
        pan_action = QAction("Pan", self)
        pan_action.setCheckable(True)
        pan_action.toggled.connect(self.pan_clicked)
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

    def zoom_clicked(self, checked):
        self.vtk_viewer.enable_zooming(checked)

    def pan_clicked(self, checked):
        self.vtk_viewer.enable_panning(checked)


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

            self.vtk_viewer.set_window_level(window, level)

            self.print_status(f"Window: {window}, Level: {level}")

    def get_last_dir(self):
        if settings.contains('last_directory'):
            return settings.value('last_directory')
        else:
            return '.'

    def import_image_clicked(self):
        #file_path, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", self.get_last_dir(), "Medical Image Files (*.mhd *.mha);;MetaImage Files (*.mhd *.mha);;All Files (*)")
        
        file_path = 'C:/Users/jkim20/Documents/projects/vtk_image_labeler_3d/sample_data/Dataset101_Eye[ul]L/imagesTr/eye[ul]l_0_0000.mha'
        if file_path == '':
            return 
        
        # save to last_directory
        settings.setValue("last_directory", os.path.dirname(file_path))

    
        _info(f"Loading image from {file_path}")
        self.image_path = file_path 

        _,file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()

        _info(f"File extension: {file_extension}")  # Output: .mha    

        image_type = ""
        from itkvtk import load_vtk_image_using_sitk
        if file_extension == ".mhd" or file_extension == ".mha":
            self.vtk_image = load_vtk_image_using_sitk(file_path)
            image_type = "meta"
        else:
            raise Exception("Only meta image formats are supported at the moment.")

        self.image_type = image_type

        # align the center of the image to the center of the world coordiante system
        # Get image properties
        dims = self.vtk_image.GetDimensions()
        spacing = self.vtk_image.GetSpacing()
        original_origin = self.vtk_image.GetOrigin()

        #for debug
        self.vtk_image.SetOrigin([0.0, 0.0, 0.0])

        _info(f'dims={dims}')
        _info(f'spacing={spacing}')
        _info(f'original_origin={original_origin}')

        # Get the scalar range (pixel intensity range)
        scalar_range = self.vtk_image.GetScalarRange()

        self.range_slider.range_min = scalar_range[0]
        self.range_slider.range_max = scalar_range[1]
        self.range_slider.low_value = scalar_range[0]
        self.range_slider.high_value = scalar_range[1]
        self.range_slider.update()  
        
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())

        self.setWindowTitle(f"Image Labeler 3D - {os.path.basename(file_path)}")
        
        _info("Image loaded successfully")
        #except Exception as e:
        #    _err(f"Failed to load image:{e}") 
        #    self.show_popup("Load Image", f"Error: Load Image Failed, {str(e)}", QMessageBox.Critical)


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
            _info("Save workspace operation canceled by user.")
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
            _info(f"Saved input image to {input_image_path}")
            
            _info('Saving manager states')
            for manager in self.managers:
                _info(f'{manager} - Saving state')
                manager.save_state(workspace_data, data_dir)

            # Save metadata as 'workspace.json'
            with open(workspace_json_path, "w") as f:
                json.dump(workspace_data, f, indent=4)
            
            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()
            
            _info(f"Workspace metadata saved to {workspace_json_path}.")
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
        workspace_json_path, _ = QFileDialog.getOpenFileName(self, "Select Workspace File", self.get_last_dir(), "JSON Files (*.json)")
        if not workspace_json_path:
           _info("Load workspace operation canceled by user.")
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

            _info(f"Loaded workspace metadata from {workspace_json_path}.")

            # Clear existing workspace
            self.vtk_image = None
            #self.point_list_manager.points.clear()

            from itkvtk import load_vtk_image_using_sitk

            # Load input image
            input_image_path = os.path.join(data_path, "input_image.mhd")
            if os.path.exists(input_image_path):
                self.vtk_image = load_vtk_image_using_sitk(input_image_path)
                _info(f"Loaded input image from {input_image_path}.")
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

            _info('loading manager states')
            for manager in self.managers:
                _info(f'{manager} - Loading state')
                manager.load_state(workspace_data, data_path, {'base_image': self.vtk_image})

            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()

            self.print_status(f"Workspace loaded from {data_path}.")
            _info("Loaded workspace successfully.")

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
    
    _info("Application started")

    app = QApplication(sys.argv)
    
    app.setWindowIcon(QIcon(brush_icon_path))  # Set application icon

    app.aboutToQuit.connect(lambda: _info("Application is quitting."))

    main_window = MainWindow3D()
    #main_window.show()
    main_window.showMaximized()
    sys.exit(app.exec_())
