"""人脸识别模块

基于 MediaPipe 的人脸检测、匹配与分组。
"""

from typing import List, Dict


def detect_faces(image_path: str) -> List[dict]:
    from .detector import detect_faces
    return detect_faces(image_path)


def batch_detect_faces(image_paths: List[str]) -> Dict:
    from .detector import batch_detect_faces
    return batch_detect_faces(image_paths)


def count_faces(image_path: str) -> int:
    from .detector import count_faces
    return count_faces(image_path)


def extract_face_region(image_path: str, face: dict):
    from .matcher import extract_face_region
    return extract_face_region(image_path, face)


def group_faces_by_image(detection_results: Dict) -> Dict:
    from .matcher import group_faces_by_image
    return group_faces_by_image(detection_results)


def count_total_faces(detection_results: Dict) -> int:
    from .matcher import count_total_faces
    return count_total_faces(detection_results)


def get_images_with_faces(detection_results: Dict, min_faces: int = 1) -> List[str]:
    from .matcher import get_images_with_faces
    return get_images_with_faces(detection_results, min_faces)


def get_images_by_face_count(detection_results: Dict) -> Dict[int, List[str]]:
    from .matcher import get_images_by_face_count
    return get_images_by_face_count(detection_results)


__all__ = [
    "detect_faces",
    "batch_detect_faces",
    "count_faces",
    "extract_face_region",
    "group_faces_by_image",
    "count_total_faces",
    "get_images_with_faces",
    "get_images_by_face_count",
]