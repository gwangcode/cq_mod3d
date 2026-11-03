import numpy as np
import trimesh
import math
from scipy.ndimage import gaussian_filter, map_coordinates
import cadquery as cq
from .utils import _tessellate, _tri_mesh_to_wp

def brep_twist_z(part: cq.Workplane, az: float, sections: int = 30) -> cq.Workplane:
    """纯 B-rep 沿 Z 轴扭转（切片放样法）"""
    bb = part.val().BoundingBox()
    z_min, z_max = bb.zmin, bb.zmax
    height = z_max - z_min
    
    if height <= 0:
        return part
        
    xc = (bb.xmin + bb.xmax) / 2.0
    yc = (bb.ymin + bb.ymax) / 2.0
    profiles = []
    
    try:
        wp = cq.Workplane("XY").add(part.val().clean())
        
        for i in range(1, sections):
            t = i / sections
            z_level = z_min + t * height
            angle_deg = math.degrees(t * az * height)
            
            sec = wp.section(z_level)
            if sec is None or sec.val() is None: 
                continue
            faces = sec.faces().vals()
            if not faces: 
                continue
                
            main_face = max(faces, key=lambda f: f.Area())
            center = cq.Vector(xc, yc, z_level)
            rotated_face = main_face.rotate(center, center + cq.Vector(0, 0, 1), angle_deg)
            profiles.append(cq.Workplane("XY").add(rotated_face))
            
        if len(profiles) >= 2:
            f_bot = max(wp.faces("<Z").vals(), key=lambda f: f.Area())
            profiles.insert(0, cq.Workplane("XY").add(f_bot))
            
            f_top = max(wp.faces(">Z").vals(), key=lambda f: f.Area())
            center_top = cq.Vector(xc, yc, z_max)
            rot_f_top = f_top.rotate(center_top, center_top + cq.Vector(0, 0, 1), math.degrees(az * height))
            profiles.append(cq.Workplane("XY").add(rot_f_top))
            
            result = profiles[0].loft(ruled=True)
            if result is not None and result.val().Volume() > 0:
                return result
    except Exception as e:
        print(f"⚠️ [cq_mod3d] B-rep 放样失败，触发网格降级: {e}")
        
    # 降级保护：如果 B-rep 放样失败，转入网格法
    try:
        verts, faces = _tessellate(part, tol=0.1)
        new_verts = np.empty_like(verts)
        for i, (x, y, z) in enumerate(verts):
            tz = az * z
            Rz = np.array([[np.cos(tz), -np.sin(tz), 0],
                           [np.sin(tz),  np.cos(tz), 0],
                           [0, 0, 1]])
            new_verts[i] = Rz @ np.array([x, y, z])
        return _tri_mesh_to_wp(new_verts, faces)
    except Exception as e:
        print(f"❌ [cq_mod3d] 网格扭转彻底失败: {e}")
        return None


def apply_noise(part: cq.Workplane, density: float = 0.2, smoothness: float = 2.0, amplitude: float = 0.1) -> cq.Workplane:
    """
    为规则的 B-rep 模型生成自然的不规则纹理（凸凹）。
    
    ⚠️ 警告 (Warning)：
    此函数通过 B-rep -> Mesh -> 变形 -> B-rep 的流程工作。
    处理后的实体将失去原有的纯数学解析曲面（如完美的圆柱、圆锥面），
    转变为由微小三角平面拼接的多面体。这对于渲染和 3D 打印毫无影响，
    但可能对后续需要极低公差的高精度布尔运算或倒角操作（Fillet）带来困难。
    """
    if not isinstance(part, cq.Workplane):
        raise TypeError("输入必须是 cq.Workplane 对象")

    verts, faces = _tessellate(part, tol=0.1)
    if len(verts) == 0:
        return part

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    normals = mesh.vertex_normals

    bounds = mesh.bounds
    padding = (bounds[1] - bounds[0]) * 0.1
    b_min = bounds[0] - padding
    b_max = bounds[1] + padding
    b_size = b_max - b_min

    grid_res = max(int(32 / max(density, 0.01)), 32)
    
    random_field = np.random.rand(grid_res, grid_res, grid_res)
    smoothed_field = gaussian_filter(random_field, sigma=max(smoothness, 0.1))

    indices = (verts - b_min) / b_size * (grid_res - 1)
    noise_vals = map_coordinates(smoothed_field, indices.T, order=1)
    
    noise_vals = (noise_vals - np.mean(noise_vals)) / (np.std(noise_vals) + 1e-6)
    noise_vals = np.clip(noise_vals, -2.0, 2.0) / 2.0

    new_verts = verts + normals * (noise_vals[:, np.newaxis] * amplitude)
    result_wp = _tri_mesh_to_wp(new_verts, faces)

    return result_wp


def apply_noise_wire(part: cq.Workplane, density: float = 0.2, smoothness: float = 2.0, amplitude: float = 0.1) -> cq.Workplane:
    """为线框或曲线（如树枝骨架、路径）生成不规则的抖动。"""
    verts, _ = _tessellate(part)
    if len(verts) == 0:
        return part
    mesh = trimesh.Trimesh(vertices=verts, faces=[[0, 1, 2]] if len(verts)>2 else [], process=False)
    bounds = mesh.bounds
    b_size = bounds[1] - bounds[0]
    grid_res = max(int(32 / max(density, 0.01)), 32)
    
    random_field = np.random.rand(grid_res, grid_res, grid_res)
    smoothed_field = gaussian_filter(random_field, sigma=max(smoothness, 0.1))
    
    indices = (verts - bounds[0]) / (b_size + 1e-6) * (grid_res - 1)
    noise_vals = map_coordinates(smoothed_field, indices.T, order=1)
    noise_vals = (noise_vals - np.mean(noise_vals)) / (np.std(noise_vals) + 1e-6)
    noise_vals = np.clip(noise_vals, -2.0, 2.0) / 2.0

    offsets = np.random.randn(*verts.shape) * (noise_vals[:, np.newaxis] * amplitude)
    new_verts = verts + offsets

    wp = cq.Workplane("XY")
    for i in range(len(new_verts) - 1):
        wp = wp.moveTo(new_verts[i][0], new_verts[i][1]).lineTo(new_verts[i+1][0], new_verts[i+1][1])
    return wp
