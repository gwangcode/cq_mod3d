import cadquery as cq
from typing import Union, Tuple

def array_rect(part: cq.Workplane, nx: int, ny: int, spacing: Union[float, Tuple[float, float]]) -> cq.Workplane:
    """矩形阵列。"""
    dx, dy = (spacing, spacing) if isinstance(spacing, (int, float)) else spacing
    to_compound = []
    for i in range(nx):
        for j in range(ny):
            to_compound.append(part.translate((i * dx, j * dy, 0)).val())
            
    # 对于互不相交的阵列，直接返回 Compound 更高效且不破坏拓扑
    return cq.Workplane("XY").add(cq.Compound.makeCompound(to_compound))

def array_polar(part: cq.Workplane, count: int, radius: float, angle: float = 360.0) -> cq.Workplane:
    """极坐标（环形）阵列。"""
    to_compound = []
    for i in range(count):
        deg = i * (angle / count)
        rotated = part.rotate((0, 0, 0), (0, 0, 1), deg).translate((radius, 0, 0))
        to_compound.append(rotated.val())
        
    return cq.Workplane("XY").add(cq.Compound.makeCompound(to_compound))
