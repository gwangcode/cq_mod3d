import pytest
import cadquery as cq
import cq_mod3d as m3

def test_array_rect_validity():
    base = m3.cube(1)
    arr = m3.array_rect(base, nx=3, ny=2, spacing=2)
    assert isinstance(arr, cq.Workplane)
    
    # 提取 Compound 中的 solids
    solids = arr.solids().vals()
    assert len(solids) == 6, "阵列实体数量不等于 nx * ny"
    assert abs(arr.val().Volume() - 6.0) < 1e-3
    
    bb = arr.val().BoundingBox()
    assert abs(bb.xmin - (-0.5)) < 1e-3
    assert abs(bb.xmax - (4.5)) < 1e-3

def test_array_polar_validity():
    base = m3.cylinder(radius=0.5, height=1)
    arr = m3.array_polar(base, count=4, radius=5)
    
    solids = arr.solids().vals()
    assert len(solids) == 4
    assert abs(arr.val().Volume() - base.val().Volume() * 4) < 1e-3
    
    bb = arr.val().BoundingBox()
    assert abs(bb.xmax - (5 + 0.5)) < 1e-2
