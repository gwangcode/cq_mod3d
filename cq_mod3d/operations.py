import cadquery as cq
from typing import Union, Tuple

def array_rect(part: cq.Workplane, nx: int, ny: int, spacing: Union[float, Tuple[float, float]]) -> cq.Workplane:
    """
    矩形阵列。
    :param part: 原始零件
    :param nx: X 方向数量
    :param ny: Y 方向数量
    :param spacing: 间距（单个数为 XY 相同间距，元组为 (dx, dy)）
    """
    dx, dy = (spacing, spacing) if isinstance(spacing, (int, float)) else spacing
    res = cq.Workplane("XY")
    
    # 使用 fuse 替代多次 union 提升性能
    to_fuse = []
    for i in range(nx):
        for j in range(ny):
            to_fuse.append(part.translate((i * dx, j * dy, 0)))
            
    for p in to_fuse:
        res = res.union(p)
    return res

def array_polar(part: cq.Workplane, count: int, radius: float, angle: float = 360.0) -> cq.Workplane:
    """
    极坐标（环形）阵列。
    :param part: 原始零件
    :param count: 阵列数量
    :param radius: 阵列半径
    :param angle: 阵列占据的圆周角度（默认 360 度）
    """
    res = cq.Workplane("XY")
    to_fuse = []
    for i in range(count):
        deg = i * (angle / count)
        # 绕原点旋转并沿 X 平移，也可以根据需求改成围绕特定中心
        rotated = part.rotate((0, 0, 0), (0, 0, 1), deg).translate((radius, 0, 0))
        to_fuse.append(rotated)
        
    for p in to_fuse:
        res = res.union(p)
    return res
