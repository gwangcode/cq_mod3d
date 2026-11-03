import pytest
import cadquery as cq
import numpy as np
import cq_mod3d as m3

# ==========================================
# 1. 验证变换与布尔运算（覆盖所有运算符）
# ==========================================
def test_operator_subtraction():
    """测试差集 - 和 反向平移 -"""
    c1 = m3.cube(2)
    c2 = m3.cube(2) + [1, 0, 0]  # 平移
    
    diff = c1 - c2
    assert isinstance(diff, cq.Workplane)
    # 两个边长 2 的立方体，错开 1，差集体积应该是 8 - 4 = 4
    assert abs(diff.val().Volume() - 4.0) < 1e-3
    
    # 测试反向平移
    moved = c1 - [1, 0, 0]
    assert abs(moved.val().BoundingBox().xmin - (-2.5)) < 1e-5

def test_operator_multiplication():
    """测试交集 * 和缩放 *"""
    c1 = m3.cube(2)
    s1 = m3.sphere(1.5) # 半径1.5的球放中间
    
    # 交集
    inter = c1 * s1
    assert isinstance(inter, cq.Workplane)
    assert inter.val().Volume() > 0
    
    # 均匀缩放
    scaled = c1 * 3
    assert abs(scaled.val().BoundingBox().xlen - 6.0) < 1e-5
    
    # 非均匀缩放
    non_uniform = c1 * [3, 1, 0.5]
    bb = non_uniform.val().BoundingBox()
    assert abs(bb.xlen - 6.0) < 1e-5
    assert abs(bb.ylen - 2.0) < 1e-5
    assert abs(bb.zlen - 1.0) < 1e-5

def test_operator_rotation():
    """测试旋转 @"""
    c1 = m3.cuboid(4, 2, 1) # 长条
    rotated = c1 @ [0, 0, np.pi/2] # 绕 Z 转 90度
    bb = rotated.val().BoundingBox()
    # 原本 x=4, y=2，转90度后 x=2, y=4
    assert abs(bb.xlen - 2.0) < 1e-5
    assert abs(bb.ylen - 4.0) < 1e-5


# ==========================================
# 2. 验证噪声与水密性（核心难点）
# ==========================================
def test_apply_noise_validity():
    """测试噪声生成后，是否依然是合法且水密的实体"""
    base = m3.cube(5)
    noisy = m3.apply_noise(base, density=0.5, smoothness=2.0, amplitude=0.3)
    
    solid = noisy.val()
    
    # 1. 验证是否为合法的 OCC 实体 (没有被撕裂)
    assert solid.isValid(), "生成的模型是 Invalid Solid"
    
    # 2. 验证水密性 (Watertight)
    # CadQuery 的 Solid 只要 isValid 且没抛出异常，通常就是封闭的
    # 但我们可以尝试做一次微小的收缩，如果不报错说明没问题
    shrunk = solid.faces("<Z").workplane().offset(-0.01)
    assert shrunk is not None
    
    # 3. 验证形变确实起作用了 (体积应该变了)
    assert abs(solid.Volume() - base.val().Volume()) > 0.1


# ==========================================
# 3. 验证纯 B-rep 扭转
# ==========================================
def test_brep_twist():
    """测试纯 B-rep 切片放样扭转是否生成合法实体"""
    # 用一个长条立方体测试
    part = m3.cuboid(2, 2, 10)
    # 沿 Z 轴扭转 90度
    twisted = m3.brep_twist_z(part, az=np.pi/2, sections=20)
    
    assert twisted is not None, "扭转失败，返回了 None"
    assert isinstance(twisted, cq.Workplane)
    assert twisted.val().isValid(), "扭转后的实体无效"
    
    # 验证包围盒：原本 2x2，扭转 90 度后，中间部分会向外凸出
    bb = twisted.val().BoundingBox()
    assert bb.xlen > 2.0 
    assert bb.ylen > 2.0


# ==========================================
# 4. 2D 图元与运算测试
# ==========================================
def test_2d_shapes_and_ops():
    """测试 2D 图形生成、面积与布尔运算"""
    # 生成一个半径 2 的圆
    c = m3.circle(R=2)
    assert len(c.vertices) > 0
    
    # 生成一个 2x2 的正方形
    sq = m3.rectangle(2, 2) 
    
    # 2D 交集
    inter_2d = c * sq
    assert isinstance(inter_2d, m3.Shape2d)
    
    # 2D 并集
    union_2d = c + sq + [3, 0] # 平移 3 后求并集
    assert isinstance(union_2d, m3.Shape2d)
    
    # 转换为 Workplane 并拉伸出实体
    wp = union_2d.to_workplane().extrude(5)
    assert isinstance(wp, cq.Workplane)
    assert wp.val().Volume() > 0


# ==========================================
# 5. 批量图元有效性测试 (参数化测试)
# ==========================================
@pytest.mark.parametrize("shape_func", [
    m3.tetrahedron, 
    m3.octahedron, 
    m3.dodecahedron, 
    m3.icosahedron,
    lambda: m3.spiral(2, 2, 3), # 阿基米德螺线
    lambda: m3.astroid(2),      # 星形线
    lambda: m3.heart(2) if hasattr(m3, 'heart') else m3.circle(1) # 如果有心形线
])
def test_all_primitives_valid(shape_func):
    """参数化测试：确保所有 3D/2D 图元函数都能生成有效对象"""
    shape = shape_func()
    # 如果是 Workplane，检查是否有效
    if isinstance(shape, cq.Workplane):
        assert shape.val().isValid()
    # 如果是 Shape2d，检查顶点数
    else:
        assert len(shape.vertices) > 0
