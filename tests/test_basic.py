import pytest
import cadquery as cq
import cq_mod3d as m3


def test_imports():
    """测试包是否能正常导入"""
    assert m3 is not None
    assert hasattr(m3, "sphere")
    assert hasattr(m3, "apply_noise")

def test_primitives():
    """测试基础图元生成"""
    part = m3.sphere(1)
    assert isinstance(part, cq.Workplane)
    
    # 验证体积大致正确
    vol = part.val().Volume()
    assert 4.0 < vol < 4.2  # (4/3)*pi*1^3 ≈ 4.188

def test_operator_patch_translation():
    """测试平移运算符 +"""
    part = m3.cube(1)
    moved = part + [10, 0, 0]
    bb = moved.val().BoundingBox()
    # 原来的 box 在 -0.5 到 0.5，平移 10 后应该在 9.5 到 10.5
    assert abs(bb.xmin - 9.5) < 1e-5

def test_operator_patch_boolean():
    """测试布尔并集 + 和差集 -"""
    c1 = m3.cube(2)
    c2 = m3.cube(2) + [1, 0, 0]
    union = c1 + c2
    assert isinstance(union, cq.Workplane)

def test_apply_noise():
    """测试噪声生成器是否不报错并返回实体"""
    base = m3.sphere(5)
    # 使用较小的幅度，确保不会自交崩溃
    rock = m3.apply_noise(base, density=0.5, smoothness=2.0, amplitude=0.2)
    assert isinstance(rock, cq.Workplane)
    assert rock.val().Volume() > 0
