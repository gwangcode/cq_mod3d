import pytest
import cadquery as cq
import numpy as np
import cq_mod3d as m3

def test_operator_subtraction():
    """测试差集 - 和 反向平移 -"""
    c1 = m3.cube(2)
    c2 = m3.cube(2) + [1, 0, 0]  # 平移
    
    diff = c1 - c2
    assert isinstance(diff, cq.Workplane)
    assert abs(diff.val().Volume() - 4.0) < 1e-3
    
    # 修复：原本写的 -2.5 是我算错了，正确应该是 -2.0
    moved = c1 - [1, 0, 0]
    assert abs(moved.val().BoundingBox().xmin - (-2.0)) < 1e-5

def test_operator_multiplication():
    """测试交集 * 和缩放 *"""
    c1 = m3.cube(2)
    s1 = m3.sphere(1.5)
    
    inter = c1 * s1
    assert isinstance(inter, cq.Workplane)
    assert inter.val().Volume() > 0
    
    scaled = c1 * 3
    assert abs(scaled.val().BoundingBox().xlen - 6.0) < 1e-5
    
    non_uniform = c1 * [3, 1, 0.5]
    bb = non_uniform.val().BoundingBox()
    assert abs(bb.xlen - 6.0) < 1e-5
    assert abs(bb.ylen - 2.0) < 1e-5
    assert abs(bb.zlen - 1.0) < 1e-5

def test_operator_rotation():
    """测试旋转 @"""
    c1 = m3.cuboid(4, 2, 1)
    rotated = c1 @ [0, 0, np.pi/2]
    bb = rotated.val().BoundingBox()
    assert abs(bb.xlen - 2.0) < 1e-5
    assert abs(bb.ylen - 4.0) < 1e-5

def test_apply_noise_validity():
    """测试噪声生成后，是否依然是合法且水密的实体"""
    base = m3.cube(5)
    noisy = m3.apply_noise(base, density=0.5, smoothness=2.0, amplitude=0.3)
    
    solid = noisy.val()
    assert solid.isValid(), "生成的模型是 Invalid Solid"
    
    # 修复：solid 是 Shape 对象，不能选面，要用 noisy(Workplane) 来操作
    shrunk = noisy.faces("<Z").workplane().offset(-0.01)
    assert shrunk is not None
    assert abs(solid.Volume() - base.val().Volume()) > 0.1

def test_brep_twist():
    """测试纯 B-rep 切片放样扭转是否生成合法实体"""
    part = m3.cuboid(2, 2, 10)
    twisted = m3.brep_twist_z(part, az=np.pi/2, sections=20)
    
    assert twisted is not None, "扭转失败，返回了 None"
    assert isinstance(twisted, cq.Workplane)
    assert twisted.val().isValid(), "扭转后的实体无效"
    
    bb = twisted.val().BoundingBox()
    assert bb.xlen > 2.0 
    assert bb.ylen > 2.0

def test_2d_shapes_and_ops():
    """测试 2D 图形生成、面积与布尔运算"""
    c = m3.circle(R=2)
    assert len(c.vertices) > 0
    
    sq = m3.rectangle(2, 2) 
    inter_2d = c * sq
    assert isinstance(inter_2d, m3.Shape2d)
    
    union_2d = c + sq + [3, 0]
    assert isinstance(union_2d, m3.Shape2d)
    
    wp = union_2d.to_workplane().extrude(5)
    assert isinstance(wp, cq.Workplane)
    assert wp.val().Volume() > 0

@pytest.mark.parametrize("shape_func", [
    m3.tetrahedron, 
    m3.octahedron, 
    m3.dodecahedron, 
    m3.icosahedron,
    lambda: m3.spiral(2, 2, 3),
    lambda: m3.astroid(2), 
])
def test_all_primitives_valid(shape_func):
    """参数化测试：确保所有 3D/2D 图元函数都能生成有效对象"""
    shape = shape_func()
    if isinstance(shape, cq.Workplane):
        assert shape.val().isValid()
    else:
        assert len(shape.vertices) > 0
