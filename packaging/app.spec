# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for vtk-image-labeler-3d (onedir)."""

import re
import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_submodules

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent
PKG = ROOT / "src" / "vtk_image_labeler_3d"
ENTRY = PKG / "app.py"

datas = []
binaries = []
hiddenimports = []

# Bundle default settings next to the frozen app payload.
settings = ROOT / "settings.json"
if settings.exists():
    datas.append((str(settings), "."))

icons = PKG / "icons"
if icons.exists():
    datas.append((str(icons), "icons"))

for name in (
    "vtk",
    "PyQt5",
    "SimpleITK",
    "skimage",
    "cv2",
    "itk",
    "maxflow",
    "qtawesome",
):
    try:
        d, b, h = collect_all(name)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # noqa: BLE001 - best-effort collection
        print(f"collect_all({name!r}) skipped: {exc}", file=sys.stderr)

# VTK util helpers are imported dynamically and often missed by Analysis.
try:
    hiddenimports += collect_submodules("vtk.util")
except Exception as exc:  # noqa: BLE001
    print(f"collect_submodules(vtk.util) skipped: {exc}", file=sys.stderr)
try:
    hiddenimports += collect_submodules("vtkmodules.util")
except Exception as exc:  # noqa: BLE001
    print(f"collect_submodules(vtkmodules.util) skipped: {exc}", file=sys.stderr)

hiddenimports += [
    "vtk.util",
    "vtk.util.numpy_support",
    "vtkmodules",
    "vtkmodules.util",
    "vtkmodules.util.numpy_support",
]

# Bare imports used throughout the package
hiddenimports += [
    "mainwindow3d",
    "app_icon",
    "crash_reporting",
    "feedback_dialog",
    "viewer3d",
    "viewer2d",
    "config",
    "logger",
    "itk_tools",
    "itkvtk",
    "nnunet_service",
    "nnunet_client_manager",
    "nnunet_login_dialog",
    "preferences_dialog",
    "version_info",
    "splash_screen",
    "qtawesome",
    "ui_theme",
    "ui_icons",
    "update_check",
    "vtk_segmentation_list_manager",
    "vtk_point_list_manager",
    "vtk_line_list_manager",
    "vtk_rect_list_manager",
    "graphcut_histogram",
    "fill_between_slices",
    "flowlayout",
    "qt_tools",
    "model_viewer",
    "reslicer",
]

# Host OS should supply these; shipping copies from a newer distro
# (e.g. Ubuntu 24.04) causes GLIBC_2.38-not-found on older desktops.
_SYSTEM_LIB_PREFIXES = (
    "libX11",
    "libXext",
    "libXrender",
    "libXfixes",
    "libXinerama",
    "libXi",
    "libXrandr",
    "libXcursor",
    "libXdamage",
    "libXcomposite",
    "libXtst",
    "libXxf86vm",
    "libXss",
    "libxcb",
    "libbsd",
    "libmd.so",
)


def _is_os_x11_lib(dest_name: str) -> bool:
    name = Path(str(dest_name)).name
    # Keep auditwheel/vtk.libs hashed copies like libXcursor-<hash>.so.* (must ship).
    if re.search(r"-[0-9a-f]{6,}\.so", name):
        return False
    return any(name.startswith(prefix) for prefix in _SYSTEM_LIB_PREFIXES)


a = Analysis(
    [str(ENTRY)],
    pathex=[str(PKG)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(SPEC_DIR / "runtime_hook_path.py")],
    excludes=[],
    noarchive=False,
)

kept_bins = []
dropped = []
for entry in a.binaries:
    dest = entry[0]
    if _is_os_x11_lib(dest):
        dropped.append(dest)
    else:
        kept_bins.append(entry)
if dropped:
    print(
        f"Excluded {len(dropped)} OS X11/bsd libs from bundle "
        f"(examples: {', '.join(dropped[:5])})",
        file=sys.stderr,
    )
a.binaries = kept_bins

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageLabeler3D",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(SPEC_DIR / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ImageLabeler3D",
)
