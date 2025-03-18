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
        self.slider = QSlider(Qt.Horizontal)
        layout.addWidget(QLabel(f"{orientation.capitalize()} Slice"))
        layout.addWidget(self.slider)
        self.setLayout(layout)

        self.reslice = vtk.vtkImageReslice()
        self.mapper = vtk.vtkImageSliceMapper()
        self.mapper.SetInputConnection(self.reslice.GetOutputPort())
        self.actor = vtk.vtkImageSlice()
        self.actor.SetMapper(self.mapper)
        self.renderer.AddViewProp(self.actor)

    def set_image(self, vtk_image):
        self.vtk_image = vtk_image
       
        axis = {'axial': 2, 'coronal': 1, 'sagittal': 0}[self.orientation]

        self.reslice.SetInputData(vtk_image)

        extent = vtk_image.GetExtent()
        self.slider.setMinimum(extent[axis*2])
        self.slider.setMaximum(extent[axis*2+1])
        self.slider.valueChanged.connect(self.update_slice)
        self.slider.setValue((extent[axis*2] + extent[axis*2+1]) // 2)

        self.update_slice()

        self.renderer.ResetCamera()
        self.render()
        

    def update_slice(self):
        axis = {'axial': 2, 'coronal': 1, 'sagittal': 0}[self.orientation]
        spacing = self.vtk_image.GetSpacing()
        origin = self.vtk_image.GetOrigin()
        slice_pos = self.slider.value() * spacing[axis] + origin[axis]

        reslice = self.reslice
        background_value = -1000
        
        reslice.SetInputData(self.vtk_image)
        reslice.SetOutputDimensionality(2)
        reslice.SetInterpolationModeToLinear()
        reslice.SetBackgroundLevel(background_value)

        imgo_H_sliceo = vtk.vtkMatrix4x4()
        if axis == 2: # axial
            z_index = self.slider.value()
            imgo_H_sliceo.DeepCopy((1, 0, 0, 0,
                                    0, 1, 0, 0,
                                    0, 0, 1, z_index * spacing[2], # this only works when the image direction vector is unit vector
                                    0, 0, 0, 1))
        elif axis == 1: # coronal
            y_index = self.slider.value()
            imgo_H_sliceo.DeepCopy((1, 0, 0, 0,
                            0, 0, -1, y_index * spacing[1],  # this only works when the image direction vector is unit vector
                            0, 1, 0, 0,
                            0, 0, 0, 1))
        elif axis == 0: # sagittal
            x_index = self.slider.value()
            imgo_H_sliceo.DeepCopy((0, 0, -1, x_index * spacing[0],  # this only works when the image direction vector is unit vector
                                    0, 1, 0, 0,
                                    1, 0, 0, 0,
                                    0, 0, 0, 1))
        else:
            raise Exception(f'invalid axis: {axis}')
            
        reslice.SetResliceAxes(imgo_H_sliceo)
        reslice.Update()
        self.render()

        print(f'=== update_slice({self.orientation}) ===')
        print(f'axix={axis}')
        print(f'spacing={spacing}')
        print(f'origin={origin}')
        print(f'slice_pos={slice_pos}')
        print(f'')

        import itkvtk
        self.reslice.Update()
        slice = self.reslice.GetOutput()
        itkvtk.save_vtk_image_using_sitk(slice, f'{self.orientation}.mhd')

    def render(self):
        self.render_window.Render()

class VTK3DViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.renderer = vtk.vtkRenderer()
        self.interactor = QVTKRenderWindowInteractor(self)
        self.render_window = self.interactor.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        layout = QVBoxLayout()
        layout.addWidget(self.interactor)
        self.setLayout(layout)

        self.volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        self.volume = vtk.vtkVolume()
        self.volume.SetMapper(self.volume_mapper)
        self.renderer.AddVolume(self.volume)

    def set_image(self, vtk_image):
        self.volume_mapper.SetInputData(vtk_image)
        self.renderer.ResetCamera()
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
        self.surface_viewer = VTK3DViewer()

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

        #m = vtk_image.GetDirectionMatrix()
        #print(m)


        vtk_image.SetSpacing([1.0, 1.0, 1.0])
        spacing = vtk_image.GetSpacing()
        print(f'spacing={spacing}')

        self.axial_viewer.set_image(vtk_image)
        self.coronal_viewer.set_image(vtk_image)
        self.sagittal_viewer.set_image(vtk_image)
        self.surface_viewer.set_image(vtk_image)

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