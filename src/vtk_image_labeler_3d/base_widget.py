from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QApplication
import sys
from PyQt5.QtCore import Qt, pyqtSignal, QObject

import qt_tools

class BaseWidget(QWidget):

    def __init__(self):
        super().__init__()

    def show_msgbox_error(self, title:str="Error", msg:str="something went wrong!"):
        qt_tools.show_msgbox_error(title=title, msg=msg, parent=self)

    def show_msgbox_warning(self, title:str="Warning", msg:str="something went wrong!"):
        qt_tools.show_msgbox_warning(title=title, msg=msg, parent=self)

    def show_msgbox_info(self, title:str="Information", msg:str="something went wrong!"):
        qt_tools.show_msgbox_info(title=title, msg=msg, parent=self)

