"""启发式美学评分模块（降级方案）

当 NIMA 模型不可用时，使用基于 OpenCV 的启发式规则进行美学评分。
"""

import cv2
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


def brightness_score(image: np.ndarray) -> float:
    """基于亮度分布评分（避免过曝/欠曝）

    理想的照片亮度分布接近正态分布，不过曝也不欠曝。
    使用直方图分析，评分越高表示亮度分布越好。

    Returns:
        float: 0-1 分
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()

    # 计算过曝比例（亮度 > 230）
    over_exposed = hist[230:].sum()
    # 计算欠曝比例（亮度 < 25）
    under_exposed = hist[:25].sum()

    # 理想情况下，过曝和欠曝比例都应很低
    score = 1.0 - (over_exposed + under_exposed)
    return max(0.0, min(1.0, score))


def sharpness_score(image: np.ndarray) -> float:
    """基于拉普拉斯算子的清晰度评分

    使用拉普拉斯算子计算图像的二阶导数，方差越大表示图像越清晰。
    模糊照片的拉普拉斯方差较小。

    Returns:
        float: 0-1 分
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()

    # 经验值：variance > 100 为清晰，< 20 为模糊
    # 使用 sigmoid 函数将方差映射到 0-1
    score = 1.0 / (1.0 + np.exp(-0.05 * (variance - 50)))
    return float(score)


def color_score(image: np.ndarray) -> float:
    """基于色彩饱和度评分

    计算 HSV 色彩空间的 S 通道均值，饱和度高的照片通常更吸引人。

    Returns:
        float: 0-1 分
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].mean() / 255.0

    # 饱和度在 0.2-0.8 之间最好，过高可能过于鲜艳
    if saturation < 0.1:
        return 0.1
    elif saturation < 0.3:
        return saturation * 2.0  # 线性提升
    elif saturation < 0.7:
        return 1.0  # 理想范围
    else:
        return max(0.5, 1.0 - (saturation - 0.7) * 1.5)  # 过高则下降


def composition_score(image: np.ndarray) -> float:
    """基于构图规则评分

    检查主体是否在画面中心附近，以及画面是否平衡。

    Returns:
        float: 0-1 分
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 使用 Sobel 边缘检测找到主体区域
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edges = np.sqrt(sobel_x**2 + sobel_y**2)

    # 计算边缘质量中心
    y_indices, x_indices = np.indices((h, w))
    total_edge = edges.sum()
    if total_edge == 0:
        return 0.5  # 无边缘信息，给中等分

    center_x = (x_indices * edges).sum() / total_edge
    center_y = (y_indices * edges).sum() / total_edge

    # 计算主体偏离画面中心的程度（归一化）
    cx, cy = w / 2, h / 2
    dx = abs(center_x - cx) / cx
    dy = abs(center_y - cy) / cy
    distance = np.sqrt(dx**2 + dy**2)

    # 偏离越小越好，但也允许三分法构图
    score = max(0.0, 1.0 - distance * 1.5)
    return float(score)


def heuristic_aesthetic_score(image_path: str) -> float:
    """综合启发式美学评分

    结合亮度、清晰度、色彩饱和度、构图等维度，综合评分。

    Args:
        image_path: 图片路径

    Returns:
        float: 0-1 分
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            logger.warning(f"无法读取图片: {image_path}")
            return 0.0
    except Exception as e:
        logger.error(f"读取图片失败 {image_path}: {e}")
        return 0.0

    scores = {
        "brightness": brightness_score(image) * 0.25,
        "sharpness": sharpness_score(image) * 0.30,
        "color": color_score(image) * 0.25,
        "composition": composition_score(image) * 0.20,
    }

    total = sum(scores.values())
    logger.debug(f"  美学评分 [{image_path[-30:]}]: {scores} = {total:.3f}")
    return total


def batch_heuristic(image_paths: List[str]) -> List[Tuple[str, float]]:
    """批量启发式美学评分

    Args:
        image_paths: 图片路径列表

    Returns:
        List[Tuple[str, float]]: [(path, score), ...]，按评分降序排列
    """
    results = []
    for path in image_paths:
        score = heuristic_aesthetic_score(path)
        results.append((path, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results