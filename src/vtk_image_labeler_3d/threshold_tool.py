"""Threshold the base image into a binary segmentation layer."""

from __future__ import annotations

import numpy as np


def scalar_range_of_vtk_image(vtk_image) -> tuple[float, float]:
    if vtk_image is None:
        raise ValueError("VTK image is None")
    scalars = vtk_image.GetPointData().GetScalars()
    if scalars is None:
        raise ValueError("VTK image has no scalars")
    r = scalars.GetRange()
    return float(r[0]), float(r[1])


def _vtk_scalars_as_xyz_flat(vtk_image) -> tuple[np.ndarray, tuple[int, int, int]]:
    from vtk.util import numpy_support

    dims = vtk_image.GetDimensions()  # x, y, z
    scalars = vtk_image.GetPointData().GetScalars()
    if scalars is None:
        raise ValueError("VTK image has no scalars")
    arr = numpy_support.vtk_to_numpy(scalars)
    expected = int(dims[0]) * int(dims[1]) * int(dims[2])
    if arr.ndim > 1:
        arr = arr.reshape(-1, arr.shape[-1])[:, 0]
    arr = np.asarray(arr).reshape(-1)[:expected]
    if arr.size != expected:
        raise ValueError(
            f"Scalar size {arr.size} does not match dimensions {dims} (expected {expected})"
        )
    return arr, (int(dims[0]), int(dims[1]), int(dims[2]))


def apply_threshold_to_layer(
    base_vtk_image,
    target_vtk_image,
    lower: float,
    upper: float,
    foreground: int = 1,
    background: int = 0,
) -> int:
    """
    Write a binary mask into target_vtk_image from base_vtk_image intensities.

    Voxels with lower <= intensity <= upper become ``foreground``, else ``background``.
    Returns the number of foreground voxels written.
    """
    if lower > upper:
        lower, upper = upper, lower

    base_flat, base_dims = _vtk_scalars_as_xyz_flat(base_vtk_image)
    tgt_flat, tgt_dims = _vtk_scalars_as_xyz_flat(target_vtk_image)
    if base_dims != tgt_dims:
        raise ValueError(
            f"Base and target dimensions differ: {base_dims} vs {tgt_dims}"
        )

    mask = (base_flat >= float(lower)) & (base_flat <= float(upper))
    from vtk.util import numpy_support

    scalars = target_vtk_image.GetPointData().GetScalars()
    view = numpy_support.vtk_to_numpy(scalars)
    expected = tgt_flat.size
    if view.ndim > 1:
        shaped = view.reshape(expected, -1)
        out = np.where(mask, foreground, background).astype(shaped.dtype, copy=False)
        shaped[:, 0] = out
    else:
        view = view.reshape(-1)[:expected]
        view[:] = np.where(mask, foreground, background).astype(view.dtype, copy=False)

    scalars.Modified()
    target_vtk_image.Modified()
    return int(np.count_nonzero(mask))
