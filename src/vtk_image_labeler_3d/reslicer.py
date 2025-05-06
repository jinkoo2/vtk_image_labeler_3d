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
    def __init__(self, axis, vtk_image=None, background_value=-1000, viewer=None):
        self.vtk_image = vtk_image
        self.background_value = background_value
        self.axis = axis
        self.viewer = viewer

        reslice = vtk.vtkImageReslice()
        
        if vtk_image:
            reslice.SetInputData(vtk_image)
        
        reslice.SetOutputDimensionality(2)
        reslice.SetInterpolationModeToNearestNeighbor()
        reslice.SetBackgroundLevel(background_value)

        self.vtk_image_reslice = reslice

        self.slice_index = 0

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

        self.slice_index = index 

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

 
class ReslicerWithImageActor(Reslicer):
    def __init__(self, axis, vtk_image=None, background_value=-1000, vtk_color=(1,0,0), alpha=0.8, border_color=(1, 0, 0), viewer=None):
        super().__init__(axis, vtk_image, background_value, viewer=viewer)
      
        self._create_slice_actor(vtk_color, alpha)
        self._create_contour_border(border_color)

    def _create_slice_actor(self, vtk_color, alpha):
        # Color lookup table
        self.lookup_table = vtk.vtkLookupTable()
        self.lookup_table.SetNumberOfTableValues(2)
        self.lookup_table.SetTableRange(0, 1)
        self.lookup_table.SetTableValue(0, 0, 0, 0, 0)  # transparent
        self.lookup_table.SetTableValue(1, *vtk_color, alpha)
        self.lookup_table.Build()

        self.slice_mapper = vtk.vtkImageMapToColors()
        self.slice_mapper.SetLookupTable(self.lookup_table)

        self.slice_actor = vtk.vtkImageActor()
        self.slice_actor.GetMapper().SetInputConnection(self.slice_mapper.GetOutputPort())

    def _create_contour_border(self, border_color):
        # Extract border from segmentation
        self.contour_filter = vtk.vtkContourFilter()
        self.contour_filter.SetValue(0, 0.5)

        self.border_mapper = vtk.vtkPolyDataMapper()
        self.border_mapper.SetInputConnection(self.contour_filter.GetOutputPort())
        self.border_mapper.ScalarVisibilityOff()  

        self.border_actor = vtk.vtkActor()
        self.border_actor.SetMapper(self.border_mapper)
        self.border_actor.GetProperty().SetColor(*border_color)
        self.border_actor.GetProperty().SetLineWidth(1)
        self.border_actor.GetProperty().SetOpacity(1.0)
        #self.border_actor.GetProperty().LightingOff()

    def get_actors(self):
        return [self.slice_actor, self.border_actor]
        #return [self.border_actor]
    
    def _poly_data_point_list_to_4xN_numpy_matrix(self, points):

        n_points = points.GetNumberOfPoints()

        # Allocate a 3xN numpy array
        points_array = np.ones((3, n_points))

        for i in range(n_points):
            pt = points.GetPoint(i)  # Returns a tuple of (x, y, z)
            points_array[:, i] = pt

        print(points_array.shape)  # (3, N)

        N = points_array.shape[1]

        # Create a new 4xN array
        points_homogeneous = np.vstack((points_array, np.ones((1, N))))

        print(points_homogeneous.shape)  # (4, N)

        return points_homogeneous


    def _4xN_numpy_matrix_to_poly_data_point_list(self, PT):
        N = PT.shape[1]
        new_points = vtk.vtkPoints()
        for i in range(N):
            x, y, z = PT[0:3, i]  # Extract x, y, z
            new_points.InsertNextPoint(x, y, z)
        return new_points


    def _transform_contour_filter_output_to_w(self, poly_data, slice):

        import vtk_image_wrapper
        slice_wrapper = vtk_image_wrapper.vtk_image_wrapper(slice)
        w_H_sliceo = slice_wrapper.get_w_H_o()
       
        # contour filter output point list matrix
        PT = self._poly_data_point_list_to_4xN_numpy_matrix(poly_data.GetPoints())

        # subtract origin
        slice_org_w = np.append(slice_wrapper.get_origin(), 0.0).reshape(4,1)
        PT_sliceo = PT - slice_org_w

        # transform to w 
        PT_w = w_H_sliceo @ PT_sliceo

        # shift points towards to the camera near plane
        camera = self.viewer.get_renderer().GetActiveCamera()
        import vtk_camera_wrapper
        cam = vtk_camera_wrapper.vtk_camera_wrapper(camera)
        uz = np.append(cam.get_z_axis(), 0.0).reshape(4,1)

        # shift by 10.0
        uz10 = uz * 10.0 
        PT2_w = PT_w - uz10
        
        # convert to vtkPoints
        new_points = self._4xN_numpy_matrix_to_poly_data_point_list(PT2_w)

        # Copy cells
        new_polydata = vtk.vtkPolyData()
        new_polydata.SetPoints(new_points)
        new_polydata.SetPolys(poly_data.GetPolys())
        new_polydata.SetLines(poly_data.GetLines())  # Optional
        
        return new_polydata
        
    def _print_poly_data_points(self, poly_data, skip):
        num_points = poly_data.GetNumberOfPoints()
        for i in range(int(num_points/skip)):
            point = poly_data.GetPoint(i*skip)
            print(f"Point {i*skip}: {point}")

    def set_slice_index_and_update_slice_actor(self, index):
        slice = super().get_slice_image(index)

        # Update image slice
        self.slice_mapper.SetInputData(slice)
        self.slice_actor.Update()

        # Update border contour
        self.contour_filter.SetInputData(slice)
        self.contour_filter.Update()

        contour_output = self.contour_filter.GetOutput()
        if contour_output.GetNumberOfPoints() == 0 or contour_output.GetNumberOfCells() == 0:
            print("Contour output is empty — no valid polygons.")
            return  # or skip further processing

        print('---- before transform ---')
        self._print_poly_data_points(contour_output, 30)

        # transform contour output to w
        poly_data_w = self._transform_contour_filter_output_to_w(contour_output, slice)

        print('---- after transform ---')
        self._print_poly_data_points(poly_data_w, 30)

        # set new data to mapper
        self.border_mapper.SetInputData(poly_data_w)
        self.border_actor.GetProperty().SetColor(0,1,0)
        self.border_mapper.Update()

        self.border_actor.SetMapper(self.border_mapper)

class ReslicerWithContourPolyActor(Reslicer):
    def __init__(self, axis, vtk_image=None, background_value=-1000, vtk_color=(1,0,0), alpha=0.8, viewer=None):
        super().__init__(axis, vtk_image, background_value, viewer=viewer)
        self._create_slice_actor(vtk_color, alpha)

    def _create_slice_actor(self, vtk_color, alpha):
        self.contour_filter = vtk.vtkContourFilter()
        self.hatch_lines = vtk.vtkAppendPolyData()
        self.clipper = vtk.vtkClipPolyData()
        self.loop_points = vtk.vtkPoints()
        self.loop = vtk.vtkImplicitSelectionLoop()
        self.mapper = vtk.vtkPolyDataMapper()
        self.hatch_actor = vtk.vtkActor()
    
    def get_actors(self):
        return [self.hatch_actor]

    def _clear_data(self):
        # Clear previous hatch lines
        self.hatch_lines.RemoveAllInputs()

        # Clear loop points (used for clipping)
        self.loop_points.Reset()


    def set_slice_index_and_update_slice_actor(self, index):
        slice = super().get_slice_image(index)
    
        self._clear_data()

        # ------------------------------
        # Step 2: Convert mask to polygon
        # ------------------------------
        contour_filter = self.contour_filter
        contour_filter.SetInputData(slice)
        contour_filter.SetValue(0, 0.5)
        contour_filter.Update()

        output = contour_filter.GetOutput()
        if output.GetNumberOfPoints() == 0 or output.GetNumberOfCells() == 0:
            print("Contour output is empty — no valid polygons.")
            return  # or skip further processing

        # ------------------------------
        # Step 3: Generate hatch lines (diagonal)
        # ------------------------------
        bounds = contour_filter.GetOutput().GetBounds()

        # Create hatch lines across bounding box
        hatch_lines = self.hatch_lines
        spacing = 5.0
        x0, x1, y0, y1 = bounds[0], bounds[1], bounds[2], bounds[3]
        for i in np.arange(y0 - 100, y1 + 100, spacing):
            points = vtk.vtkPoints()
            lines = vtk.vtkCellArray()

            p0 = (x0 - 50, i, 0)
            p1 = (x1 + 50, i + (x1 - x0), 0)

            points.InsertNextPoint(p0)
            points.InsertNextPoint(p1)

            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, 0)
            line.GetPointIds().SetId(1, 1)
            lines.InsertNextCell(line)

            line_poly = vtk.vtkPolyData()
            line_poly.SetPoints(points)
            line_poly.SetLines(lines)

            hatch_lines.AddInputData(line_poly)

        hatch_lines.Update()

        # ------------------------------
        # Step 4: Clip hatch lines to polygon
        # ------------------------------
        clipper = self.clipper
        clipper.SetInputConnection(hatch_lines.GetOutputPort())
        clipper.InsideOutOn()

        # For clipping, convert contour to loop
        loop_points = self.loop_points
        for i in range(contour_filter.GetOutput().GetNumberOfPoints()):
            loop_points.InsertNextPoint(contour_filter.GetOutput().GetPoint(i))

        self.loop.SetLoop(loop_points)
        clipper.SetClipFunction(self.loop)
        clipper.Update()


        # ------------------------------
        # Step 5: Create actors
        # ------------------------------
        # Hatch actor
        mapper = self.mapper
        mapper.SetInputConnection(clipper.GetOutputPort())

        hatch_actor = self.hatch_actor
        hatch_actor.SetMapper(mapper)
        hatch_actor.GetProperty().SetColor(1, 0.5, 0)  # orange
        hatch_actor.GetProperty().SetLineWidth(1.5)

       

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
