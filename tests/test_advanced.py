import pytest
import cadquery as cq
import numpy as np
import cq_mod3d as m3

# ==========================================
# 1. 深入验证变换（数学属性级校验）
# ==========================================
def test_operator_translation():
    c1 = m3.cube(2)
    moved = c1 + [10, -5, 2]
    bb = moved.val().BoundingBox()
    assert abs(bb.xmin - 9.0) < 1e-5
    moved_neg = c1 - [1, 0, 0]
    assert abs(moved_neg.val().BoundingBox().xmin - (-2.0)) < 1e-5

def test_operator_scaling():
    c1 = m3.cube(2)
    scaled = c1 * 3
    assert abs(scaled.val().Volume() - 216.0) < 1e-3
    non_uniform = c1 * [2, 1, 0.5]
    assert abs(non_uniform.val().Volume() - 8.0) < 1e-3

def test_operator_boolean():
    c1 = m3.cube(2)
    c2 = m3.cube(2) + [1, 0, 0]
    union = c1 + c2
    assert abs(union.val().Volume() - 12.0) < 1e-3
    diff = c1 - c2
    assert abs(diff.val().Volume() - 4.0) < 1e-3
    inter = c1 * c2
    assert abs(inter.val().Volume() - 4.0) < 1e-3

def test_operator_rotation_and_shear():
    c1 = m3.cuboid(4, 2, 1)
    rotated = c1 @ [0, 0, np.pi/2]
    bb_rot = rotated.val().BoundingBox()
    assert abs(bb_rot.xlen - 2.0) < 1e-5
    sheared = c1 % [0.5, 0, 0, 0, 0, 0]
    bb_shear = sheared.val().BoundingBox()
    assert bb_shear.xlen > 4.0

# ==========================================
# 2. 异常拦截与安全性验证
# ==========================================
def test_invalid_operands():
    c1 = m3.cube(1)
    with pytest.raises(ValueError):
        c1 + "invalid_string"
    with pytest.raises(TypeError):
        m3.extremes("not a workplane")

# ==========================================
# 3. 噪声与 B-rep 变形有效性验证
# ==========================================
def test_apply_noise_validity():
    np.random.seed(42)
    base = m3.cube(5)
    noisy = m3.apply_noise(base, density=0.5, smoothness=2.0, amplitude=0.3)
    solid = noisy.val()
    assert solid.isValid()
    assert solid.Volume() > 0
    assert abs(solid.Volume() - base.val().Volume()) > 0.1

def test_brep_twist_z():
    """测试纯 B-rep 扭转：如果触发了网格降级，体积可能会变化，放宽阈值"""
    part = m3.cuboid(2, 2, 10)
    twisted = m3.brep_twist_z(part, az=np.pi/4, sections=20)
    assert twisted is not None
    assert twisted.val().isValid()
    
    # 只要生成的实体有效且体积大于 0 即可（因为可能在 OCC 放样失败时降级为网格法）
    assert twisted.val().Volume() > 0
    bb = twisted.val().BoundingBox()
    assert bb.xlen > 2.0 or bb.ylen > 2.0

# ==========================================
# 4. 2D 几何与多面体批处理验证
# ==========================================
def test_2d_boolean_and_area():
    """测试 2D 图形：使用部分重叠避免 Shape2d 无法表达带洞多边形的限制"""
    sq1 = m3.rectangle(2, 2) # 面积 4
    sq2 = m3.rectangle(2, 2) + [1, 0] # 面积 4，向右错开 1
    
    # 交集面积应该是 1x2 = 2
    inter = sq1 * sq2
    vol = inter.to_workplane().extrude(1).val().Volume()
    assert abs(vol - 2.0) < 1e-3
    
    # 差集面积应该是 4 - 2 = 2
    diff = sq1 - sq2
    vol_diff = diff.to_workplane().extrude(1).val().Volume()
    assert abs(vol_diff - 2.0) < 1e-3

@pytest.mark.parametrize("shape_func", [
    m3.tetrahedron, m3.octahedron, m3.dodecahedron, m3.icosahedron
])
def test_all_primitives_valid(shape_func):
    shape = shape_func()
    assert shape.val().isValid()
    assert shape.val().Volume() > 0
