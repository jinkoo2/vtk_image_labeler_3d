import vtk
import SimpleITK as sitk
from vtk.util.numpy_support import numpy_to_vtk
import numpy as np

def numpy_dtype_to_vtk_type(dtype):
    """Map a NumPy dtype to the corresponding VTK type."""
    vtk_type_map = {
        np.int8: vtk.VTK_CHAR,
        np.uint8: vtk.VTK_UNSIGNED_CHAR,
        np.int16: vtk.VTK_SHORT,
        np.uint16: vtk.VTK_UNSIGNED_SHORT,
        np.int32: vtk.VTK_INT,
        np.uint32: vtk.VTK_UNSIGNED_INT,
        np.int64: vtk.VTK_LONG,  # Note: VTK_LONG may be platform-dependent
        np.uint64: vtk.VTK_UNSIGNED_LONG,
        np.float32: vtk.VTK_FLOAT,
        np.float64: vtk.VTK_DOUBLE,
    }
    
    # Ensure the dtype is a NumPy type
    dtype = np.dtype(dtype)
    
    if dtype.type in vtk_type_map:
        return vtk_type_map[dtype.type]
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")



def sitk_to_vtk(sitk_image):
    """Convert a SimpleITK image to a VTK image."""
    import numpy as np
    from vtk.util.numpy_support import numpy_to_vtk

    # Get image dimensions and metadata
    dims = sitk_image.GetSize()
    spacing = sitk_image.GetSpacing()
    origin = sitk_image.GetOrigin()
    direction = sitk_image.GetDirection()
    if len(dims) == 2:
        dims = (dims[0], dims[1], 1)
        spacing = (spacing[0], spacing[1], 1.0)  # Typically 1.0 or some default slice thickness
        origin = (origin[0], origin[1], 0.0)
        direction = [
            direction[0], direction[1], 0.0,
            direction[2], direction[3], 0.0,
            0.0,             0.0,             1.0
        ]


    # Create a VTK image
    vtk_image = vtk.vtkImageData()
    vtk_image.SetDimensions(dims)  # Reverse dimensions to match VTK
    vtk_image.SetSpacing(spacing)
    vtk_image.SetOrigin(origin)

    # Set the direction matrix if supported by VTK
    if hasattr(vtk_image, "SetDirectionMatrix"):
        vtk_matrix = vtk.vtkMatrix3x3()
        for i in range(3):
            for j in range(3):
                vtk_matrix.SetElement(i, j, direction[i * 3 + j])  # Convert flat list to 3x3
        vtk_image.SetDirectionMatrix(vtk_matrix)

    # Get the numpy array from SimpleITK
    np_array = sitk.GetArrayFromImage(sitk_image)

    # Convert numpy array to VTK array
    vtk_type = numpy_dtype_to_vtk_type(np_array.dtype)

    # Flatten the array with Fortran-order for VTK
    vtk_array = numpy_to_vtk(np_array.ravel(order='C'), deep=True, array_type=vtk_type) 
    vtk_image.GetPointData().SetScalars(vtk_array)

    return vtk_image

def vtk_to_sitk(vtk_image):
    """Convert vtkImageData to SimpleITK Image."""
    # Get the dimensions, spacing, and origin of the VTK image
    dims = vtk_image.GetDimensions()
    spacing = vtk_image.GetSpacing()
    origin = vtk_image.GetOrigin()
    direction_matrix = None

    # Check if the VTK image has a direction matrix (not always present)
    if hasattr(vtk_image, "GetDirectionMatrix"):
        direction_matrix = vtk_image.GetDirectionMatrix()

    # Extract the image scalars as a NumPy array
    scalars = vtk_image.GetPointData().GetScalars()
    np_array = vtk.util.numpy_support.vtk_to_numpy(scalars)
    np_array = np_array.reshape(dims[::-1])  # Reshape to (z, y, x)

    # Convert to a SimpleITK image
    sitk_image = sitk.GetImageFromArray(np_array)
    sitk_image.SetSpacing(spacing)
    sitk_image.SetOrigin(origin)
    if direction_matrix:
        direction_list = [direction_matrix.GetElement(i, j) for i in range(3) for j in range(3)]
        sitk_image.SetDirection(direction_list)
        
    return sitk_image

def save_vtk_image_using_sitk(vtk_image, file_path):
    """Save vtkImageData as an .mha file."""
    sitk_image = vtk_to_sitk(vtk_image)
    sitk.WriteImage(sitk_image, file_path, useCompression=True)
    print(f"Saved as {file_path}")

def load_vtk_image_using_sitk(file_path):
    sitk_image = sitk.ReadImage(file_path)
    vtk_image = sitk_to_vtk(sitk_image)
    print(f"Loaded {file_path}")
    return vtk_image

def extract_binary_label_image_from_composit_labels_image(composit_labels_image, label_value):
    threshold = vtk.vtkImageThreshold()
    threshold.SetInputData(composit_labels_image)
    threshold.ThresholdBetween(label_value, label_value)       # Only value 5 will be extracted
    threshold.SetInValue(1)                # Set pixels with value 5 to 1
    threshold.SetOutValue(0)               # All others to 0
    threshold.Update()
    return threshold.GetOutput()

def vtk_get_w_H_imageo(vtk_image):
    """
    Create a 4x4 homogeneous matrix from a vtkImageData's direction matrix and origin.
    
    Args:
        vtk_image: vtkImageData object
    
    Returns:
        vtkMatrix4x4: 4x4 homogeneous transformation matrix
    """
    # Get the 3x3 direction matrix
    v3x3 = vtk_image.GetDirectionMatrix()
    
    # Get the origin (translation)
    org = vtk_image.GetOrigin()
    
    # Create a 4x4 matrix
    matrix_4x4 = vtk.vtkMatrix4x4()
    
    # Populate the 3x3 rotation part
    for i in range(3):
        for j in range(3):
            matrix_4x4.SetElement(i, j, v3x3.GetElement(i, j))
    
    # Populate the translation part (4th column)
    matrix_4x4.SetElement(0, 3, org[0])  # Tx
    matrix_4x4.SetElement(1, 3, org[1])  # Ty
    matrix_4x4.SetElement(2, 3, org[2])  # Tz
    
    # Bottom row is [0, 0, 0, 1] by default in vtkMatrix4x4, so no need to set it explicitly
    
    return matrix_4x4

import numpy as np

vtk.vtkMatrix3x3
def vtk_matrix3x3_to_numpy(vtk_matrix):
    """
    Convert a vtkMatrix4x4 to a 3x3 NumPy array.
    
    Args:
        vtk_matrix: vtk.vtkMatrix3x3 object
    
    Returns:
        np.ndarray: 4x4 NumPy array
    """
    # Initialize a 4x4 NumPy array
    numpy_array = np.zeros((3, 3))
    
    # Populate the array with elements from the vtkMatrix4x4
    for i in range(3):
        for j in range(3):
            numpy_array[i, j] = vtk_matrix.GetElement(i, j)
    
    return numpy_array

def vtk_matrix4x4_to_numpy(vtk_matrix):
    """
    Convert a vtkMatrix4x4 to a 3x3 NumPy array.
    
    Args:
        vtk_matrix: vtk.vtkMatrix3x3 object
    
    Returns:
        np.ndarray: 4x4 NumPy array
    """
    # Initialize a 4x4 NumPy array
    numpy_array = np.zeros((4, 4))
    
    # Populate the array with elements from the vtkMatrix4x4
    for i in range(4):
        for j in range(4):
            numpy_array[i, j] = vtk_matrix.GetElement(i, j)
    
    return numpy_array

def vtk_get_w_H_imageo_np(vtk_image):
    H = vtk_get_w_H_imageo_np(vtk_image)
    return vtk_matrix4x4_to_numpy(H)

def vtk_matrix4x4_to_direction_and_origin_arrays(vtk_matrix):
    # Extract direction (rotation) and origin (translation) from matrix
    direction = [0.0] * 9
    origin = [0.0] * 3

    for row in range(3):
        for col in range(3):
            direction[row * 3 + col] = vtk_matrix.GetElement(row, col)
        origin[row] = vtk_matrix.GetElement(row, 3)

    return direction, origin

def vtk_matrix4x4_to_matrix3x3_and_t(matrix4x4):
    # Extract direction (rotation) and origin (translation) from matrix
    t = [0.0] * 3

    # Create vtkMatrix3x3
    matrix3x3 = vtk.vtkMatrix3x3()

    # Copy the top-left 3x3 part
    for i in range(3):
        for j in range(3):
            matrix3x3.SetElement(i, j, matrix4x4.GetElement(i, j))

    return matrix3x3, t

def numpy_to_vtk_matrix4x4(matrix_np: np.ndarray) -> vtk.vtkMatrix4x4:
    if matrix_np.shape != (4, 4):
        raise ValueError("Input matrix must be 4x4")

    vtk_mat = vtk.vtkMatrix4x4()
    for i in range(4):
        for j in range(4):
            vtk_mat.SetElement(i, j, matrix_np[i, j])
    return vtk_mat


def fill_square_at_center(image, width_in_pixels, pixel_value):
    dims = image.GetDimensions()
    center = [dims[i] // 2 for i in range(3)]

    half_size = width_in_pixels//2 
    #start = [center[i] - half_size for i in range(3)]
    start = [0, 0, 0]
    end = [center[i] + half_size for i in range(3)]

    # Fill central 50x50x50 with value 1
    component = 0
    for z in range(start[2], end[2]):
        for y in range(start[1], end[1]):
            for x in range(start[0], end[0]):
                image.SetScalarComponentFromDouble(x, y, z, component, pixel_value)

    image.Modified()

import vtk

def fill_rectangular_region(image, start_idx, end_idx, value):
    """
    Fill a rectangular 3D region in vtkImageData with a specified value.

    Parameters:
        image_data (vtk.vtkImageData): The VTK image object to modify.
        start_idx (tuple): Starting index (x0, y0, z0) of the box.
        end_idx (tuple): Ending index (x1, y1, z1) of the box (inclusive).
        value (float): Pixel value to set.
    """
    dims = image.GetDimensions()

    # Clip to valid bounds
    x0, y0, z0 = [max(0, min(start_idx[i], dims[i] - 1)) for i in range(3)]
    x1, y1, z1 = [max(0, min(end_idx[i], dims[i] - 1)) for i in range(3)]

    component = 0

    for z in range(z0, z1 + 1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                # Calculate flat index
                image.SetScalarComponentFromDouble(x, y, z, component, value)

    image.Modified()

