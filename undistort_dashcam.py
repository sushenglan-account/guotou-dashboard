#!/usr/bin/env python3
"""
行车记录仪广角桶形畸变矫正脚本
基于经验参数，无需棋盘格标定
处理后自动裁剪掉黑色边缘，只保留有效画面
"""

import cv2
import numpy as np
from pathlib import Path

def undistort_image(input_path, output_dir, k1=-0.3, k2=0.1, p1=0, p2=0, alpha=1.0, label=""):
    """
    使用径向畸变系数矫正图像，并自动裁剪黑色边缘
    
    参数:
        k1, k2: 径向畸变系数（桶形畸变k1<0, k2>0）
        p1, p2: 切向畸变系数（通常很小，设为0）
        alpha: 缩放因子，1.0保留所有像素，0.0裁剪到无黑边
    """
    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"无法读取图片: {input_path}")
    
    h, w = img.shape[:2]
    
    # 构建相机内参矩阵 (假设主点在图像中心，fx/fy用图像宽度的一半作为估计)
    fx = fy = w * 0.8  # 焦距估计值
    cx, cy = w / 2, h / 2
    
    K = np.array([
        [fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]
    ], dtype=np.float64)
    
    # 畸变系数: [k1, k2, p1, p2, k3]
    dist_coeffs = np.array([k1, k2, p1, p2, 0], dtype=np.float64)
    
    # 计算最优新相机矩阵
    new_K, roi = cv2.getOptimalNewCameraMatrix(K, dist_coeffs, (w, h), alpha, (w, h))
    
    # 执行去畸变
    undistorted = cv2.undistort(img, K, dist_coeffs, None, new_K)
    
    # 自动裁剪黑色边缘（只保留有效画面，不留黑边）
    undistorted = auto_crop_black_edges(undistorted)
    
    # 保存结果
    output_path = Path(output_dir) / f"undistorted_{label}_{Path(input_path).name}"
    cv2.imwrite(str(output_path), undistorted)
    
    return output_path, undistorted

def auto_crop_black_edges(img, threshold=5):
    """
    自动检测并裁剪图像边缘的黑色无效区域
    扫描所有边界，找到第一个有效像素位置，然后裁剪
    返回裁剪后的图像（不留任何黑边）
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 二值化：亮度>threshold为有效内容
    _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    
    # 获取有效像素坐标
    ys, xs = np.where(thresh > 0)
    if len(xs) == 0:
        return img
    
    # 找到有效内容的边界
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    
    # 裁剪到有效区域（+1是因为切片是左闭右开）
    return img[y_min:y_max+1, x_min:x_max+1]

def create_comparison(original, variants, output_path):
    """创建对比图：原图 + 多个矫正版本并排"""
    # 统一缩放到相同高度以便对比
    h = original.shape[0]
    resized_original = original.copy()
    
    all_images = [resized_original]
    for _, img in variants:
        # 等比例缩放，保持高度一致
        scale = h / img.shape[0]
        new_w = int(img.shape[1] * scale)
        resized = cv2.resize(img, (new_w, h))
        all_images.append(resized)
    
    # 水平拼接
    comparison = np.hstack(all_images)
    
    # 添加标签
    labels = ["Original"] + [f"k1={k1},k2={k2}" for k1, k2, _, _, _ in variant_params]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2
    
    x_positions = [0]
    for i in range(len(variants)):
        x_positions.append(x_positions[-1] + all_images[i].shape[1])
    
    for i, label in enumerate(labels):
        x = x_positions[i] + 10
        y = 30
        # 黑色背景
        (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)
        cv2.rectangle(comparison, (x-5, y-text_h-5), (x+text_w+5, y+5), (0,0,0), -1)
        cv2.putText(comparison, label, (x, y), font, font_scale, (255,255,255), thickness)
    
    cv2.imwrite(str(output_path), comparison)
    return comparison

if __name__ == "__main__":
    input_path = "/Users/sushenglan/.qianfan/workspace/d20f9967641d4235ad3d03e9942bf08a/.dumate/inbox/8c9b5fe1cd9547ddc10a0d9c801bc1e6.jpg"
    output_dir = "/Users/sushenglan/.qianfan/workspace/d20f9967641d4235ad3d03e9942bf08a"
    
    Path(output_dir).mkdir(exist_ok=True)
    
    # 读取原图
    original = cv2.imread(input_path)
    
    # 尝试多组畸变参数
    # 桶形畸变: k1 < 0, k2 > 0
    # k1 控制主要弯曲程度, k2 控制边缘区域修正
    variant_params = [
        (-0.2, 0.05, 0, 0, 1.0),   # 轻度矫正
        (-0.3, 0.08, 0, 0, 1.0),   # 中度矫正
        (-0.4, 0.12, 0, 0, 1.0),   # 较强矫正
        (-0.5, 0.15, 0, 0, 1.0),   # 强力矫正
    ]
    
    variants = []
    for i, (k1, k2, p1, p2, alpha) in enumerate(variant_params):
        label = f"v{i+1}_k1_{k1}_k2_{k2}"
        path, img = undistort_image(input_path, output_dir, k1, k2, p1, p2, alpha, label)
        variants.append((path, img))
        print(f"已生成（已裁剪黑边）: {path} | 尺寸: {img.shape[1]}x{img.shape[0]}")
    
    # 创建对比图
    comparison_path = Path(output_dir) / "comparison_all.jpg"
    create_comparison(original, variants, comparison_path)
    print(f"\n对比图已生成: {comparison_path}")
    
    # 同时生成一个最佳推荐版本（通常中度矫正效果最好）
    best_path, best_img = undistort_image(input_path, output_dir, -0.3, 0.08, 0, 0, 1.0, "RECOMMENDED")
    print(f"推荐版本（已裁剪）: {best_path} | 尺寸: {best_img.shape[1]}x{best_img.shape[0]}")
