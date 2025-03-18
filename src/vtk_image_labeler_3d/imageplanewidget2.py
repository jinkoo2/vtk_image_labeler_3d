import sys
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

class VTKImageWidget(QMainWindow):
    def __init__(self, input_filename):
        super().__init__()
        self.setWindowTitle("VTK Image Plane Widget")
        self.frame = QWidget()
        self.layout = QVBoxLayout()

        self.vtk_widget = QVTKRenderWindowInteractor(self.frame)
        self.layout.addWidget(self.vtk_widget)
        self.frame.setLayout(self.layout)
        self.setCentralWidget(self.frame)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

        reader = vtk.vtkMetaImageReader()
        reader.SetFileName(input_filename)
        reader.Update()

        self.plane_widget = vtk.vtkImagePlaneWidget()
        self.plane_widget.SetInteractor(self.interactor)
        self.plane_widget.SetInputConnection(reader.GetOutputPort())
        self.plane_widget.SetPlaneOrientationToZAxes()
        self.plane_widget.SetSliceIndex(50)
        self.plane_widget.DisplayTextOn()
        self.plane_widget.SetPicker(vtk.vtkCellPicker())
        self.plane_widget.SetKeyPressActivationValue('x')
        self.plane_widget.TextureInterpolateOn()
        self.plane_widget.On()

        self.renderer.SetBackground(0.1, 0.2, 0.4)
        self.renderer.ResetCamera()

        self.interactor.AddObserver("MouseWheelForwardEvent", self.mouse_wheel_forward)
        self.interactor.AddObserver("MouseWheelBackwardEvent", self.mouse_wheel_backward)

        self.show()
        self.interactor.Initialize()

    def mouse_wheel_forward(self, obj, event):
        if QApplication.keyboardModifiers() == Qt.ShiftModifier:
            current_index = self.plane_widget.GetSliceIndex()
            self.plane_widget.SetSliceIndex(current_index + 1)
            self.interactor.Render()

    def mouse_wheel_backward(self, obj, event):
        if QApplication.keyboardModifiers() == Qt.ShiftModifier:
            current_index = self.plane_widget.GetSliceIndex()
            self.plane_widget.SetSliceIndex(current_index - 1)
            self.interactor.Render()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    input_filename = "C:/Users/jkim20/Documents/projects/vtk_image_labeler_3d/sample_data/Dataset101_Eye[ul]L/imagesTr/eye[ul]l_0_0000.mha"
    window = VTKImageWidget(input_filename)
    sys.exit(app.exec_())

