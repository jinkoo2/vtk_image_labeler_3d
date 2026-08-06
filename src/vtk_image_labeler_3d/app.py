import os
import sys


def _resource_dir():
    """Package dir in source runs; PyInstaller extract dir when frozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def main():
    # Add package directory to sys.path so bare imports (e.g. `import mainwindow3d`)
    # resolve when launched via `poetry run app` instead of direct execution.
    pkg_dir = _resource_dir()
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    from crash_reporting import capture_exception, init_crash_reporting
    from version_info import get_version

    # Initialize BugSink as early as possible (before heavy imports).
    init_crash_reporting(release=get_version())

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
    from logger import logger, _info, _err
    from splash_screen import create_splash, show_message
    from ui_theme import apply_material_theme

    # Construct paths to the icons
    current_dir = pkg_dir
    brush_icon_path = os.path.join(current_dir, "icons", "brush.png")

    _info("Application started")

    try:
        app = QApplication(sys.argv)
        apply_material_theme(app)
        app.setWindowIcon(QIcon(brush_icon_path))
        app.aboutToQuit.connect(lambda: _info("Application is quitting."))

        splash = create_splash(version=get_version())
        splash.show()
        show_message(splash, "Loading modules...")

        import mainwindow3d

        show_message(splash, "Building main window...")
        main_window = mainwindow3d.MainWindow3D()

        show_message(splash, "Ready")
        main_window.showMaximized()
        splash.finish(main_window)

        sys.exit(app.exec_())
    except BaseException as exc:
        # Ensure fatal startup / top-level failures reach BugSink.
        if not isinstance(exc, (SystemExit, KeyboardInterrupt)):
            capture_exception(exc)
            _err(f"Fatal application error: {exc}")
        raise


if __name__ == "__main__":
    main()
