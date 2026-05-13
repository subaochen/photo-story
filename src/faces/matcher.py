"""人脸匹配与聚类模块

基于 MediaPipe 人脸检测结果，使用人脸关键点进行匹配和聚类。
"""

import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def extract_face_region(image_path: str, face: dict) -> np.ndarray:
    """从图片中提取人脸区域

    Args:
        image_path: 图片路径
        face: 人脸检测结果 {"bbox": [x, y, w, h], ...}

    Returns:
        np.ndarray: 人脸区域图像 (RGB)
    """
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图片: {image_path}")

    x, y, w, h = [int(v) for v in face["bbox"]]
    # 扩大人脸区域 20%，包含更多特征
    padding_x = int(w * 0.2)
    padding_y = int(h * 0.2)
    x1 = max(0, x - padding_x)
    y1 = max(0, y - padding_y)
    x2 = min(img.shape[1], x + w + padding_x)
    y2 = min(img.shape[0], y + h + padding_y)

    face_img = img[y1:y2, x1:x2]
    return cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)


def group_faces_by_image(
    detection_results: Dict[str, List[dict]]
) -> Dict[str, List[dict]]:
    """按图片对人脸检测结果进行分组

    Args:
        detection_results: batch_detect_faces 的返回结果

    Returns:
        Dict[str, List[dict]]: 每张图片的人脸列表
    """
    return detection_results


def count_total_faces(detection_results: Dict[str, List[dict]]) -> int:
    """统计检测到的总人脸数

    Args:
        detection_results: batch_detect_faces 的返回结果

    Returns:
        int: 总人脸数
    """
    return sum(len(faces) for faces in detection_results.values())


def get_images_with_faces(
    detection_results: Dict[str, List[dict]],
    min_faces: int = 1
) -> List[str]:
    """获取包含至少 min_faces 张人脸的照片

    Args:
        detection_results: batch_detect_faces 的返回结果
        min_faces: 最少人脸数

    Returns:
        List[str]: 符合条件的图片路径
    """
    return [
        path for path, faces in detection_results.items()
        if len(faces) >= min_faces
    ]


def get_images_by_face_count(
    detection_results: Dict[str, List[dict]]
) -> Dict[int, List[str]]:
    """按人脸数量对图片进行分组

    Args:
        detection_results: batch_detect_faces 的返回结果

    Returns:
        Dict[int, List[str]]: {人脸数: [图片路径列表]}
    """
    result = defaultdict(list)
    for path, faces in detection_results.items():
        result[len(faces)].append(path)
    return dict(result)