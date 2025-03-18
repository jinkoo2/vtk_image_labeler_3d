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