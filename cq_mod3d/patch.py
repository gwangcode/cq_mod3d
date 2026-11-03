import numpy as np
import cadquery as cq
from typing import Union, List, Tuple
from OCP.gp import gp_GTrsf, gp_Mat, gp_XYZ
from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
from .utils import _is_vec, _vec, _tessellate, _tri_mesh_to_wp
from .deformers import brep_twist_z

_orig_add = cq.Workplane.__add__

def _wp_add(self: cq.Workplane, other: Union[cq.Workplane, List[float]]) -> cq.Workplane:
    if _is_vec(other, 3):
        return self.translate(_vec(other))
    return _orig_add(self, other)

def _wp_sub(self: cq.Workplane, other: Union[cq.Workplane, List[float]]) -> cq.Workplane:
    if isinstance(other, cq.Workplane):
        return self.cut(other)
    if _is_vec(other, 3):
        return self.translate(_vec(-np.asarray(other, dtype=float)))
    raise ValueError(f"Unsupported operand for -: {type(other)}")

def _wp_mul(self: cq.Workplane, other: Union[cq.Workplane, float, List[float]]) -> cq.Workplane:
    if isinstance(other, cq.Workplane):
        return self.intersect(other)
        
    if isinstance(other, (int, float)):
        gtrsf = gp_GTrsf()
        gtrsf.SetVectorialPart(gp_Mat(other, 0, 0, 0, other, 0, 0, 0, other))
        gtrsf.SetTranslationPart(gp_XYZ(0, 0, 0))
        new_shape = BRepBuilderAPI_GTransform(self.val().wrapped, gtrsf, True).Shape()
        return cq.Workplane("XY").add(cq.Shape.cast(new_shape))
        
    if _is_vec(other, 3):
        ax, ay, az = _vec(other)
        gtrsf = gp_GTrsf()
        gtrsf.SetVectorialPart(gp_Mat(ax, 0, 0, 0, ay, 0, 0, 0, az))
        gtrsf.SetTranslationPart(gp_XYZ(0, 0, 0))
        new_shape = BRepBuilderAPI_GTransform(self.val().wrapped, gtrsf, True).Shape()
        return cq.Workplane("XY").add(cq.Shape.cast(new_shape))
    raise ValueError(f"Unsupported operand for *: {type(other)}")

def _wp_matmul(self: cq.Workplane, angles: List[float]) -> cq.Workplane:
    if not _is_vec(angles, 3):
        raise ValueError("Rotation expects [rx, ry, rz]")
    ax, ay, az = _vec(angles)
    return (self.rotate((0, 0, 0), (1, 0, 0), np.degrees(ax))
                .rotate((0, 0, 0), (0, 1, 0), np.degrees(ay))
                .rotate((0, 0, 0), (0, 0, 1), np.degrees(az)))

def _wp_mod(self: cq.Workplane, factors: List[float]) -> cq.Workplane:
    if not _is_vec(factors, 6):
        raise ValueError("Shear expects [sxy, sxz, syx, syz, szx, szy]")
    sxy, sxz, syx, syz, szx, szy = _vec(factors)
    gtrsf = gp_GTrsf()
    gtrsf.SetVectorialPart(gp_Mat(1, sxy, sxz, syx, 1, syz, szx, szy, 1))
    gtrsf.SetTranslationPart(gp_XYZ(0, 0, 0))
    new_shape = BRepBuilderAPI_GTransform(self.val().wrapped, gtrsf, True).Shape()
    return cq.Workplane("XY").add(cq.Shape.cast(new_shape))

def _wp_xor(self: cq.Workplane, angles: List[float]) -> cq.Workplane:
    if not _is_vec(angles, 3):
        raise ValueError("Twist expects [ax, ay, az]")
    ax, ay, az = _vec(angles)
    
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        try:
            res = brep_twist_z(self, az)
            if res is not None:
                return res
        except Exception as e:
            print(f"⚠️ [cq_mod3d] B-rep 扭转失败，切换为网格降级方案: {e}")

    verts, faces = _tessellate(self, tol=0.1)
    new_verts = np.empty_like(verts)
    for i, (x, y, z) in enumerate(verts):
        tx, ty, tz = ax * x, ay * y, az * z
        Rx = np.array([[1, 0, 0], [0, np.cos(tx), -np.sin(tx)], [0, np.sin(tx),  np.cos(tx)]])
        Ry = np.array([[np.cos(ty), 0, np.sin(ty)], [0, 1, 0], [-np.sin(ty), 0, np.cos(ty)]])
        Rz = np.array([[np.cos(tz), -np.sin(tz), 0], [np.sin(tz),  np.cos(tz), 0], [0, 0, 1]])
        new_verts[i] = (Rx @ Ry @ Rz) @ np.array([x, y, z])
    return _tri_mesh_to_wp(new_verts, faces)


def _patch_workplane():
    if getattr(cq.Workplane, '_mod3d_patched', False):
        return
    cq.Workplane.__add__     = _wp_add
    cq.Workplane.__sub__     = _wp_sub
    cq.Workplane.__mul__     = _wp_mul
    cq.Workplane.__matmul__  = _wp_matmul
    cq.Workplane.__mod__     = _wp_mod
    cq.Workplane.__xor__     = _wp_xor
    cq.Workplane._mod3d_patched = True

_patch_workplane()
