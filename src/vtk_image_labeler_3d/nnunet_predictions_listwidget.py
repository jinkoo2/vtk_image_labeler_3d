from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QApplication, QListWidgetItem
import sys
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import uuid
import os
import zip_tools
import nnunet_service 

from config import get_config
conf = get_config()

def extract_image_number(filename):
    import re
    match = re.match(r'^.*?_(\d+)_\d+\.(nii\.gz|mha|mhd)$', filename)
    if match:
        return int(match.group(1))
    raise ValueError(f"Could not extract number from filename: {filename}")

def extract_req_id(listitem_text):
    listitem_text_parts = listitem_text.split('/')
    return listitem_text_parts[0]


nnunet_server_url = conf['nnunet_server_url']

from base_widget import BaseWidget
class nnUnetPredictionsListWidget(BaseWidget):

    images_downloaded = pyqtSignal(str, str, QObject) # 
    post_clicked = pyqtSignal(str, QObject) 
    delete_clicked = pyqtSignal(str, str, QObject) 
    
    def __init__(self):
        super().__init__()

        self._dataset_id = None
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add a title bar using QLabel
        self.title_label_widget = QLabel(f'Predictions')
        self.title_label_widget.setStyleSheet("padding: 0;")
        self.title_label_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget( self.title_label_widget)

        # Create the list widget
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # add 4 command buttons in horizontal layout (get, post, delete)
        button_layout = QHBoxLayout()
        self.get_button = QPushButton("Get")
        self.post_button = QPushButton("Post")
        self.delete_button = QPushButton("Delete")

        for btn in [self.get_button, self.post_button, self.delete_button]:
            btn.clicked.connect(self.command_button_clicked)
            btn.setMinimumWidth(60)
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle("QListWidget with Title")

    def on_item_double_clicked(self, item):
        self.download_prediction_images()
        
    def set_dataset(self, dataset_id, req_list):
        self.list_widget.clear()
        self._dataset_id = dataset_id

        for item in req_list:
            req_id = item['req_id']
            input_images = ','.join(item['input_images'])
            completed = item['completed']
            label = f'{req_id}/{input_images}'
            if completed:
                label += '/completed'
            elif 'job_status' in item:
                label += f"/{item['job_status']}"

            list_item = QListWidgetItem(label)
            list_item.setData(Qt.UserRole, item)  # Attach the full item object
            self.list_widget.addItem(list_item)

    def command_button_clicked(self):
        sender = self.sender()
        if sender == self.get_button:
            self.download_prediction_images()
        
        elif sender == self.post_button:
            self.post_prediction()

        elif sender == self.delete_button:
            self.delete_prediction()
  
    def download_prediction_images(self):
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            print("No image selected.")
            return
                
        # request data from the server 
        req_data = selected_item.data(Qt.UserRole)
        print(req_data['req_id'])

        if 'input_images' not in req_data:
            self.show_msgbox_error(msg="Internal error: Missing 'input_images' field from server response.")
            return 
        
        # input images of the selected item
        images = req_data['input_images']
        
        if len(images) == 0:
            self.show_msgbox_error(msg="Internal error: There is no input image for this request.")
            return 
        
        if len(images)>1:
            import qt_tools
            selected_image = qt_tools.show_select_options_dlg(title="Select Image", label="Please select an image", options=images, parent=self.list_widget)
            if not selected_image:
                print("No image selected.")
                return
        else:
            selected_image = images[0]

        try:
            dataset_id = self._dataset_id
            selected_image_number = selected_image.split('_')[1]

            download_dir = os.path.join("./_downloads", str(uuid.uuid4()))
            result = nnunet_service.download_prediction_images_and_labels(
                BASE_URL=nnunet_server_url,
                dataset_id=dataset_id,
                req_id=req_data['req_id'],
                image_number=int(selected_image_number),
                out_dir=download_dir
            )
            print("Download complete:", result)

            image_names = result['image_names']
            label_name = result['label_name']
            zip_path = result['zip_path']

            # unzip to download dir
            zip_tools.unzip_to_folder(zip_path, download_dir)

            if len(images)> 1:
                self.show_msgbox_info(title="Multi-Channel Inputs", msg="there are more than 1 input images (multi-channel). Only the first image (ch=0) is used for rendering.", parent=self.main_widget)

            # notify image download (only use the first image)
            image_path = os.path.join(download_dir, image_names[0])
            label_path = os.path.join(download_dir, label_name)
            self.images_downloaded.emit(image_path, label_path, self)

        except Exception as e:
            print("Error downloading dataset:", str(e))

    def post_prediction(self):
        self.post_clicked.emit(self._dataset_id, self )

    
    def delete_prediction(self):
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            print("No image selected.")
            return

        # number
        selected_text = selected_item.text()
        req_id = extract_req_id(selected_text)  # crude way to extract number
        print(f"Deleting prediction with req_id={req_id}")

        self.delete_clicked.emit(self._dataset_id, req_id, self)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = nnUnetImageDataSetListWidget(images_for='train')
    window.show()
    sys.exit(app.exec_())
