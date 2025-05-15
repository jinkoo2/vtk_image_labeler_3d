
from PyQt5.QtCore import QObject, QThread, pyqtSignal
import vtk


class ContourWorker(QObject):
    finished = pyqtSignal(vtk.vtkPolyData)

    def __init__(self, segmentation_volume):
        super().__init__()
        self.segmentation_volume = segmentation_volume

    def run(self):
        contour = vtk.vtkContourFilter()
        contour.SetInputData(self.segmentation_volume)
        contour.SetValue(0, 0.5)
        contour.Update()
        polydata = vtk.vtkPolyData()
        polydata.DeepCopy(contour.GetOutput())  # Important!
        self.finished.emit(polydata)

import vtk

class SegmentationLayerSurface():
    def __init__(self, layer, renderer=None, render_window=None):

        self.layer = layer
        self.renderer = renderer
        self.render_window = render_window

        self._create_surface_actor()

        self.update_surface_async()

    def _create_surface_actor(self):
        # Extract border from segmentation
        #self.contour_filter = vtk.vtkContourFilter()
        #self.contour_filter.SetInputData(self.seg_item.segmentation)
        #self.contour_filter.SetValue(0, 0.5)
        #self.contour_filter.Update()
        
        self.surface_mapper = vtk.vtkPolyDataMapper()
        #self.surface_mapper.SetInputConnection(self.contour_filter.GetOutputPort())
        self.surface_mapper.ScalarVisibilityOff()  

        self.surface_actor = vtk.vtkActor()
        self.surface_actor.SetMapper(self.surface_mapper)
        self.surface_actor.GetProperty().SetColor(*self.layer.get_vtk_color())
        self.surface_actor.GetProperty().SetLighting(True)
        self.surface_actor.GetProperty().SetLineWidth(1.0)

        self.update_actors()

        if self.renderer:
            for actor in self.get_actors():
                self.renderer.AddActor(actor)

    def get_actors(self):
        return [self.surface_actor]

    def update_actors(self):
        self.surface_actor.SetVisibility(self.layer.get_visible())
        self.surface_actor.GetProperty().SetColor(*self.layer.get_vtk_color())
        self.surface_actor.GetProperty().SetOpacity(self.layer.get_alpha())
        

    def update_surface_async(self):
        self.thread = QThread()
        self.worker = ContourWorker(self.layer.get_image())
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_surface_ready)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_surface_ready(self, polydata):
        self.surface_mapper.SetInputData(polydata)
        self.surface_mapper.Update()
        if self.render_window:
            self.render_window.Render()

        
from typing import List
class SegmentationLayerSurfaceList():

    def __init__(self):
        self._surfaces: List[SegmentationLayerSurface] = []
    
    def clear(self):
        self._surfaces.clear()

    def get_surface_by_layer_name(self, name):
        for surface in self._surfaces:
            if surface.layer.get_name() == name:
                return surface
        return None

    def add_surface(self, surface):
        
        # add list as parent
        surface.parent_list = self

        # add to the list
        self._surfaces.append(surface)

    
    def remove_surface_by_layer_name(self,name):
        surface = self.get_surface_by_layer_name(name)
        if surface:

            surface.parent_list = None

            self._surfaces.remove(surface)

            return surface
        
        return None
        
    def pop(self, name):
        return self.remove_surface_by_layer_name(name)
    
    def get_surfaces(self):
        return self._surfaces
    
    def get_layer_names(self):
        return [surface.layer.get_name() for surface in self.get_surfaces()]



      