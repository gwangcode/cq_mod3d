import numpy as np
import trimesh
import cadquery as cq

from OCP.ShapeFix import ShapeFix_Shell, ShapeFix_Solid
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.gp import gp_Pnt
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_Sewing,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeSolid,
)
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS


def _is_vec(x, n):
    """高性能向量检查"""
    arr = np.asarray(x)
    return arr.ndim == 1 and arr.size == n and np.issubdtype(arr.dtype, np.number)

def _vec(x):
    return tuple(float(v) for v in x)

def _tessellate(shape, tol=0.1):
    """Workplane/Shape/wrapped -> (verts, faces)"""
    if isinstance(shape, cq.Workplane):
        wrapped = shape.val().wrapped
    elif isinstance(shape, cq.Shape):
        wrapped = shape.wrapped
    else:
        wrapped = shape
    BRepMesh_IncrementalMesh(wrapped, tol, False, 0.3, True)
    verts, faces, vmap = [], [], {}
    exp = TopExp_Explorer(wrapped, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face_s(exp.Current())
        loc, tri = TopLoc_Location(), BRep_Tool.Triangulation_s(
            TopoDS.Face_s(exp.Current()), TopLoc_Location())
        if tri is not None:
            trsf = loc.Transformation()
            def idx_of(p):
                k = (round(p.X(), 6), round(p.Y(), 6), round(p.Z(), 6))
                if k not in vmap:
                    vmap[k] = len(verts)
                    verts.append([p.X(), p.Y(), p.Z()])
                return vmap[k]
            for i in range(1, tri.NbTriangles() + 1):
                t = tri.Triangle(i)
                faces.append([idx_of(tri.Node(t.Value(1)).Transformed(trsf)),
                              idx_of(tri.Node(t.Value(2)).Transformed(trsf)),
                              idx_of(tri.Node(t.Value(3)).Transformed(trsf))])
        exp.Next()
    return np.asarray(verts), faces


def _tri_mesh_to_wp(verts, faces, tol=0.05):
    sewing = BRepBuilderAPI_Sewing(tol)
    for f in faces:
        poly = BRepBuilderAPI_MakePolygon()
        for i in f:
            poly.Add(gp_Pnt(*verts[i]))
        poly.Close()
        try:
            sewing.Add(BRepBuilderAPI_MakeFace(poly.Wire()).Face())
        except Exception:
            continue
    sewing.Perform()
    shell = sewing.SewedShape()

    def _ensure_positive_volume(shape):
        """确保实体的体积为正，如果法线朝内则翻转"""
        cq_shape = cq.Shape.cast(shape)
        if cq_shape.Volume() < 0:
            return cq_shape.reverse()
        return cq_shape

    # --- 第一次尝试：直接缝合为 Solid ---
    try:
        solid = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shell)).Solid()
        if BRepCheck_Analyzer(solid).IsValid():
            return cq.Workplane("XY").add(_ensure_positive_volume(solid))
    except Exception:
        pass

    # --- 第二次尝试：使用 ShapeFix 强制修复缝隙 ---
    try:
        fixer_shell = ShapeFix_Shell(TopoDS.Shell_s(shell))
        fixer_shell.Perform()
        fixed_shell = fixer_shell.Shell()
        
        solid = BRepBuilderAPI_MakeSolid(fixed_shell).Solid()
        fixer_solid = ShapeFix_Solid(solid)
        fixer_solid.Perform()
        fixed_solid = fixer_solid.Solid()
        
        if BRepCheck_Analyzer(fixed_solid).IsValid():
            return cq.Workplane("XY").add(_ensure_positive_volume(fixed_solid))
    except Exception:
        pass

    # --- 兜底：如果强行修复也失败，退回原始形状 ---
    print("⚠️ 警告：网格自交过于严重，无法修复为 Watertight Solid，已降级返回 Shell。")
    return cq.Workplane("XY").add(cq.Shape.cast(shell))

def extremes(part):
    """返回 cq.Workplane 的包围盒 (minx, maxx, miny, maxy, minz, maxz)"""
    if not isinstance(part, cq.Workplane):
        raise TypeError(f"extremes expects cq.Workplane, got {type(part)}")
    bb = part.val().BoundingBox()
    return bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax
