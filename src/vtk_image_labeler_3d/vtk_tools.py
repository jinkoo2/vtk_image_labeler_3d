import vtk
import numpy as np


def create_image_outline_polydata(vtk_image):
    """Build a wireframe box of the image volume in world coordinates.

    ``vtkOutlineFilter`` uses axis-aligned bounds and historically ignored
    ``vtkImageData`` direction matrices, so NIfTI-style flips/rotations made
    the 3D outline disagree with the resliced slices. This builds the 12 edges
    from the eight index-extent corners transformed by origin/spacing/direction.
    """
    if vtk_image is None:
        raise ValueError("vtk_image is required")

    dims = vtk_image.GetDimensions()
    spacing = np.asarray(vtk_image.GetSpacing(), dtype=float)
    origin = np.asarray(vtk_image.GetOrigin(), dtype=float)

    direction = np.eye(3)
    if hasattr(vtk_image, "GetDirectionMatrix"):
        mat = vtk_image.GetDirectionMatrix()
        if mat is not None:
            direction = np.array(
                [[mat.GetElement(i, j) for j in range(3)] for i in range(3)],
                dtype=float,
            )

    # Corner voxel indices of the extent (matches vtkImageData bounds corners).
    i_vals = (0, max(dims[0] - 1, 0))
    j_vals = (0, max(dims[1] - 1, 0))
    k_vals = (0, max(dims[2] - 1, 0))
    corners = []
    for k in k_vals:
        for j in j_vals:
            for i in i_vals:
                index_offset = np.array(
                    [i * spacing[0], j * spacing[1], k * spacing[2]], dtype=float
                )
                corners.append(origin + direction @ index_offset)

    # Binary corner order: bit0=i, bit1=j, bit2=k  -> edges along each axis.
    edges = (
        (0, 1), (2, 3), (4, 5), (6, 7),  # i
        (0, 2), (1, 3), (4, 6), (5, 7),  # j
        (0, 4), (1, 5), (2, 6), (3, 7),  # k
    )

    points = vtk.vtkPoints()
    for c in corners:
        points.InsertNextPoint(float(c[0]), float(c[1]), float(c[2]))

    lines = vtk.vtkCellArray()
    for a, b in edges:
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, a)
        line.GetPointIds().SetId(1, b)
        lines.InsertNextCell(line)

    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetLines(lines)
    return poly


def create_oriented_image_slice(input_connection=None, input_data=None):
    """Build a ``vtkImageSlice`` that respects DirectionMatrix.

    ``vtkImageActor`` ignores direction cosines (and a UserMatrix workaround
    collapses oriented coronal/sagittal planes to zero thickness). Prefer
    ``vtkImageSlice`` + ``vtkImageSliceMapper`` for oriented medical slices.
    """
    mapper = vtk.vtkImageSliceMapper()
    if input_connection is not None:
        mapper.SetInputConnection(input_connection)
    elif input_data is not None:
        mapper.SetInputData(input_data)
    prop = vtk.vtkImageSlice()
    prop.SetMapper(mapper)
    return prop


def dicom_lps_screen_labels(camera):
    """Map camera screen edges to DICOM LPS letters (R/L, A/P, I/S).

    Patient axes in world coordinates (DICOM LPS):
      +X = Left (L),  -X = Right (R)
      +Y = Posterior (P), -Y = Anterior (A)
      +Z = Superior (S), -Z = Inferior (I)
    """
    pos = np.asarray(camera.GetPosition(), dtype=float)
    focal = np.asarray(camera.GetFocalPoint(), dtype=float)
    view_up = np.asarray(camera.GetViewUp(), dtype=float)

    # VTK view-plane normal points from focal point toward the camera.
    vpn = pos - focal
    vpn_norm = np.linalg.norm(vpn)
    up_norm = np.linalg.norm(view_up)
    if vpn_norm < 1e-12 or up_norm < 1e-12:
        return {"left": "", "right": "", "top": "", "bottom": ""}

    vpn = vpn / vpn_norm
    view_up = view_up / up_norm
    # Screen-right in VTK display space is ViewUp × ViewPlaneNormal
    # (not VPN × ViewUp, which points screen-left).
    view_right = np.cross(view_up, vpn)
    right_norm = np.linalg.norm(view_right)
    if right_norm < 1e-12:
        return {"left": "", "right": "", "top": "", "bottom": ""}
    view_right = view_right / right_norm

    return dicom_lps_letters_for_screen_axes(view_right, view_up)


def dicom_lps_letters_for_screen_axes(view_right, view_up):
    """Map world-space screen-right / screen-up vectors to LPS edge letters."""
    view_right = np.asarray(view_right, dtype=float)
    view_up = np.asarray(view_up, dtype=float)
    axis_letters = (("R", "L"), ("A", "P"), ("I", "S"))

    def letter_for(direction):
        abs_components = np.abs(direction)
        axis = int(np.argmax(abs_components))
        if abs_components[axis] < 1e-6:
            return ""
        neg, pos = axis_letters[axis]
        return pos if direction[axis] >= 0.0 else neg

    return {
        "right": letter_for(view_right),
        "left": letter_for(-view_right),
        "top": letter_for(view_up),
        "bottom": letter_for(-view_up),
    }


def dicom_lps_labels_from_slice_world(w_H_sliceo, flip_ud=False, flip_lr=False):
    """LPS edge letters for the oriented slice camera used by the 2D viewers.

    Camera convention before flips: look along +sliceZ (``R[:,2]``) with
    ViewUp = -sliceY (``-R[:,1]``). Screen-right is ViewUp × VPN. Using
    ``R @ (-1,0,0)`` for screen-right is wrong when ``det(R) < 0`` (e.g.
    NIfTI ``diag(1,-1,1)``), which swapped L/R on Dataset510.
    """
    w_R = np.asarray(w_H_sliceo, dtype=float)[:3, :3]
    view_up = -w_R[:, 1]
    vpn = w_R[:, 2]
    if flip_ud:
        view_up = -view_up
    if flip_lr:
        vpn = -vpn
    view_right = np.cross(view_up, vpn)
    return dicom_lps_letters_for_screen_axes(view_right, view_up)


def choose_dicom_display_flips(w_H_sliceo):
    """Pick in-plane flips for radiologic LPS viewport convention.

    Target (identity LPS and oriented volumes via flips):
      - top in {A, S}
      - right in {L, A}  → axial/coronal: R on screen-left; sagittal: A on screen-right
    """
    for flip_ud in (False, True):
        for flip_lr in (False, True):
            labels = dicom_lps_labels_from_slice_world(
                w_H_sliceo, flip_ud=flip_ud, flip_lr=flip_lr
            )
            if labels.get("top") in ("A", "S") and labels.get("right") in ("L", "A"):
                return flip_ud, flip_lr, labels
    # Fallback: no flips
    labels = dicom_lps_labels_from_slice_world(w_H_sliceo)
    return False, False, labels


def apply_patient_axis_display_flips(
    camera, flip_lr=False, flip_ap=False, flip_si=False
):
    """Mirror 2D display about patient L/R, A/P, and/or S/I (camera only).

    For each enabled pair, flips the screen axis that currently shows that
    pair so anatomy and LPS edge letters stay consistent. Does not modify
    image voxels. No-op for a view when that pair is not on-screen (e.g.
    Flip L/R on a pure sagittal view).
    """
    if camera is None:
        return

    for enabled, pair in (
        (flip_lr, ("L", "R")),
        (flip_ap, ("A", "P")),
        (flip_si, ("S", "I")),
    ):
        if not enabled:
            continue
        labels = dicom_lps_screen_labels(camera)
        on_horizontal = labels.get("left") in pair or labels.get("right") in pair
        on_vertical = labels.get("top") in pair or labels.get("bottom") in pair
        # Horizontal: mirror through focal (reverse VPN) → swaps L/R-like edge.
        # Vertical: reverse VPN *and* ViewUp so screen-right is unchanged
        # (negating ViewUp alone also flips L/R via ViewUp × VPN).
        if on_horizontal or on_vertical:
            pos = np.asarray(camera.GetPosition(), dtype=float)
            foc = np.asarray(camera.GetFocalPoint(), dtype=float)
            camera.SetPosition(*(2.0 * foc - pos))
        if on_vertical:
            view_up = np.asarray(camera.GetViewUp(), dtype=float)
            camera.SetViewUp((-view_up).tolist())


def flatten_slice_geometry_for_display(vtk_image):
    """Force identity direction and zero origin on a 2D reslice for display.

    ``vtkImageReslice`` already samples along the oriented slice axes. Writing
    the oriented ``w_H`` back onto the output (previous behavior) double-applies
    NIfTI ``diag(-1,-1,1)`` and makes LPS edge letters disagree with anatomy.
    """
    if vtk_image is None:
        return
    identity = vtk.vtkMatrix3x3()
    identity.Identity()
    vtk_image.SetDirectionMatrix(identity)
    vtk_image.SetOrigin(0.0, 0.0, 0.0)


def apply_flattened_slice_camera(camera, vtk_image, flip_ud=False, flip_lr=False):
    """Parallel camera for a flattened (identity-geometry) 2D slice."""
    if camera is None or vtk_image is None:
        return
    dims = np.asarray(vtk_image.GetDimensions(), dtype=float)
    spacing = np.asarray(vtk_image.GetSpacing(), dtype=float)
    center = spacing * (dims / 2.0)
    dist = max(500.0, float(np.max(spacing * dims)))
    camera.SetParallelProjection(True)
    camera.SetFocalPoint(float(center[0]), float(center[1]), 0.0)
    if flip_lr:
        camera.SetPosition(float(center[0]), float(center[1]), -dist)
    else:
        camera.SetPosition(float(center[0]), float(center[1]), dist)
    if flip_ud:
        camera.SetViewUp(0.0, 1.0, 0.0)
    else:
        camera.SetViewUp(0.0, -1.0, 0.0)
    camera.SetParallelScale(float(np.max(spacing[:2] * dims[:2]) / 2.0))
    camera.SetClippingRange(0.1, dist * 3.0)


def to_vtk_color(c):
    return [c[0]/255, c[1]/255, c[2]/255]

def from_vtk_color(c):
    return [int(c[0]*255), int(c[1]*255), int(c[2]*255)]

def copy_image_origin_spacing_direction_matrix(src_img: vtk.vtkImageData, dst_img: vtk.vtkImageData):

    # Copy spacing
    spacing = src_img.GetSpacing()
    dst_img.SetSpacing(spacing)

    # Copy origin
    origin = src_img.GetOrigin()
    dst_img.SetOrigin(origin)

    # Copy direction matrix (VTK 9+)
    if hasattr(dst_img, 'SetDirectionMatrix') and hasattr(src_img, 'GetDirectionMatrix'):
        direction_matrix = src_img.GetDirectionMatrix()
        dst_img.SetDirectionMatrix(direction_matrix)
    else:
        print("Direction matrix support requires VTK 9 or higher.")

def remove_widget(widget, renderer):
    if widget:
        # Disable the widget
        widget.EnabledOff()

        # If the widget has a representation, remove associated actors
        if hasattr(widget, "GetRepresentation"):
            representation = widget.GetRepresentation()
            if hasattr(representation, "GetActors"):
                actors = vtk.vtkActorCollection()
                representation.GetActors(actors)
                actors.InitTraversal()
                for i in range(actors.GetNumberOfItems()):
                    renderer.RemoveActor(actors.GetNextActor())

        # Remove the widget from the interactor (if any)
        interactor = widget.GetInteractor()
        if interactor and hasattr(widget, "interaction_observer_id"):
            interactor.RemoveObserver(widget.interaction_observer_id)
            widget.interaction_observer_id = None

        # Free memory by deleting the widget
        del widget
        widget = None

        # Trigger re-rendering of the scene
        renderer.GetRenderWindow().Render()


def create_uchar_image_based_on_image(base_image, fill_pixel_value=0):
    
    if base_image is None:
        raise ValueError("Base image data is not loaded. Cannot create segmentation.")

    # Get properties from the base image
    dims = base_image.GetDimensions()
    spacing = base_image.GetSpacing()
    origin = base_image.GetOrigin()
    direction_matrix = base_image.GetDirectionMatrix()

    # Create a new vtkImageData object for the segmentation
    uchar_image = vtk.vtkImageData()
    uchar_image.SetDimensions(dims)
    uchar_image.SetSpacing(spacing)
    uchar_image.SetOrigin(origin)
    uchar_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)  # Single component for segmentation
    uchar_image.GetPointData().GetScalars().Fill(fill_pixel_value)  

    # Set the direction matrix 
    # SetDirectionMatrix() function is required (old versions of vtk may not have this function)
    uchar_image.SetDirectionMatrix(direction_matrix)

    #degug
    #import itkvtk
    #itkvtk.fill_square_at_center(segmentation, 100, 1)

    return uchar_image  

def deep_copy_image(image):
    # Create a new vtkImageData object and deep copy the original
    copied_image = vtk.vtkImageData()
    copied_image.DeepCopy(image)
    return copied_image


import vtk
import numpy as np
from skimage import measure
from vtk.util import numpy_support

def extract_largest_components(binary_image: vtk.vtkImageData, top_n: int = 3):
    # Step 1: Convert vtkImageData to numpy array
    dims = binary_image.GetDimensions()
    scalars = binary_image.GetPointData().GetScalars()
    np_image = numpy_support.vtk_to_numpy(scalars).reshape(dims[::-1])  # shape: (z, y, x)

    # Step 2: Label connected components
    labeled = measure.label(np_image, connectivity=1)  # 6-connectivity for 3D
    props = measure.regionprops(labeled)

    # Step 3: Sort components by size (descending)
    sorted_regions = sorted(props, key=lambda r: r.area, reverse=True)

    # Step 4: Extract top-N blobs
    result_images = []
    for i in range(min(top_n, len(sorted_regions))):
        mask = np.zeros_like(np_image, dtype=np.uint8)
        mask[labeled == sorted_regions[i].label] = 1

        # Convert mask back to vtkImageData
        flat_mask = mask.flatten(order="C")  # VTK expects flat C-style array
        vtk_array = numpy_support.numpy_to_vtk(num_array=flat_mask, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)

        blob = vtk.vtkImageData()
        blob.SetDimensions(dims)
        blob.SetSpacing(binary_image.GetSpacing())
        blob.SetOrigin(binary_image.GetOrigin())
        if hasattr(blob, "SetDirectionMatrix"):
            blob.SetDirectionMatrix(binary_image.GetDirectionMatrix())
        blob.GetPointData().SetScalars(vtk_array)

        result_images.append(blob)

    return result_images



def _copy_geometry_and_return(source_image, result_image):
    output = vtk.vtkImageData()
    output.DeepCopy(result_image)
    output.SetSpacing(source_image.GetSpacing())
    output.SetOrigin(source_image.GetOrigin())
    if hasattr(output, "SetDirectionMatrix"):
        output.SetDirectionMatrix(source_image.GetDirectionMatrix())
    return output

def binary_sub(imageA, imageB):
    # Invert imageB
    invert = vtk.vtkImageLogic()
    invert.SetInput1Data(imageB)
    invert.SetOperationToNot()
    invert.SetOutputTrueValue(1)
    if hasattr(invert, "SetOutputFalseValue"):
        invert.SetOutputFalseValue(0)
    invert.Update()

    # A AND (NOT B)
    logic = vtk.vtkImageLogic()
    logic.SetOperationToAnd()
    logic.SetInput1Data(imageA)
    logic.SetInput2Data(invert.GetOutput())
    logic.SetOutputTrueValue(1)

    if hasattr(logic, "SetOutputFalseValue"):
        logic.SetOutputFalseValue(0) 
        logic.Update()
        return _copy_geometry_and_return(imageA, logic.GetOutput())
    else:
        logic.Update()

        # Threshold to clamp everything else to 0
        thresh = vtk.vtkImageThreshold()
        thresh.SetInputConnection(logic.GetOutputPort())
        thresh.ThresholdByLower(0)  # Everything ≤ 0 becomes 0
        thresh.ReplaceInOn()
        thresh.SetInValue(0)
        thresh.ReplaceOutOn()
        thresh.SetOutValue(1)
        thresh.SetOutputScalarTypeToUnsignedChar()
        thresh.Update()

        return _copy_geometry_and_return(imageA, thresh.GetOutput())

def binary_and(imageA, imageB):
    logic = vtk.vtkImageLogic()
    logic.SetInput1Data(imageA)
    logic.SetInput2Data(imageB)
    logic.SetOperationToAnd()
    logic.SetOutputTrueValue(1)
    
    if hasattr(logic, "SetOutputFalseValue"):
        logic.SetOutputFalseValue(0) 
        logic.Update()
        return _copy_geometry_and_return(imageA, logic.GetOutput())
    else:
        logic.Update()

        # Threshold to clamp everything else to 0
        thresh = vtk.vtkImageThreshold()
        thresh.SetInputConnection(logic.GetOutputPort())
        thresh.ThresholdByLower(0)  # Everything ≤ 0 becomes 0
        thresh.ReplaceInOn()
        thresh.SetInValue(0)
        thresh.ReplaceOutOn()
        thresh.SetOutValue(1)
        thresh.SetOutputScalarTypeToUnsignedChar()
        thresh.Update()

        return _copy_geometry_and_return(imageA, thresh.GetOutput())

def binary_or(imageA, imageB):
    logic = vtk.vtkImageLogic()
    logic.SetInput1Data(imageA)
    logic.SetInput2Data(imageB)
    logic.SetOperationToOr()
    logic.SetOutputTrueValue(1)
    
    if hasattr(logic, "SetOutputFalseValue"):
        logic.SetOutputFalseValue(0) 
        logic.Update()
        return _copy_geometry_and_return(imageA, logic.GetOutput())
    else:
        logic.Update()
    
        # Threshold to clamp everything else to 0
        thresh = vtk.vtkImageThreshold()
        thresh.SetInputConnection(logic.GetOutputPort())
        thresh.ThresholdByLower(0)  # Everything ≤ 0 becomes 0
        thresh.ReplaceInOn()
        thresh.SetInValue(0)
        thresh.ReplaceOutOn()
        thresh.SetOutValue(1)
        thresh.SetOutputScalarTypeToUnsignedChar()
        thresh.Update()

        return _copy_geometry_and_return(imageA, thresh.GetOutput())

def perform_boolean_operation(imageA, imageB, operation):
    if operation == "AND":
        return binary_and(imageA, imageB)
    elif operation == "OR":
        return binary_or(imageA, imageB)
    elif operation == "SUB":
        return binary_sub(imageA, imageB)
    else:
        return None
    

