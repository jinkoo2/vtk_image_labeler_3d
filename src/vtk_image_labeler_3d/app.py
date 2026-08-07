import os
import sys
import traceback
from pathlib import Path


SMOKE_FLAG = "--smoke-test"


def _resource_dir():
    """Package dir in source runs; PyInstaller extract dir when frozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _smoke_result_path() -> Path:
    """Prefer a writable dir next to the frozen EXE; fall back to CWD."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "smoke_result.txt"
    return Path.cwd() / "smoke_result.txt"


def _write_smoke_result(ok: bool, detail: str = "") -> None:
    path = _smoke_result_path()
    body = "SMOKE_OK\n" if ok else f"SMOKE_FAIL\n{detail}\n"
    try:
        path.write_text(body, encoding="utf-8")
    except OSError:
        pass


def _run_smoke_test(pkg_dir: str) -> int:
    """Import-only packaging smoke test (no Qt/VTK windows).

    CI runners are headless: constructing MainWindow3D / OpenGL contexts
    segfaults (Windows 0xC0000005, macOS SIGSEGV, Linux X BadWindow).
    Importing the mainwindow chain still catches missing hidden imports
    such as vtk.util.numpy_support (via reslicer -> itkvtk).
    """
    del pkg_dir  # reserved for future resource checks
    # Avoid accidental GUI backend selection if any import constructs QApplication.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from version_info import get_version

        from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy  # noqa: F401
        import itkvtk  # noqa: F401
        # Pulls viewer3d -> reslicer -> itkvtk; same path as cold start before UI.
        import mainwindow3d  # noqa: F401

        detail = f"version={get_version()} imports=ok"
        _write_smoke_result(True, detail=detail)
        print("SMOKE_OK", detail, flush=True)
        return 0
    except BaseException as exc:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        _write_smoke_result(False, detail=detail)
        print("SMOKE_FAIL", flush=True)
        print(detail, flush=True)
        return 1


def main():
    # Add package directory to sys.path so bare imports (e.g. `import mainwindow3d`)
    # resolve when launched via `poetry run app` instead of direct execution.
    pkg_dir = _resource_dir()
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    smoke = SMOKE_FLAG in sys.argv
    if smoke:
        sys.argv = [a for a in sys.argv if a != SMOKE_FLAG]
        raise SystemExit(_run_smoke_test(pkg_dir))

    from crash_reporting import capture_exception, init_crash_reporting
    from version_info import get_version

    # Initialize BugSink as early as possible (before heavy imports).
    init_crash_reporting(release=get_version())

    from PyQt5.QtWidgets import QApplication
    from app_icon import load_app_icon
    from logger import logger, _info, _err
    from splash_screen import create_splash, show_message
    from ui_theme import apply_material_theme

    _info("Application started")

    try:
        app = QApplication(sys.argv)
        apply_material_theme(app)
        app_icon = load_app_icon(pkg_dir)
        app.setWindowIcon(app_icon)
        app.aboutToQuit.connect(lambda: _info("Application is quitting."))

        splash = create_splash(version=get_version(), icon=app_icon)
        splash.show()
        show_message(splash, "Loading modules...")

        import mainwindow3d

        show_message(splash, "Building main window...")
        main_window = mainwindow3d.MainWindow3D()
        main_window.setWindowIcon(app_icon)

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
