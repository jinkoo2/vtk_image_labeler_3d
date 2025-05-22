import SimpleITK as sitk
import numpy as np

def rot90(sitk_image, plus: bool):

    image = sitk_image

    # Convert to NumPy array while preserving data type
    pixel_type = image.GetPixelID()  # Get original pixel type
    image_array = sitk.GetArrayFromImage(image)
    origin = image.GetOrigin()
    spacing = image.GetSpacing()
    direction = image.GetDirection()

    # Rotate 90 degrees clockwise
    if plus: # x axis to y
        rotated_array = np.rot90(image_array, k=-1, axes=(1, 2))
    else: # y axis to x
        rotated_array = np.rot90(image_array, k=1, axes=(1, 2))

    # Convert back to SimpleITK image with the same pixel type
    rotated_image = sitk.GetImageFromArray(rotated_array)
    rotated_image = sitk.Cast(rotated_image, pixel_type)  # Ensure same pixel type

    # Keep metadata unchanged
    rotated_image.SetOrigin(origin)
    rotated_image.SetDirection(direction)
    rotated_image.SetSpacing([spacing[1], spacing[0], spacing[2]])
    
    return rotated_image




def flip_x(sitk_image):
    return flip(sitk_image, axis=2)

def flip_y(sitk_image):
    return flip(sitk_image, axis=1)


def flip(sitk_image, axis):
    """
    Flip a SimpleITK image along the x-axis.
    """
    # Convert to NumPy array
    pixel_type = sitk_image.GetPixelID()
    image_array = sitk.GetArrayFromImage(sitk_image)
    
    # Flip along the x-axis (axis=1)
    flipped_array = np.flip(image_array, axis)

    # Convert back to SimpleITK image
    flipped_image = sitk.GetImageFromArray(flipped_array)
    flipped_image = sitk.Cast(flipped_image, pixel_type)  # Preserve pixel type

    # Preserve metadata (origin, spacing, direction)
    origin = sitk_image.GetOrigin()
    spacing = sitk_image.GetSpacing()
    direction = sitk_image.GetDirection()

    # Update metadata
    flipped_image.SetOrigin(origin)
    flipped_image.SetSpacing(spacing)
    flipped_image.SetDirection(direction)  # Direction remains the same

    return flipped_image


import SimpleITK as sitk
import numpy as np

def combine_sitk_labels(label_images, label_values):
    """
    Combine multiple binary label images into a single labeled image, using specified label values.

    Parameters:
        label_images (list of sitk.Image): List of binary SimpleITK images (0=background, 1=foreground).
        label_values (list of int): List of unique label values to assign in the combined image.
        
    Returns:
        sitk.Image: A single SimpleITK label image with specified label values.
    """
    if not label_images or len(label_images)==0:
        raise ValueError("Input label_images list is empty.")

    if len(label_images) != len(label_values):
        raise ValueError("label_images and label_values must be the same length.")

    # Reference metadata from first image
    ref_img = label_images[0]
    ref_shape = sitk.GetArrayFromImage(ref_img).shape

    # Initialize combined label array
    combined = np.zeros(ref_shape, dtype=np.uint16)

    # Assign label values
    for img, label in zip(label_images, label_values):
        arr = sitk.GetArrayFromImage(img)
        if arr.shape != ref_shape:
            raise ValueError("All label images must have the same shape.")
        combined[arr > 0] = label  # Use the given label value

    # Convert to SimpleITK image
    combined_img = sitk.GetImageFromArray(combined)
    combined_img.CopyInformation(ref_img)
    
    return combined_img

def is_single_slice_3d_image(image):
    # Get the image dimension
    dimension = image.GetDimension()

    # Get the size of the image (Width, Height, Depth)
    size = image.GetSize()

    return dimension == 3 and size[2] == 1

def save_sitk_image(sitk_image, file_path, save_as_2d_if_single_slice_3d_image=True):
    
    if save_as_2d_if_single_slice_3d_image and is_single_slice_3d_image(sitk_image):
        image_2d = convert_single_slice_3d_image_to_2d_image(sitk_image)
        sitk.WriteImage(image_2d, file_path, useCompression=True)
    else:
        sitk.WriteImage(sitk_image, file_path, useCompression=True)

    print(f"Saved as {file_path}")

def convert_single_slice_3d_image_to_2d_image(image_3d):
    # Get image size
    size = image_3d.GetSize()  # (width, height, depth)
    
    if size[2] == 1:  # Check if it's a single-slice 3D image
        
        # Extract the first (and only) slice
        new_size = (size[0], size[1], 0)
        start_index = (0, 0, 0)
        image_2d = sitk.Extract(image_3d, new_size , start_index )

        return image_2d
    else:
        raise Exception(f'Not a single-slice 3D image')

import numpy as np
from scipy.spatial import ConvexHull, Delaunay

def make_convex_volume(binary_mask_np):
    # binary_mask_np: shape (Z, Y, X), dtype=uint8

    points = np.argwhere(binary_mask_np > 0)  # get (z, y, x) of foreground
    if len(points) < 4:
        raise ValueError("Convex hull needs at least 4 non-coplanar points.")

    hull = ConvexHull(points)
    delaunay = Delaunay(points[hull.vertices])

    # Create a dense grid of all voxel coordinates
    zz, yy, xx = np.indices(binary_mask_np.shape)
    test_points = np.stack((zz, yy, xx), axis=-1).reshape(-1, 3)

    # Test which points lie inside the convex hull
    mask = delaunay.find_simplex(test_points) >= 0
    convex_volume = mask.reshape(binary_mask_np.shape).astype(np.uint8)

    return convex_volume

def numpy_to_itk_binary(convex_volume: np.ndarray, reference_image: sitk.Image = None) -> sitk.Image:
    # Step 1: Convert NumPy → SimpleITK
    itk_image = sitk.GetImageFromArray(convex_volume.astype(np.uint8))  # shape (z, y, x)

    # Step 2: Set geometry to match reference image (if available)
    if reference_image is not None:
        itk_image.CopyInformation(reference_image)

    return itk_image

def itk_to_numpy_binary(itk_image: sitk.Image) -> np.ndarray:
    arr = sitk.GetArrayFromImage(itk_image)  # shape: (z, y, x)
    binary = (arr > 0).astype(np.uint8)      # ensure binary: 0 or 1
    return binary

def make_convex_label(label_image_sitk):

    np_image = itk_to_numpy_binary(label_image_sitk)

    np_convex_volume = make_convex_volume(np_image)

    itk_convex_volume = numpy_to_itk_binary(np_convex_volume, label_image_sitk)
    
    return itk_convex_volume
    
if __name__ == '__main__':
    import numpy as np

    # Define a 2x8 array with values from 0 to 7
    array = np.array([[[0, 1, 2, 3],
                    [4, 5, 6, 7]]])

    print("Original Array:")
    print(array)

    # Rotate 90 degrees clockwise (k=-1 for clockwise rotation)
    #transformed_array = np.rot90(array, k=-1, axes=(1, 2))
    #transformed_array = np.flip(array, axis=1)
    transformed_array = np.flip(array, axis=2)


    print("\nTraisnformed Array (90° Clockwise):")
    print(transformed_array)

