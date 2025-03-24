import vtk
import SimpleITK as sitk
import numpy as np
import itkvtk


def reslice_image_z(vtk_image, z_index, background_value=-1000, vtk_image_reslice=None):
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

    # Create reslicer if not given
    if not vtk_image_reslice:
        reslice = vtk.vtkImageReslice()
    else:
        reslice = vtk_image_reslice

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

def reslice_image_x(vtk_image, x_index, background_value=-1000, vtk_image_reslice=None):
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


    # Create reslicer if not given
    if not vtk_image_reslice:
        reslice = vtk.vtkImageReslice()
    else:
        reslice = vtk_image_reslice

    # Create reslicer
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

def reslice_image_y(vtk_image, y_index, background_value=-1000, vtk_image_reslice=None):
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

    # Create reslicer if not given
    if not vtk_image_reslice:
        reslice = vtk.vtkImageReslice()
    else:
        reslice = vtk_image_reslice

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

AXIAL = 2
CORONAL = 1
SAGITTAL = 0

class Reslicer():
    def __init__(self, axis, vtk_image=None, background_value=-1000):
        self.vtk_image = vtk_image
        self.background_value = background_value
        self.axis = axis

        reslice = vtk.vtkImageReslice()
        
        if vtk_image:
            reslice.SetInputData(vtk_image)
        
        reslice.SetOutputDimensionality(2)
        reslice.SetInterpolationModeToNearestNeighbor()
        reslice.SetBackgroundLevel(background_value)

        self.vtk_image_reslice = reslice

    def set_vtk_image(self, vtk_image):
        self.vtk_image = vtk_image
        self.vtk_image_reslice.SetInputData(vtk_image)
    
    def calculate_axes(self, index):
        
        spacing = self.vtk_image.GetSpacing()
        offset = index * spacing[self.axis]
        #reslice = self.vtk_image_reslice
        imgo_H_sliceo = vtk.vtkMatrix4x4()

        extent = self.vtk_image.GetExtent()
        
        if self.axis == AXIAL:
            imgo_H_sliceo.DeepCopy((1, 0, 0, 0,
                                    0, 1, 0, 0,
                                    0, 0, 1, offset,
                                    0, 0, 0, 1))
        elif self.axis == CORONAL:
            z_offset = extent[5] * spacing[2]
            imgo_H_sliceo.DeepCopy((1, 0, 0, 0,
                                    0, 0,  1, offset,  
                                    0, -1, 0, z_offset,
                                    0, 0, 0, 1))
        elif self.axis == SAGITTAL:
            z_offset = extent[5] * spacing[2]
            y_offset = extent[3] * spacing[1]
            imgo_H_sliceo.DeepCopy(( 0,  0, 1, offset,
                                    -1,  0, 0, y_offset,
                                     0, -1, 0, z_offset,
                                     0,  0, 0, 1))
        else:
            raise Exception(f'Invalid Axis ({self.axis})')

        import itkvtk
        w_H_imgo = itkvtk.vtk_get_w_H_imageo(self.vtk_image)
        w_H_sliceo = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(w_H_imgo, imgo_H_sliceo, w_H_sliceo)

        return w_H_sliceo
    
    def set_slice_index(self, index):
        
        min, max = self.get_slice_index_min_max()
        if not (min <= index <= max):
            print(f"slice index {index} is out of bounds ({min}, {max})")

        w_H_sliceo = self.calculate_axes(index)

        self.vtk_image_reslice.SetResliceAxes(w_H_sliceo)

        self.vtk_image_reslice.Update()

        return w_H_sliceo

    def get_slice_index_min_max(self):
        if not self.vtk_image:
            raise Exception("vtk_image is not set yet.")

        extent = self.vtk_image.GetExtent()
        axis = int(self.axis)
        return extent[axis*2], extent[axis*2+1]

    def get_slice_image_at_center(self):
        if not self.vtk_image:
            raise Exception("vtk_image is not set yet.")
        
        min, max = self.get_slice_index_min_max()

        # Center indices for each axis
        index = (max - min) // 2 + min
        
        return self.get_slice_image(index), index

    def get_slice_image(self, index):
        w_H_sliceo = self.set_slice_index(index)

        slice = self.vtk_image_reslice.GetOutput()
        
        # set slice direction & origin from w_H_sliceo,
        # note: self.vtk_image_reslicer.SetOutputOrigin and SetOutputDirectionMatrix did not work somehow. So, setting here after obraining the slice image
        direction, origin = itkvtk.vtk_matrix4x4_to_direction_and_origin_arrays(w_H_sliceo)
        slice.SetOrigin(origin)
        slice.SetDirectionMatrix(direction)

        # debug
        #itkvtk.save_vtk_image_using_sitk(slice, f'slice_{self.axis}_{index}.mhd')

        return slice

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
