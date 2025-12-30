import json
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QLabel, QWidget, 
                             QDockWidget, QHBoxLayout, QLineEdit, QComboBox, 
                             QTextEdit, QSizePolicy, QDialog, QListWidget, QListWidgetItem)

from PyQt5.QtWidgets import QTabWidget
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

class FileContentDialog(QDialog):
    """Popup window for displaying file content."""
    
    def __init__(self, file_name, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"File Content: {file_name}")
        self.setGeometry(300, 200, 800, 600)  # Set window size
        
        # Layout
        layout = QVBoxLayout()
        
        # File name label
        name_label = QLabel(f"File: {file_name}")
        name_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(name_label)
        
        # Content text area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFontFamily("Courier")
        
        # Format content based on type
        if isinstance(content, (dict, list)):
            # JSON content - prettify it
            formatted_content = json.dumps(content, indent=4)
        elif isinstance(content, str):
            formatted_content = content
        else:
            formatted_content = str(content)
        
        self.text_edit.setPlainText(formatted_content)
        layout.addWidget(self.text_edit)
        
        # Close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

class CollapsibleGroupBox(QWidget):
    """A collapsible widget with a title bar that can expand/collapse its content."""
    
    # Class-level list to track all instances for accordion behavior
    _all_instances = []
    
    def __init__(self, title="", parent=None, start_expanded=False):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Add this instance to the list
        CollapsibleGroupBox._all_instances.append(self)
        
        # Toggle button (acts as title bar)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(start_expanded)  # Use parameter instead of always True
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                border: 1px solid #ccc;
                padding: 5px;
                background-color: #f0f0f0;
            }
            QPushButton::checked {
                background-color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_widget.setLayout(self.content_layout)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_widget)
        self.setLayout(main_layout)
        
        # Set initial visibility based on start_expanded
        self.content_widget.setVisible(start_expanded)
        
        # Update button text with arrow indicator
        self._update_button_text()
    
    def toggle(self, checked):
        """Toggle the visibility of the content widget. If expanding, collapse others."""
        if checked:
            # Collapse all other instances
            for instance in CollapsibleGroupBox._all_instances:
                if instance != self and instance.toggle_button.isChecked():
                    instance.toggle_button.setChecked(False)
                    instance.content_widget.setVisible(False)
                    instance._update_button_text()
        
        self.content_widget.setVisible(checked)
        self._update_button_text()
    
    def _update_button_text(self):
        """Update the button text with arrow indicator."""
        arrow = "▼" if self.toggle_button.isChecked() else "▶"
        title = self.toggle_button.text().replace("▼", "").replace("▶", "").strip()
        self.toggle_button.setText(f"{arrow} {title}")
    
    def setTitle(self, title):
        """Set the title of the collapsible panel."""
        arrow = "▼" if self.toggle_button.isChecked() else "▶"
        self.toggle_button.setText(f"{arrow} {title}")
    
    def addWidget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)

from base_object import BaseObject
class nnUNetDatasetManager(BaseObject):
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

        self.main_widget = widget

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
        self.dataset_dropdown.currentIndexChanged.connect(self._on_dataset_selected)
        layout.addWidget(self.dataset_dropdown)

        # Main tab widget to replace all CollapsibleGroupBoxes
        main_tab_widget = QTabWidget()
        
        # === Dataset Tab ===
        dataset_tab_widget = QWidget()
        dataset_tab_layout = QVBoxLayout()
        dataset_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Inner Tab Widget for Train/Test (moved from Raw tab)
        inner_tab_widget = QTabWidget()
        
        # Dataset details text area
        self.details_label = QTextEdit("Dataset details will appear here.")
        self.details_label.setReadOnly(True)  # Make it read-only
        self.details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # Allow copy-paste
        self.details_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Make it expand
        dataset_tab_layout.addWidget(self.details_label)

        # Train Image lists
        import nnunet_image_dataset_listwidget
        train_image_list_widget = nnunet_image_dataset_listwidget.nnUnetImageDataSetListWidget('train')
        train_image_list_widget.image_dataset_downloaded.connect(self.handle_image_dataset_downloaded)
        train_image_list_widget.post_dataset_clicked.connect(self.handle_image_dataset_listwidget_post_dataset_clicked)
        train_image_list_widget.update_dataset_clicked.connect(self.handle_image_dataset_listwidget_update_dataset_clicked)
        train_image_list_widget.delete_dataset_clicked.connect(self.handle_image_dataset_listwidget_delete_dataset_clicked)
        train_image_list_widget.setMinimumWidth(200)
        train_image_list_widget.setToolTip("Training Images")
        inner_tab_widget.addTab(train_image_list_widget, "Train")
        self.train_image_list_widget = train_image_list_widget
       
        # Test Image lists
        test_image_list_widget = nnunet_image_dataset_listwidget.nnUnetImageDataSetListWidget('test')
        test_image_list_widget.image_dataset_downloaded.connect(self.handle_image_dataset_downloaded)
        test_image_list_widget.post_dataset_clicked.connect(self.handle_image_dataset_listwidget_post_dataset_clicked)
        test_image_list_widget.update_dataset_clicked.connect(self.handle_image_dataset_listwidget_update_dataset_clicked)
        test_image_list_widget.delete_dataset_clicked.connect(self.handle_image_dataset_listwidget_delete_dataset_clicked)
        test_image_list_widget.setMinimumWidth(200)
        test_image_list_widget.setToolTip("Test Images")
        inner_tab_widget.addTab(test_image_list_widget, "Test")
        self.test_image_list_widget = test_image_list_widget
        
        dataset_tab_layout.addWidget(inner_tab_widget)
        
       
        dataset_tab_widget.setLayout(dataset_tab_layout)
        main_tab_widget.addTab(dataset_tab_widget, "Dataset")
        

        # === Plan and Preprocess Tab ===
        # Store job_id for status checking
        self.plan_preprocess_job_id = None
        
        preprocessed_tab_widget = QWidget()
        preprocessed_tab_layout = QVBoxLayout()
        preprocessed_tab_layout.setContentsMargins(0, 0, 0, 0)
        
         # Button to run plan and preprocess
        self.plan_preprocess_button = QPushButton("Run Plan and Preprocess")
        self.plan_preprocess_button.clicked.connect(self.run_plan_and_preprocess_clicked)
        preprocessed_tab_layout.addWidget(self.plan_preprocess_button)
        
        # Status text area with scrollbar for long JSON results
        self.worker_status_label = QTextEdit("Worker Status: Not started")
        self.worker_status_label.setReadOnly(True)
        self.worker_status_label.setMaximumHeight(200)  # Limit height to show scrollbar
        preprocessed_tab_layout.addWidget(self.worker_status_label)
        
        # Refresh status button
        self.worker_status_refresh_button = QPushButton("Refresh Worker Status")
        self.worker_status_refresh_button.clicked.connect(self.refresh_plan_and_preprocess_status)
        self.worker_status_refresh_button.setEnabled(False)  # Disabled until job is started
        preprocessed_tab_layout.addWidget(self.worker_status_refresh_button)

        # Status label for preprocessed summary
        self.data_status_label = QLabel("Status: Not loaded")
        self.data_status_label.setWordWrap(True)
        self.data_status_label.setStyleSheet("padding: 5px; border: 1px solid #ccc; background-color: #f9f9f9;")
        preprocessed_tab_layout.addWidget(self.data_status_label)
        
        # Preprocessed files list widget
        self.preprocessed_files_list = QListWidget()
        self.preprocessed_files_list.setMinimumHeight(150)
        self.preprocessed_files_list.itemDoubleClicked.connect(self.on_preprocessed_file_double_clicked)
        preprocessed_tab_layout.addWidget(self.preprocessed_files_list)
        
        # Refresh button for preprocessed files
        self.data_status_refresh_button = QPushButton("Refresh Data Status")
        self.data_status_refresh_button.clicked.connect(self.refresh_preprocessed_files_list)
        preprocessed_tab_layout.addWidget(self.data_status_refresh_button)
        
        preprocessed_tab_widget.setLayout(preprocessed_tab_layout)
        main_tab_widget.addTab(preprocessed_tab_widget, "Plan and Preprocess")

        # === Train Tab ===
        # Store job_id for training status checking
        self.train_job_id = None
        
        train_tab_widget = QWidget()
        train_tab_layout = QVBoxLayout()
        train_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Button to run training
        self.train_run_button = QPushButton("Run Training")
        self.train_run_button.clicked.connect(self.run_training_clicked)
        train_tab_layout.addWidget(self.train_run_button)
        
        # Status text area with scrollbar for long JSON results
        self.train_status_label = QTextEdit("Training Status: Not started")
        self.train_status_label.setReadOnly(True)
        self.train_status_label.setMaximumHeight(200)  # Limit height to show scrollbar
        train_tab_layout.addWidget(self.train_status_label)
        
        # Refresh status button
        self.train_status_refresh_button = QPushButton("Refresh Training Status")
        self.train_status_refresh_button.clicked.connect(self.refresh_training_status)
        self.train_status_refresh_button.setEnabled(False)  # Disabled until job is started
        train_tab_layout.addWidget(self.train_status_refresh_button)
        
        # Model folder selection
        model_folder_label = QLabel("Model Folder:")
        train_tab_layout.addWidget(model_folder_label)
        
        self.training_model_folder_combo = QComboBox()
        self.training_model_folder_combo.setEditable(False)
        train_tab_layout.addWidget(self.training_model_folder_combo)
        
        # Refresh button for model folders
        self.training_model_folders_refresh_button = QPushButton("Refresh Model Folders")
        self.training_model_folders_refresh_button.clicked.connect(self.refresh_training_model_folders)
        train_tab_layout.addWidget(self.training_model_folders_refresh_button)
        
        # Training log files list widget
        self.training_log_files_list = QListWidget()
        self.training_log_files_list.setMinimumHeight(150)
        self.training_log_files_list.itemDoubleClicked.connect(self.on_training_log_file_double_clicked)
        train_tab_layout.addWidget(self.training_log_files_list)
        
        # Refresh button for training log files
        self.training_log_files_refresh_button = QPushButton("Refresh Training Log Files")
        self.training_log_files_refresh_button.clicked.connect(self.refresh_training_log_files_list)
        train_tab_layout.addWidget(self.training_log_files_refresh_button)
        
        train_tab_widget.setLayout(train_tab_layout)
        main_tab_widget.addTab(train_tab_widget, "Train")

        # === Predictions Tab ===
        predictions_tab_widget = QWidget()
        predictions_tab_layout = QVBoxLayout()
        predictions_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Predictions lists
        import nnunet_predictions_listwidget
        predictions_list_widget = nnunet_predictions_listwidget.nnUnetPredictionsListWidget()
        predictions_list_widget.images_downloaded.connect(self.handle_image_dataset_downloaded)
        predictions_list_widget.post_clicked.connect(self.handle_predictions_listwidget_post_dataset_clicked)
        predictions_list_widget.delete_clicked.connect(self.handle_predictions_listwidget_delete_dataset_clicked)
        predictions_list_widget.setMinimumWidth(200)
        predictions_list_widget.setToolTip("Predictions")
        self.predictions_list_widget = predictions_list_widget
        
        predictions_tab_layout.addWidget(predictions_list_widget)
        predictions_tab_widget.setLayout(predictions_tab_layout)
        main_tab_widget.addTab(predictions_tab_widget, "Predictions")

        layout.addWidget(main_tab_widget)

        return layout
    
    def _create_command_button_layout(self):
        # Button layout
        import flowlayout
        layout = flowlayout.FlowLayout()

        # New Dataset button
        self.new_dataset_button = QPushButton("New Dataset")
        self.new_dataset_button.clicked.connect(self.open_new_dataset_dialog)
        layout.addWidget(self.new_dataset_button)

        # Update list
        self.refresh_list_button = QPushButton("Refrush List")
        self.refresh_list_button.clicked.connect(self.update_train_test_prediction_lists)
        layout.addWidget(self.refresh_list_button)


        # # push for prediction
        # self.new_dataset_button = QPushButton("Push Image for Prediction")
        # self.new_dataset_button.clicked.connect(self._push_image_for_prediction_clicked)
        # layout.addWidget(self.new_dataset_button)


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

    def run_plan_and_preprocess_clicked(self):
        """Handle the Run Plan & Preprocess button click."""
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first")
            return

        dataset = self.datasets[selected_index]
        dataset_id = dataset.get("id", selected_text)

        try:
            # Disable button while processing
            self.plan_preprocess_button.setEnabled(False)
            self.worker_status_label.setPlainText("Status: Submitting job...")
            
            # Submit the plan and preprocess job
            response_data = nnunet_service.post_plan_and_preprocess_run(self.get_server_url(), dataset_id)
            
            # Store job_id
            self.plan_preprocess_job_id = response_data.get("job_id")
            number_of_jobs_ahead = response_data.get("number_of_jobs_ahead", 0)
            
            # Update UI
            self.worker_status_label.setPlainText(
                f"Status: Job submitted\nJob ID: {self.plan_preprocess_job_id}\n"
                f"Queue position: {number_of_jobs_ahead} jobs ahead"
            )
            self.worker_status_refresh_button.setEnabled(True)
            self.plan_preprocess_button.setEnabled(True)
            
            self.log_message.emit("INFO", f"Plan & Preprocess job submitted: {self.plan_preprocess_job_id}")
            
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            self.worker_status_label.setPlainText(f"Status: Error - {str(e)}")
            self.plan_preprocess_button.setEnabled(True)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            self.worker_status_label.setPlainText(f"Status: Request failed - {str(e)}")
            self.plan_preprocess_button.setEnabled(True)

    def refresh_plan_and_preprocess_status(self):
        """Refresh the status of the plan and preprocess job."""
        if not self.plan_preprocess_job_id:
            self.worker_status_label.setPlainText("Status: No job ID available")
            return

        try:
            status_data = nnunet_service.get_plan_and_preprocess_job_status(
                self.get_server_url(), 
                self.plan_preprocess_job_id
            )
            
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", "N/A")
            number_of_jobs_ahead = status_data.get("number_of_jobs_ahead", 0)
            
            status_text = (
                f"Status: {status}\n"
                f"Progress: {progress}\n"
                f"Queue position: {number_of_jobs_ahead} jobs ahead"
            )
            
            # Add result or error if available
            if status == "finished":
                result = status_data.get("result")
                if result:
                    # Prettify JSON result
                    try:
                        if isinstance(result, (dict, list)):
                            prettified_result = json.dumps(result, indent=4)
                        else:
                            # Try to parse as JSON string first
                            try:
                                parsed_result = json.loads(str(result))
                                prettified_result = json.dumps(parsed_result, indent=4)
                            except (json.JSONDecodeError, TypeError):
                                prettified_result = str(result)
                        status_text += f"\n\nResult:\n{prettified_result}"
                    except Exception as e:
                        status_text += f"\n\nResult: {str(result)}\n(Error formatting JSON: {e})"
                self.worker_status_label.setPlainText(status_text)
                self.log_message.emit("INFO", f"Plan & Preprocess job finished: {self.plan_preprocess_job_id}")
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                status_text += f"\n\nError: {error}"
                self.worker_status_label.setPlainText(status_text)
                self.log_message.emit("ERROR", f"Plan & Preprocess job failed: {error}")
            else:
                self.worker_status_label.setPlainText(status_text)
                
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            self.worker_status_label.setPlainText(f"Status: Error checking status - {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            self.worker_status_label.setPlainText(f"Status: Request failed - {str(e)}")

    def run_training_clicked(self):
        """Handle the Run Training button click."""
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first")
            return

        dataset = self.datasets[selected_index]
        dataset_id = dataset.get("id", selected_text)

        try:
            # Disable button while processing
            self.train_run_button.setEnabled(False)
            self.train_status_label.setPlainText("Status: Submitting training job...")
            
            # Submit the training job
            response_data = nnunet_service.post_train_run(self.get_server_url(), dataset_id)
            
            # Store job_id
            self.train_job_id = response_data.get("job_id")
            number_of_jobs_ahead = response_data.get("number_of_jobs_ahead", 0)
            
            # Update UI
            self.train_status_label.setPlainText(
                f"Status: Training job submitted\nJob ID: {self.train_job_id}\n"
                f"Queue position: {number_of_jobs_ahead} jobs ahead"
            )
            self.train_status_refresh_button.setEnabled(True)
            self.train_run_button.setEnabled(True)
            
            self.log_message.emit("INFO", f"Training job submitted: {self.train_job_id}")
            
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            self.train_status_label.setPlainText(f"Status: Error - {str(e)}")
            self.train_run_button.setEnabled(True)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            self.train_status_label.setPlainText(f"Status: Request failed - {str(e)}")
            self.train_run_button.setEnabled(True)

    def refresh_training_status(self):
        """Refresh the status of the training job."""
        if not self.train_job_id:
            self.train_status_label.setPlainText("Status: No job ID available")
            return

        try:
            status_data = nnunet_service.get_train_job_status(
                self.get_server_url(), 
                self.train_job_id
            )
            
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", "N/A")
            number_of_jobs_ahead = status_data.get("number_of_jobs_ahead", 0)
            
            status_text = (
                f"Status: {status}\n"
                f"Progress: {progress}\n"
                f"Queue position: {number_of_jobs_ahead} jobs ahead"
            )
            
            # Add result or error if available
            if status == "finished":
                result = status_data.get("result")
                if result:
                    # Prettify JSON result
                    try:
                        if isinstance(result, (dict, list)):
                            prettified_result = json.dumps(result, indent=4)
                        else:
                            # Try to parse as JSON string first
                            try:
                                parsed_result = json.loads(str(result))
                                prettified_result = json.dumps(parsed_result, indent=4)
                            except (json.JSONDecodeError, TypeError):
                                prettified_result = str(result)
                        status_text += f"\n\nResult:\n{prettified_result}"
                    except Exception as e:
                        status_text += f"\n\nResult: {str(result)}\n(Error formatting JSON: {e})"
                self.train_status_label.setPlainText(status_text)
                self.log_message.emit("INFO", f"Training job finished: {self.train_job_id}")
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                status_text += f"\n\nError: {error}"
                self.train_status_label.setPlainText(status_text)
                self.log_message.emit("ERROR", f"Training job failed: {error}")
            else:
                self.train_status_label.setPlainText(status_text)
                
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            self.train_status_label.setPlainText(f"Status: Error checking status - {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            self.train_status_label.setPlainText(f"Status: Request failed - {str(e)}")

    def refresh_training_model_folders(self):
        """Refresh the list of model folders for the selected dataset."""
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first")
            return

        dataset = self.datasets[selected_index]
        dataset_id = dataset.get("id", selected_text)

        try:
            # Verify combobox exists
            if not hasattr(self, 'training_model_folder_combo') or self.training_model_folder_combo is None:
                print("ERROR: training_model_folder_combo not found!")
                self.log_message.emit("ERROR", "Model folder combobox not initialized")
                return
            
            # Clear existing items
            self.training_model_folder_combo.clear()
            print(f"Refreshing model folders for dataset: {dataset_id}")
            
            # Get list of model folders
            response_data = nnunet_service.get_training_model_folder_names(self.get_server_url(), dataset_id)
            print(f"Response data: {response_data}")
            
            folders = response_data.get("folders", [])
            print(f"Extracted folders: {folders}")
            
            # Populate combobox
            for folder_name in folders:
                print(f"Adding folder to combobox: {folder_name}")
                self.training_model_folder_combo.addItem(folder_name)
            
            if not folders:
                self.training_model_folder_combo.addItem("No model folders available")
                self.training_model_folder_combo.setEnabled(False)
                # Clear log files list when no model folders are available
                if hasattr(self, 'training_log_files_list'):
                    self.training_log_files_list.clear()
            else:
                self.training_model_folder_combo.setEnabled(True)
            
            print(f"Combobox now has {self.training_model_folder_combo.count()} items")
            self.log_message.emit("INFO", f"Found {len(folders)} model folder(s)")
            
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            self.training_model_folder_combo.clear()
            self.training_model_folder_combo.addItem(f"Error: {str(e)}")
            self.training_model_folder_combo.setEnabled(False)
            # Clear log files list on error
            if hasattr(self, 'training_log_files_list'):
                self.training_log_files_list.clear()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            self.training_model_folder_combo.clear()
            self.training_model_folder_combo.addItem(f"Request failed: {str(e)}")
            self.training_model_folder_combo.setEnabled(False)
            # Clear log files list on error
            if hasattr(self, 'training_log_files_list'):
                self.training_log_files_list.clear()
        except Exception as e:
            print(f"Unexpected error in refresh_training_model_folders: {e}")
            import traceback
            traceback.print_exc()
            self.log_message.emit("ERROR", f"Unexpected error: {e}")
            self.training_model_folder_combo.clear()
            self.training_model_folder_combo.addItem(f"Error: {str(e)}")
            self.training_model_folder_combo.setEnabled(False)
            # Clear log files list on error
            if hasattr(self, 'training_log_files_list'):
                self.training_log_files_list.clear()

    def refresh_training_log_files_list(self):
        """Refresh the list of training log files for the selected dataset and model folder."""
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first")
            return

        # Check if model folder is selected
        model_folder_name = self.training_model_folder_combo.currentText()
        if not model_folder_name or model_folder_name == "" or model_folder_name.startswith("Error:") or model_folder_name.startswith("No model") or model_folder_name.startswith("Request failed"):
            self.log_message.emit("INFO", "Please select a model folder first")
            return

        dataset = self.datasets[selected_index]
        dataset_id = dataset.get("id", selected_text)

        try:
            # Clear existing items
            self.training_log_files_list.clear()
            
            # Get list of training log files
            response_data = nnunet_service.get_training_log_files(self.get_server_url(), dataset_id, model_folder_name)
            files = response_data.get("files", [])
            
            # Populate list widget
            for file_name in files:
                item = QListWidgetItem(file_name)
                self.training_log_files_list.addItem(item)
            
            if not files:
                item = QListWidgetItem("No training log files available")
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)  # Disable the item
                self.training_log_files_list.addItem(item)
            
            self.log_message.emit("INFO", f"Found {len(files)} training log file(s)")
            
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            self.training_log_files_list.clear()
            item = QListWidgetItem(f"Error: {str(e)}")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.training_log_files_list.addItem(item)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            self.training_log_files_list.clear()
            item = QListWidgetItem(f"Request failed: {str(e)}")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.training_log_files_list.addItem(item)

    def on_training_log_file_double_clicked(self, item):
        """Handle double-click on a training log file to show its content."""
        file_name = item.text()
        
        # Skip if it's an error or empty message
        if not file_name or file_name.startswith("Error:") or file_name.startswith("No training") or file_name.startswith("Request failed"):
            return
        
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first")
            return

        # Check if model folder is selected
        model_folder_name = self.training_model_folder_combo.currentText()
        if not model_folder_name or model_folder_name == "" or model_folder_name.startswith("Error:") or model_folder_name.startswith("No model") or model_folder_name.startswith("Request failed"):
            self.log_message.emit("INFO", "Please select a model folder first")
            return

        dataset = self.datasets[selected_index]
        dataset_id = dataset.get("id", selected_text)

        try:
            # Get file content
            response_data = nnunet_service.get_training_file_content(
                self.get_server_url(), 
                dataset_id,
                model_folder_name,
                file_name
            )
            
            content = response_data.get("content", "")
            
            # Show content in dialog
            dialog = FileContentDialog(file_name, content, self.dock_widget)
            dialog.exec_()
            
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            QMessageBox.warning(self.dock_widget, "Error", f"Failed to load file content: {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            QMessageBox.warning(self.dock_widget, "Error", f"Request failed: {str(e)}")

    def refresh_preprocessed_files_list(self):
        """Refresh the list of preprocessed files and summary status for the selected dataset."""
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first")
            return

        dataset = self.datasets[selected_index]
        dataset_id = dataset.get("id", selected_text)

        try:
            # Get preprocessed summary first
            try:
                summary_response = nnunet_service.get_preprocessed_summary(self.get_server_url(), dataset_id)
                summary = summary_response.get("summary", {})
                
                # Build status text with requested fields
                status_text_parts = []
                
                status = summary.get("status", "Unknown")
                status_text_parts.append(f"<b>Data Status:</b> {status}")
                
                finished_at = summary.get("finished_at", "N/A")
                if finished_at != "N/A":
                    status_text_parts.append(f"<b>Finished at:</b> {finished_at}")
                
                execution_seconds = summary.get("execution_seconds")
                if execution_seconds is not None:
                    status_text_parts.append(f"<b>Execution time:</b> {execution_seconds:.2f} seconds")
                
                stderr = summary.get("stderr", "")
                if stderr:
                    status_text_parts.append(f"<b>Error:</b> {stderr}")
                else:
                    status_text_parts.append(f"<b>Error:</b> (empty)")
                
                status_text = "<br>".join(status_text_parts)
                self.data_status_label.setText(status_text)
                
            except Exception as e:
                print(f"Error getting summary: {e}")
                self.data_status_label.setText(f"Status: Error loading summary - {str(e)}")
            
            # Clear existing items
            self.preprocessed_files_list.clear()
            
            # Get list of preprocessed files
            response_data = nnunet_service.get_preprocessed_files(self.get_server_url(), dataset_id)
            files = response_data.get("files", [])
            
            # Populate list widget
            for file_name in files:
                item = QListWidgetItem(file_name)
                self.preprocessed_files_list.addItem(item)
            
            if not files:
                item = QListWidgetItem("No preprocessed files available")
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)  # Disable the item
                self.preprocessed_files_list.addItem(item)
            
            self.log_message.emit("INFO", f"Found {len(files)} preprocessed file(s)")
            
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            self.data_status_label.setText(f"Status: Error - {str(e)}")
            self.preprocessed_files_list.clear()
            item = QListWidgetItem(f"Error: {str(e)}")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.preprocessed_files_list.addItem(item)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            self.data_status_label.setText(f"Status: Request failed - {str(e)}")
            self.preprocessed_files_list.clear()
            item = QListWidgetItem(f"Request failed: {str(e)}")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.preprocessed_files_list.addItem(item)

    def on_preprocessed_file_double_clicked(self, item):
        """Handle double-click on a preprocessed file to show its content."""
        file_name = item.text()
        
        # Skip if it's an error or empty message
        if not file_name or file_name.startswith("Error:") or file_name.startswith("No preprocessed") or file_name.startswith("Request failed"):
            return
        
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first")
            return

        dataset = self.datasets[selected_index]
        dataset_id = dataset.get("id", selected_text)

        try:
            # Get file content
            response_data = nnunet_service.get_preprocessed_file_content(
                self.get_server_url(), 
                dataset_id, 
                file_name
            )
            
            content = response_data.get("content", "")
            
            # Show content in dialog
            dialog = FileContentDialog(file_name, content, self.dock_widget)
            dialog.exec_()
            
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
            QMessageBox.critical(self.dock_widget, "Error", f"Failed to load file content: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")
            QMessageBox.critical(self.dock_widget, "Error", f"Request failed: {e}")

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
                    self._on_dataset_selected(len(self.datasets) - 1)  # Show details

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

    def handle_predictions_listwidget_post_dataset_clicked(self, dataset_id, sender):
        print('posting a prediction request')
        self.post_image_for_prediction()

    def handle_predictions_listwidget_delete_dataset_clicked(self, dataset_id, req_id, sender):
        print(f'deleting a prediction request: dataset_id={dataset_id}, req_id={req_id}')
        self.delete_prediction(req_id)

    def post_image_and_labels(self, images_for):
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text=="" or selected_index==-1:
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
            self._on_dataset_selected(selected_index)
        
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

    def save_image_to_temp_folder(self, dataset):
        # get vtk image and label list
        vtk_image = self.segmentation_list_manager.get_base_vtk_image()

        # save the files to a temporary folders
        temp_dir = conf['temp_dir']
        import time
        sec = int(time.time())  # Current time in seconds
        import os
        image_path = os.path.join(temp_dir, f'image_{sec}.mha')

        print(f'saving image to {image_path}')
        #save_as_2d_if_single_slice_3d_image=False, in nnunet everything is 3d. so, no need to save as 2d
        from itk_tools import save_sitk_image
        from itkvtk import vtk_to_sitk
        save_sitk_image(vtk_to_sitk(vtk_image), image_path, save_as_2d_if_single_slice_3d_image=False)
        
        return image_path

    def update_image_and_labels(self, images_for, num):
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text == "" or selected_index == -1:
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
            self._on_dataset_selected(selected_index)  

        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")

    def post_image_for_prediction(self):
        selected_text = self.dataset_dropdown.currentText()
        selected_index = self.dataset_dropdown.currentIndex()

        if selected_text=="" or selected_index==-1:
            self.log_message.emit("INFO", "Please select a dataset to add images to")
            return 

        dataset = self.datasets[selected_index]

        """updating the images and labels"""
        try:
            if "id" in dataset:
                dataset_id = dataset["id"]
            else:
                dataset_id = selected_text

            image_path = self.save_image_to_temp_folder(dataset)

            import os

            requester_id = "vtk_image_labeler_3d@varianEclipseTest"
            image_id = os.path.basename(image_path)
            req_metadata = {
                            "requester_id": requester_id,
                            "image_id": image_id,
                            "user": "Jinkoo Kim",
                            "email": "jinkoo.kim@stonybrookmedicine.edu",
                            "institution": "Stony Brook" ,
                            "notes": "submitted for predition"
                        }

            # Show dialog to edit metadata
            from metadata_dialog import MetadataDialog
            dialog = MetadataDialog(req_metadata, self.dock_widget)
            if dialog.exec_() != QDialog.Accepted:
                self.log_message.emit("INFO", "Metadata input canceled.")
                return

            req_metadata = dialog.get_metadata()

            req_metadata['dataset_id'] = dataset_id

            #requester_id = req_metadata["requester_id"]
            image_id = req_metadata["image_id"]

            req_response = nnunet_service.post_image_for_prediction(self.get_server_url(), dataset_id, image_path, requester_id, image_id, req_metadata)
            print(f"response_data={req_response}")
            self.log_message.emit("INFO",f"dateset_updated={req_response}")

            # this is a rough way to refresh the prediction list (this will also update the train/terst image list as well)
            self._on_dataset_selected(selected_index)
       
        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
            self.log_message.emit("ERROR", f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.log_message.emit("ERROR", f"Request failed: {e}")


    def delete_prediction(self, req_id):
        selected_dataset_text = self.dataset_dropdown.currentText()
        selected_dataset_index = self.dataset_dropdown.currentIndex()

        if selected_dataset_text == "" or selected_dataset_index == -1:
            self.log_message.emit("INFO", "Please select a dataset first!")
            return 

        dataset = self.datasets[selected_dataset_index]

        """deleting the images and labels"""
        try:
            if "id" in dataset:
                dataset_id = dataset["id"]
            else:
                dataset_id = selected_dataset_text

            delete_info = nnunet_service.delete_prediction(self.get_server_url(), dataset_id, req_id)
            print(f"response_data={delete_info}")
            self.log_message.emit("INFO",f"delete_info={delete_info}")
       
            # update the list
            self._on_dataset_selected(selected_dataset_index)  

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
                self._on_dataset_selected(0)

        except nnunet_service.ServerError as e:
            self.show_msgbox_error(title="Error", msg=f"Server error: {e}", parent=self.main_widget)
        except requests.exceptions.RequestException as e:
            self.show_msgbox_error(title="Error", msg=f"Request failed: {e}", parent=self.main_widget)
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
    
    def update_train_test_prediction_lists(self):
        print("updating train/test/prediction lists")
        selected_index = self.dataset_dropdown.currentIndex()
        self._on_dataset_selected(selected_index)

    def _on_dataset_selected(self, dataset_index):
        """Triggered when the user selects a dataset."""
        if not self.datasets or dataset_index < 0 or dataset_index >= len(self.datasets):
            self.details_label.setText("<b>Error:</b> No dataset selected.")
            return

        # Make a copy of the dataset
        dataset = self.datasets[dataset_index].copy()
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

            req_list = nnunet_service.get_dataset_image_name_list(self.get_server_url(), dataset_id)
            print(f"response_data={req_list}")

            # --- Populate training image list ---
            self.train_image_list_widget.set_dataset(dataset_id, req_list['train_images'])

            # --- Populate testing image list ---
            self.test_image_list_widget.set_dataset(dataset_id, req_list['test_images'])

            # get predictions list and polulate the list widget
            req_list = nnunet_service.get_prediction_list(self.get_server_url(), dataset_id)
            if req_list is not None and isinstance(req_list, list):
                print(f"response_data={req_list}")
                self.predictions_list_widget.set_dataset(dataset_id, req_list)
            else: 
                self.predictions_list_widget.set_dataset(dataset_id, [])

            # Refresh Plan and Preprocess tab data status
            try:
                self.refresh_preprocessed_files_list()
            except Exception as e:
                print(f"Error refreshing preprocessed files list: {e}")

            # Refresh Train tab model folders and log files
            try:
                self.refresh_training_model_folders()
                # After model folders are refreshed, select first folder and refresh log files if available
                if (hasattr(self, 'training_model_folder_combo') and 
                    self.training_model_folder_combo.count() > 0 and
                    self.training_model_folder_combo.isEnabled()):
                    current_text = self.training_model_folder_combo.currentText()
                    # If no valid selection or if it's an error/empty message, select first item
                    if (not current_text or 
                        current_text.startswith("Error:") or 
                        current_text.startswith("No model") or 
                        current_text.startswith("Request failed")):
                        if self.training_model_folder_combo.count() > 0:
                            self.training_model_folder_combo.setCurrentIndex(0)
                            current_text = self.training_model_folder_combo.currentText()
                    # Refresh log files if we have a valid folder selected
                    if (current_text and 
                        not current_text.startswith("Error:") and 
                        not current_text.startswith("No model") and 
                        not current_text.startswith("Request failed")):
                        self.refresh_training_log_files_list()
            except Exception as e:
                print(f"Error refreshing training model folders/log files: {e}")

        except nnunet_service.ServerError as e:
            print(f"Server error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        # return []  # Return an empty list in case of failure

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
