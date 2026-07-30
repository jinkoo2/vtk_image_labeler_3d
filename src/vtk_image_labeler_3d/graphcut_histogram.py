"""Histogram + GraphCut interactive segmentation (MONAI Label Scribble algorithm).

Ported from monailabel.scribbles.utils (Histogram+GraphCut / Wang et al. TMI 2018).
GraphCut uses PyMaxflow with the same energy as numpymaxflow (unary=-log(p),
pairwise=lambda*exp(-d^2/(2*sigma^2))).
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

SCRIBBLE_BG_LABEL = 2
SCRIBBLE_FG_LABEL = 3


def _get_eps(data: np.ndarray) -> float:
    return float(np.finfo(data.dtype).eps)


def _ensure_channel_first(arr: np.ndarray) -> np.ndarray:
    if arr.ndim < 3:
        raise ValueError(f"Expected at least 3D array, got shape {arr.shape}")
    if arr.ndim == 3:
        return arr[np.newaxis, ...]
    return arr


def _softmax(data: np.ndarray, axis: int = 0) -> np.ndarray:
    shifted = data - np.max(data, axis=axis, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=axis, keepdims=True)


def maxflow(image: np.ndarray, prob: np.ndarray, lamda: float = 1.0, sigma: float = 0.1) -> np.ndarray:
    """
    Binary GraphCut matching numpymaxflow.maxflow(image, prob, lamda, sigma).

    image: [1, ...] float intensities
    prob:  [2, ...] BG/FG probabilities
    returns: [1, ...] float labels (1=FG/source-set, 0=BG)
    """
    try:
        import maxflow as mf
    except ImportError as e:
        raise ImportError(
            "PyMaxflow is required for the Scribble Tool. Install with: pip install PyMaxflow"
        ) from e

    image = np.asarray(image, dtype=np.float32)
    prob = np.asarray(prob, dtype=np.float32)
    if image.ndim != prob.ndim:
        raise ValueError(f"image/prob ndim mismatch: {image.shape} vs {prob.shape}")
    if prob.shape[0] != 2:
        raise ValueError(f"prob must have 2 channels (BG, FG), got {prob.shape[0]}")
    if list(image.shape[1:]) != list(prob.shape[1:]):
        raise ValueError(f"spatial shape mismatch: {image.shape} vs {prob.shape}")

    spatial = image.shape[1:]
    img = image[0]

    g = mf.Graph[float]()
    nodeids = g.add_grid_nodes(spatial)

    eps = np.finfo(np.float32).eps
    p_bg = np.maximum(prob[0], eps)
    p_fg = np.maximum(prob[1], eps)
    # Same as numpymaxflow: source_cap=-log(bg), sink_cap=-log(fg);
    # source set is labeled FG (1).
    g.add_grid_tedges(nodeids, -np.log(p_bg), -np.log(p_fg))

    sigma = max(float(sigma), 1e-8)
    lamda = float(lamda)

    # 6-connected (3D) / 4-connected (2D) contrast-sensitive n-links
    axes = list(range(img.ndim))
    for axis in axes:
        sl_p = [slice(None)] * img.ndim
        sl_q = [slice(None)] * img.ndim
        sl_p[axis] = slice(1, None)
        sl_q[axis] = slice(0, -1)
        diff = np.abs(img[tuple(sl_p)] - img[tuple(sl_q)])
        weights = lamda * np.exp(-(diff * diff) / (2.0 * sigma * sigma))

        structure = np.zeros((3,) * img.ndim, dtype=np.int8)
        center = tuple(1 for _ in axes)
        offset = [1] * img.ndim
        offset[axis] = 0  # neighbor toward -axis from the + side node
        # Use add_grid_edges with a structure selecting one neighbor direction.
        structure[center] = 0
        neighbor = list(center)
        neighbor[axis] = 0  # -1 along this axis in 3x3x3 structure
        structure[tuple(neighbor)] = 1

        # Weights array must broadcast to nodeids; pad to full grid shape.
        full_w = np.zeros(spatial, dtype=np.float64)
        full_w[tuple(sl_p)] = weights
        g.add_grid_edges(nodeids, full_w, structure=structure, symmetric=True)

    g.maxflow()
    # get_grid_segments: True => sink segment. Source set => FG label 1.
    sink = g.get_grid_segments(nodeids)
    label = (~sink).astype(np.float32)
    return label[np.newaxis, ...]


def make_iseg_unary(
    prob: np.ndarray,
    scribbles: np.ndarray,
    scribbles_bg_label: int = SCRIBBLE_BG_LABEL,
    scribbles_fg_label: int = SCRIBBLE_FG_LABEL,
) -> np.ndarray:
    prob = np.asarray(prob)
    scribbles = _ensure_channel_first(np.asarray(scribbles))

    if scribbles.shape[0] != 1:
        raise ValueError(f"scribbles should have single channel first, received {scribbles.shape[0]}")
    if list(prob.shape[1:]) != list(scribbles.shape[1:]):
        raise ValueError(f"shapes for prob and scribbles dont match: {prob.shape} vs {scribbles.shape}")

    if prob.shape[0] == 1:
        prob = np.concatenate([prob, 1.0 - prob], axis=0)

    mask = np.concatenate(
        [scribbles == scribbles_bg_label, scribbles == scribbles_fg_label],
        axis=0,
    )

    if not np.any(mask[0, ...]):
        logger.info(
            "warning: no background scribbles received with label %s (unique=%s)",
            scribbles_bg_label,
            np.unique(scribbles),
        )
    if not np.any(mask[1, ...]):
        logger.info(
            "warning: no foreground scribbles received with label %s (unique=%s)",
            scribbles_fg_label,
            np.unique(scribbles),
        )

    unary_term = np.copy(prob)
    eps = _get_eps(unary_term)
    unary_term[mask] = 1.0 - eps
    unary_term[np.flip(mask, axis=0)] = eps
    return unary_term


def make_histograms(
    image: np.ndarray,
    scrib: np.ndarray,
    scribbles_bg_label: int,
    scribbles_fg_label: int,
    alpha_bg=1,
    alpha_fg=1,
    bins: int = 32,
):
    def expand_pseudocounts(alpha):
        if not isinstance(alpha, list):
            alpha = [alpha] * bins
        elif len(alpha) != bins:
            raise ValueError(
                f"pseudo-counts size does not match number of bins: {len(alpha)} vs {bins}"
            )
        return np.array(alpha)

    alpha_bg = expand_pseudocounts(alpha_bg)
    alpha_fg = expand_pseudocounts(alpha_fg)

    bg_vals = image[scrib == scribbles_bg_label]
    fg_vals = image[scrib == scribbles_fg_label]

    bg_hist, _ = np.histogram(bg_vals, bins=bins, range=(0, 1), density=False)
    fg_hist, fg_bin_edges = np.histogram(fg_vals, bins=bins, range=(0, 1), density=False)

    bg_hist = bg_hist + alpha_bg
    fg_hist = fg_hist + alpha_fg
    bg_hist = bg_hist / np.sum(bg_hist)
    fg_hist = fg_hist / np.sum(fg_hist)

    return bg_hist.astype(np.float32), fg_hist.astype(np.float32), fg_bin_edges.astype(np.float32)


def make_likelihood_image_histogram(
    image: np.ndarray,
    scrib: np.ndarray,
    scribbles_bg_label: int = SCRIBBLE_BG_LABEL,
    scribbles_fg_label: int = SCRIBBLE_FG_LABEL,
    num_bins: int = 64,
    return_label: bool = False,
) -> np.ndarray:
    image = np.asarray(image, dtype=np.float32)
    scrib = np.asarray(scrib)

    image_cf = _ensure_channel_first(image)
    scrib_cf = _ensure_channel_first(scrib)

    img = image_cf[0]
    scrib_mask = scrib_cf[0]

    min_img = float(np.min(img))
    max_img = float(np.max(img))
    if min_img < 0.0 or max_img > 1.0:
        img = (img - min_img) / (max_img - min_img + 1e-8)

    bg_hist, fg_hist, bin_edges = make_histograms(
        img,
        scrib_mask,
        scribbles_bg_label,
        scribbles_fg_label,
        alpha_bg=1,
        alpha_fg=1,
        bins=num_bins,
    )

    dimage = np.digitize(img, bin_edges[:-1]) - 1
    dimage = np.clip(dimage, 0, num_bins - 1)
    bprob = bg_hist[dimage][np.newaxis, ...]
    fprob = fg_hist[dimage][np.newaxis, ...]
    retprob = np.concatenate([bprob, fprob], axis=0).astype(np.float32)

    if not np.allclose(np.sum(retprob, axis=0), 1.0):
        retprob = _softmax(retprob, axis=0).astype(np.float32)

    if return_label:
        return np.expand_dims(np.argmax(retprob, axis=0), axis=0).astype(np.float32)
    return retprob


def histogram_graphcut(
    image: np.ndarray,
    scribbles: np.ndarray,
    scribbles_bg_label: int = SCRIBBLE_BG_LABEL,
    scribbles_fg_label: int = SCRIBBLE_FG_LABEL,
    num_bins: int = 64,
    lamda: float = 1.0,
    sigma: float = 0.1,
) -> np.ndarray:
    """
    Full Histogram+GraphCut pipeline.

    Returns binary mask (Z,Y,X) with 1=foreground, 0=background.
    """
    image_cf = _ensure_channel_first(np.asarray(image, dtype=np.float32))
    scrib_cf = _ensure_channel_first(np.asarray(scribbles))

    has_fg = np.any(scrib_cf == scribbles_fg_label)
    has_bg = np.any(scrib_cf == scribbles_bg_label)
    if not has_fg:
        raise ValueError("Draw at least one Foreground scribble before running.")
    if not has_bg:
        raise ValueError("Draw at least one Background scribble before running.")

    pairwise = image_cf.astype(np.float32).copy()
    pmin, pmax = float(pairwise.min()), float(pairwise.max())
    if pmin < 0.0 or pmax > 1.0:
        pairwise = (pairwise - pmin) / (pmax - pmin + 1e-8)

    prob = make_likelihood_image_histogram(
        pairwise,
        scrib_cf,
        scribbles_bg_label=scribbles_bg_label,
        scribbles_fg_label=scribbles_fg_label,
        num_bins=num_bins,
        return_label=False,
    )
    unary = make_iseg_unary(
        prob,
        scrib_cf,
        scribbles_bg_label=scribbles_bg_label,
        scribbles_fg_label=scribbles_fg_label,
    )

    pred = maxflow(pairwise, unary, lamda=lamda, sigma=sigma)
    pred = np.asarray(pred)
    if pred.ndim == image_cf.ndim and pred.shape[0] == 1:
        pred = pred[0]
    elif pred.ndim == image_cf.ndim and pred.shape[0] > 1:
        pred = np.argmax(pred, axis=0)

    return (pred > 0).astype(np.uint8)


def _resample_zyx(arr, spacing_xyz, out_spacing_xyz, is_label=False):
    """Resample (Z,Y,X) array with SimpleITK. spacing_xyz is (sx,sy,sz)."""
    import SimpleITK as sitk

    img = sitk.GetImageFromArray(arr)  # sits as z,y,x
    img.SetSpacing(tuple(float(s) for s in spacing_xyz))
    original_size = np.array(img.GetSize(), dtype=np.float64)
    original_spacing = np.array(img.GetSpacing(), dtype=np.float64)
    out_spacing = np.array(out_spacing_xyz, dtype=np.float64)
    out_size = np.maximum(1, np.round(original_size * original_spacing / out_spacing)).astype(int)

    rf = sitk.ResampleImageFilter()
    rf.SetOutputSpacing(tuple(out_spacing.tolist()))
    rf.SetSize([int(x) for x in out_size.tolist()])
    rf.SetOutputOrigin(img.GetOrigin())
    rf.SetOutputDirection(img.GetDirection())
    rf.SetTransform(sitk.Transform())
    rf.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    rf.SetDefaultPixelValue(0)
    return sitk.GetArrayFromImage(rf.Execute(img))


def vtk_arrays_histogram_graphcut(
    base_vtk_image,
    fg_scribble_vtk,
    bg_scribble_vtk,
    num_bins: int = 64,
    lamda: float = 1.0,
    sigma: float = 0.1,
    working_spacing=(2.5, 2.5, 5.0),
    max_voxels: int = 8_000_000,
):
    """Run Histogram+GraphCut from VTK images; return a new VTK uchar FG mask.

    Optionally downsamples to working_spacing (MONAI Label default) when the
    volume exceeds max_voxels, then upsamples the result with nearest-neighbor.
    """
    from vtk.util import numpy_support

    import vtk_tools

    def _vtk_to_zyx(vtk_image) -> np.ndarray:
        dims = vtk_image.GetDimensions()  # (x, y, z)
        scalars = vtk_image.GetPointData().GetScalars()
        arr = numpy_support.vtk_to_numpy(scalars)
        return arr.reshape(dims[2], dims[1], dims[0])

    image_zyx = _vtk_to_zyx(base_vtk_image).astype(np.float32)
    fg_zyx = _vtk_to_zyx(fg_scribble_vtk)
    bg_zyx = _vtk_to_zyx(bg_scribble_vtk)

    scribbles = np.zeros_like(image_zyx, dtype=np.int32)
    scribbles[bg_zyx > 0] = SCRIBBLE_BG_LABEL
    scribbles[fg_zyx > 0] = SCRIBBLE_FG_LABEL

    spacing = tuple(float(s) for s in base_vtk_image.GetSpacing())  # x,y,z
    work_img = image_zyx
    work_scrib = scribbles
    do_resample = image_zyx.size > max_voxels and working_spacing is not None
    if do_resample:
        logger.info(
            "Scribble GraphCut: downsampling %s voxels to spacing %s",
            image_zyx.size,
            working_spacing,
        )
        work_img = _resample_zyx(
            image_zyx, spacing, working_spacing, is_label=False
        ).astype(np.float32)
        work_scrib = _resample_zyx(
            scribbles, spacing, working_spacing, is_label=True
        ).astype(np.int32)

    pred_work = histogram_graphcut(
        work_img,
        work_scrib,
        num_bins=num_bins,
        lamda=lamda,
        sigma=sigma,
    )

    if do_resample:
        pred_zyx = _resample_zyx(
            pred_work, working_spacing, spacing, is_label=True
        ).astype(np.uint8)
        if pred_zyx.shape != image_zyx.shape:
            from skimage.transform import resize

            pred_zyx = resize(
                pred_zyx.astype(np.float32),
                image_zyx.shape,
                order=0,
                preserve_range=True,
                anti_aliasing=False,
            ).astype(np.uint8)
    else:
        pred_zyx = pred_work

    out = vtk_tools.create_uchar_image_based_on_image(base_vtk_image, 0)
    out_scalars = out.GetPointData().GetScalars()
    out_np = numpy_support.vtk_to_numpy(out_scalars)
    dims = out.GetDimensions()
    out_view = out_np.reshape(dims[2], dims[1], dims[0])
    out_view[:] = pred_zyx
    out.GetPointData().GetScalars().Modified()
    out.Modified()
    return out
