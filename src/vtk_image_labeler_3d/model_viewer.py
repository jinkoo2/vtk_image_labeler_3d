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

class Model():
    def __init__(self, name):
        self.name = name

class SingleActorModel(Model):
    def __init__(self, name, actor):
        super().__init__(name)
        self.actor = actor

    def set_visibility(self, flag):
        self.actor.SetVisibility(flag)

class ModelList():
    def __init__(self):
        self.list = {}

    def add_model(self, name, model):
        self.list[name] = model

    def get_model(self, name):
        return self.list[name]
        
    def get_model_names(self):
        return list(self.list.keys())
    

        
class ModelViewer(QWidget):
    
    status_message = pyqtSignal(str, QObject)

    def __init__(self, main_window=None):
        super().__init__()
    
        self.main_window = main_window

        # delayed rendering
        from PyQt5.QtCore import QTimer
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._on_render_timer_timedout)

        # contour surface update timer
        self.surface_update_timer = QTimer()
        self.surface_update_timer.setSingleShot(True)
        self.surface_update_timer.timeout.connect(self._on_surface_update_timer_timeout)

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
        self.models = ModelList()

    def get_interactor(self):
        return self.interactor

    def get_renderer(self):
        return self.renderer
    
    def get_render_window(self):
        return self.render_window
    
    def _add_image_boundary_surface_model(self):
        # Create outline filter
        outline_filter = vtk.vtkOutlineFilter()
        outline_filter.SetInputData(self.vtk_image)

        # Mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(outline_filter.GetOutputPort())

        outline_actor = vtk.vtkActor()
        outline_actor.SetMapper(mapper)
        outline_actor.GetProperty().SetColor(0.8, 0.8, 0.8)  
        outline_actor.GetProperty().SetLineWidth(2.0)

        self.add_actor_as_model("image", outline_actor)

    def set_vtk_image(self, vtk_image):
        self.vtk_image = vtk_image
        
        self._add_image_boundary_surface_model()
        
        self.renderer.ResetCamera()
        
        self.render_window.Render()

    def add_actor_as_model(self, name, actor):
        model  = SingleActorModel(name, actor)
        self.models.add_model(name, model)
        self.renderer.AddActor(actor)

    def set_model_visibility(self, name, flag):
        self.models.get_model(name).set_visibility(flag)

    def set_active(self, active=True):
        self.active = active
        if active:
            self.renderer.SetBackground(*background_color_active)  
        else:
            self.renderer.SetBackground(*background_color)  
        self.render()

    def render(self):
        self.render_window.Render()

    def render_delayed(self, delayed_render_ms=100):
        self.render_timer.start(delayed_render_ms)  

    def _on_render_timer_timedout(self):
        self.render()

    def _on_surface_update_timer_timeout(self):
        layer_name = self.pending_layer
        print(f'SurfaceViewer: _do_surface_update(layername={layer_name})')
        if layer_name in self.segmentation_surfaces:
            self.segmentation_surfaces[layer_name].update_surface_async()

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
        seg_item.color_changed.connect(self.on_segmentation_layer_color_changed)
        seg_item.alpha_changed.connect(self.on_segmentation_layer_alpha_changed)

    def on_layer_visibility_changed(self, sender): 
        seg_item = sender
        name = seg_item.get_name()
        self.segmentation_surfaces[name].update_actors()
        self.render()

    def on_layer_name_changed(self, old_layer_name, sender):
        new_layer_name = sender.get_name()
        print(f'name changed from {old_layer_name} to {new_layer_name}')

        if old_layer_name in self.segmentation_surfaces:
            self.segmentation_surfaces[new_layer_name] = self.segmentation_surfaces.pop(old_layer_name)
        else:
            print(f'Warning: layer {old_layer_name} not found in segmentation_surfaces')

    def on_segmentation_layer_color_changed(self, sender):
        seg_item = sender
        name = seg_item.get_name()
        self.segmentation_surfaces[name].update_actors()
        self.render()
    
    def on_segmentation_layer_alpha_changed(self, sender):
        seg_item = sender
        name = seg_item.get_name()
        self.segmentation_surfaces[name].update_actors()
        self.render_delayed(100)

    def on_segmentation_layer_modified(self, layer_name, sender):
        self.pending_layer = layer_name
        self.surface_update_timer.start(1000)  # wait 1000ms before updating

    def on_segmentation_layer_removed(self, layer_name, sender):
        print(f'SurfaceViewer: on_segmentation_layer_removed(layername={layer_name}')
        
        seg_surface = self.segmentation_surfaces.pop(layer_name)
        for actor in seg_surface.get_actors():
            self.get_renderer().RemoveActor(actor)

        self.render()     


