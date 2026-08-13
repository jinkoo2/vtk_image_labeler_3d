"""Fill between slices via ITK Morphological Contour Interpolation (Slicer algorithm)."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# ITK axis indices after itk.GetImageFromArray(zyx):
#   dim0 = Z (axial), dim1 = Y (coronal), dim2 = X (sagittal)
AXIS_AUTO = -1  # all axes (Slicer default)
AXIS_AXIAL = 0  # Z
AXIS_CORONAL = 1  # Y
AXIS_SAGITTAL = 2  # X


def _vtk_to_zyx_uint16(vtk_image) -> np.ndarray:
    from vtk.util import numpy_support

    if vtk_image is None:
        raise ValueError("VTK image is None")

    dims = vtk_image.GetDimensions()  # x, y, z
    if any(int(d) <= 0 for d in dims):
        raise ValueError(f"Invalid VTK dimensions: {dims}")

    scalars = vtk_image.GetPointData().GetScalars()
    if scalars is None:
        raise ValueError("Target layer has no scalar data to interpolate.")

    arr = numpy_support.vtk_to_numpy(scalars)
    expected = int(dims[0]) * int(dims[1]) * int(dims[2])
    if arr.size < expected:
        raise ValueError(
            f"Scalar size {arr.size} does not match image dimensions {dims} "
            f"(expected at least {expected} values)."
        )
    # Drop extra components if present (use first component only).
    if arr.ndim > 1:
        arr = arr.reshape(-1, arr.shape[-1])[:, 0]
    arr = np.asarray(arr).reshape(-1)[:expected]
    return arr.reshape(dims[2], dims[1], dims[0]).astype(np.uint16, copy=False)


def _count_labeled_slices(vol: np.ndarray, axis: int) -> int:
    """Number of slices along axis that contain any nonzero label."""
    if axis < 0:
        # Auto: report max across axes for messaging.
        return max(_count_labeled_slices(vol, a) for a in (0, 1, 2))
    axes = tuple(i for i in range(3) if i != axis)
    labeled = np.any(vol != 0, axis=axes)
    return int(np.count_nonzero(labeled))


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
        -1 = all axes; 0 = Z (axial); 1 = Y (coronal); 2 = X (sagittal).
    label : int
        0 = all labels; otherwise only interpolate this label value.

    Returns
    -------
    ndarray uint16
        Filled label volume, same shape.
    """
    try:
        import itk
    except ImportError as exc:
        raise RuntimeError(
            "ITK is not available. Install itk-morphologicalcontourinterpolation."
        ) from exc

    # Ensure the remote module is loaded (PyInstaller / lazy factories).
    try:
        _ = itk.MorphologicalContourInterpolator
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Morphological Contour Interpolator is not available. "
            "Install/upgrade package itk-morphologicalcontourinterpolation."
        ) from exc

    vol = np.ascontiguousarray(np.asarray(label_zyx))
    if vol.ndim != 3:
        raise ValueError(f"Expected 3D label volume, got shape {vol.shape}")
    if not np.any(vol):
        raise ValueError("Target layer is empty. Paint labels on sparse slices first.")

    axis = int(axis)
    if axis not in (-1, 0, 1, 2):
        raise ValueError(f"Invalid axis {axis}. Use -1, 0, 1, or 2.")

    # For a single-axis request, require >=2 labeled slices along that axis.
    if axis >= 0 and _count_labeled_slices(vol, axis) < 2:
        raise ValueError(
            "Need labels on at least two slices along the selected axis "
            "before fill-between-slices can run."
        )
    if axis < 0 and max(_count_labeled_slices(vol, a) for a in (0, 1, 2)) < 2:
        raise ValueError(
            "Need labels on at least two slices (on some axis) "
            "before fill-between-slices can run."
        )

    itk_img = itk.GetImageFromArray(vol.astype(np.uint16, copy=False))
    ImageType = type(itk_img)
    try:
        filt = itk.MorphologicalContourInterpolator[ImageType].New()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Could not create MorphologicalContourInterpolator: {exc}"
        ) from exc

    filt.SetInput(itk_img)
    filt.SetAxis(axis)
    filt.SetLabel(int(label))
    filt.SetHeuristicAlignment(True)
    # Match Slicer vtkITKMorphologicalContourInterpolator defaults:
    if hasattr(filt, "SetUseDistanceTransform"):
        filt.SetUseDistanceTransform(False)
    if hasattr(filt, "SetUseBallStructuringElement"):
        filt.SetUseBallStructuringElement(False)
    try:
        filt.Update()
    except Exception as exc:  # noqa: BLE001
        logger.exception("MorphologicalContourInterpolator.Update failed")
        raise RuntimeError(
            "Interpolation failed inside ITK. Try another axis, or paint "
            f"clearer contours on more slices. Details: {exc}"
        ) from exc

    out = itk.GetArrayFromImage(filt.GetOutput())
    return np.ascontiguousarray(out, dtype=np.uint16)


def fill_between_slices_vtk(
    vtk_label_image,
    axis: int = AXIS_AUTO,
    label: int = 0,
) -> np.ndarray:
    """Run MCI on a VTK label image; return filled (Z,Y,X) uint16 array."""
    zyx = _vtk_to_zyx_uint16(vtk_label_image)
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
    view = numpy_support.vtk_to_numpy(scalars)
    expected = int(dims[0]) * int(dims[1]) * int(dims[2])
    if view.size < expected:
        raise RuntimeError(
            f"Cannot write interpolated labels: scalar buffer too small ({view.size} < {expected})"
        )
    if view.ndim > 1:
        # Multi-component: write into first component only.
        shaped = view.reshape(dims[2], dims[1], dims[0], -1)
        shaped[..., 0] = zyx.astype(shaped.dtype, copy=False)
    else:
        shaped = view.reshape(dims[2], dims[1], dims[0])
        shaped[:] = zyx.astype(shaped.dtype, copy=False)
    scalars.Modified()
    vtk_image.Modified()
