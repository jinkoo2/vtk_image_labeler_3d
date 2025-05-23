# import sys
# import vtk
# import SimpleITK as sitk
# from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QDockWidget, 
#                              QToolBar, QAction, QListWidget, QListWidgetItem, QHBoxLayout, QGridLayout, QSlider,
#                              QPushButton, QCheckBox, QLabel, QColorDialog, QFileDialog)
# from PyQt5.QtCore import Qt, QObject, pyqtSignal
# from PyQt5.QtGui import QColor
# from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
# import numpy as np

# # Custom class to manage 3D annotations (unchanged)
# class AnnotationManager(QObject):
#     log_message = pyqtSignal(str, str)

#     def __init__(self, viewers, name="Annotations"):
#         super().__init__()
#         self.viewers = viewers
#         self.annotations = {}
#         self.name = name
#         self.color_rotator = ColorRotator()

#     def setup_ui(self):
#         dock = QDockWidget(self.name)
#         widget = QWidget()
#         layout = QVBoxLayout()

#         self.list_widget = QListWidget()
#         self.list_widget.currentItemChanged.connect(self.on_item_changed)
#         layout.addWidget(self.list_widget)

#         button_layout = QHBoxLayout()
#         for btn_text, func in [("Add Segmentation", self.add_segmentation), 
#                                ("Add Box", self.add_box), 
#                                ("Add Line", self.add_line), 
#                                ("Add Point", self.add_point)]:
#             btn = QPushButton(btn_text)
#             btn.clicked.connect(func)
#             button_layout.addWidget(btn)
#         layout.addLayout(button_layout)

#         widget.setLayout(layout)
#         dock.setWidget(widget)
#         return None, dock

#     def add_segmentation(self):
#         name = self.generate_unique_name("Segmentation")
#         color = self.color_rotator.next()
#         segmentation = self.create_empty_segmentation()
#         actor = self.create_segmentation_actor(segmentation, color)
#         for viewer in self.viewers:
#             viewer.renderer.AddActor(actor)
#         self.annotations[name] = {"type": "segmentation", "data": segmentation, "actor": actor, "color": color, "visible": True}
#         self.add_to_list(name)

#     def add_box(self):
#         name = self.generate_unique_name("Box")
#         color = self.color_rotator.next()
#         box_widget = vtk.vtkBoxWidget()
#         box_widget.SetInteractor(self.viewers[3].interactor)
#         box_widget.SetPlaceFactor(1.0)
#         box_widget.PlaceWidget(self.viewers[3].vtk_image.GetBounds())
#         box_widget.On()
#         self.annotations[name] = {"type": "box", "data": box_widget, "color": color, "visible": True}
#         self.add_to_list(name)

#     def add_line(self):
#         name = self.generate_unique_name("Line")
#         color = self.color_rotator.next()
#         line_widget = vtk.vtkLineWidget()
#         line_widget.SetInteractor(self.viewers[3].interactor)
#         line_widget.SetPlaceFactor(1.0)
#         line_widget.PlaceWidget(self.viewers[3].vtk_image.GetBounds())
#         line_widget.On()
#         self.annotations[name] = {"type": "line", "data": line_widget, "color": color, "visible": True}
#         self.add_to_list(name)

#     def add_point(self):
#         name = self.generate_unique_name("Point")
#         color = self.color_rotator.next()
#         sphere = vtk.vtkSphereSource()
#         sphere.SetRadius(5.0)
#         sphere.SetCenter(self.viewers[3].vtk_image.GetCenter())
#         mapper = vtk.vtkPolyDataMapper()
#         mapper.SetInputConnection(sphere.GetOutputPort())
#         actor = vtk.vtkActor()
#         actor.SetMapper(mapper)
#         actor.GetProperty().SetColor(color[0]/255, color[1]/255, color[2]/255)
#         for viewer in self.viewers:
#             viewer.renderer.AddActor(actor)
#         self.annotations[name] = {"type": "point", "data": actor, "color": color, "visible": True}
#         self.add_to_list(name)

#     def create_empty_segmentation(self):
#         image_data = self.viewers[0].vtk_image
#         segmentation = vtk.vtkImageData()
#         segmentation.SetDimensions(image_data.GetDimensions())
#         segmentation.SetSpacing(image_data.GetSpacing())
#         segmentation.SetOrigin(image_data.GetOrigin())
#         segmentation.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
#         segmentation.GetPointData().GetScalars().Fill(0)
#         return segmentation

#     def create_segmentation_actor(self, segmentation, color):
#         lookup_table = vtk.vtkLookupTable()
#         lookup_table.SetNumberOfTableValues(2)
#         lookup_table.SetTableRange(0, 1)
#         lookup_table.SetTableValue(0, 0, 0, 0, 0)
#         lookup_table.SetTableValue(1, color[0]/255, color[1]/255, color[2]/255, 0.5)
#         lookup_table.Build()
#         mapper = vtk.vtkImageMapToColors()
#         mapper.SetInputData(segmentation)
#         mapper.SetLookupTable(lookup_table)
#         actor = vtk.vtkImageActor()
#         actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
#         return actor

#     def add_to_list(self, name):
#         item_widget = AnnotationItemWidget(name, self.annotations[name], self)
#         item = QListWidgetItem()
#         item.setSizeHint(item_widget.sizeHint())
#         self.list_widget.addItem(item)
#         self.list_widget.setItemWidget(item, item_widget)
#         self.render_all()

#     def generate_unique_name(self, base):
#         index = 1
#         while f"{base} {index}" in self.annotations:
#             index += 1
#         return f"{base} {index}"

#     def on_item_changed(self, current, previous):
#         if current:
#             item_widget = self.list_widget.itemWidget(current)
#             name = item_widget.name
#             for key, ann in self.annotations.items():
#                 if key != name and ann["type"] in ["segmentation", "point"]:
#                     ann["data"].GetProperty().SetOpacity(0.3 if ann["visible"] else 0)
#                 elif key == name and ann["type"] in ["segmentation", "point"]:
#                     ann["data"].GetProperty().SetOpacity(0.5 if ann["visible"] else 0)
#             self.render_all()

#     def remove_annotation(self, name):
#         ann = self.annotations.pop(name)
#         if ann["type"] in ["segmentation", "point"]:
#             for viewer in self.viewers:
#                 viewer.renderer.RemoveActor(ann["data"])
#         elif ann["type"] in ["box", "line"]:
#             ann["data"].Off()
#         item, _ = self.find_item_by_name(name)
#         self.list_widget.takeItem(self.list_widget.row(item))
#         self.render_all()

#     def find_item_by_name(self, name):
#         for i in range(self.list_widget.count()):
#             item = self.list_widget.item(i)
#             widget = self.list_widget.itemWidget(item)
#             if widget.name == name:
#                 return item, widget
#         return None, None

#     def render_all(self):
#         for viewer in self.viewers:
#             viewer.render_window.Render()

# # Custom widget for annotation list items (unchanged)
# class AnnotationItemWidget(QWidget):
#     def __init__(self, name, ann_data, manager):
#         super().__init__()
#         self.name = name
#         self.ann_data = ann_data
#         self.manager = manager
#         layout = QHBoxLayout()
#         self.checkbox = QCheckBox()
#         self.checkbox.setChecked(ann_data["visible"])
#         self.checkbox.stateChanged.connect(self.toggle_visibility)
#         layout.addWidget(self.checkbox)
#         self.color_patch = QLabel()
#         self.color_patch.setFixedSize(16, 16)
#         self.color_patch.setStyleSheet(f"background-color: rgb({ann_data['color'][0]}, {ann_data['color'][1]}, {ann_data['color'][2]}); border: 1px solid black;")
#         self.color_patch.mousePressEvent = self.change_color
#         layout.addWidget(self.color_patch)
#         layout.addWidget(QLabel(name))
#         remove_btn = QPushButton("X")
#         remove_btn.clicked.connect(self.remove)
#         layout.addWidget(remove_btn)
#         self.setLayout(layout)

#     def toggle_visibility(self, state):
#         self.ann_data["visible"] = state == Qt.Checked
#         if self.ann_data["type"] in ["segmentation", "point"]:
#             self.ann_data["data"].SetVisibility(self.ann_data["visible"])
#         elif self.ann_data["type"] in ["box", "line"]:
#             self.ann_data["data"].SetEnabled(self.ann_data["visible"])
#         self.manager.render_all()

#     def change_color(self, event):
#         color = QColorDialog.getColor(QColor(*self.ann_data["color"]), self)
#         if color.isValid():
#             c = [color.red(), color.green(), color.blue()]
#             self.ann_data["color"] = c
#             self.color_patch.setStyleSheet(f"background-color: rgb({c[0]}, {c[1]}, {c[2]}); border: 1px solid black;")
#             if self.ann_data["type"] == "segmentation":
#                 self.manager.create_segmentation_actor(self.ann_data["data"], c)
#             elif self.ann_data["type"] == "point":
#                 self.ann_data["data"].GetProperty().SetColor(c[0]/255, c[1]/255, c[2]/255)
#             self.manager.render_all()

#     def remove(self):
#         self.manager.remove_annotation(self.name)

# # ColorRotator (unchanged)
# class ColorRotator:
#     def __init__(self):
#         self.colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255)]
#         self.index = 0

#     def next(self):
#         color = self.colors[self.index]
#         self.index = (self.index + 1) % len(self.colors)
#         return color

# class VTKViewer(QWidget):
#     slice_changed = pyqtSignal(int, str)  # Signal to emit when slice changes

#     def __init__(self, orientation="axial", parent=None):
#         super().__init__(parent)
#         self.orientation = orientation
#         self.vtk_widget = QVTKRenderWindowInteractor(self)
#         self.render_window = self.vtk_widget.GetRenderWindow()
#         self.renderer = vtk.vtkRenderer()
#         self.render_window.AddRenderer(self.renderer)
#         self.interactor = self.render_window.GetInteractor()
#         self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleImage())

#         # Layout
#         layout = QVBoxLayout()
#         layout.addWidget(self.vtk_widget)

#         # Slider for slice control
#         self.slider = QSlider(Qt.Horizontal)
#         self.slider.setMinimum(0)
#         self.slider.setMaximum(0)
#         self.slider.valueChanged.connect(self.on_slider_changed)
#         layout.addWidget(self.slider)

#         self.setLayout(layout)
#         self.vtk_image = None
#         self.reslicer = None
#         self.slice_actor = None
#         self.current_slice = 0

#     def set_image(self, vtk_image):
#         self.vtk_image = vtk_image
#         self.reslicer = vtk.vtkImageReslice()
#         self.reslicer.SetInputData(vtk_image)

#         # Get image extent
#         extent = vtk_image.GetExtent()
#         dims = [extent[1] - extent[0] + 1, extent[3] - extent[2] + 1, extent[5] - extent[4] + 1]

#         # Set reslice axes and initial slice position
#         if self.orientation == "axial":
#             self.reslicer.SetResliceAxesDirectionCosines(1, 0, 0, 0, 1, 0, 0, 0, 1)
#             center_slice = dims[2] // 2  # Z-axis
#             self.slider.setMaximum(dims[2] - 1)
#         elif self.orientation == "coronal":
#             self.reslicer.SetResliceAxesDirectionCosines(1, 0, 0, 0, 0, 1, 0, 1, 0)
#             center_slice = dims[1] // 2  # Y-axis
#             self.slider.setMaximum(dims[1] - 1)
#         elif self.orientation == "sagittal":
#             self.reslicer.SetResliceAxesDirectionCosines(0, 1, 0, 0, 0, 1, 1, 0, 0)
#             center_slice = dims[0] // 2  # X-axis
#             self.slider.setMaximum(dims[0] - 1)
#         else:  # 3D view
#             # Configure volume rendering
#             volume_mapper = vtk.vtkSmartVolumeMapper()
#             volume_mapper.SetInputData(vtk_image)
#             volume = vtk.vtkVolume()
#             volume.SetMapper(volume_mapper)
#             volume_property = vtk.vtkVolumeProperty()
#             color_func = vtk.vtkColorTransferFunction()
#             color_func.AddRGBPoint(0, 0.0, 0.0, 0.0)
#             color_func.AddRGBPoint(255, 1.0, 1.0, 1.0)
#             opacity_func = vtk.vtkPiecewiseFunction()
#             opacity_func.AddPoint(0, 0.0)
#             opacity_func.AddPoint(255, 1.0)
#             volume_property.SetColor(color_func)
#             volume_property.SetScalarOpacity(opacity_func)
#             volume_property.ShadeOn()
#             volume.SetProperty(volume_property)
#             self.renderer.AddVolume(volume)

#             # Add orientation marker
#             cube = vtk.vtkAnnotatedCubeActor()
#             # Set face texts individually
#             cube.SetXPlusFaceText("R")   # Right
#             cube.SetXMinusFaceText("L")  # Left
#             cube.SetYPlusFaceText("A")   # Anterior
#             cube.SetYMinusFaceText("P")  # Posterior
#             cube.SetZPlusFaceText("S")   # Superior
#             cube.SetZMinusFaceText("I")  # Inferior
#             cube.GetTextEdgesProperty().SetColor(1, 1, 1)
#             cube.GetCubeProperty().SetColor(0, 1, 0)
#             marker = vtk.vtkOrientationMarkerWidget()
#             marker.SetOrientationMarker(cube)
#             marker.SetInteractor(self.interactor)
#             marker.SetViewport(0.0, 0.0, 0.2, 0.2)
#             marker.SetEnabled(1)
#             marker.InteractiveOff()

#             self.renderer.ResetCamera()
#             self.render_window.Render()
#             self.slider.hide()
#             return

#         self.reslicer.SetOutputDimensionality(2)

#         # Set initial slice position to center
#         origin = list(vtk_image.GetOrigin())
#         spacing = list(vtk_image.GetSpacing())
#         if self.orientation == "axial":
#             origin[2] += center_slice * spacing[2]
#         elif self.orientation == "coronal":
#             origin[1] += center_slice * spacing[1]
#         elif self.orientation == "sagittal":
#             origin[0] += center_slice * spacing[0]
#         self.reslicer.SetResliceAxesOrigin(origin)

#         self.reslicer.Update()

#         # Create and add actor with vtkImageSliceMapper
#         mapper = vtk.vtkImageSliceMapper()
#         mapper.SetInputConnection(self.reslicer.GetOutputPort())
#         self.slice_actor = vtk.vtkImageSlice()
#         self.slice_actor.SetMapper(mapper)
#         self.renderer.AddActor(self.slice_actor)

#         # Add orientation labels
#         labels = {
#             "axial": [("A", 0.9, 0.9), ("P", 0.9, 0.1), ("L", 0.1, 0.5), ("R", 0.9, 0.5)],
#             "coronal": [("S", 0.9, 0.9), ("I", 0.9, 0.1), ("L", 0.1, 0.5), ("R", 0.9, 0.5)],
#             "sagittal": [("A", 0.9, 0.9), ("P", 0.9, 0.1), ("S", 0.1, 0.5), ("I", 0.9, 0.5)]
#         }
#         for label, x, y in labels[self.orientation]:
#             text_actor = vtk.vtkTextActor()
#             text_actor.SetInput(label)
#             text_actor.GetTextProperty().SetColor(0, 1, 0)
#             text_actor.GetTextProperty().SetFontSize(20)
#             text_actor.SetDisplayPosition(int(x * self.render_window.GetSize()[0]), int(y * self.render_window.GetSize()[1]))
#             self.renderer.AddActor2D(text_actor)

#         self.renderer.ResetCamera()
#         self.render_window.Render()

#         # Set slider to center position
#         self.current_slice = center_slice
#         self.slider.setValue(center_slice)
        
#     def on_slider_changed(self, value):
#         if not self.vtk_image or not self.reslicer or self.orientation == "3d":
#             return
#         self.current_slice = value
#         self.update_slice_position()
#         self.slice_changed.emit(value, self.orientation)

#     def update_slice_position(self):
#         if not self.vtk_image or not self.reslicer:
#             return
#         origin = list(self.vtk_image.GetOrigin())
#         spacing = list(self.vtk_image.GetSpacing())
#         if self.orientation == "axial":
#             origin[2] += self.current_slice * spacing[2]
#         elif self.orientation == "coronal":
#             origin[1] += self.current_slice * spacing[1]
#         elif self.orientation == "sagittal":
#             origin[0] += self.current_slice * spacing[0]
#         self.reslicer.SetResliceAxesOrigin(origin)
#         self.reslicer.Update()
#         self.render_window.Render()

#     def set_slice_position(self, value, sender_orientation):
#         if self.orientation == "3d" or self.orientation == sender_orientation:
#             return
#         self.current_slice = value
#         self.slider.setValue(value)
#         self.update_slice_position()

# # Main Application
# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.vtk_image = None

#         self.setWindowTitle("3D Image Viewer")
#         self.central_widget = QWidget()
#         self.setCentralWidget(self.central_widget)
#         layout = QGridLayout(self.central_widget)

#         # Create four viewers
#         self.viewers = [
#             VTKViewer("axial", self),
#             VTKViewer("3d", self),
#             VTKViewer("coronal", self),
#             VTKViewer("sagittal", self)
#         ]

#         # Arrange viewers in a 2x2 grid
#         layout.addWidget(self.viewers[0], 0, 0)  # Axial
#         layout.addWidget(self.viewers[1], 0, 1)  # 3D
#         layout.addWidget(self.viewers[2], 1, 0)  # Coronal
#         layout.addWidget(self.viewers[3], 1, 1)  # Sagittal

#         # Connect viewers for slice synchronization
#         for viewer in self.viewers:
#             viewer.slice_changed.connect(self.sync_slices)

#         # Toolbar
#         toolbar = QToolBar("Tools")
#         self.addToolBar(toolbar)
#         load_action = QAction("Load Image", self)
#         load_action.triggered.connect(self.load_image_clicked)
#         toolbar.addAction(load_action)

#         # Annotation Manager
#         self.ann_manager = AnnotationManager(self.viewers)
#         _, dock = self.ann_manager.setup_ui()
#         self.addDockWidget(Qt.RightDockWidgetArea, dock)

#         # Test image (commented out since paths are specific)
#         # image_path = 'C:/Users/jkim20/Documents/projects/vtk_image_labeler_3d/sample_data/Dataset101_Eye[ul]L/imagesTr/eye[ul]l_0_0000.mha'
#         # self.load_image_mha(image_path)

#     def sync_slices(self, value, orientation):
#         for viewer in self.viewers:
#             viewer.set_slice_position(value, orientation)

#     def closeEvent(self, event):
#         if self.vtk_image is not None:
#             self.close_image()
#         event.accept()

#     def load_image_mha(self, file_path):
#         # Read image using SimpleITK
#         sitk_image = sitk.ReadImage(file_path)
#         vtk_image = vtk.vtkImageData()

#         # Convert SimpleITK image to numpy array
#         array = sitk.GetArrayFromImage(sitk_image)
#         array = np.transpose(array, (2, 1, 0))  # VTK expects (x, y, z)

#         # Create VTK image
#         vtk_image.SetDimensions(array.shape)
#         vtk_image.SetSpacing(sitk_image.GetSpacing())
#         vtk_image.SetOrigin(sitk_image.GetOrigin())
#         vtk_image.AllocateScalars(vtk.VTK_FLOAT, 1)

#         # Copy data to VTK image
#         vtk_array = vtk.vtkFloatArray()
#         vtk_array.SetNumberOfTuples(array.size)
#         flat_array = array.ravel()
#         for i in range(len(flat_array)):
#             vtk_array.SetTuple1(i, flat_array[i])
#         vtk_image.GetPointData().SetScalars(vtk_array)

#         # Normalize origin and spacing for simplicity
#         vtk_image.SetOrigin([0.0, 0.0, 0.0])
#         vtk_image.SetSpacing([1.0, 1.0, 1.0])

#         # Update viewers
#         for viewer in self.viewers:
#             viewer.set_image(vtk_image)

#         self.vtk_image = vtk_image

#     def load_image_clicked(self):
#         file_path, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "MHA Files (*.mha);;All Files (*)")
#         if file_path:
#             self.load_image_mha(file_path)

#     def close_image(self):
#         if hasattr(self, 'vtk_image') and self.vtk_image is not None:
#             for viewer in self.viewers:
#                 actors = viewer.renderer.GetActors()
#                 actors.InitTraversal()
#                 actor = actors.GetNextItem()
#                 while actor:
#                     viewer.renderer.RemoveActor(actor)
#                     actor = actors.GetNextItem()
#                 viewer.renderer.ResetCamera()
#                 viewer.render_window.Render()
#                 viewer.vtk_image = None

#             # Clear annotations
#             self.ann_manager.annotations.clear()
#             self.ann_manager.list_widget.clear()

#             self.vtk_image = None
#             print("Image closed and resources cleared.")

# def main():
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec_())

# if __name__ == "__main__":
#     main()