import vtk
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5.QtWidgets import (QVBoxLayout, QWidget)

from logger import logger, _info

import numpy as np

background_color = (0.5, 0.5, 0.5)
background_color_active = (0.6, 0.6, 0.6)

from PyQt5.QtCore import pyqtSignal, QObject

class ModelViewer(QWidget):
    
    status_message = pyqtSignal(str, QObject)

    def __init__(self, main_window=None):
        super().__init__()
    
        self.main_window = main_window

        # Create a VTK Renderer
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetLayer(0)
        self.renderer.SetBackground(*background_color)  # Set background to gray
        self.renderer.GetActiveCamera().SetParallelProjection(False)
        self.renderer.SetInteractive(True)

        # Create a QVTKRenderWindowInteractor
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.render_window = self.vtk_widget.GetRenderWindow()  # Retrieve the render window
        self.render_window.AddRenderer(self.renderer)

        # Set up interactor style
        self.interactor = self.render_window.GetInteractor()

        from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
        self.interactor_style = vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(self.interactor_style)

        # Layout for embedding the VTK widget
        layout = QVBoxLayout()
        layout.addWidget(self.vtk_widget)
        self.setLayout(layout)

        self.vtk_image = None

        self.set_active(False)

    def set_vtk_image(self, vtk_image):
        self.vtk_image = vtk_image
        self.renderer.ResetCamera()
        self.render_window.Render()

    def add_actor(self, actor):
        self.renderer.AddActor(actor)

    def set_active(self, active=True):
        self.active = active
        if active:
            self.renderer.SetBackground(*background_color_active)  
        else:
            self.renderer.SetBackground(*background_color)  
        self.render()

    def render(self):
        self.render_window.Render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'render_window') and self.render_window is not None:
            self.render_window.SetSize(self.width(), self.height())
            self.render_window.Render()

    def cleanup_vtk(self, event):
        if hasattr(self, 'interactor') and self.interactor is not None:
            self.interactor.Disable()
            self.interactor.TerminateApp()
            del self.interactor

        if hasattr(self, 'render_window') and self.render_window is not None:
            self.render_window.Finalize()
            del self.render_window

        super().closeEvent(event)

    def on_segmentation_layer_added(self, layer_name, sender):
        print(f'SurfaceViewer: on_segmentation_layer_added(layername={layer_name}')

    def on_segmentation_layer_removed(self, layer_name, sender):
        print(f'SurfaceViewer: on_segmentation_layer_removed(layername={layer_name}')
        


