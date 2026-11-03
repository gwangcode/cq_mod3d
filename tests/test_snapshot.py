import os
import pytest
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cq_mod3d as m3
from cq_mod3d.utils import _tessellate

# 定义基准图存放目录
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def render_to_array(part, elev=30, azim=45):
    """将 CadQuery 模型渲染为三维 NumPy 图像数组"""
    verts, faces = _tessellate(part, tol=0.5) # 为了提高测试速度，网格稍微粗一点
    
    fig = plt.figure(figsize=(6, 6), dpi=80)
    ax = fig.add_subplot(111, projection='3d')
    
    # 绘制三角面，关闭光影影响以保证纯色渲染
    triangles = verts[np.array(faces)]
    poly3d = Poly3DCollection(triangles, facecolors='gray', edgecolors='none', alpha=0.9)
    ax.add_collection3d(poly3d)
    
    # 统一视角和比例
    ax.view_init(elev=elev, azim=azim)
    if len(verts) > 0:
        bounds = [verts[:,0].min(), verts[:,0].max(), 
                  verts[:,1].min(), verts[:,1].max(), 
                  verts[:,2].min(), verts[:,2].max()]
        ax.set_xlim(bounds[0], bounds[1])
        ax.set_ylim(bounds[2], bounds[3])
        ax.set_zlim(bounds[4], bounds[5])
    
    # 去除坐标轴
    ax.axis('off')
    
    # 将 canvas 转为 numpy 数组
    fig.canvas.draw()
    
    # 兼容不同版本的 matplotlib
    try:
        img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    except AttributeError:
        img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
        img = img[:, :, :3] # 丢弃 alpha 通道
        
    if img.ndim == 1:
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        
    plt.close(fig)
    return img

def test_apply_noise_visual_snapshot():
    """图像快照测试：确保噪声算法的视觉输出保持一致"""
    # 核心：因为不修改 deformers.py，我们在外部固定全局随机种子
    np.random.seed(42)
    
    base = m3.sphere(5)
    # apply_noise 内部会使用 np.random，这里受上面的 seed 控制
    noisy = m3.apply_noise(base, density=0.5, smoothness=2.0, amplitude=0.3)
    
    current_img = render_to_array(noisy)
    baseline_path = os.path.join(SNAPSHOT_DIR, "rock_baseline.npy")
    
    # 如果基准图不存在，保存并跳过测试（即首次运行）
    if not os.path.exists(baseline_path):
        np.save(baseline_path, current_img)
        pytest.skip("已生成初始快照基准，请重新运行测试进行比对。")
        
    # 加载历史基准图并计算像素均方根误差 (RMSE)
    baseline_img = np.load(baseline_path)
    
    if current_img.shape != baseline_img.shape:
        pytest.fail(f"图像尺寸发生变化！基准: {baseline_img.shape}, 当前: {current_img.shape}")
        
    rmse = np.sqrt(np.mean((current_img.astype(np.float32) - baseline_img.astype(np.float32)) ** 2))
    
    # 阈值设为 5.0（非常严苛，肉眼绝对看不出区别）
    assert rmse < 5.0, f"视觉输出发生改变！RMSE={rmse}"
