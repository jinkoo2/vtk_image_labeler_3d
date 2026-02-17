import os
import sys

def main():
    # Add package directory to sys.path so bare imports (e.g. `import mainwindow3d`)
    # resolve when launched via `poetry run app` instead of direct execution.
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
    from logger import logger, _info, _err

    # Construct paths to the icons
    current_dir = os.path.dirname(__file__)
    brush_icon_path = os.path.join(current_dir, "icons", "brush.png")

    _info("Application started")

    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(brush_icon_path))

    app.aboutToQuit.connect(lambda: _info("Application is quitting."))

    import mainwindow3d
    main_window = mainwindow3d.MainWindow3D()

    #main_window.show()
    main_window.showMaximized()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
