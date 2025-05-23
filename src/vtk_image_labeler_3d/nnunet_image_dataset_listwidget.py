from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QApplication
import sys
from PyQt5.QtCore import Qt, pyqtSignal, QObject

import nnunet_service 

from config import get_config
conf = get_config()

def extract_image_number(filename):
    import re
    match = re.match(r'^.*?_(\d+)_\d+\.(nii\.gz|mha|mhd)$', filename)
    if match:
        return int(match.group(1))
    raise ValueError(f"Could not extract number from filename: {filename}")

nnunet_server_url = conf['nnunet_server_url']

class nnUnetImageDataSetListWidget(QWidget):

    image_dataset_downloaded = pyqtSignal(str, str, QObject) # 
    post_dataset_clicked = pyqtSignal(str, str, QObject) 
    update_dataset_clicked = pyqtSignal(str, str, int, QObject) 
    delete_dataset_clicked = pyqtSignal(str, str, int, QObject) 
    
    def __init__(self, images_for:str):
        super().__init__()

        if images_for != 'train' and images_for != 'test':
            raise Exception('images_for must be either TRAIN(=0) or TEST(=1)')
        
        self.images_for = images_for
        self._dataset_id = None
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add a title bar using QLabel
        self.title_label_widget = QLabel(f'{images_for.upper()} Images')
        self.title_label_widget.setStyleSheet("padding: 0;")
        self.title_label_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget( self.title_label_widget)

        # Create the list widget
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # add 4 command buttons in horizontal layout (get, post, update, delete)
        button_layout = QHBoxLayout()
        self.get_button = QPushButton("Get")
        self.post_button = QPushButton("Post")
        self.update_button = QPushButton("Update")
        self.delete_button = QPushButton("Delete")

        for btn in [self.get_button, self.post_button, self.update_button, self.delete_button]:
            btn.clicked.connect(self.command_button_clicked)
            btn.setMinimumWidth(60)
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle("QListWidget with Title")

    def on_item_double_clicked(self, item):
        self.get_image_dataset()
        
    def set_dataset(self, dataset_id, image_list):
        self.list_widget.clear()
        self._dataset_id = dataset_id
        for item in image_list:
            self.list_widget.addItem(item["filename"])

    def command_button_clicked(self):
        sender = self.sender()
        if sender == self.get_button:
            self.get_image_dataset()
        
        elif sender == self.post_button:
            self.post_image_dataset()

        elif sender == self.update_button:
            self.update_image_dataset()

        elif sender == self.delete_button:
            self.delete_image_dataset()
  
    def get_image_dataset(self):
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            print("No image selected.")
            return

        try:
            # Extract ID from the selected item's data or text
            selected_text = selected_item.text()
            number = extract_image_number(selected_text)  # crude way to extract number
            dataset_id = self._dataset_id

            from nnunet_service import download_dataset_images_and_labels
            result = download_dataset_images_and_labels(
                BASE_URL=nnunet_server_url,
                dataset_id=dataset_id,
                images_for=self.images_for,
                num=number,
                out_dir="./_downloads"
            )

            print("Download complete:", result)

            # notify image download
            image_path = result['downloaded_base_image_path']
            labels_path = result['downloaded_labels_image_path']
            self.image_dataset_downloaded.emit(image_path, labels_path, self)

        except Exception as e:
            print("Error downloading dataset:", str(e))

    def post_image_dataset(self):
        self.post_dataset_clicked.emit(self._dataset_id, self.images_for, self )

    def update_image_dataset(self):
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            print("No image selected.")
            return

        # number
        selected_text = selected_item.text()
        number = extract_image_number(selected_text)  # crude way to extract number

        self.update_dataset_clicked.emit(self._dataset_id, self.images_for, number, self)
    
    def delete_image_dataset(self):
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            print("No image selected.")
            return

        # number
        selected_text = selected_item.text()
        number = extract_image_number(selected_text)  # crude way to extract number

        self.delete_dataset_clicked.emit(self._dataset_id, self.images_for, number, self)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = nnUnetImageDataSetListWidget(images_for='train')
    window.show()
    sys.exit(app.exec_())
