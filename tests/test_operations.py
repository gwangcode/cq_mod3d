import pytest
import cadquery as cq
import cq_mod3d as m3

def test_array_rect_validity():
    """测试矩形阵列：数量、包围盒和体积"""
    base = m3.cube(1) # 体积 1
    
    # 生成 3x2 的阵列，间距 2
    arr = m3.array_rect(base, nx=3, ny=2, spacing=2)
    assert isinstance(arr, cq.Workplane)
    assert arr.val().isValid()
    
    # 1. 检查数量（通过 compound/solids 数量）
    # 注意：如果间距足够，它们不会被融合成一个 Solid，但我们的实现用了 union/fuse
    # 如果它们不相交，结果可能是一个 Compound 包含多个 Solid
    solids = arr.solids().vals()
    assert len(solids) == 6, "阵列实体数量不等于 nx * ny"
    
    # 2. 检查总体积
    # union 了多个不相交的实体后，CadQuery 的 Volume 会将它们相加
    assert abs(arr.val().Volume() - 6.0) < 1e-3
    
    # 3. 检查包围盒边界 (3个零件跨度: 0到4，所以长度是4，加上 cube 边长 1 的一半是 0.5，总共 5)
    bb = arr.val().BoundingBox()
    assert abs(bb.xmin - (-0.5)) < 1e-3
    assert abs(bb.xmax - (4.5)) < 1e-3
    assert abs(bb.ymin - (-0.5)) < 1e-3
    assert abs(bb.ymax - (2.5)) < 1e-3

def test_array_rect_overlapping():
    """测试矩形阵列：间距过小导致融合"""
    base = m3.cube(2) # 体积 8
    # 间距 1，意味着它们有一半重叠
    arr = m3.array_rect(base, nx=2, ny=1, spacing=1)
    
    solids = arr.solids().vals()
    # 因为重叠了，union 会将其合并成一个连续的 Solid
    assert len(solids) == 1, "重叠的阵列应该被合并为单一实体"
    
    # 两个 2x2x2 错开 1 的立方体，体积 = 8 + 8 - 4 = 12
    assert abs(arr.val().Volume() - 12.0) < 1e-3

def test_array_polar_validity():
    """测试极坐标阵列：数量与体积"""
    base = m3.cylinder(radius=0.5, height=1) # 体积 pi * 0.5^2 * 1 = 0.785
    # 绕原点，半径 5，分布 4 个
    arr = m3.array_polar(base, count=4, radius=5)
    
    solids = arr.solids().vals()
    assert len(solids) == 4
    
    # 检查体积是否累加
    vol_single = base.val().Volume()
    assert abs(arr.val().Volume() - vol_single * 4) < 1e-3
    
    # 检查包围盒是否扩展到了半径 5 加上圆柱自身半径
    bb = arr.val().BoundingBox()
    assert abs(bb.xmax - (5 + 0.5)) < 1e-2
    assert abs(bb.xmin - (-5 - 0.5)) < 1e-2
