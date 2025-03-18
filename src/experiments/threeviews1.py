import sys
import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class OrthogonalViewer(QMainWindow):
    def __init__(self, filename):
        super().__init__()
        self.setWindowTitle("VTK Orthogonal Views")

        self.reader = vtk.vtkMetaImageReader()
        self.reader.SetFileName(filename)
        self.reader.Update()

        self.central_widget = QWidget()
        self.layout = QHBoxLayout()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        orientations = ["Axial", "Coronal", "Sagittal"]
        self.widgets = []

        for orientation in range(3):
            vtk_widget = self.create_vtk_widget(orientation)
            self.layout.addWidget(vtk_widget)

        self.show()

    def create_vtk_widget(self, orientation):
        vtk_widget = QVTKRenderWindowInteractor(self)
        renderer = vtk.vtkRenderer()
        vtk_widget.GetRenderWindow().AddRenderer(renderer)

        plane_widget = vtk.vtkImagePlaneWidget()
        plane_widget.SetInteractor(vtk_widget.GetRenderWindow().GetInteractor())
        plane_widget.SetInputConnection(self.reader.GetOutputPort())
        plane_widget.SetPlaneOrientation(orientation)
        plane_widget.SetSliceIndex(self.reader.GetOutput().GetExtent()[orientation*2+1] // 2)
        plane_widget.DisplayTextOn()
        plane_widget.SetPicker(vtk.vtkCellPicker())
        plane_widget.TextureInterpolateOn()
        plane_widget.SetKeyPressActivationValue('x')
        plane_widget.On()

        vtk_widget.GetRenderWindow().GetInteractor().AddObserver("MouseWheelForwardEvent",
            lambda obj, event: self.change_slice(plane_widget, 1))
        vtk_widget.GetRenderWindow().GetInteractor().AddObserver("MouseWheelBackwardEvent", 
            lambda obj, event: self.mouse_wheel_backward(plane_widget, orientation))

        renderer.SetBackground(0.1, 0.2, 0.4)
        renderer.ResetCamera()

        vtk_widget.Initialize()
        vtk_widget.Start()

        return vtk_widget

    def change_slice(self, plane_widget, delta):
        idx = plane_widget.GetSliceIndex()
        idx = idx + delta
        idx_min, idx_max = plane_widget.GetSliceIndexMin(), plane_widget.GetSliceIndexMax()
        plane_widget.SetSliceIndex(max(min(idx, idx_max), extent[0]))
        plane_widget.GetInteractor().Render()

    def mouse_wheel_forward(self, plane_widget, orientation):
        if QApplication.keyboardModifiers() == Qt.ShiftModifier:
            self.change_slice(plane_widget, 1)

    def mouse_wheel_backward(self, plane_widget, orientation):
        if QApplication.keyboardModifiers() == Qt.ShiftModifier:
            self.change_slice(plane_widget, -1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    filename = "C:/Users/jkim20/Documents/projects/vtk_image_labeler_3d/sample_data/Dataset101_Eye[ul]L/imagesTr/eye[ul]l_0_0000.mha"
    viewer = OrthogonalViewer(filename)
    sys.exit(app.exec_())



