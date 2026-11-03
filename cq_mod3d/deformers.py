import numpy as np
import trimesh
import math
from scipy.ndimage import gaussian_filter, map_coordinates
import cadquery as cq
from .utils import _tessellate, _tri_mesh_to_wp

def brep_twist_z(part, az, sections=30):
    """纯 B-rep 沿 Z 轴扭转（切片放样法）"""
    bb = part.val().BoundingBox()
    z_min, z_max = bb.zmin, bb.zmax
    height = z_max - z_min
    
    if height <= 0:
        return part
        
    xc = (bb.xmin + bb.xmax) / 2.0
    yc = (bb.ymin + bb.ymax) / 2.0
    
    profiles = []
    # 确保实体是清理过的，否则布尔切割容易失败
    wp = cq.Workplane("XY").add(part.val().clean())
    
    # 从 1 循环到 sections-1，避开底端和顶端，防止切片退化
    for i in range(1, sections):
        t = i / sections
        z_level = z_min + t * height
        angle_deg = math.degrees(t * az * height)
        
        try:
            # 构造一个无限大的切面
            cut_plane = cq.Face.makePlane(10000, 10000, basePnt=(0, 0, z_level), dir=(0, 0, 1))
            # 将实体切掉上半部分，保留下半部分
            bottom = wp.split(cut_plane, keepTop=False)
            if bottom is None: 
                continue
                
            # 提取下半部分实体最高处的面（即正好在 z_level 处的截面）
            faces = bottom.faces(">Z").vals()
            if not faces: 
                continue
                
            main_face = max(faces, key=lambda f: f.Area())
            center = cq.Vector(xc, yc, z_level)
            rotated_face = main_face.rotate(center, center + cq.Vector(0, 0, 1), angle_deg)
            profiles.append(cq.Workplane("XY").add(rotated_face))
        except Exception:
            continue
            
    if len(profiles) < 2:
        return None
        
    try:
        # 安全地补上最底端的原始底面
        f_bot = max(wp.faces("<Z").vals(), key=lambda f: f.Area())
        profiles.insert(0, cq.Workplane("XY").add(f_bot))
        
        # 安全地补上最顶端的原始顶面，并施加最终的旋转
        f_top = max(wp.faces(">Z").vals(), key=lambda f: f.Area())
        center = cq.Vector(xc, yc, z_max)
        rot_f_top = f_top.rotate(center, center + cq.Vector(0, 0, 1), math.degrees(az * height))
        profiles.append(cq.Workplane("XY").add(rot_f_top))
        
        # 所有截面按顺序放样
        return profiles[0].loft(ruled=True)
    except Exception:
        return None


def apply_noise(part, density=0.2, smoothness=2.0, amplitude=0.1):
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


def apply_noise_wire(part, density=0.2, smoothness=2.0, amplitude=0.1):
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
