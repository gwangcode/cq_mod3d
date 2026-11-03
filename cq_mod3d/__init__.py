# cq_mod3d/__init__.py

# 1. 最先执行 patch，保证所有 cq.Workplane 都被注入了魔法
from . import patch

# 2. 导出数据类
from .shapes import Shape2d, Shape3d, solenoid

# 3. 导出 2D / 3D 生成函数
from .primitives import (
    cuboid, cube, cylinder, cone, sphere, torus, ellipsoid,
    prism, pyramid, convex_hull, tetrahedron, octahedron, dodecahedron, icosahedron,
    polygon, circle, rectangle, square, parallelogram, rhombus, trapezoid,
    pentagon, hexagon, heptagon, octagon, nonagon, decagon, ellipse,
    parabola, hyperbola, spiral, cardioid, cycloid, astroid, catenary,
    epicycloid, hypocycloid, lemniscate, semicircle, sine, tangent
)

# 4. 导出变形算法
from .deformers import apply_noise, apply_noise_wire, brep_twist_z

# 5. 导出底层工具（包括 extremes）
from .utils import extremes

# 6. 导出可视化
from .vis import showx, plothull, plot2d, plot3d