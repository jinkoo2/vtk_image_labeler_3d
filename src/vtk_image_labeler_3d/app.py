from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from logger import logger, _info, _err

import os

# Construct paths to the icons
current_dir = os.path.dirname(__file__)
brush_icon_path = os.path.join(current_dir, "icons", "brush.png")
eraser_icon_path = os.path.join(current_dir, "icons", "eraser.png")
reset_zoom_icon_path = os.path.join(current_dir, "icons", "reset_zoom.png")

if __name__ == "__main__":
    import sys
    
    _info("Application started")

    app = QApplication(sys.argv)
    
    app.setWindowIcon(QIcon(brush_icon_path))  # Set application icon

    app.aboutToQuit.connect(lambda: _info("Application is quitting."))

    import mainwindow3d
    main_window = mainwindow3d.MainWindow3D()

    #main_window.show()
    main_window.showMaximized()
    sys.exit(app.exec_())

