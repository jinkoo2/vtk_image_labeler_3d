import itkvtk
import numpy as np

class vtk_image_wrapper:
    def __init__(self, vtk_image):
        self.vtk_image = vtk_image

    def get_origin(self):
        return np.array(self.vtk_image.GetOrigin())

    def get_spacing(self):
        return np.array(self.vtk_image.GetSpacing())

    def get_dimensions(self):
        return np.array(self.vtk_image.GetDimensions())

    def get_direction_matrix(self):
        """Return the 3x3 direction matrix as a NumPy array."""
        if hasattr(self.vtk_image, 'GetDirectionMatrix'):
            vtk_mat = self.vtk_image.GetDirectionMatrix()
            mat_np = np.zeros((3, 3))
            for i in range(3):
                for j in range(3):
                    mat_np[i, j] = vtk_mat.GetElement(i, j)
            return mat_np
        else:
            return np.eye(3)

    def set_origin(self, origin_np):
        """
        Set the origin of the VTK image.
        Args:
            origin_np (np.ndarray): 1D array of length 3
        """
        if origin_np.shape != (3,):
            raise ValueError("Origin must be a 1D numpy array of length 3.")
        self.vtk_image.SetOrigin(*origin_np)


    def set_spacing(self, spacing_np):
        """
        Set the spacing of the VTK image.
        Args:
            spacing_np (np.ndarray): 1D array of length 3
        """
        if spacing_np.shape != (3,):
            raise ValueError("Spacing must be a 1D numpy array of length 3.")
        self.vtk_image.SetSpacing(*spacing_np)


    def set_dimensions(self, dims_np):
        """
        Set the dimensions of the VTK image.
        Note: this does not allocate memory or resize the image data.
        Args:
            dims_np (np.ndarray): 1D array of length 3 (int)
        """
        if dims_np.shape != (3,):
            raise ValueError("Dimensions must be a 1D numpy array of length 3.")
        self.vtk_image.SetDimensions(int(dims_np[0]), int(dims_np[1]), int(dims_np[2]))


    def set_direction_matrix(self, R_np):
        """
        Set the direction matrix of the VTK image.
        Args:
            R_np (np.ndarray): 3x3 direction matrix
        """
        if R_np.shape != (3, 3):
            raise ValueError("Direction matrix must be a 3x3 numpy array.")

        vtk_matrix = vtk.vtkMatrix3x3()
        for i in range(3):
            for j in range(3):
                vtk_matrix.SetElement(i, j, R_np[i, j])

        self.vtk_image.SetDirectionMatrix(vtk_matrix)

    def get_w_H_o(self):
        """
        Returns the 4x4 homogeneous transformation matrix:
            world_H_origin = [[R, t],
                              [0, 0, 0, 1]]
        """
        R = self.get_direction_matrix()            # 3x3 rotation/direction
        t = self.get_origin().reshape((3, 1))       # 3x1 translation

        w_H_o = np.eye(4)
        w_H_o[:3, :3] = R
        w_H_o[:3, 3] = t.flatten()

        return w_H_o

    def get_o_H_I(self):
        """
        Returns the 4x4 matrix converting from image index to origin (voxel spacing):
            origin_H_index = [[S, 0],
                              [0, 1]]
        """
        spacing = self.get_spacing()
        o_H_I = np.eye(4)
        np.fill_diagonal(o_H_I[:3, :3], spacing)
        return o_H_I

    def get_w_H_I(self):
        """Returns world_H_index = world_H_origin @ origin_H_index"""
        return self.get_w_H_o() @ self.get_o_H_I()

    def get_center_point_o(self):
        """Center in origin (physical) coordinate frame"""
        return (self.get_spacing() * self.get_dimensions()) / 2.0

    def get_center_point_w(self):
        """Center in world coordinate frame"""
        o_pt = np.append(self.get_center_point_o(), 1.0)  # shape (4,)
        w_H_o = self.get_w_H_o()  # shape (4,4)
        w_pt = w_H_o @ o_pt  # shape (4,)
        return w_pt[:3]

    def __repr__(self):
        return f"<vtk_image_wrapper dims={self.get_dimensions()} spacing={self.get_spacing()} origin={self.get_origin()} direction={self.get_direction_matrix()}>"
