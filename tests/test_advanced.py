import pytest
import cadquery as cq
import numpy as np
import cq_mod3d as m3

# ==========================================
# 1. 深入验证变换（数学属性级校验）
# ==========================================
def test_operator_translation():
    """测试平移：验证包围盒位置是否精确偏移"""
    c1 = m3.cube(2)
    moved = c1 + [10, -5, 2]
    bb = moved.val().BoundingBox()
    # 原来在 [-1, 1]，平移后应该是 [9, 11], [-6, -4], [1, 3]
    assert abs(bb.xmin - 9.0) < 1e-5
    assert abs(bb.ymin - (-6.0)) < 1e-5
    assert abs(bb.zmin - 1.0) < 1e-5

    # 负向平移
    moved_neg = c1 - [1, 0, 0]
    assert abs(moved_neg.val().BoundingBox().xmin - (-2.0)) < 1e-5

def test_operator_scaling():
    """测试缩放：验证体积的立方/乘积关系"""
    c1 = m3.cube(2) # 体积 8
    # 均匀缩放 3 倍 -> 体积应放大 27 倍 (8 * 27 = 216)
    scaled = c1 * 3
    assert abs(scaled.val().Volume() - 216.0) < 1e-3

    # 非均匀缩放 [2, 1, 0.5] -> 体积放大 2*1*0.5 = 1 倍 (仍为 8)
    non_uniform = c1 * [2, 1, 0.5]
    assert abs(non_uniform.val().Volume() - 8.0) < 1e-3
    bb = non_uniform.val().BoundingBox()
    assert abs(bb.xlen - 4.0) < 1e-5
    assert abs(bb.zlen - 1.0) < 1e-5

def test_operator_boolean():
    """测试布尔运算：验证体积的加减关系"""
    c1 = m3.cube(2)        # 体积 8
    c2 = m3.cube(2) + [1, 0, 0] # 体积 8，向右错开 1
    
    # 并集：两个错开 1 的 2x2x2 立方体，总体积 = 8 + 8 - 4 = 12
    union = c1 + c2
    assert abs(union.val().Volume() - 12.0) < 1e-3
    
    # 差集：8 - 4 = 4
    diff = c1 - c2
    assert abs(diff.val().Volume() - 4.0) < 1e-3

    # 交集：交叠部分是 1x2x2，体积 4
    inter = c1 * c2
    assert abs(inter.val().Volume() - 4.0) < 1e-3

def test_operator_rotation_and_shear():
    """测试旋转和剪切：验证包围盒的变形"""
    c1 = m3.cuboid(4, 2, 1)
    # 绕 Z 轴转 90 度
    rotated = c1 @ [0, 0, np.pi/2]
    bb_rot = rotated.val().BoundingBox()
    assert abs(bb_rot.xlen - 2.0) < 1e-5
    assert abs(bb_rot.ylen - 4.0) < 1e-5

    # 沿 XY 平面剪切
    sheared = c1 % [0.5, 0, 0, 0, 0, 0]
    bb_shear = sheared.val().BoundingBox()
    # X 方向由于剪切被拉长，Y 方向不变
    assert bb_shear.xlen > 4.0
    assert abs(bb_shear.ylen - 2.0) < 1e-5

# ==========================================
# 2. 异常拦截与安全性验证
# ==========================================
def test_invalid_operands():
    """测试传入非法参数时，是否能优雅报错而不是静默崩溃"""
    c1 = m3.cube(1)
    
    with pytest.raises(ValueError):
        c1 + "invalid_string"
        
    with pytest.raises(ValueError):
        c1 @ [1, 2] # 长度不够的旋转参数
        
    with pytest.raises(ValueError):
        c1 % [1, 2, 3] # 缺少剪切参数
        
    with pytest.raises(TypeError):
        m3.extremes("not a workplane")

# ==========================================
# 3. 噪声与 B-rep 变形有效性验证
# ==========================================
def test_apply_noise_validity():
    """深入测试噪声生成：验证实体有效性、水密性和体积变化"""
    np.random.seed(42) # 固定随机种子
    base = m3.cube(5)
    noisy = m3.apply_noise(base, density=0.5, smoothness=2.0, amplitude=0.3)
    
    solid = noisy.val()
    # 1. OCC 底层拓扑有效性
    assert solid.isValid(), "生成的模型不是合法的 OCC 实体"
    
    # 2. 体积变化验证（幅度为 0.3，体积必然发生变化，但不能为负）
    assert solid.Volume() > 0
    assert abs(solid.Volume() - base.val().Volume()) > 0.1

def test_brep_twist_z():
    """测试纯 B-rep 扭转：验证体积守恒和几何有效性"""
    part = m3.cuboid(2, 2, 10) # 体积 40
    twisted = m3.brep_twist_z(part, az=np.pi/4, sections=20)
    
    assert twisted is not None
    assert isinstance(twisted, cq.Workplane)
    assert twisted.val().isValid(), "扭转后的实体无效"
    
    # 扭转本身不改变体积（但由于切片放样可能有极小的数值积分误差）
    vol = twisted.val().Volume()
    assert abs(vol - 40.0) < 0.5, f"扭转导致体积严重改变: {vol}"
    
    # 包围盒应该在 XY 方向变大（因为发生了扭曲凸出）
    bb = twisted.val().BoundingBox()
    assert bb.xlen > 2.0 or bb.ylen > 2.0

# ==========================================
# 4. 2D 几何与多面体批处理验证
# ==========================================
def test_2d_boolean_and_area():
    """测试 2D 图形面积计算的精确性"""
    sq1 = m3.rectangle(2, 2) # 面积 4
    sq2 = m3.rectangle(1, 1) + [0.5, 0.5] # 面积 1，位于中心
    
    diff = sq1 - sq2
    # 无法直接取面积，我们将其拉伸为实体来计算体积
    vol = diff.to_workplane().extrude(1).val().Volume()
    assert abs(vol - 3.0) < 1e-3

@pytest.mark.parametrize("shape_func", [
    m3.tetrahedron, 
    m3.octahedron, 
    m3.dodecahedron, 
    m3.icosahedron,
    lambda: m3.spiral(2, 2, 3),
    lambda: m3.astroid(2), 
])
def test_all_primitives_valid(shape_func):
    """参数化测试：遍历所有复杂图元，确保都是有效实体/数据"""
    shape = shape_func()
    if isinstance(shape, cq.Workplane):
        assert shape.val().isValid()
        assert shape.val().Volume() > 0
    else:
        assert len(shape.vertices) > 0
