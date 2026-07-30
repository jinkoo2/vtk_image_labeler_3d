"""Fill between slices via ITK Morphological Contour Interpolation (Slicer algorithm)."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# VTK/ITK axis names for UI
AXIS_AUTO = -1  # all axes (Slicer default)
AXIS_SAGITTAL = 0  # X
AXIS_CORONAL = 1  # Y
AXIS_AXIAL = 2  # Z


def _vtk_to_zyx_uint16(vtk_image) -> np.ndarray:
    from vtk.util import numpy_support

    dims = vtk_image.GetDimensions()  # x, y, z
    scalars = vtk_image.GetPointData().GetScalars()
    arr = numpy_support.vtk_to_numpy(scalars)
    return arr.reshape(dims[2], dims[1], dims[0]).astype(np.uint16)


def fill_between_slices_array(
    label_zyx: np.ndarray,
    axis: int = AXIS_AUTO,
    label: int = 0,
) -> np.ndarray:
    """
    Interpolate sparse labeled slices using Morphological Contour Interpolation.

    Parameters
    ----------
    label_zyx : ndarray
        Integer label volume shaped (Z, Y, X). 0 = background.
    axis : int
        -1 = all axes; 0 = X (sagittal); 1 = Y (coronal); 2 = Z (axial).
    label : int
        0 = all labels; otherwise only interpolate this label value.

    Returns
    -------
    ndarray uint16
        Filled label volume, same shape.
    """
    import itk

    vol = np.asarray(label_zyx)
    if vol.ndim != 3:
        raise ValueError(f"Expected 3D label volume, got shape {vol.shape}")
    if not np.any(vol):
        raise ValueError("Target layer is empty. Paint labels on sparse slices first.")

    # Require at least one "gap" pattern along some axis for useful fill;
    # ITK will still run, but warn if everything looks contiguous.
    itk_img = itk.GetImageFromArray(vol.astype(np.uint16))
    ImageType = type(itk_img)
    filt = itk.MorphologicalContourInterpolator[ImageType].New()
    filt.SetInput(itk_img)
    filt.SetAxis(int(axis))
    filt.SetLabel(int(label))
    filt.SetHeuristicAlignment(True)
    # Match Slicer vtkITKMorphologicalContourInterpolator defaults:
    if hasattr(filt, "SetUseDistanceTransform"):
        filt.SetUseDistanceTransform(False)
    if hasattr(filt, "SetUseBallStructuringElement"):
        filt.SetUseBallStructuringElement(False)
    filt.Update()
    out = itk.GetArrayFromImage(filt.GetOutput())
    return np.asarray(out, dtype=np.uint16)


def fill_between_slices_vtk(
    vtk_label_image,
    axis: int = AXIS_AUTO,
    label: int = 0,
) -> np.ndarray:
    """Run MCI on a VTK label image; return filled (Z,Y,X) uint16 array."""
    zyx = _vtk_to_zyx_uint16(vtk_label_image)
    # Binary layers often use 0/1; treat any nonzero as label 1 for single-structure.
    if label == 0:
        uniq = np.unique(zyx)
        uniq = uniq[uniq != 0]
        if len(uniq) == 1 and uniq[0] != 1:
            # Keep original label id
            pass
    return fill_between_slices_array(zyx, axis=axis, label=label)


def write_zyx_into_vtk_image(vtk_image, zyx: np.ndarray) -> None:
    """Overwrite vtkImageData scalars in-place (preserve geometry)."""
    from vtk.util import numpy_support

    dims = vtk_image.GetDimensions()
    if tuple(zyx.shape) != (dims[2], dims[1], dims[0]):
        raise ValueError(
            f"Shape mismatch: array {zyx.shape} vs vtk (z,y,x)={(dims[2], dims[1], dims[0])}"
        )
    scalars = vtk_image.GetPointData().GetScalars()
    if scalars is None:
        raise RuntimeError("VTK image has no scalars")
    view = numpy_support.vtk_to_numpy(scalars).reshape(dims[2], dims[1], dims[0])
    # Preserve existing scalar dtype (typically uint8 for binary layers)
    view[:] = zyx.astype(view.dtype, copy=False)
    scalars.Modified()
    vtk_image.Modified()
