import sys
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QFileDialog, QDockWidget, QPushButton, QVBoxLayout, QSlider, QLabel
from PyQt5.QtCore import Qt

class VTKViewer(QWidget):

    def __init__(self, orientation="axial"):
        super().__init__()
        self.orientation = orientation
        self.renderer = vtk.vtkRenderer()
        self.interactor = QVTKRenderWindowInteractor(self)
        self.render_window = self.interactor.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        layout = QVBoxLayout()
        layout.addWidget(self.interactor)
        layout.addWidget(QLabel(f"{orientation.capitalize()} Slice"))
        self.slider = QSlider(Qt.Horizontal)
        layout.addWidget(self.slider)
        self.setLayout(layout)

        # Use vtkOpenGLImageMapper instead of vtkImageMapper
        self.mapper = vtk.vtkImageSliceMapper()
        self.actor = vtk.vtkImageSlice()
        self.actor.SetMapper(self.mapper)
        self.renderer.AddActor(self.actor)

    def set_image(self, vtk_image):
        self.vtk_image = vtk_image
        extent = vtk_image.GetExtent()

        # Determine the slicing axis and initial slice index
        if self.orientation == "axial":
            axis = 2
            initial_slice = (extent[4] + extent[5]) // 2  # Middle Z slice
        elif self.orientation == "coronal":
            axis = 1
            initial_slice = (extent[2] + extent[3]) // 2  # Middle Y slice
        elif self.orientation == "sagittal":
            axis = 0
            initial_slice = (extent[0] + extent[1]) // 2  # Middle X slice

        # Set slider range
        self.slider.setMinimum(extent[axis*2])
        self.slider.setMaximum(extent[axis*2+1])
        self.slider.valueChanged.connect(self.update_slice)
        self.slider.setValue(initial_slice)

        # Extract the initial slice
        self.extract_slice(initial_slice)
        self.renderer.ResetCamera()
        self.render_window.Render()

    def extract_slice(self, slice_index):
        # Create vtkExtractVOI to extract a 2D slice
        extract_voi = vtk.vtkExtractVOI()
        extent = self.vtk_image.GetExtent()
        if self.orientation == "axial":
            extract_voi.SetVOI(extent[0], extent[1], extent[2], extent[3], slice_index, slice_index)
        elif self.orientation == "coronal":
            extract_voi.SetVOI(extent[0], extent[1], slice_index, slice_index, extent[4], extent[5])
        elif self.orientation == "sagittal":
            extract_voi.SetVOI(slice_index, slice_index, extent[2], extent[3], extent[4], extent[5])

        extract_voi.SetInputData(self.vtk_image)
        extract_voi.Update()
        slice_image = extract_voi.GetOutput()

        # Update the mapper with the extracted slice
        self.mapper.SetInputData(slice_image)
        self.mapper.Update()

    def update_slice(self):
        slice_index = self.slider.value()
        self.extract_slice(slice_index)
        self.render_window.Render()

    def render(self):
        self.render_window.Render()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Medical Image Labeler")
        self.resize(1200, 800)

        central_widget = QWidget()
        layout = QGridLayout()

        # Create four viewers
        self.axial_viewer = VTKViewer("axial")
        self.coronal_viewer = VTKViewer("coronal")
        self.sagittal_viewer = VTKViewer("sagittal")
        self.surface_viewer = VTKViewer("3d")

        layout.addWidget(self.axial_viewer, 0, 0)
        layout.addWidget(self.coronal_viewer, 0, 1)
        layout.addWidget(self.sagittal_viewer, 1, 0)
        layout.addWidget(self.surface_viewer, 1, 1)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.create_toolbar()

    def create_toolbar(self):
        dock = QDockWidget("Controls", self)
        btn_load = QPushButton("Load Image")
        btn_load.clicked.connect(self.load_image)

        dock_widget_layout = QVBoxLayout()
        dock_widget_layout.addWidget(btn_load)
        dock_widget_layout.addStretch()
        dock_widget = QWidget()
        dock_widget.setLayout(dock_widget_layout)

        dock.setWidget(dock_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open 3D Image", "", "Medical Images (*.mha *.mhd *.nii *.nii.gz)")
        if not file_path:
            return

        
        
        import itkvtk
        
        vtk_image = itkvtk.load_vtk_image_using_sitk(file_path)

        vtk_image.SetOrigin([0.0, 0.0, 0.0])
        org = vtk_image.GetOrigin()
        print(f'org={org}')

        m = vtk_image.GetDirectionMatrix()
        print(m)


        vtk_image.SetSpacing([1.0, 1.0, 1.0])
        spacing = vtk_image.GetSpacing()
        print(f'spacing={spacing}')

        self.axial_viewer.set_image(vtk_image)
        self.coronal_viewer.set_image(vtk_image)
        self.sagittal_viewer.set_image(vtk_image)
        #self.surface_viewer.set_image(vtk_image)

    def sitk_to_vtk(self, sitk_image):
        from vtk.util.numpy_support import numpy_to_vtk
        img_array = sitk.GetArrayFromImage(sitk_image)
        vtk_array = numpy_to_vtk(img_array.ravel(order='F'))
        vtk_image = vtk.vtkImageData()
        vtk_image.SetDimensions(img_array.shape[::-1])
        vtk_image.SetSpacing(sitk_image.GetSpacing())
        vtk_image.SetOrigin(sitk_image.GetOrigin())
        vtk_image.GetPointData().SetScalars(vtk_array)
        return vtk_image

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())