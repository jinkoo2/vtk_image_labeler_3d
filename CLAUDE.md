# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A 3D medical image annotation and segmentation labeling tool built with PyQt5, VTK, and SimpleITK. Supports loading 3D medical images (DICOM, MHA, MHD), manual brush-based segmentation painting, point/line/rectangle annotations, and integration with an external nnUNet server for automated segmentation predictions.

## Commands

```bash
# Install dependencies (uses Poetry)
poetry install

# Run the application
python src/vtk_image_labeler_3d/app.py

# Run tests
pytest tests/
```

## Architecture

### Entry Point
`src/vtk_image_labeler_3d/app.py` → creates `MainWindow3D` (the main application window).

### Core Components
- **MainWindow3D** (`mainwindow3d.py`): Main window orchestrating all managers and UI panels
- **VTKViewer3D** (`viewer3d.py`): 3D rendering widget with mouse interaction and slice synchronization
- **Viewer2D** (`viewer2d.py`): 2D slice viewer for axial/coronal/sagittal planes

### Manager Pattern
Annotation types are each handled by a dedicated manager class:
- **SegmentationListManager** (`vtk_segmentation_list_manager.py`): Segmentation layers with brush painting, boolean operations (AND/OR/SUB), component extraction — this is the largest and most central component
- **PointListManager** (`vtk_point_list_manager.py`): 3D point annotations
- **LineListManager** (`vtk_line_list_manager.py`): Line/ruler annotations with distance measurement
- **RectListManager** (`vtk_rect_list_manager.py`): Rectangle annotations

### Image Processing Pipeline
```
SimpleITK Image ↔ VTK Image ↔ NumPy Array
```
- `itkvtk.py`: Bidirectional SimpleITK ↔ VTK conversion (preserves geometry metadata)
- `itk_tools.py`: SimpleITK image operations
- `vtk_tools.py`: VTK image utilities and binary operations
- `reslicer.py`: Efficient 2D slice extraction from 3D volumes across planes

### nnUNet Integration
- `nnunet_service.py`: REST API client for the external nnUNet server
- `nnunet_client_manager.py`: Orchestrates dataset management, upload, and prediction workflows
- Server URL configured via `.env` (`nnunet_server_url`)

### Paint System
`PaintBrush` class in the segmentation manager handles circular brush painting directly on VTK image scalars, supporting both 2D plane painting and 3D volumetric painting.

## Key Patterns
- **Qt Signal-Slot**: Components communicate via PyQt5 signals (e.g., `layer_added`, `layer_image_modified`, `active_layer_changed`)
- **Configuration**: `.env` file loaded via `python-dotenv` (see `config.py`); app state persisted in `_settings.conf` (INI format)
- **Logging**: Centralized logger (`logger.py`) — DEBUG to daily log files in `_logs/`, INFO to console
- **Imports are relative**: Modules in `src/vtk_image_labeler_3d/` import each other by name directly (e.g., `import mainwindow3d`), not as package imports

## Directories
- `_logs/`, `_temp/`, `_downloads/`: Runtime directories (gitignored via `_*` pattern)
- `sample_data/`: Sample nnUNet-format datasets for testing
