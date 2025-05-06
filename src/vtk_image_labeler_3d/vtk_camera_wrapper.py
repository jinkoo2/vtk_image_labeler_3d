import numpy as np

import vtk
vtk.vtkCamera

class vtk_camera_wrapper:
    def __init__(self, vtk_camera):
        self.vtk_camera = vtk_camera

    def get_parallel_projection(self):
        return self.vtk_camera.GetParallelProjection()

    def set_parallel_projection(self, value):
        return self.vtk_camera.SetParallelProjection()

    def get_position(self):
        return np.array(self.vtk_camera.GetPosition())
    
    def set_position(self, np_arr):
        if np_arr.shape != (3,):
            raise ValueError("np_arr must be a 1D numpy array of length 3.")
        self.vtk_camera.SetPosition(*np_arr)

    def get_focal_point(self):
        return np.array(self.vtk_camera.GetFocalPoint())
    
    def set_focal_point(self, np_arr):
        if np_arr.shape != (3,):
            raise ValueError("np_arr must be a 1D numpy array of length 3.")
        self.vtk_camera.SetFocalPoint(*np_arr)

    def get_view_up(self):
        return np.array(self.vtk_camera.GetViewUp())

    def set_view_up(self, np_arr):
        if np_arr.shape != (3,):
            raise ValueError("np_arr must be a 1D numpy array of length 3.")
        self.vtk_camera.SetViewUp(*np_arr)

    def get_view_angle(self):
        return self.vtk_camera.GetViewAngle()

    def set_view_angle(self, value):
        self.vtk_camera.SetViewAngle(value)


    def get_parallel_scale(self):
        return self.vtk_camera.GetParallelScale()

    def set_parallel_scale(self, value):
        self.vtk_camera.SetParallelScale(value)


    def get_clip_range(self):
        return np.array(self.vtk_camera.GetClippingRange())    
    
    def set_clip_range(self, np_arr):
        if np_arr.shape != (3,):
            raise ValueError("np_arr must be a 1D numpy array of length 3.")
        self.vtk_camera.SetClippingRange(*np_arr)

    def get_origin(self):
        return self.get_position()
    
    def get_z_axis(self):

        fp = self.get_focal_point() 
        ps = self.get_position()
        v = fp - ps

        norm = np.linalg.norm(v)
        if norm != 0:
            return v / norm
        else:
            raise ValueError(f"the camera focal point {fp} and position {ps} cannot be the same!")

        return uv 

    def get_y_axis(self):

        v = self.get_view_up()

        norm = np.linalg.norm(v)
        if norm != 0:
            return v / norm
        else:
            raise ValueError(f"the view up vector cannot be zero (view_up={v}) ")
        
    def get_x_axis(self):
        z = self.get_z_axis()
        y = self.get_y_axis()
        return np.cross(y, z)

    def ux(self):
        return self.get_x_axis()
    def uy(self):
        return self.get_y_axis()
    def uz(self):
        return self.get_z_axis()
    
    def get_w_H_o(self):
        """
        Returns the 4x4 homogeneous transformation matrix:
            world_H_origin = [[R, t],
                              [0, 0, 0, 1]]
        """
        R = np.column_stack((self.ux(),self.uy(),self.uz()))
        t = self.get_origin().reshape((3, 1))       # 3x1 translation

        w_H_o = np.eye(4)
        w_H_o[:3, :3] = R
        w_H_o[:3, 3] = t.flatten()

        return w_H_o

    def get_o_H_w(self):
        return np.linalg.inv(self.get_w_H_o())
    
    def project_point_to_camera_near_plane_w(self, pt_w):

        camo_H_w = self.get_o_H_w()
            
        # pt in camo
        pt_camo = camo_H_w @ np.array([pt_w[0], pt_w[1], pt_w[2], 1.0]).reshape(4,1)
        
        # projec to near plane
        clip_range = self.get_clip_range()
        z_near = clip_range[0]
        pt_camo[2,0] = z_near+0.001
        
        # back to w
        w_H_camo = self.get_w_H_o()
            
        pt_near_w = w_H_camo @ pt_camo
        
        return pt_near_w.flatten()[:3]
        
    def __repr__(self):
        return f"<vtk_camera_wrapper position={self.get_poistion()} focal point={self.get_focal_point()} w_H_o={self.get_w_H_o()}>"
