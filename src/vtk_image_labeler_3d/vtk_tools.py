import vtk

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
    

