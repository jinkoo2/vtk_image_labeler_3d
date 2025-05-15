import vtk

def to_vtk_color(c):
    return [c[0]/255, c[1]/255, c[2]/255]

def from_vtk_color(c):
    return [int(c[0]*255), int(c[1]*255), int(c[2]*255)]

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