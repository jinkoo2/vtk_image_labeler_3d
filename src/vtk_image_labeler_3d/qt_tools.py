
from PyQt5.QtWidgets import QMessageBox, QApplication, QWidget

def show_msg_box_yes_no(title:str="Confirm", msg:str="", parent: QWidget = None):
    reply = QMessageBox.question(
        parent,
        title,
        msg,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes  # Default button
    )

    if reply == QMessageBox.Yes:
        print("User clicked Yes")
        return True
    else:
        print("User clicked No")
        return False

