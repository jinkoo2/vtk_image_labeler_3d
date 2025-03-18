import vtk
import SimpleITK as sitk
import numpy as np

def reslice_image_z(vtk_image, z_index, background_value=-1000):
    """
    Reslice a vtkImageData along the Z-axis (axial) at a given index with a specified background value.
    
    Args:
        vtk_image: Input vtkImageData (e.g., CT volume)
        z_index: Index along Z-axis for the slice
        background_value: Pixel value for areas outside the image extent (default: -1000 for CT air)
    
    Returns:
        Resliced 2D vtkImageData
    """
    # Get image properties
    spacing = vtk_image.GetSpacing()
    extent = vtk_image.GetExtent()
    z_min, z_max = extent[4], extent[5]
    
    # Validate z_index
    if not (z_min <= z_index <= z_max):
        raise ValueError(f"z_index {z_index} out of bounds. Must be between {z_min} and {z_max}")

    # Create reslicer
    reslice = vtk.vtkImageReslice()
    reslice.SetInputData(vtk_image)
    reslice.SetOutputDimensionality(2)

    # Define reslice matrix for axial slice (X-Y plane) at z_index
    imgo_H_sliceo = vtk.vtkMatrix4x4()
    imgo_H_sliceo.DeepCopy((1, 0, 0, 0,
                            0, 1, 0, 0,
                            0, 0, 1, z_index * spacing[2],
                            0, 0, 0, 1))

    reslice.SetResliceAxes(imgo_H_sliceo)
    reslice.SetInterpolationModeToLinear()
    reslice.SetBackgroundLevel(background_value)
    reslice.Update()

    return reslice.GetOutput()

def reslice_image_x(vtk_image, x_index, background_value=-1000):
    """
    Reslice a vtkImageData along the X-axis (sagittal) at a given index with a specified background value.
    
    Args:
        vtk_image: Input vtkImageData (e.g., CT volume)
        x_index: Index along X-axis for the slice
        background_value: Pixel value for areas outside the image extent (default: -1000 for CT air)
    
    Returns:
        Resliced 2D vtkImageData
    """
    # Get image properties
    spacing = vtk_image.GetSpacing()
    extent = vtk_image.GetExtent()
    x_min, x_max = extent[0], extent[1]
    
    # Validate x_index
    if not (x_min <= x_index <= x_max):
        raise ValueError(f"x_index {x_index} out of bounds. Must be between {x_min} and {x_max}")

    # Create reslicer
    reslice = vtk.vtkImageReslice()
    reslice.SetInputData(vtk_image)
    reslice.SetOutputDimensionality(2)

    # Define reslice matrix for sagittal slice (Y-Z plane) at x_index
    imgo_H_sliceo = vtk.vtkMatrix4x4()
    imgo_H_sliceo.DeepCopy((0, 0, -1, x_index * spacing[0],  # X-axis aligned to Y (swap X and Y)
                            0, 1, 0, 0,
                            1, 0, 0, 0,
                            0, 0, 0, 1))

    reslice.SetResliceAxes(imgo_H_sliceo)
    reslice.SetInterpolationModeToLinear()
    reslice.SetBackgroundLevel(background_value)
    reslice.Update()

    return reslice.GetOutput()

def reslice_image_y(vtk_image, y_index, background_value=-1000):
    """
    Reslice a vtkImageData along the Y-axis (coronal) at a given index with a specified background value.
    
    Args:
        vtk_image: Input vtkImageData (e.g., CT volume)
        y_index: Index along Y-axis for the slice
        background_value: Pixel value for areas outside the image extent (default: -1000 for CT air)
    
    Returns:
        Resliced 2D vtkImageData
    """
    # Get image properties
    spacing = vtk_image.GetSpacing()
    extent = vtk_image.GetExtent()
    y_min, y_max = extent[2], extent[3]
    
    # Validate y_index
    if not (y_min <= y_index <= y_max):
        raise ValueError(f"y_index {y_index} out of bounds. Must be between {y_min} and {y_max}")

    # Create reslicer
    reslice = vtk.vtkImageReslice()
    reslice.SetInputData(vtk_image)
    reslice.SetOutputDimensionality(2)

    # Define reslice matrix for coronal slice (X-Z plane) at y_index
    imgo_H_sliceo = vtk.vtkMatrix4x4()
    imgo_H_sliceo.DeepCopy((1, 0, 0, 0,
                            0, 0, -1, y_index * spacing[1],  # Y-axis aligned to Z (swap Y and Z)
                            0, 1, 0, 0,
                            0, 0, 0, 1))

    reslice.SetResliceAxes(imgo_H_sliceo)
    reslice.SetInterpolationModeToLinear()
    reslice.SetBackgroundLevel(background_value)
    reslice.Update()

    return reslice.GetOutput()

def main():
    input_filename = "C:/Users/jkim20/Documents/projects/vtk_image_labeler_3d/sample_data/Dataset101_Eye[ul]L/imagesTr/eye[ul]l_0_0000.mha"
    import itkvtk
    vtk_image = itkvtk.load_vtk_image_using_sitk(input_filename)
    # Optionally override origin and spacing (commented out unless needed)
    vtk_image.SetOrigin([0.0, 0.0, 0.0])
    vtk_image.SetSpacing([1.0, 1.0, 1.0])

    extent = vtk_image.GetExtent()
    x_min, x_max = extent[0], extent[1]
    y_min, y_max = extent[2], extent[3]
    z_min, z_max = extent[4], extent[5]

    # Center indices for each axis
    x_index = (x_max - x_min) // 2 + x_min
    y_index = (y_max - y_min) // 2 + y_min
    z_index = (z_max - z_min) // 2 + z_min

    # Reslice along Z (axial)
    resliced_z = reslice_image_z(vtk_image, z_index)
    itkvtk.save_vtk_image_using_sitk(resliced_z, f"slice_z_{z_index}.mhd")
    print(f"Saved axial slice to slice_z_{z_index}.mhd")

    # Reslice along X (sagittal)
    resliced_x = reslice_image_x(vtk_image, x_index)
    itkvtk.save_vtk_image_using_sitk(resliced_x, f"slice_x_{x_index}.mhd")
    print(f"Saved sagittal slice to slice_x_{x_index}.mhd")

    # Reslice along Y (coronal)
    resliced_y = reslice_image_y(vtk_image, y_index)
    itkvtk.save_vtk_image_using_sitk(resliced_y, f"slice_y_{y_index}.mhd")
    print(f"Saved coronal slice to slice_y_{y_index}.mhd")

if __name__ == "__main__":
    main()
