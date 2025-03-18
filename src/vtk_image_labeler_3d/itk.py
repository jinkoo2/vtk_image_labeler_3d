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

def combine_sitk_labels(label_images):
    """
    Combine multiple binary label images into a single labeled image.
    
    Parameters:
        label_images (list of sitk.Image): List of SimpleITK binary label images (0-background, 1-object).
        
    Returns:
        sitk.Image: A single SimpleITK image where each object is uniquely labeled.
    """
    if not label_images:
        raise ValueError("Input label_images list is empty.")

    # Get image size and dimension
    ref_size = label_images[0].GetSize()
    ref_spacing = label_images[0].GetSpacing()
    ref_origin = label_images[0].GetOrigin()
    ref_direction = label_images[0].GetDirection()

    # Convert all images to numpy arrays
    label_arrays = [sitk.GetArrayFromImage(img) for img in label_images]

    # Ensure all images have the same shape
    for i, arr in enumerate(label_arrays):
        if arr.shape != label_arrays[0].shape:
            raise ValueError(f"Label image {i} does not match dimensions of the first label image.")

    # Create an empty label map
    combined_label_array = np.zeros_like(label_arrays[0], dtype=np.uint8)

    # Assign unique labels to each object
    for i, label_array in enumerate(label_arrays):
        combined_label_array[label_array > 0] = i + 1  # Background remains 0, first object = 1, second = 2, etc.

    # Convert back to SimpleITK image
    combined_label_image = sitk.GetImageFromArray(combined_label_array)

    # Set spatial information
    combined_label_image.SetSpacing(ref_spacing)
    combined_label_image.SetOrigin(ref_origin)
    combined_label_image.SetDirection(ref_direction)

    return combined_label_image

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

