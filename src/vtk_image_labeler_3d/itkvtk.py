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

def vtk_matrix4x4_to_numpy(vtk_matrix):
    """
    Convert a vtkMatrix4x4 to a 4x4 NumPy array.
    
    Args:
        vtk_matrix: vtk.vtkMatrix4x4 object
    
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