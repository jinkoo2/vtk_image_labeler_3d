import json
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QLabel, QWidget, 
                             QDockWidget, QHBoxLayout, QLineEdit, QComboBox, 
                             QTextEdit, QSizePolicy, QDialog)

from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QTextEdit, QHBoxLayout, QDialog, QMessageBox

from PyQt5.QtCore import Qt, pyqtSignal, QObject

from logger import logger
from color_rotator import ColorRotator
import nnunet_service 
import requests

from config import get_config
conf = get_config()



def extract_image_number(filename):
    import re
    match = re.match(r'^.*?_(\d+)_\d+\.(nii\.gz|mha|mhd)$', filename)
    if match:
        return int(match.group(1))
    raise ValueError(f"Could not extract number from filename: {filename}")

class NewDatasetDialog(QDialog):
    """Popup window for creating a new dataset."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Dataset")
        self.setGeometry(300, 200, 500, 400)  # Set window size

        # Layout
        layout = QVBoxLayout()

        # Edit box with default JSON
        self.text_edit = QTextEdit()
        self.text_edit.setText(self.get_default_json())  # Load default JSON
        layout.addWidget(self.text_edit)

        # Button layout
        button_layout = QHBoxLayout()

        # Create Button
        self.create_button = QPushButton("Create")
        self.create_button.clicked.connect(self.create_dataset)
        button_layout.addWidget(self.create_button)

        # Cancel Button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)  # Close window
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_default_json(self):
        """Returns a default JSON structure as a formatted string."""
        default_data = {
            "name": "NewName",
            "description": "New description",
            "reference": "Your institution",
            "licence": "CC-BY-SA 4.0",
            "tensorImageSize": "3D",
            "labels": {
                "background": 0,
                "label1": 1
            },
            "channel_names": {
                "0": "CT"
            }
        }
        return json.dumps(default_data, indent=4)  # Return formatted JSON

    def show_error_popup(self, message):
        """Display an error message popup."""
        QMessageBox.critical(self, "Error", message, QMessageBox.Ok)

    def create_dataset(self):
        """Handles the 'Create' button click with validation checks."""
        try:
            dataset_data = json.loads(self.text_edit.toPlainText())  # Parse JSON

            # **Validation 1: Check if all required fields exist**
            required_fields = ["name", "description", "reference", "licence", "tensorImageSize", "labels", "channel_names"]
            for field in required_fields:
                if field not in dataset_data:
                    self.show_error_popup(f"⚠ Error: Missing required field '{field}'.")
                    return

            # **Validation 2: Check if "name" is alphanumeric without spaces**
            if not dataset_data["name"].isalnum():
                self.show_error_popup("⚠ Error: 'name' must be alphanumeric and contain no spaces.")
                return

            # **Validation 3: Check if "tensorImageSize" is either "2D" or "3D"**
            if dataset_data["tensorImageSize"] not in ["2D", "3D"]:
                self.show_error_popup("⚠ Error: 'tensorImageSize' must be either '2D' or '3D'.")
                return

            # **Validation 4: Ensure "labels" contains "background" with value 0**
            if "background" not in dataset_data["labels"] or dataset_data["labels"]["background"] != 0:
                self.show_error_popup("⚠ Error: 'labels' must include a 'background' key with value 0.")
                return

            # If all validations pass, store the dataset and close the window
            self.new_dataset = dataset_data  # Store the new dataset
            self.accept()  # Close window after successful creation

        except json.JSONDecodeError:
            self.show_error_popup("⚠ Error: Invalid JSON format! Please fix it.")  # Show error

class nnUNetDatasetManager(QObject):
    """Main application class for dataset management."""

    log_message = pyqtSignal(str, str)  # For emitting log messages
    image_dataset_downloaded = pyqtSignal(str, str, QObject) # 

    def __init__(self, segmentation_list_manager, name):
        super().__init__()
        self.name = name
        self.segmentation_list_manager = segmentation_list_manager
        self.color_rotator = ColorRotator()
        self.datasets = []  # Ensure datasets list is initialized

    def setup_ui(self):
        """Set up the UI with a dockable widget."""
        dock = QDockWidget(self.name)
        widget = QWidget()
        layout = QVBoxLayout()

        # connection layout
        layout.addLayout(self._create_connection_layout())

        # dataset layout
        layout.addLayout(self._create_dataset_layout())

        # Button layout
        layout.addLayout(self._create_command_button_layout())

        widget.setLayout(layout)
        dock.setWidget(widget)

        self.dock_widget = dock
        return None, dock

    def _create_connection_layout(self):
        layout = QHBoxLayout()

        self.server_url_input = QLineEdit()
        self.server_url_input.setText(conf['nnunet_server_url'])
        self.server_url_input.setPlaceholderText("Server URL here")
        layout.addWidget(self.server_url_input)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_server_clicked)  # You need to define this method
        layout.addWidget(self.connect_button)

        # Ping button
        self.ping_button = QPushButton("Ping")
        self.ping_button.clicked.connect(self.ping_clicked)
        layout.addWidget(self.ping_button)
    
        return layout 

    def _create_dataset_layout(self):
        layout = QVBoxLayout()

        # Label
        self.label = QLabel("Select a Dataset:")
        layout.addWidget(self.label)

        # Dropdown (ComboBox)
        self.dataset_dropdown = QComboBox()
        self.dataset_dropdown.currentIndexChanged.connect(self.dataset_selected)
        layout.addWidget(self.dataset_dropdown)

        # Dataset details text area (Expands to fill space)
        self.details_label = QTextEdit("Dataset details will appear here.")
        self.details_label.setReadOnly(True)  # Make it read-only
        self.details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # Allow copy-paste
        self.details_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Make it expand
        layout.addWidget(self.details_label)

        # Train  Image lists
        import nnunet_image_dataset_listwidget
        listwidget = nnunet_image_dataset_listwidget.nnUnetImageDataSetListWidget('train')
        listwidget.image_dataset_downloaded.connect(self.handle_image_dataset_downloaded)
        listwidget.post_dataset_clicked.connect(self.handle_image_dataset_listwidget_post_dataset_clicked)
        listwidget.update_dataset_clicked.connect(self.handle_image_dataset_listwidget_update_dataset_clicked)
        listwidget.delete_dataset_clicked.connect(self.handle_image_dataset_listwidget_delete_dataset_clicked)
        listwidget.setMinimumWidth(200)
        listwidget.setToolTip("Training Images")
        layout.addWidget(listwidget)
        self.train_image_list_widget = listwidget
       
        # Test  Image lists
        listwidget = nnunet_image_dataset_listwidget.nnUnetImageDataSetListWidget('test')
        listwidget.image_dataset_downloaded.connect(self.handle_image_dataset_downloaded)
        listwidget.post_dataset_clicked.connect(self.handle_image_dataset_listwidget_post_dataset_clicked)
        listwidget.update_dataset_clicked.connect(self.handle_image_dataset_listwidget_update_dataset_clicked)
        listwidget.delete_dataset_clicked.connect(self.handle_image_dataset_listwidget_delete_dataset_clicked)
        listwidget.setMinimumWidth(200)
        listwidget.setToolTip("Test Images")
        layout.addWidget(listwidget)
        self.test_image_list_widget = listwidget
        return layout
    
    def _create_command_button_layout(self):
        # Button layout
        import flowlayout
        layout = flowlayout.FlowLayout()

        # New Dataset button
        self.new_dataset_button = QPushButton("New Dataset")
        self.new_dataset_button.clicked.connect(self.open_new_dataset_dialog)
        layout.addWidget(self.new_dataset_button)

        return layout
    ""
    def get_exclusive_actions(self):
        """Returns an empty list since there are no exclusive actions."""
        return []
    
    def ping_clicked(self):
        """Ping the nnUNet server to check connectivity."""
        try:
            response_data = nnunet_service.get_ping(self.get_server_url())
            print(f"response_data={response_data}")
            self.log_message.emit("INFO", response_data.get("msg", "No message received"))
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")

    def open_new_dataset_dialog(self):
        """Opens the New Dataset Dialog."""
        dialog = NewDatasetDialog()
        if dialog.exec_():  # If the user clicks "Create"
            new_dataset = dialog.new_dataset
            if new_dataset:

                # add fiel_ending
                new_dataset["file_ending"] =".mha"

                try:
                    response_data = nnunet_service.post_dataset_json(self.get_server_url(), new_dataset)

                    # dataset from the server
                    new_dataset = response_data["dataset"]

                    self.datasets.append(new_dataset)  # Add new dataset to list
                    self.dataset_dropdown.addItem(new_dataset["id"])  # Add to dropdown
                    self.dataset_dropdown.setCurrentIndex(len(self.datasets) - 1)  # Select new dataset
                    self.dataset_selected(len(self.datasets) - 1)  # Show details

                    print(f"response_data={response_data}")
                    self.log_message.emit("INFO", response_data.get("message", "No message received"))
                except nnunet_service.ServerError as e:
                    print(f"Server error: {e}")
                    self.log_message.emit("ERROR", f"Server error: {e}")
                except requests.exceptions.RequestException as e:
                    print(f"Request failed: {e}")
                    self.log_message.emit("ERROR", f"Request failed: {e}")
    
    def get_selected_dataset_id(self):
        selected_text = self.dataset_dropdown.currentText()
        return selected_text

    def get_seletect_train_image_name(self):
        selected_item = self.train_image_list_widget.currentItem()
        if not selected_item:
            return None
        return selected_item.text()

    def get_seletect_test_image_name(self):
        selected_item = self.test_image_list_widget.currentItem()
        if not selected_item:
            return None
        return selected_item.text()

    def pull_seleted_image_dataset(self, images_for='train'):
        pass

    # def on_train_listwidget_item_double_clicked(self,item):
    #     self.pull_seleted_image_dataset('train')
              
    # def on_test_listwidget_item_double_clicked(self,item):
    #     self.pull_seleted_image_dataset('test')

    def handle_image_dataset_downloaded(self, image_path, labels_path, list_widget):
        self.image_dataset_downloaded.emit(image_path, labels_path, self)  

    def handle_image_dataset_listwidget_post_dataset_clicked(self, dataset_id, images_for, sender):
        self.post_image_and_labels(images_for)

    def handle_image_dataset_listwidget_update_dataset_clicked(self, dataset_id, images_for, num, sender):
        self.update_image_and_labels(images_for, num)

    def handle_image_dataset_listwidget_delete_dataset_clicked(self, dataset_id, images_for, num, sender):
        self.delete_image_and_labels(images_for, num)


    def post_image_and_labels(self, images_for):
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text is "" or selected_index is -1:
            self.log_message.emit("INFO", "Please select a dataset to add images to")
            return 

        dataset = self.datasets[selected_index]

        """posting the images and labels"""
        try:
            if "id" in dataset:
                dataset_id = dataset["id"]
            else:
                dataset_id = selected_text

            image_path, labels_path = self.save_image_and_combined_label_to_temp_folder(dataset)

            dataset_updated = nnunet_service.post_image_and_labels(self.get_server_url(), dataset_id, images_for, image_path, labels_path)
            print(f"response_data={dataset_updated}")
            self.log_message.emit("INFO",f"dateset_updated={dataset_updated}")

            # update the data & the view
            self.datasets[selected_index] = dataset_updated
            self.dataset_selected(selected_index)  
        
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")

    def save_image_and_combined_label_to_temp_folder(self, dataset):
         # get vtk image and label list
        vtk_image = self.segmentation_list_manager.get_base_vtk_image()
        vtk_label_image_list = []
        label_list = []
        for name, pixel_value in dataset['labels'].items():
            #skip background
            if pixel_value == 0:
                continue

            layer = self.segmentation_list_manager.get_segmentation_layer_list().get_layer_by_name(name)
            if layer:
                vtk_label = layer.get_image()
                vtk_label_image_list.append(vtk_label)
                label_list.append(pixel_value)
            else:
                print(f'Warning segmentation layer not found for name={name}')

        # combine the labels 
        from itkvtk import vtk_to_sitk
        sitk_label_list = [vtk_to_sitk(vtk_label) for vtk_label in vtk_label_image_list]
        from itk_tools import combine_sitk_labels, save_sitk_image
        sitk_labels = combine_sitk_labels(sitk_label_list, label_list)

        # save the files to a temporary folders
        temp_dir = conf['temp_dir']
        import time
        sec = int(time.time())  # Current time in seconds
        import os
        image_path = os.path.join(temp_dir, f'image_{sec}.mha')
        labels_path = os.path.join(temp_dir, f'labels_{sec}.mha')

        print(f'saving image to {image_path}')
        #save_as_2d_if_single_slice_3d_image=False, in nnunet everything is 3d. so, no need to save as 2d
        save_sitk_image(vtk_to_sitk(vtk_image), image_path, save_as_2d_if_single_slice_3d_image=False)
        
        print(f'saving labels to {labels_path}')
        #save_as_2d_if_single_slice_3d_image=False, in nnunet everything is 3d. so, no need to save as 2d
        save_sitk_image(sitk_labels, labels_path, save_as_2d_if_single_slice_3d_image=False)

        return image_path, labels_path

    def update_image_and_labels(self, images_for, num):
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text is "" or selected_index is -1:
            self.log_message.emit("INFO", "Please select a dataset to add images to")
            return 

        dataset = self.datasets[selected_index]

        """updating the images and labels"""
        try:
            if "id" in dataset:
                dataset_id = dataset["id"]
            else:
                dataset_id = selected_text

            image_path, labels_path = self.save_image_and_combined_label_to_temp_folder(dataset)

            dataset_updated = nnunet_service.update_image_and_labels(self.get_server_url(), dataset_id, images_for, num, image_path, labels_path)
            print(f"response_data={dataset_updated}")
            self.log_message.emit("INFO",f"dateset_updated={dataset_updated}")
       
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")


    def delete_image_and_labels(self, images_for, num):
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset to add images to")
            return 

        dataset = self.datasets[selected_index]

        """deleting the images and labels"""
        try:
            if "id" in dataset:
                dataset_id = dataset["id"]
            else:
                dataset_id = selected_text

            delete_info = nnunet_service.delete_image_and_labels(self.get_server_url(), dataset_id, images_for, num)
            print(f"response_data={delete_info}")
            self.log_message.emit("INFO",f"dateset_updated={delete_info}")
       
            dataset_updated = delete_info['dataset_json']

            # update the data & the view
            self.datasets[selected_index] = dataset_updated
            self.dataset_selected(selected_index)  

        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")

    def get_server_url(self):
        """Retrieve the current server URL from the input field."""
        return self.server_url_input.text()

    def connect_to_server_clicked(self):
        """Fetch datasets and populate dropdown list."""
        self.dataset_dropdown.clear()  # Clear existing items
        
        try:
            self.datasets = nnunet_service.get_dataset_json_list(self.get_server_url(), 5)
    
            if not self.datasets:
                self.dataset_dropdown.addItem("No datasets available")
                self.details_label.setText("<b>Error:</b> No datasets could be loaded.")
                return

            dataset_ids = [dataset['id'] for dataset in self.datasets]
            self.dataset_dropdown.addItems(dataset_ids)

            # Set first dataset as default and show its details
            if dataset_ids:
                self.dataset_dropdown.setCurrentIndex(0)
                self.dataset_selected(0)

        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return []  # Return an empty list in case of failure


    def get_dataset_image_list(self, dataset_id):
        """Fetch dataset list from nnUNet server."""
        try:
            response_data = nnunet_service.get_dataset_json_list(self.get_server_url(), dataset_id)
            print(f"response_data={response_data}")
            return response_data
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return []  # Return an empty list in case of failure
    
    def get_selected_dataset(self):
        return self._current_datast
    
    
    def dataset_selected(self, index):
        """Triggered when the user selects a dataset."""
        if not self.datasets or index < 0 or index >= len(self.datasets):
            self.details_label.setText("<b>Error:</b> No dataset selected.")
            return

        # Make a copy of the dataset and remove 'id'
        dataset = self.datasets[index].copy()
        #dataset.pop("id", None)  # Remove 'id' if it exists
        self._current_datast = dataset


        # Convert dataset dictionary to formatted JSON string
        details_json = json.dumps(dataset, indent=4)

        # Set formatted JSON text with monospace font
        details_text = f"<pre>{details_json}</pre>"

        self.details_label.setHtml(details_text)  # Use HTML to render formatted JSON
       
        try:
            dataset_id = dataset.get('id')
            if not dataset_id:
                print("Missing dataset ID")
                return

            response_data = nnunet_service.get_dataset_image_name_list(self.get_server_url(), dataset_id)
            print(f"response_data={response_data}")

            # --- Populate training image list ---
            self.train_image_list_widget.set_dataset(dataset_id, response_data['train_images'])

            # --- Populate testing image list ---
            self.test_image_list_widget.set_dataset(dataset_id, response_data['test_images'])

        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return []  # Return an empty list in case of failure

    def load_state(self, data_dict, data_dir, aux_data):
        pass

    def save_state(self,data_dict, data_dir):
        pass

    def reset_modified(self):
        pass

    def clear(self):
        pass 

    def modified(self):
        return False
