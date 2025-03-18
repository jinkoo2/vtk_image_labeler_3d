import vtk

input_filename = "C:/Users/jkim20/Documents/projects/vtk_image_labeler_3d/sample_data/Dataset101_Eye[ul]L/imagesTr/eye[ul]l_0_0000.mha"

# Create a VTK renderer and render window
renderer = vtk.vtkRenderer()
render_window = vtk.vtkRenderWindow()
render_window.AddRenderer(renderer)
interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(render_window)

# Load the sample image
reader = vtk.vtkMetaImageReader()
reader.SetFileName(input_filename)
reader.Update()

# Create a flip transformation matrix (flip vertically)
flip_matrix = vtk.vtkMatrix4x4()
flip_matrix.Identity()
flip_matrix.SetElement(1, 1, -1)  # Flip along Y-axis (top-bottom)

# Setup Image Plane Widget
plane_widget = vtk.vtkImagePlaneWidget()
plane_widget.SetInteractor(interactor)
plane_widget.SetInputConnection(reader.GetOutputPort())
plane_widget.SetPlaneOrientationToZAxes()
plane_widget.SetSliceIndex(50)
plane_widget.DisplayTextOn()
plane_widget.SetPicker(vtk.vtkCellPicker())
plane_widget.SetKeyPressActivationValue('x')
plane_widget.SetInteraction(0)

# Flip vertically by adjusting the ResliceAxes manually
flip_matrix = vtk.vtkMatrix4x4()
flip_matrix.Identity()
flip_matrix.SetElement(0, 0, 1)
flip_matrix.SetElement(1, 1, -1)  # Vertical flip
flip_matrix.SetElement(2, 2, 1)

# Fix: Instead of SetResliceAxes (which doesn't exist), we set this via the plane_widget's own ResliceAxes object:
#plane_widget.GetResliceAxes().DeepCopy(flip_matrix)

# Customize widget appearance
plane_widget.GetPlaneProperty().SetColor(1, 0, 0)  # Red border
plane_widget.TextureInterpolateOn()

plane_widget.On()

# Renderer settings
renderer.SetBackground(0.1, 0.2, 0.4)
renderer.ResetCamera()

# Start interaction
render_window.Render()
interactor.Initialize()
interactor.Start()
