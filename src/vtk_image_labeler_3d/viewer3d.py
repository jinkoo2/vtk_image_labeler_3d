import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSlider, QLabel, QHBoxLayout, QGridLayout
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, 
    QFileDialog, QVBoxLayout, QSlider, QPushButton, QLabel, QWidget, QMenuBar, QAction, QToolBar, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit
)
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QListWidgetItem, QColorDialog
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon

from logger import logger, _info

import numpy as np

class LineWidget:
    def __init__(self, vtk_image, pt1_w, pt2_w, line_color_vtk=[1,0,0], line_width=2, renderer=None):
        # Create a ruler using vtkLineWidget2
        widget = vtk.vtkLineWidget2()
        representation = vtk.vtkLineRepresentation()
        widget.SetRepresentation(representation)

        # Set initial position of the ruler
        representation.SetPoint1WorldPosition(pt1_w)
        representation.SetPoint2WorldPosition(pt2_w)
        representation.GetLineProperty().SetColor(line_color_vtk[0],line_color_vtk[1],line_color_vtk[2])  
        representation.GetLineProperty().SetLineWidth(line_width)
        representation.SetVisibility(True)

        representation.text_actor = vtk.vtkTextActor()
        representation.text_actor.GetTextProperty().SetFontSize(12)
        representation.text_actor.GetTextProperty().SetColor(1, 1, 1)  # White color
        
        renderer.AddActor2D(representation.text_actor)

        interactor = renderer.GetRenderWindow().GetInteractor()

        # Set interactor and enable interaction
        if interactor:
            widget.SetInteractor(interactor)

        self.widget = widget
        self.representation = representation
        self.interactor = interactor
        self.renderer = renderer
        self.color_vtk = line_color_vtk
        self.line_width = line_width
        self.vtk_image = vtk_image

        # Attach a callback to update distance when the ruler is moved
        widget.AddObserver("InteractionEvent", lambda obj, event: self.update_ruler_distance())

        # Attach the camera observer
        self.renderer.GetActiveCamera().AddObserver("ModifiedEvent", lambda obj, event: self.update_ruler_distance())

        # Attach the window resize observer
        self.renderer.GetRenderWindow().AddObserver("WindowResizeEvent", lambda obj, event: self.update_ruler_distance())

        self.update_ruler_distance()
    
    def world_to_display(self, renderer, world_coordinates):
        """Convert world coordinates to display coordinates."""
        display_coordinates = [0.0, 0.0, 0.0]
        renderer.SetWorldPoint(*world_coordinates, 1.0)
        renderer.WorldToDisplay()
        display_coordinates = renderer.GetDisplayPoint()
        return display_coordinates

    def update_ruler_distance(self):

        representation = self.representation

        # Calculate the distance
        point1 = representation.GetPoint1WorldPosition()
        point2 = representation.GetPoint2WorldPosition()
        distance = ((point2[0] - point1[0]) ** 2 +
                    (point2[1] - point1[1]) ** 2 +
                    (point2[2] - point1[2]) ** 2) ** 0.5

        print(f"Ruler Distance: {distance:.2f} mm")

        # Update the text actor position 
        midpoint_w = [(point1[i] + point2[i]) / 2 for i in range(3)]
        midpoint_screen = self.world_to_display(self.renderer, midpoint_w)
        representation.text_actor.SetInput(f"{distance:.2f} mm")
        representation.text_actor.SetPosition(midpoint_screen[0], midpoint_screen[1])       

background_color = (0.5, 0.5, 0.5)
background_color_active = (0.6, 0.6, 0.6)

from PyQt5.QtCore import pyqtSignal, QObject

from model_viewer import ModelViewer


from PyQt5.QtCore import pyqtSignal, QObject

class Slicing(QObject):

    slice_changed = pyqtSignal(int, int, QObject)

    def __init__(self, interactor, slice_index = 0, slice_step_size = 1):
        super().__init__()
        self.interactor = interactor
        self.enabled = False
        self.slicing_step_size = slice_step_size
        self.slice_index = slice_index

    def enable(self, enabled=True):
        self.enabled = enabled

        if enabled:
            self.mouse_wheel_forward_observer = self.interactor.AddObserver("MouseWheelForwardEvent", self.on_mouse_wheel_forward)
            self.on_mouse_wheel_backward_observer = self.interactor.AddObserver("MouseWheelBackwardEvent", self.on_mouse_wheel_backward)
            self.key_press_observer = self.interactor.AddObserver("KeyPressEvent", self.on_key_press)
        else:    
            self.interactor.RemoveObserver(self.mouse_wheel_forward_observer)
            self.interactor.RemoveObserver(self.on_mouse_wheel_backward_observer)   
            self.interactor.RemoveObserver(self.key_press_observer)   

        print(f"Slicing mode: {'enabled' if enabled else 'disabled'}")
    
    def set_slice_index(self, new_index):
        if not self.interactor:
            return 
        
        if self.slice_index != new_index:
            
            old_index = self.slice_index 
            
            self.slice_index = new_index

            self.slice_changed.emit(new_index, old_index, self)

    def move_slice_up(self):
        current_index = self.slice_index
        self.slice_index += self.slicing_step_size
        self.slice_changed.emit(self.slice_index, current_index, self)

    def move_slice_down(self):
        current_index = self.slice_index
        self.slice_index -= self.slicing_step_size
        self.slice_changed.emit(self.slice_index, current_index, self)
        
    def on_mouse_wheel_forward(self, obj, event):
        if not self.enabled:
            return
        self.move_slice_up()

    def on_mouse_wheel_backward(self, obj, event):
        if not self.enabled:
            return
        self.move_slice_down()

    def on_key_press(self, obj, event):
        key = self.interactor.GetKeySym()
        if key == "Up":
            self.move_slice_up()
        elif key == "Down":
            self.move_slice_down()

from PyQt5.QtCore import QTimer

class SlicePlaneObject():
    def __init__(self, color):

        self.color = color
        self.plane_source = vtk.vtkPlaneSource()
        self.texture = vtk.vtkTexture()
        self.texture.InterpolateOn()

        self.tex_coords = vtk.vtkFloatArray()
        self.tex_coords.SetNumberOfComponents(2)
        self.tex_coords.SetName("TextureCoordinates")
        self.tex_coords.InsertNextTuple2(0.0, 0.0)
        self.tex_coords.InsertNextTuple2(1.0, 0.0)
        self.tex_coords.InsertNextTuple2(0.0, 1.0)
        self.tex_coords.InsertNextTuple2(1.0, 1.0)

        self.mapper = vtk.vtkPolyDataMapper()

        self.actor = vtk.vtkActor()

        self.vtk_image_slice = None

    def update(self, vtk_texture_image, w_H_sliceo):
        
        self.vtk_image_slice = vtk_texture_image

        dims = vtk_texture_image.GetDimensions()
        spacing = vtk_texture_image.GetSpacing()

        # Image plane corners in index space
        p0_o = np.array([0, 0, 0, 1.0]).reshape(4,1)           # origin
        p1_o = np.array([dims[0]*spacing[0], 0, 0, 1.0]).reshape(4,1)     # along i-axis
        p2_o = np.array([0, dims[1]*spacing[1], 0, 1.0]).reshape(4,1)     # along j-axis

        # points in w
        p0_w = (w_H_sliceo @ p0_o).flatten()[:3]
        p1_w = (w_H_sliceo @ p1_o).flatten()[:3]
        p2_w = (w_H_sliceo @ p2_o).flatten()[:3]
        
        # Create a plane with correct geometry
        self.plane_source.SetOrigin(*p0_w)
        self.plane_source.SetPoint1(*p1_w)
        self.plane_source.SetPoint2(*p2_w)
        self.plane_source.Update()

        # Texture map the slice
        self.texture.SetInputData(vtk_texture_image)

        # Map texture coordinates
        polydata = self.plane_source.GetOutput()
        polydata.GetPointData().SetTCoords(self.tex_coords)

        # mapper
        self.mapper.SetInputData(polydata)

        # actor
        self.actor.SetMapper(self.mapper)
        self.actor.SetTexture(self.texture)

        # keep the points
        self.pt0_w = p0_w
        self.pt1_w = p1_w
        self.pt2_w = p2_w

class SliceIndicator():
    def __init__(self):
        # 1. Create a line from point A to B
        line_source = vtk.vtkLineSource()
        line_source.SetPoint1(0, 0, 0)
        line_source.SetPoint2(0, 0, 0)
        line_source.Update()

        # 2. Mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line_source.GetOutputPort())

        # 3. Actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(1)
        actor.GetProperty().SetColor(1, 1, 1) 

        self.line_source = line_source
        self.mapper = mapper
        self.actor = actor

    def set_points(self, pt0_w, pt1_w):
        self.line_source.SetPoint1(*pt0_w)
        self.line_source.SetPoint2(*pt1_w)
        self.line_source.Update()

    def set_color(self, color):
        self.actor.GetProperty().SetColor(*color) 

from reslicer import ReslicerWithImageActor
from typing import List

class SegmentationLayerReslicerList():

    def __init__(self):
        self._reslicers: List[ReslicerWithImageActor] = []
    
    def clear(self):
        for reslicer in self._reslicers:
            reslicer.clear()
        self._reslicers.clear()

    def get_reslicer_by_layer_name(self, name):
        for reslicer in self._reslicers:
            if reslicer.layer.get_name() == name:
                return reslicer
        return None

    def add_reslicer(self, reslicer):
        
        # add list as parent
        reslicer.parent_list = self

        # add to the list
        self._reslicers.append(reslicer)

    
    def remove_reslicer_by_layer_name(self,name):
        reslicer = self.get_reslicer_by_layer_name(name)
        if reslicer:

            reslicer.parent_list = None

            self._reslicers.remove(reslicer)

            return reslicer
        
        return None
        
    def pop(self, name):
        return self.remove_reslicer_by_layer_name(name)
    
    def get_reslicers(self):
        return self._reslicers
    
    def get_layer_names(self):
        return [reslicer.layer.get_name() for reslicer in self.get_reslicers()]


    # def __getitem__(self, key):
    #     return self.get_reslicer_by_layer_name(key)

    # def __delitem__(self, key):
    #     self.remove_reslicer_by_layer_name(key)

    # def __setitem__(self, key, value):
    #     # if exists, remove first
    #     self.remove_reslicer_by_layer_name(key)

    #     # add layer
    #     self.add_reslicer(value)


    
import viewer2d
import reslicer
class VTKViewer2DWithReslicer(viewer2d.VTKViewer2D):
    
    slice_changed = pyqtSignal(QObject)

    def __init__(self, axis, name, slice_plane_color, parent):
        super().__init__(name=name, parent=parent)

        self.reslicer = reslicer.Reslicer(axis)
        self.vtk_image_3d = None
        self._set_slice(None)
        self.slice_index = None
        self.slicing = Slicing(self.get_interactor())
        self.slicing.slice_changed.connect(self.on_slice_changed)
        self.slicing.enable(True)

        self.segmentation_layer_reslicers = SegmentationLayerReslicerList()

        self.slice_plane_object = SlicePlaneObject(slice_plane_color)
        self.slice_indicators_of_other_views = {}

    def clear(self):
        if self.vtk_image_3d == None:
            return 

        self.reslicer.clear()
        self.vtk_image_3d = None
        self.slice_index = None
        
        for seg_reslicer in self.segmentation_layer_reslicers.get_reslicers():
            for actor in seg_reslicer.get_actors():
                self.get_renderer().RemoveActor(actor)

        self.segmentation_layer_reslicers.clear()

        # hide slice indicators
        for name, slice_indicator in self.slice_indicators_of_other_views.items():
            if slice_indicator.actor:
                slice_indicator.actor.SetVisibility(False)

        super().clear()

    def _set_slice(self, slice):
        self.slice = slice
        self.vtk_image = slice

    def _get_slice(self):
        return self.vtk_image

    def update_slice_indicator(self, source_viewer):

        axis = source_viewer.reslicer.axis
        slice_index = source_viewer.slice_index
        color = source_viewer.slice_plane_object.color
        print(f'update_slice_indicator(axis={axis}, slice_index={slice_index})')

        # plane objects points
        pt0_w = source_viewer.slice_plane_object.pt0_w
        pt1_w = source_viewer.slice_plane_object.pt1_w
        pt2_w = source_viewer.slice_plane_object.pt2_w

        # project to cam near plane
        pt0_w = self.project_world_point_to_camera_near_plane(pt0_w)
        pt1_w = self.project_world_point_to_camera_near_plane(pt1_w)
        pt2_w = self.project_world_point_to_camera_near_plane(pt2_w)

        # find the line of 
        v1 = pt1_w - pt0_w
        v2 = pt2_w - pt0_w

        if np.linalg.norm(v1) > np.linalg.norm(v2):
            pt1_w = pt1_w
        else:
            pt1_w = pt2_w

        if source_viewer.name in self.slice_indicators_of_other_views:
            slice_indicator = self.slice_indicators_of_other_views[source_viewer.name]
        else:
            slice_indicator = SliceIndicator()
            self.get_renderer().AddActor(slice_indicator.actor)
            self.slice_indicators_of_other_views[source_viewer.name] = slice_indicator
            
        slice_indicator.set_points(pt0_w, pt1_w)
        slice_indicator.set_color(color)
         
        self.render()

    def on_slice_changed(self, new_slice_index, old_slice_index, sender):
        print(f'slice_index={new_slice_index}')

        if not self.vtk_image:
            return 

        if self.slice_index == new_slice_index:
            return 
       
        # get the center slice
        new_slice = self.reslicer.get_slice_image(new_slice_index)
    
        self._set_slice(new_slice)
        self.slice_index = new_slice_index
                
        # Connect reader to window/level filter
        self.window_level_filter.SetInputData(new_slice)
        self.window_level_filter.Update()
    
        # update the segmentation reslicers
        for reslicer in self.segmentation_layer_reslicers.get_reslicers():
            if reslicer.layer.get_visible():
                reslicer.set_slice_index_and_update_slice_actor(new_slice_index)

        # update slice plane object
        self.update_slice_plane_object()

        self.slice_changed.emit(self)

        # display slice index
        if self.reslicer.axis == 2:
            self.text_bottom_left.set_text(f"z={self.slice_index}")
        elif self.reslicer.axis == 1:
            self.text_bottom_left.set_text(f"y={self.slice_index}")
        elif self.reslicer.axis == 0:
            self.text_bottom_left.set_text(f"x={self.slice_index}")
        else:
            print(f'invalid axis (axis={self.reslicer.axis})')

        self.render()

    def update_slice_plane_object(self):
        import vtk_image_wrapper
        wrapper = vtk_image_wrapper.vtk_image_wrapper(self._get_slice())
        self.slice_plane_object.update(self.window_level_filter.GetOutput(), wrapper.get_w_H_o())

    def set_window_level(self, window, level):
        if self.window_level_filter:
            self.window_level_filter.SetWindow(window)
            self.window_level_filter.SetLevel(level)
            self.window_level_filter.Update()
            self.get_render_window().Render()

            self.update_slice_plane_object()

    def reset_camera(self):
        if not self.vtk_image_3d:
            print("No image loaded.")
            return

        camera = self.renderer.GetActiveCamera()
        camera.SetParallelProjection(True)

        # set the camera position to the center of the volume
        import vtk_image_wrapper
        wrapper_image3d = vtk_image_wrapper.vtk_image_wrapper(self.vtk_image_3d)

        dims = wrapper_image3d.get_dimensions()
        spacing = wrapper_image3d.get_spacing()
        #w_H_imgo = wrapper.get_w_H_o() # homogenious transform for point transforms from o to w
        #w_R_imgo = w_H_imgo[:3,:3] # rotation matrix for vector transforms from o to w

        w_camera_position = wrapper_image3d.get_center_point_w()
        camera.SetPosition(*w_camera_position)

        import numpy as np

        # central slice coodinate system
        center_slice_index = dims[self.reslicer.axis]//2
        vkt_w_H_center_sliceo = self.reslicer.calculate_axes(center_slice_index)
        import itkvtk
        w_H_center_sliceo = itkvtk.vtk_matrix4x4_to_numpy(vkt_w_H_center_sliceo)

        # viewup and focal point in sliceo
        sliceo_viewup = np.array([0.0, -1.0, 0.0]).reshape(3,1)
        wrapper_slice = vtk_image_wrapper.vtk_image_wrapper(self.vtk_image)
        sliceo_pt_center = wrapper_slice.get_center_point_o()
        sliceo_focal_pt = np.array([sliceo_pt_center[0], sliceo_pt_center[1], 100.0 , 1.0]).reshape(4,1)

        # set the view up vector
        w_R_sliceo = w_H_center_sliceo[:3,:3]
        w_viewup = w_R_sliceo @ sliceo_viewup
        camera.SetViewUp(*w_viewup)

        # set focal point to the far end of the image bound through the image center
        focal_pt_w = (w_H_center_sliceo @ sliceo_focal_pt)[:3]
        camera.SetFocalPoint(*focal_pt_w)
        
        # Set scale based on physical height of image in world space
        max_half_size_physical = (spacing * dims / 2.0).max()
        camera.SetParallelScale(max_half_size_physical)

        # set clip range
        z_near = max_half_size_physical * -3.0
        z_far = max_half_size_physical * 3.0
        camera.SetClippingRange([z_near, z_far])

        self.render_window.Render()

    def set_vtk_image_3d(self, vtk_image_3d, window, level):

        # debug
        #vtk_image_3d.SetOrigin([0.0, 0.0, 0.0])

        self.vtk_image_3d = vtk_image_3d 

        self.reslicer.set_vtk_image(vtk_image_3d)
        
        # get the center slice
        slice, index = self.reslicer.get_slice_image_at_center()
        _info(f'the center slice index is {index}')
        
        # save the slice & slice index
        self._set_slice(slice)
        self.slice_index = index

        self.slicing.set_slice_index(index)

        super().set_vtk_image(slice, window, level)

        self.update_slice_plane_object()

        # show slice indicators
        for name, slice_indicator in self.slice_indicators_of_other_views.items():
            if slice_indicator.actor:
                slice_indicator.actor.SetVisibility(True)


        self.reset_camera()

    def set_segmentation_layers(self, segmentaiton_layers):
        self.segmentaiton_layers = segmentaiton_layers

    def on_segmentation_layer_added(self, layer_name, sender):
        print(f'VTKViewer2DWithReslicer.on_segmentation_layer_added({layer_name})')

        # seg item
        layer = self.segmentaiton_layers[layer_name]
        seg3d = layer.get_image()
        vtk_color = layer.get_vtk_color()
        alpha = layer.get_alpha()
        
        # create a reslicer with actor
        axis = self.reslicer.axis
        slice_index = self.reslicer.slice_index 
        seg_reslicer = reslicer.ReslicerWithImageActor(axis = axis, vtk_image=seg3d, background_value=0, fill_color=vtk_color, fill_alpha=alpha, border_line_color = vtk_color, viewer = self)
        seg_reslicer.layer = layer # reference to the layer
        seg_reslicer.set_slice_index_and_update_slice_actor(slice_index)
        for actor in seg_reslicer.get_actors():
            self.get_renderer().AddActor(actor)
        
        # add to segmentaion reslicer list        
        #layer.reslicer = seg_reslicer # this would not work because layer can have multiple reslicers
        self.segmentation_layer_reslicers.add_reslicer(seg_reslicer)
                
        self.render_delayed(100)

        layer.visibility_changed.connect(self.on_layer_visibility_changed)
        layer.name_changed.connect(self.on_layer_name_changed)
        layer.color_changed.connect(self.on_layer_color_changed)
        layer.alpha_changed.connect(self.on_layer_alpha_changed)
        layer.image_changed.connect(self.on_layer_image_changed)

    def update_slice_and_render(self, layer):
        seg_reslicer = self.segmentation_layer_reslicers.get_reslicer_by_layer_name(layer.get_name())

        if seg_reslicer:
            seg_reslicer.set_slice_index_and_update_slice_actor(self.slice_index)
            
            # if active view, render right away, if not do delayed render.
            if self.active:
                self.render()
            else: 
                self.render_delayed(1000)
        
    def on_segmentation_image_modified(self, layer, sender):
        print(f'VTKViewer2DWithReslicer.on_segmentation_layer_modified({layer})')
        self.update_slice_and_render(layer)

    def on_layer_image_changed(self, sender):
        layer = sender
        print(f'VTKViewer2DWithReslicer.on_layer_image_changed({layer.get_name()})')
        self.update_slice_and_render(layer)

    def on_segmentation_layer_removed(self, layer, sender):
        segmentation_list_manager = sender
        print(f'VTKViewer2DWithReslicer.on_segmentation_layer_removed({layer.get_name()})')

        # remove 
        seg_reslicer = self.segmentation_layer_reslicers.pop(layer.get_name())
        if seg_reslicer:
            for actor in seg_reslicer.get_actors():
                self.get_renderer().RemoveActor(actor)
            self.render()

    def on_layer_visibility_changed(self, sender): 
        layer_name = sender.get_name()
        new_visibility = sender.get_visible()
        print(f'Visibility changed to {new_visibility} for {layer_name}')

        seg_reslicer = self.segmentation_layer_reslicers.get_reslicer_by_layer_name(layer_name)
        if seg_reslicer:
            for actor in seg_reslicer.get_actors():
                actor.SetVisibility(new_visibility)
            self.render()
        else:
            print(f'Layer {layer_name} not found in segmentation_layer_reslicers')

    def on_layer_name_changed(self, old_layer_name, sender):
        new_layer_name = sender.get_name()
        print(f'name changed from {old_layer_name} to {new_layer_name}')

        # if old_layer_name in self.segmentation_layer_reslicers:
        #     self.segmentation_layer_reslicers[new_layer_name] = self.segmentation_layer_reslicers.pop(old_layer_name)
        # else:
        #     print(f'Warning: layer {old_layer_name} not found in segmentation_layer_reslicers')

    def on_layer_color_changed(self, sender):
        
        seg_item = sender
        name = seg_item.get_name()
        vtk_color = seg_item.get_vtk_color()

        print(f'layer [{name}] color changed to {vtk_color}')
        
        seg_reslicer = self.segmentation_layer_reslicers.get_reslicer_by_layer_name(name)

        seg_reslicer.set_color(vtk_color)

        self.render()

    def on_layer_alpha_changed(self, sender):
        
        seg_item = sender
        name = seg_item.get_name()
        alpha = seg_item.get_alpha()

        print(f'layer [{name}] alpha changed to {alpha}')
        
        seg_reslicer = self.segmentation_layer_reslicers.get_reslicer_by_layer_name(name)

        seg_reslicer.set_alpha(alpha)

        self.render()


    def on_active_segmentation_layer_changed(self, sender):
        print(f'VTKViewer2DWithReslicer.on_active_segmentation_layer_changed({sender.get_active_layer().get_name()}')

    def get_mouse_event_coordiantes(self):

        # event data on the 2d slice image
        event_data = super().get_mouse_event_coordiantes()
                
        import vtk_image_wrapper
        slice_wrapper = vtk_image_wrapper.vtk_image_wrapper(self.vtk_image)
        image_wrapper = vtk_image_wrapper.vtk_image_wrapper(self.vtk_image_3d)
        
        # convert from slice I to 3d image I
        w_H_sliceI = slice_wrapper.get_w_H_I()
        imageI_H_w = image_wrapper.get_I_H_w()
        imageI_H_sliceI = imageI_H_w @ w_H_sliceI

        # index on the slice
        sliceI = np.array([event_data['image_index'][0],event_data['image_index'][1], 0.0, 1.0], dtype=float).reshape(4,1)

        # index on the 3d image
        imageI = (imageI_H_sliceI @ sliceI).flatten()

        # override image_index
        event_data["image_index"] = np.rint(imageI[:3]).astype(int)

        return event_data
        
    def print_mouse_coordiantes(self):
        
        if not self.vtk_image_3d:
            return 

        event_data = self.get_mouse_event_coordiantes()       

        # if within image bound
        if 'world_point' in event_data and 'image_index' in event_data and 'pixel_value' in event_data:
            # Print details
            world_pos = event_data['world_point']
            image_index = event_data['image_index']
            pixel_value = event_data['pixel_value']
            self.print_status(f"Point - World: ({world_pos[0]:.2f}, {world_pos[1]:.2f}, {world_pos[2]:.2f}) Index: ({image_index[0]}, {image_index[1]}, , {image_index[2]}), Value: {pixel_value} )")
        elif 'world_point' in event_data:
            world_pos = event_data['world_point']
            self.print_status(f"Point - World: ({world_pos[0]:.2f}, {world_pos[1]:.2f}, {world_pos[2]:.2f})")

class VTKViewer3D(QWidget):
    
    status_message = pyqtSignal(str, QObject)

    def __init__(self, parent=None):
        super().__init__(parent)
    
        self.rulers = []
        self.vtk_image = None

        self.viewer_ax = VTKViewer2DWithReslicer(reslicer.AXIAL, name="Axial", slice_plane_color=[1, 0, 0],  parent=self) 
        self.viewer_cr = VTKViewer2DWithReslicer(reslicer.CORONAL, name="Coronal", slice_plane_color=[0, 1, 0], parent=self) 
        self.viewer_sg = VTKViewer2DWithReslicer(reslicer.SAGITTAL, name="Sagittal", slice_plane_color=[0, 0, 1], parent=self) 

        self.viewer_surf = ModelViewer()
        self.viewer_surf.add_actor_as_model("slice_plane_ax", self.viewer_ax.slice_plane_object.actor)
        self.viewer_surf.add_actor_as_model("slice_plane_cr", self.viewer_cr.slice_plane_object.actor)
        self.viewer_surf.add_actor_as_model("slice_plane_sg", self.viewer_sg.slice_plane_object.actor)

        self.viewer_surf.set_model_visibility("slice_plane_ax", False)
        self.viewer_surf.set_model_visibility("slice_plane_cr", False)
        self.viewer_surf.set_model_visibility("slice_plane_sg", False)

        self.viewers_2d = [self.viewer_ax, self.viewer_cr, self.viewer_sg]
        self.viewers = [self.viewer_ax, self.viewer_cr, self.viewer_sg, self.viewer_surf]
        
        # listen to view chnages from viewers
        for v in self.viewers_2d:
            v.zoom_changed.connect(self.on_zoom_changed_event)

        # listen to slice changes from viewers
        for v in self.viewers_2d:
            v.slice_changed.connect(self.on_slice_changed)
            v.left_button_double_pressed.connect(self.on_left_button_double_pressed_on_2d_viewer)

        # listen to mouse events form viewers
        for v in self.viewers_2d:
            v.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move_on_2d_viewer)
            v.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_pressed_on_2d_viewer)
            v.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_released_on_2d_viewer)
        self.viewer_surf.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move_on_surf_viewer)
        self.viewer_surf.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_pressed_on_surf_viewer)
        self.viewer_surf.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_released_on_surf_viewer)

        # listen to status message events from viewers
        for v in self.viewers:
            v.status_message.connect(self.on_status_message_from_viewer)

        # Grid Layout for viewers
        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewer_ax, 0, 0)
        layout.addWidget(self.viewer_cr, 1, 0)
        layout.addWidget(self.viewer_sg, 1, 1)
        layout.addWidget(self.viewer_surf, 0, 1)
        self.setLayout(layout)

    def on_left_button_double_pressed_on_2d_viewer(self, sender):
        source_viewer: VTKViewer2DWithReslicer = sender
        print(f'double clicked on {source_viewer.name} view')

        event_coordiantes = source_viewer.get_mouse_event_coordiantes()
        if event_coordiantes:
            if 'image_index' in event_coordiantes:
                image_index = event_coordiantes['image_index']
                print(f'double clicked image_index = {image_index}')
                for v in self.viewers_2d:
                    if v is not source_viewer:
                        new_slice_index = image_index[v.reslicer.axis]
                        print(f'setting the slice index to {new_slice_index} for viewer {v.name}')
                        v.slicing.set_slice_index(new_slice_index)

    def get_viewers_2d(self):
        return self.viewers_2d

    def get_viewers(self):
        return self.viewers

    def on_status_message_from_viewer(self, msg, sender):
        self.print_status(msg)
    
    def on_slice_changed(self, sender):
        
        source_viewer = sender

        for v in self.viewers_2d:
            if v is not sender:
                v.update_slice_indicator(source_viewer)
        
        self.viewer_surf.render()

    def enable_zooming(self, enable):
        for v in self.viewers_2d:
            v.toggle_zooming_mode(enable)

    def enable_panning(self, enable):
        for v in self.viewers_2d:
            v.toggle_panning_mode(enable)

    def on_zoom_changed_event(self, type, sender):
        for v in self.viewers_2d:
            if v is not sender:
                v.zoom(type, emit_event=False)

    def on_pan_changed_event(self, sender):
        for v in self.viewers_2d:
            if v is not sender:
                # do update something on the other views.
                print('pan chaned on a view... so need to update on this view?')

    def activate_viewer(self, viewer_interactor):
        for v in self.viewers:
            v.set_active(v.interactor == viewer_interactor)
    
    def get_active_viewer(self):
        for v in self.viewers:
            if v.active:
                return v
        return None
    
    def on_mouse_move_on_2d_viewer(self, obj, event):
        pass

    def on_left_button_pressed_on_2d_viewer(self, obj, event):
        pass

    def on_left_button_released_on_2d_viewer(self, obj, event):
        self.activate_viewer(obj)

    def on_mouse_move_on_surf_viewer(self, obj, event):
        pass

    def on_left_button_pressed_on_surf_viewer(self, obj, event):
        pass

    def on_left_button_released_on_surf_viewer(self, obj, event):
        self.activate_viewer(obj)

    def cleanup_vtk(self, event):

        for viewer in self.viewers_2d:
            viewer.cleanup_vtk(event)

        self.viewer_surf.cleanup_vtk(event)
        
    def clear(self):
        for v in self.viewers:
            v.clear()

        self.vtk_image = None

        self.render()

    def print_status(self, msg):
        self.status_message.emit(msg, self)

    def get_vtk_image(self):
        return self.vtk_image
    
    def set_vtk_image(self, vtk_image, window, level):

        # reset first
        self.clear()

        self.vtk_image = vtk_image

        for v in self.viewers_2d:
            v.set_vtk_image_3d(vtk_image, window, level)

        # display image properties
        dims = vtk_image.GetDimensions()
        spacing = vtk_image.GetSpacing()
        line1 = f"Size={dims}"
        line2 = f"Spacing=({spacing[0]:.2f}, {spacing[1]:.2f}, {spacing[2]:.2f})"
        self.viewer_ax.text_top_left.set_text(f"Image\n{line1}\n{line2}")

        # display slice index
        self.viewer_ax.text_bottom_left.set_text(f"z={self.viewer_ax.slice_index}")
        self.viewer_cr.text_bottom_left.set_text(f"y={self.viewer_cr.slice_index}")
        self.viewer_sg.text_bottom_left.set_text(f"x={self.viewer_sg.slice_index}")

        # init slice indicators
        for source_viewer in self.viewers_2d:
            for v in self.viewers_2d:
                if v is not source_viewer:
                    v.update_slice_indicator(source_viewer)

        self.viewer_surf.set_vtk_image(vtk_image)
        
    def set_segmentation_layers(self, segmentation_layers):
        self.segmentation_layers = segmentation_layers
        
        # subscribe to the list events
        self.segmentation_layers.layer_added.connect(self.on_segmentation_layer_added)
        self.segmentation_layers.layer_removed.connect(self.on_segmentation_layer_removed)

        for v in self.viewers:
            v.set_segmentation_layers(segmentation_layers)

    def on_segmentation_layer_added(self, layer, sender):
        for v in self.viewers:
            v.on_segmentation_layer_added(layer.get_name(), sender)

    def on_segmentation_image_modified(self, layer, sender):
        for v in self.viewers:
            v.on_segmentation_image_modified(layer, sender)            

    def on_segmentation_layer_removed(self, layer, sender):
        for v in self.viewers:
            v.on_segmentation_layer_removed(layer, sender)

    def on_active_segmentation_layer_changed(self, sender):
        for v in self.viewers_2d:
            v.on_active_segmentation_layer_changed(sender)

    def set_window_level(self, window, level):
        for v in self.viewers_2d:
            v.set_window_level(window, level)

        self.viewer_surf.render()

    def zoom_in(self):
        if not self.vtk_image:
            return 

        # the other viewers will zoom from zoom event
        self.viewers_2d[0].zoom('in')
        

    def zoom_out(self):
        if not self.vtk_image:
            return 

        # the other viewers will zoom from zoom event
        self.viewers_2d[0].zoom('out')


    def zoom_reset(self):
        if not self.vtk_image:
            return 

        # the other viewers will zoom from zoom event
        self.viewers_2d[0].zoom('reset')



    def get_renderer(self):
        #return self.base_renderer
        return None
    
    def get_render_window(self):
        #return self.render_window
        return None
    
    def get_camera_info(self):
        pass


    def print_camera_viewport_info(self):
        pass

    def add_ruler(self):
        if not self.vtk_image:
            print('no image at the moment')
            return 
        
        v = self.get_active_viewer()
        if v and hasattr(v, 'add_ruler'):
            v.add_ruler()

    def on_left_button_press(self, obj, event):
        pass

    def on_mouse_move(self, obj, event):
        pass

    def print_mouse_coordiantes(self):
        pass
        
    def on_left_button_release(self, obj, event):
        pass

    def center_image(self):
        pass

    def print_properties(self):
        pass

    def reset_camera_parameters(self):
        pass
            
    def toggle_base_image(self, visible):
        pass

    def toggle_panning_mode(self, checked):
        pass

    def toggle_zooming_mode(self, checked):
        pass

    def toggle_paintbrush(self, enabled):
        pass

    def render(self):
        for v in self.viewers:
            v.render()


from PyQt5.QtWidgets import QWidget, QVBoxLayout
import os

# Construct paths to the icons
current_dir = os.path.dirname(__file__)
brush_icon_path = os.path.join(current_dir, "icons", "brush.png")
eraser_icon_path = os.path.join(current_dir, "icons", "eraser.png")
reset_zoom_icon_path = os.path.join(current_dir, "icons", "reset_zoom.png")


def is_dicom(file_path):
    import pydicom 

    """Check if the file is a valid DICOM file using pydicom."""
    try:
        # Attempt to read the file as a DICOM
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        # If no exception occurs, it's a valid DICOM
        return True
    except pydicom.errors.InvalidDicomError:
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

from PyQt5.QtWidgets import QMessageBox

from PyQt5.QtCore import QSettings
settings = QSettings("_settings.conf", QSettings.IniFormat)


from vtk_segmentation_list_manager import SegmentationListManager
from vtk_point_list_manager import PointListManager
from vtk_line_list_manager import LineListManager
from vtk_rect_list_manager import RectListManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # exclusive QActions
        self.exclusive_actions = []
        self.managers = []
        self.vtk_image = None

        ### init ui ###    
        self.setWindowTitle("Image Labeler 2D")
        self.setGeometry(100, 100, 1024, 786)

        self.main_widget = QWidget()
        self.layout = QVBoxLayout()

        # VTK Viewer
        self.vtk_viewer = VTKViewer3D(parent = self, main_window = self)
        self.layout.addWidget(self.vtk_viewer)

        self.main_widget.setLayout(self.layout)
        self.setCentralWidget(self.main_widget)

        # Add the menus and toolbars
        self.create_menu()
        self.create_file_toolbar()
        self.create_view_toolbar()

        ##########################
        # Segmentation List Manager
        self.segmentation_list_manager = SegmentationListManager(self.vtk_viewer, "Segmentations")
        toolbar, dock = self.segmentation_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.add_exclusive_actions(self.segmentation_list_manager.get_exclusive_actions()) 
        self.segmentation_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.segmentation_list_manager)
        self.segmentation_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.segmentation_list_manager, True)
        

        ##########################
        # Point List Manager
        self.point_list_manager = PointListManager(self.vtk_viewer, "Points")
        toolbar, dock = self.point_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.point_list_manager.get_exclusive_actions())
        self.point_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.point_list_manager)
        self.point_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.point_list_manager, True)

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.point_list_dock_widget)

        ##########################
        # Line List Manager
        self.line_list_manager = LineListManager(self.vtk_viewer, "Lines")
        toolbar, dock = self.line_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.line_list_manager.get_exclusive_actions())
        self.line_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.line_list_manager)
        self.line_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.line_list_manager, True)

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.line_list_dock_widget)

        ##########################
        # Rect List Manager
        self.rect_list_manager = RectListManager(self.vtk_viewer, "Rects")
        toolbar, dock = self.rect_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.rect_list_manager.get_exclusive_actions())
        self.rect_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.rect_list_manager)
        self.rect_list_dock_widget = dock
        self.add_manager_visibility_toggle_menu(self.rect_list_manager, True)

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.rect_list_dock_widget)

        ##########################
        # nnUNet client manager
        from nnunet_client_manager import nnUNetDatasetManager
        self.nnunet_client_manager = nnUNetDatasetManager(self.segmentation_list_manager, "nnUNet Dashboard")
        toolbar, dock = self.nnunet_client_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        self.add_exclusive_actions(self.nnunet_client_manager.get_exclusive_actions())
        self.nnunet_client_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.nnunet_client_manager)
        self.nnunet_client_manager_widget = dock
        self.add_manager_visibility_toggle_menu(self.nnunet_client_manager, True)

        #self.tabifyDockWidget(self.nnunet_client_manager, self.rect_list_dock_widget)

        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")  # Initial message

        logger.info("MainWindow initialized")

        # Load a sample DICOM file
        #dicom_file = "./data/jaw_cal.dcm"
        #self.load_dicom(dicom_file)



    def add_manager_visibility_toggle_menu(self, manager, visible):
        toggle_action = QAction(manager.name, self)
        toggle_action.setCheckable(True)
        toggle_action.setChecked(visible)
        toggle_action.triggered.connect(lambda checked, m=manager: self.toggle_dock_widget(m.dock_widget, checked))
        if visible:
            manager.dock_widget.show()
        else: 
            manager.dock_widget.hide()

        self.managers_menu.addAction(toggle_action)
        

    def closeEvent(self, event):
        """
        Override the closeEvent to log application or window close.
        """
        logger.info("MainWindow is closing.")

        

        super().closeEvent(event)  # Call the base class method to ensure proper behavior

       

        

    def handle_log_message(self, log_type, message):
        """
        Handle log messages emitted by SegmentationListManager.
        """
        if log_type == "INFO":
            self.status_bar.showMessage(message)
            logger.info(message)  # Log the message
        elif log_type == "WARNING":
            self.status_bar.showMessage(f"WARNING: {message}")
            logger.warning(message)  # Log the warning
            self.show_popup("Warning", message, QMessageBox.Warning)
        elif log_type == "ERROR":
            self.status_bar.showMessage(f"ERROR: {message}")
            logger.error(message)  # Log the error
            self.show_popup("Error", message, QMessageBox.Critical)
        else:
            logger.debug(f"{log_type}: {message}")
            self.status_bar.showMessage(f"{log_type}: {message}")

    def show_popup(self, title, message, icon=None):
        """
        Display a QMessageBox with the specified title, message, and icon.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if icon is None:
            icon = QMessageBox.Information
            
        msg_box.setIcon(icon)
        
        msg_box.exec_()

    def on_exclusiave_action_clicked(self):
        
        sender = self.sender()

        # Check if the sender is a QAction and retrieve its text
        if isinstance(sender, QAction):
            print(f"Exclusive action clicked: {sender.text()}")
        else:
            print("The sender is not a QAction.")

        # Get the QAction that triggered this signal
        sender = self.sender()

        # uncheck all other actions
        for action in self.exclusive_actions:
            if action is not sender:
                action.setChecked(False)

    def add_exclusive_actions(self, actions):
        for action in actions:
            self.exclusive_actions.append(action)
            action.triggered.connect(self.on_exclusiave_action_clicked)

    def print_status(self, msg):
        self.status_bar.showMessage(msg)

    def create_menu(self):
        # Create a menu bar
        menubar = self.menuBar()

        # Add the File menu
        file_menu = menubar.addMenu("File")
        self.create_file_menu(file_menu)

        # Add View menu
        view_menu = menubar.addMenu("View")
        self.create_view_menu(view_menu)

    def create_file_menu(self, file_menu):
        
        from PyQt5.QtWidgets import QAction
        
        # Add Open Image action
        open_image_action = QAction("Import Image", self)
        open_image_action.triggered.connect(self.import_image_clicked)
        file_menu.addAction(open_image_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.open_workspace)
        file_menu.addAction(open_workspace_action)

        # Add Save Workspace action
        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        file_menu.addAction(save_workspace_action)

        # Add Open Image action
        close_image_action = QAction("Close Workspace", self)
        close_image_action.triggered.connect(self.close_workspace)
        file_menu.addAction(close_image_action)

        # Print Object Properties Button
        print_objects_action = QAction("Print Object Properties", self)
        print_objects_action.triggered.connect(self.vtk_viewer.print_properties)
        file_menu.addAction(print_objects_action)
        
    def create_managers_menu(self, view_menu):
        self.managers_menu = view_menu.addMenu("Managers")

    def create_view_menu(self, view_menu):
        
        # Zoom In
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.vtk_viewer.zooming.zoom_in)
        view_menu.addAction(zoom_in_action)

        # Zoom Out
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zooming.zoom_out)
        view_menu.addAction(zoom_out_action)

        # Zoom Reset
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zooming.zoom_reset)
        view_menu.addAction(zoom_reset_action)
        
        self.create_managers_menu(view_menu)

        # Add Toggle Button
        toggle_image_button = QAction("Toggle Base Image", self)
        toggle_image_button.setCheckable(True)
        toggle_image_button.setChecked(True)
        toggle_image_button.triggered.connect(self.vtk_viewer.toggle_base_image)
        view_menu.addAction(toggle_image_button)


    def create_file_toolbar(self):
        # Create a toolbar
        toolbar = QToolBar("File Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add actions to the toolbar
        # Add Open DICOM action
        open_image_action = QAction("Import Image", self)
        open_image_action.triggered.connect(self.import_image_clicked)
        toolbar.addAction(open_image_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.open_workspace)
        toolbar.addAction(open_workspace_action)

        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        toolbar.addAction(save_workspace_action)

        close_image_action = QAction("Close Workspace", self)
        close_image_action.triggered.connect(self.close_workspace)
        toolbar.addAction(close_image_action)

    def create_view_toolbar(self):
        from labeled_slider import LabeledSlider
        from rangeslider import RangeSlider

        # Create a toolbar
        toolbar = QToolBar("View Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add a label for context
        toolbar.addWidget(QLabel("Window/Level:", self))

        # Replace two QSliders with a RangeSlider for window and level
        self.range_slider = RangeSlider(self)
        self.range_slider.setFixedWidth(200)  # Adjust size for the toolbar
        self.range_slider.rangeChanged.connect(self.update_window_level)
        toolbar.addWidget(self.range_slider)
        
        # zoom in action
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.vtk_viewer.zooming.zoom_in)
        toolbar.addAction(zoom_in_action)    
        
         # zoom out action
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zooming.zoom_out)
        toolbar.addAction(zoom_out_action)    

        # zoom reset button
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zooming.zoom_reset)
        toolbar.addAction(zoom_reset_action)        

        # zoom toggle button
        zoom_action = QAction("Zoom", self)
        zoom_action.setCheckable(True)
        zoom_action.toggled.connect(self.vtk_viewer.toggle_zooming_mode)
        toolbar.addAction(zoom_action)        

        # pan toggle button
        pan_action = QAction("Pan", self)
        pan_action.setCheckable(True)
        pan_action.toggled.connect(self.vtk_viewer.toggle_panning_mode)
        toolbar.addAction(pan_action)        

        # rotate plus 90 deg (x-->y)
        rot_plus_90_action = QAction("Rot +90", self)
        rot_plus_90_action.triggered.connect(self.rotate_plus_90_clicked)
        toolbar.addAction(rot_plus_90_action)        

        # rotate minus 90 deg (y-->x)
        rot_minus_90_action = QAction("Rot -90", self)
        rot_minus_90_action.triggered.connect(self.rotate_minus_90_clicked)
        toolbar.addAction(rot_minus_90_action)        

        # flip x
        flip_x_action = QAction("Flip X", self)
        flip_x_action.triggered.connect(self.flip_x_clicked)
        toolbar.addAction(flip_x_action)      

        # flip y
        flip_y_action = QAction("Flip Y", self)
        flip_y_action.triggered.connect(self.flip_y_clicked)
        toolbar.addAction(flip_y_action)      

        # pad is an exclusive
        self.add_exclusive_actions([pan_action])
        
        # Add ruler toggle action
        add_ruler_action = QAction("Add Ruler", self)
        add_ruler_action.triggered.connect(self.vtk_viewer.add_ruler)
        toolbar.addAction(add_ruler_action)

    def rotate_plus_90_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # Get image properties
        # dims = self.vtk_image.GetDimensions()
        # spacing = self.vtk_image.GetSpacing()
        # original_origin = self.vtk_image.GetOrigin()
        # direction = self.vtk_image.GetDirectionMatrix()
        # print('dims: ', dims)
        # print('spacing: ', spacing)
        # print('original_origin: ', original_origin)
        # print('direction: ', direction)

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import rot90
        sitk_image_rotated = rot90(sitk_image, plus=True)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_rotated)

       # Get image properties
        # dims = self.vtk_image.GetDimensions()
        # spacing = self.vtk_image.GetSpacing()
        # original_origin = self.vtk_image.GetOrigin()
        # direction = self.vtk_image.GetDirectionMatrix()
        # print('dims: ', dims)
        # print('spacing: ', spacing)
        # print('original_origin: ', original_origin)
        # print('direction: ', direction)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()

    def rotate_minus_90_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import rot90
        sitk_image_rotated = rot90(sitk_image, plus=False)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_rotated)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()

    def flip_x_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import flip_x
        sitk_image_flipped = flip_x(sitk_image)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_flipped)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()


    def flip_y_clicked(self):
        
        if self.vtk_image is None:
            self.show_popup("Error", "Open an image first.")
            return 

        # to itk image
        from itkvtk import vtk_to_sitk, sitk_to_vtk
        sitk_image = vtk_to_sitk(self.vtk_image)

        # rot 90
        from itk import flip_y
        sitk_image_flipped = flip_y(sitk_image)

        # back to vtk image
        self.vtk_image = sitk_to_vtk(sitk_image_flipped)

        # set image
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
        
        self.vtk_viewer.render()

    def update_window_level(self):
        if self.vtk_image is not None:
            # Update the window and level using the RangeSlider values
            window = self.range_slider.get_width()
            level = self.range_slider.get_center()

            self.vtk_viewer.window_level_filter.SetWindow(window)
            self.vtk_viewer.window_level_filter.SetLevel(level)
            self.vtk_viewer.get_render_window().Render()

            self.print_status(f"Window: {window}, Level: {level}")

    def get_list_dir(self):
        if settings.contains('last_directory'):
            return settings.value('last_directory')
        else:
            return '.'

    def import_image_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", self.get_list_dir(), "Medical Image Files (*.dcm *.mhd *.mha);;DICOM Files (*.dcm);;MetaImage Files (*.mhd *.mha);;All Files (*)")
        
        if file_path == '':
            return 
        
        # save to last_directory
        settings.setValue("last_directory", os.path.dirname(file_path))

        try:
            logger.info(f"Loading image from {file_path}")
            self.image_path = file_path 

            _,file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()

            print(f"File extension: {file_extension}")  # Output: .mha      

            image_type = ""
            from itkvtk import load_vtk_image_using_sitk
            if file_extension == ".dcm" or is_dicom(file_path):
                # NOTE: this did not work for RTImage reading. So, using sitk to read images.
                #reader = vtk.vtkDICOMImageReader()
                self.vtk_image = load_vtk_image_using_sitk(file_path)
                image_type = "dicom"
            elif file_extension == ".mhd" or file_extension == ".mha":
                self.vtk_image = load_vtk_image_using_sitk(file_path)
                image_type = "meta"
            else:
                raise Exception("Only dicom or meta image formats are supported at the moment.")

            # Extract correct spacing for RTImage using pydicom
            if image_type == "dicom":
                
                import pydicom
                dicom_dataset = pydicom.dcmread(file_path)
                if hasattr(dicom_dataset, "Modality") and dicom_dataset.Modality == "RTIMAGE":

                    # Extract necessary tags
                    if hasattr(dicom_dataset, "ImagePlanePixelSpacing"):
                        pixel_spacing = dicom_dataset.ImagePlanePixelSpacing  # [row spacing, column spacing]
                    else:
                        raise ValueError("RTImage is missing ImagePlanePixelSpacing")

                    if hasattr(dicom_dataset, "RadiationMachineSAD"):
                        SAD = float(dicom_dataset.RadiationMachineSAD)
                    else:
                        raise ValueError("RTImage is missing RadiationMachineSAD")

                    if hasattr(dicom_dataset, "RTImageSID"):
                        SID = float(dicom_dataset.RTImageSID)
                    else:
                        raise ValueError("RTImage is missing RTImageSID")

                    # Scale pixel spacing to SAD scale
                    scaling_factor = SAD / SID
                    scaled_spacing = [spacing * scaling_factor for spacing in pixel_spacing]

                    # Update spacing in vtkImageData
                    self.vtk_image.SetSpacing(scaled_spacing[1], scaled_spacing[0], 1.0)  # Column, Row, Depth

                    # Print the updated spacing
                    print(f"Updated Spacing: {self.vtk_image.GetSpacing()}")
            
            self.image_type = image_type

            # align the center of the image to the center of the world coordiante system
            # Get image properties
            dims = self.vtk_image.GetDimensions()
            spacing = self.vtk_image.GetSpacing()
            original_origin = self.vtk_image.GetOrigin()

            print('dims: ', dims)
            print('spacing: ', spacing)
            print('original_origin: ', original_origin)

            # Get the scalar range (pixel intensity range)
            scalar_range = self.vtk_image.GetScalarRange()

            self.range_slider.range_min = scalar_range[0]
            self.range_slider.range_max = scalar_range[1]
            self.range_slider.low_value = scalar_range[0]
            self.range_slider.high_value = scalar_range[1]
            self.range_slider.update()  
            
            self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())


            self.setWindowTitle(f"Image Labeler 2D - {os.path.basename(file_path)}")
            
            logger.info("Image loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load image:{e}") 
            self.show_popup("Load Image", f"Error: Load Image Failed, {str(e)}", QMessageBox.Critical)


    def modified(self):
        for manager in self.managers:
            if manager.modified():
                return True
        return False
    
    def show_yes_no_question_dialog(self, title, msg):
        # Create a message box
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)  # Set the icon to a question mark
        msg_box.setWindowTitle(title)  # Set the title of the dialog
        msg_box.setText(msg)  # Set the main message
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)  # Add Yes and No buttons
        
        # Set the default button to Yes
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        # Show the dialog and get the user's response
        response = msg_box.exec_()
        
        if response == QMessageBox.Yes:
            return True
        elif response == QMessageBox.No:
            return False
            
    def close_workspace(self):

        if self.vtk_image is None:
            self.show_popup("Close Image", "No image has been loaded.")
            return 

        if self.modified():
            yes = self.show_yes_no_question_dialog("Save Workspace", "There are modified objects. Do you want to save the workspace?")

            if yes:
                self.save_workspace()
        
        for manager in self.managers:
            manager.clear()

        self.vtk_viewer.clear()

     

        self.image_path = None
        self.vtk_image = None
        self.image_type = None



    def save_workspace(self):
        import json
        import os
        from PyQt5.QtWidgets import QFileDialog

        """Save the current workspace to a folder."""
        if self.vtk_image is None:
            self.print_status("No image loaded. Cannot save workspace.")
            return

        # workspace json file
        workspace_json_path, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "Json (*.json)")
        if not workspace_json_path:
            logger.info("Save workspace operation canceled by user.")
            return 
        
        # save to last_directory
        settings.setValue("last_directory", os.path.dirname(workspace_json_path))

        try:
            # data folder for the workspace
            data_dir = workspace_json_path+".data"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.debug(f"Created data directory: {data_dir}")

            # Create a metadata dictionary
            workspace_data = {
                "window_settings": {
                    "level": self.range_slider.get_center(),
                    "width": self.range_slider.get_width(),
                    "range_min" : self.range_slider.range_min,
                    "range_max" : self.range_slider.range_max
                }
            }

            # Save input image as '.mha'
            from itkvtk import save_vtk_image_using_sitk
            input_image_path = os.path.join(data_dir, "input_image.mhd")
            save_vtk_image_using_sitk(self.vtk_image, input_image_path)
            logger.info(f"Saved input image to {input_image_path}")
            
            logger.info('Saving manager states')
            for manager in self.managers:
                logger.info(f'{manager} - Saving state')
                manager.save_state(workspace_data, data_dir)

            # Save metadata as 'workspace.json'
            with open(workspace_json_path, "w") as f:
                json.dump(workspace_data, f, indent=4)
            
            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()
            
            logger.info(f"Workspace metadata saved to {workspace_json_path}.")
            self.print_status(f"Workspace saved to {workspace_json_path}.")
            self.show_popup("Save Workspace", "Workspace saved successfully.", QMessageBox.Information)
        except Exception as e:
            logger.error(f"Failed to save workspace: {e}", exc_info=True)
            self.print_status("Failed to save workspace. Check logs for details.")
            self.show_popup("Save Workspace", f"Error saving workspace: {str(e)}", QMessageBox.Critical)      

    def open_workspace(self):
        import json
        import os

        """Load a workspace from a folder."""
        workspace_json_path, _ = QFileDialog.getOpenFileName(self, "Select Workspace File", self.get_list_dir(), "JSON Files (*.json)")
        if not workspace_json_path:
           logger.info("Load workspace operation canceled by user.")
           return

        # save to last dir
        settings.setValue('last_directory', os.path.dirname(workspace_json_path))

        data_path = workspace_json_path+".data"
        if not os.path.exists(data_path):
            msg = "Workspace data folder not found."
            logger.error(msg)
            self.print_status(msg)
            return

        try:
            with open(workspace_json_path, "r") as f:
                workspace_data = json.load(f)

            logger.info(f"Loaded workspace metadata from {workspace_json_path}.")

            # Clear existing workspace
            self.vtk_image = None
            #self.point_list_manager.points.clear()

            from itkvtk import load_vtk_image_using_sitk

            # Load input image
            input_image_path = os.path.join(data_path, "input_image.mhd")
            if os.path.exists(input_image_path):
                self.vtk_image = load_vtk_image_using_sitk(input_image_path)
                logger.info(f"Loaded input image from {input_image_path}.")
            else:
                raise FileNotFoundError(f"Input image file not found at {input_image_path}")

            # Restore window settings
            window_settings = workspace_data.get("window_settings", {})
            window = window_settings.get("width", 1)
            level = window_settings.get("level", 0)

            # Get the scalar range (pixel intensity range)
            scalar_range = self.vtk_image.GetScalarRange()

            self.range_slider.range_min = scalar_range[0]
            self.range_slider.range_max = scalar_range[1]
            self.range_slider.low_value = level-window/2
            self.range_slider.high_value = level+window/2
            self.range_slider.update()  

            self.vtk_viewer.set_vtk_image(self.vtk_image, window, level)

            logger.info('loading manager states')
            for manager in self.managers:
                logger.info(f'{manager} - Loading state')
                manager.load_state(workspace_data, data_path, {'base_image': self.vtk_image})

            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()

            self.print_status(f"Workspace loaded from {data_path}.")
            logger.info("Loaded workspace successfully.")

        except Exception as e:
            logger.error(f"Failed to load workspace: {e}", exc_info=True)
            self.print_status("Failed to load workspace. Check logs for details.")
  
    def toggle_dock_widget(self, dock_widget, checked):
        # Toggle the visibility of the dock widget based on the checked state
        if checked:
            dock_widget.show()
        else:
            dock_widget.hide()

        


if __name__ == "__main__":
    import sys
    
    logger.info("Application started")

    app = QApplication(sys.argv)
    
    app.setWindowIcon(QIcon(brush_icon_path))  # Set application icon

    app.aboutToQuit.connect(lambda: logger.info("Application is quitting."))

    main_window = MainWindow()
    #main_window.show()
    main_window.showMaximized()
    sys.exit(app.exec_())
