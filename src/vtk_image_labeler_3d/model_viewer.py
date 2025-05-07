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

        # delayed rendering
        from PyQt5.QtCore import QTimer
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render)
        self.delayed_render_ms = 500

        # contour surface update timer
        self.surface_update_timer = QTimer()
        self.surface_update_timer.setSingleShot(True)
        self.surface_update_timer.timeout.connect(self._do_surface_update)

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

        self.segmentation_surfaces = {}

    def get_interactor(self):
        return self.interactor

    def get_renderer(self):
        return self.renderer
    
    def get_render_window(self):
        return self.render_window
    
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

    def render_delayed(self):
        self.render_timer.start(self.delayed_render_ms)  # delay render by 20 ms

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

    def set_segmentation_layers(self, segmentaiton_layers):
        self.segmentaiton_layers = segmentaiton_layers

    def on_segmentation_layer_added(self, layer_name, sender):
        print(f'SurfaceViewer: on_segmentation_layer_added(layername={layer_name}')

        import segmentation_surface
        seg_item = self.segmentaiton_layers[layer_name]
        seg_surface = segmentation_surface.SegmentationSurface(seg_item=seg_item, renderer=self.get_renderer(), render_window=self.get_render_window())
        self.segmentation_surfaces[layer_name] = seg_surface

        seg_item.visibility_changed.connect(self.on_layer_visibility_changed)
        seg_item.name_changed.connect(self.on_layer_name_changed)
        seg_item.color_changed.connect(self.on_layer_color_changed)

    def on_layer_visibility_changed(self, sender): 
        seg_item = sender
        name = seg_item.get_name()
        self.segmentation_surfaces[name].update()
        self.render()

    def on_layer_name_changed(self, old_layer_name, sender):
        new_layer_name = sender.get_name()
        print(f'name changed from {old_layer_name} to {new_layer_name}')

        if old_layer_name in self.segmentation_surfaces:
            self.segmentation_surfaces[new_layer_name] = self.segmentation_surfaces.pop(old_layer_name)
        else:
            print(f'Warning: layer {old_layer_name} not found in segmentation_surfaces')

    def on_layer_color_changed(self, sender):
        seg_item = sender
        name = seg_item.get_name()
        self.segmentation_surfaces[name].update()
        self.render()
        
    def on_segmentation_layer_modified(self, layer_name, sender):
        self.pending_layer = layer_name
        self.surface_update_timer.start(1000)  # wait 1000ms before updating

    def _do_surface_update(self):
        layer_name = self.pending_layer
        print(f'SurfaceViewer: _do_surface_update(layername={layer_name})')
        if layer_name in self.segmentation_surfaces:
            self.segmentation_surfaces[layer_name].update_surface_async()

    def on_segmentation_layer_removed(self, layer_name, sender):
        print(f'SurfaceViewer: on_segmentation_layer_removed(layername={layer_name}')
        
        seg_surface = self.segmentation_surfaces.pop(layer_name)
        for actor in seg_surface.get_actors():
            self.get_renderer().RemoveActor(actor)

        self.render()     


