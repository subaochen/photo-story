import mediapipe as mp
import cv2
import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 全局缓存 MediaPipe 模型
_face_detection = None


def _load_model():
    """加载 MediaPipe 人脸检测模型（懒加载）"""
    global _face_detection
    if _face_detection is None:
        mp_face_detection = mp.solutions.face_detection
        _face_detection = mp_face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5
        )
    return _face_detection


def _load_image(image_path: str) -> Optional[np.ndarray]:
    """读取图片，失败时返回 None"""
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Failed to load image: {image_path}")
        return None
    # MediaPipe 期望 BGR -> RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image


def _extract_detection_results(detections, image_shape: Tuple[int, int, int]) -> List[dict]:
    """从 MediaPipe 检测结果中提取结构化数据"""
    h, w, _ = image_shape
    faces = []

    if not detections:
        return faces

    for detection in detections:
        bbox = detection.location_data.relative_bounding_box
        # 转换为绝对像素坐标
        x = int(bbox.xmin * w)
        y = int(bbox.ymin * h)
        bw = int(bbox.width * w)
        bh = int(bbox.height * h)

        # 边界裁剪到图片范围内
        x = max(0, x)
        y = max(0, y)
        bw = min(bw, w - x)
        bh = min(bh, h - y)

        # 提取关键点
        keypoints = []
        if detection.location_data.relative_keypoints:
            for kp in detection.location_data.relative_keypoints:
                keypoints.append({
                    "x": int(kp.x * w),
                    "y": int(kp.y * h),
                })

        faces.append({
            "bbox": [x, y, bw, bh],
            "keypoints": keypoints,
            "confidence": detection.score[0],
        })

    return faces


def detect_faces(image_path: str) -> List[dict]:
    """
    检测图片中的人脸

    Args:
        image_path: 图片文件路径

    Returns:
        人脸列表，每个人脸包含:
        - bbox: [x, y, w, h] 相对于原图尺寸的边框坐标
        - keypoints: 关键点列表，每个关键点为 {"x": int, "y": int}
        - confidence: 检测置信度 (0.0 ~ 1.0)

        如果图片读取失败或无人脸，返回空列表
    """
    image = _load_image(image_path)
    if image is None:
        return []

    model = _load_model()
    results = model.process(image)

    return _extract_detection_results(results.detections, image.shape)


def batch_detect_faces(image_paths: List[str]) -> dict:
    """
    批量检测人脸

    Args:
        image_paths: 图片文件路径列表

    Returns:
        {image_path: [face1, face2, ...], ...}
        失败或无人脸的图片对应空列表
    """
    result = {}
    for path in image_paths:
        try:
            result[path] = detect_faces(path)
        except Exception as e:
            logger.error(f"Error detecting faces in {path}: {e}")
            result[path] = []
    return result


def count_faces(image_path: str) -> int:
    """
    返回图片中的人脸数量

    Args:
        image_path: 图片文件路径

    Returns:
        人脸数量，图片读取失败时返回 0
    """
    return len(detect_faces(image_path))
