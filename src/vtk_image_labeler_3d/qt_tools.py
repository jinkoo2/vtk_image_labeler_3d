
from PyQt5.QtWidgets import QMessageBox, QWidget

def show_msgbox_yes_no(title:str="Confirm", msg:str="", parent: QWidget = None):
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


def show_msgbox_error(title:str="Error", msg:str="something went wrong!", parent: QWidget = None):
    QMessageBox.critical(parent, title, msg)

def show_msgbox_warning(title:str="Warning", msg:str="something went wrong!", parent: QWidget = None):
    QMessageBox.warning(parent, title, msg)

def show_msgbox_info(title:str="Information", msg:str="something went wrong!", parent: QWidget = None):
    QMessageBox.information(parent, title, msg)


def show_select_options_dlg(title, label, options, parent: QWidget = None):
    from PyQt5.QtWidgets import QInputDialog
    item, ok = QInputDialog.getItem(parent, title, label, options, 0, False)
    if ok and item:
        print(f"User selected: {item}")
        return item
    return None
