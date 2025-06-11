from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QApplication
import sys
from PyQt5.QtCore import Qt, pyqtSignal, QObject

import qt_tools

class BaseObject(QObject):

    def __init__(self):
        super().__init__()

    def show_msgbox_error(self, title:str="Error", msg:str="something went wrong!", parent: QWidget = None):
        qt_tools.show_msgbox_error(title=title, msg=msg, parent=parent)

    def show_msgbox_warning(self, title:str="Warning", msg:str="", parent: QWidget = None):
        qt_tools.show_msgbox_warning(title=title, msg=msg, parent=parent)

    def show_msgbox_info(self, title:str="Information", msg:str="", parent: QWidget = None):
        qt_tools.show_msgbox_info(title=title, msg=msg, parent=parent)