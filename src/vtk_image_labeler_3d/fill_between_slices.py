"""Fill between slices via ITK Morphological Contour Interpolation (Slicer algorithm)."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Numpy axes for volumes shaped (z, y, x):
#   0 = Z (axial), 1 = Y (coronal), 2 = X (sagittal)
# itk.GetImageFromArray reverses to ITK axes: 0 = X, 1 = Y, 2 = Z
AXIS_AUTO = -1  # all axes (Slicer default)
AXIS_AXIAL = 0  # Z (numpy)
AXIS_CORONAL = 1  # Y (numpy)
AXIS_SAGITTAL = 2  # X (numpy)

AXIS_NAMES = {
    AXIS_AUTO: "Auto (all axes)",
    AXIS_AXIAL: "Axial (Z)",
    AXIS_CORONAL: "Coronal (Y)",
    AXIS_SAGITTAL: "Sagittal (X)",
}

def _numpy_axis_to_itk(axis: int) -> int:
    """Map (z,y,x) numpy axis to ITK axis after GetImageFromArray."""
    if axis < 0:
        return -1
    return 2 - int(axis)  # Z0->2, Y1->1, X2->0





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
    if arr.ndim > 1:
        arr = arr.reshape(-1, arr.shape[-1])[:, 0]
    arr = np.asarray(arr).reshape(-1)[:expected]
    return arr.reshape(dims[2], dims[1], dims[0]).astype(np.uint16, copy=False)


def _labeled_slice_mask(vol: np.ndarray, axis: int) -> np.ndarray:
    other = tuple(i for i in range(3) if i != axis)
    return np.any(vol != 0, axis=other)


def _count_labeled_slices(vol: np.ndarray, axis: int) -> int:
    """Number of slices along axis that contain any nonzero label."""
    if axis < 0:
        return max(_count_labeled_slices(vol, a) for a in (0, 1, 2))
    return int(np.count_nonzero(_labeled_slice_mask(vol, axis)))


def _has_gaps_along_axis(vol: np.ndarray, axis: int) -> bool:
    """True if labeled slices along axis have empty slices between first and last."""
    if axis < 0:
        return any(_has_gaps_along_axis(vol, a) for a in (0, 1, 2))
    labeled = _labeled_slice_mask(vol, axis)
    idxs = np.flatnonzero(labeled)
    if idxs.size < 2:
        return False
    span = int(idxs[-1] - idxs[0] + 1)
    return span > int(idxs.size)


def _suggest_axes_with_gaps(vol: np.ndarray) -> list[int]:
    return [a for a in (0, 1, 2) if _has_gaps_along_axis(vol, a)]


def fill_between_slices_array(
    label_zyx: np.ndarray,
    axis: int = AXIS_AUTO,
    label: int = 0,
) -> tuple[np.ndarray, dict]:
    """
    Interpolate sparse labeled slices using Morphological Contour Interpolation.

    Returns
    -------
    filled : ndarray uint16
    info : dict
        Diagnostics (voxel counts, suggested axes, etc.).
    """
    try:
        import itk
    except ImportError as exc:
        raise RuntimeError(
            "ITK is not available. Install itk-morphologicalcontourinterpolation."
        ) from exc

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

    suggested = _suggest_axes_with_gaps(vol)

    if axis >= 0 and _count_labeled_slices(vol, axis) < 2:
        hint = ""
        if suggested:
            names = ", ".join(AXIS_NAMES[a] for a in suggested)
            hint = f" Your labels look sparse along: {names}."
        raise ValueError(
            "Need labels on at least two slices along the selected axis "
            f"({AXIS_NAMES.get(axis, axis)}) before fill-between-slices can run."
            + hint
        )
    if axis < 0 and max(_count_labeled_slices(vol, a) for a in (0, 1, 2)) < 2:
        raise ValueError(
            "Need labels on at least two slices (on some axis) "
            "before fill-between-slices can run."
        )

    # If a specific axis has no empty slices between labels, MCI will do nothing.
    if axis >= 0 and not _has_gaps_along_axis(vol, axis):
        hint = ""
        if suggested:
            names = ", ".join(AXIS_NAMES[a] for a in suggested)
            hint = (
                f" Try {names}. "
                "Tip: choose the same view you painted in (Sagittal view -> Sagittal (X), etc.)."
            )
        elif _count_labeled_slices(vol, axis) >= 2:
            hint = (
                " Labeled slices along this axis are contiguous (no empty slices "
                "between them), so there is nothing to fill."
            )
        raise ValueError(
            f"No empty slices to fill along {AXIS_NAMES.get(axis, axis)}."
            + hint
        )

    before_fg = int(np.count_nonzero(vol))

    itk_img = itk.GetImageFromArray(vol.astype(np.uint16, copy=False))
    ImageType = type(itk_img)
    try:
        filt = itk.MorphologicalContourInterpolator[ImageType].New()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Could not create MorphologicalContourInterpolator: {exc}"
        ) from exc

    itk_axis = _numpy_axis_to_itk(axis)
    filt.SetInput(itk_img)
    filt.SetAxis(itk_axis)
    filt.SetLabel(int(label))
    filt.SetHeuristicAlignment(True)
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

    out = np.ascontiguousarray(itk.GetArrayFromImage(filt.GetOutput()), dtype=np.uint16)
    after_fg = int(np.count_nonzero(out))
    info = {
        "axis": axis,
        "itk_axis": itk_axis,
        "axis_name": AXIS_NAMES.get(axis, str(axis)),
        "foreground_before": before_fg,
        "foreground_after": after_fg,
        "voxels_added": max(0, after_fg - before_fg),
        "suggested_axes": suggested,
    }
    if after_fg <= before_fg:
        hint = ""
        if suggested:
            names = ", ".join(AXIS_NAMES[a] for a in suggested)
            hint = f" Try axis: {names}."
        raise ValueError(
            "Interpolation produced no new voxels along "
            f"{info['axis_name']}.{hint} "
            "Paint complete contours on sparse slices in one view, then choose "
            "that same axis (Axial if you scrolled Z, etc.)."
        )
    return out, info


def fill_between_slices_vtk(
    vtk_label_image,
    axis: int = AXIS_AUTO,
    label: int = 0,
):
    """Run MCI on a VTK label image; return (filled zyx uint16, info)."""
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
        shaped = view.reshape(dims[2], dims[1], dims[0], -1)
        shaped[..., 0] = zyx.astype(shaped.dtype, copy=False)
    else:
        shaped = view.reshape(dims[2], dims[1], dims[0])
        shaped[:] = zyx.astype(shaped.dtype, copy=False)
    scalars.Modified()
    vtk_image.Modified()
