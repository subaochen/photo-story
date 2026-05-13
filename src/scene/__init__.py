"""场景分类模块 - 延迟导入"""

from typing import List, Tuple, Dict


def classify_scene(image_path: str) -> Dict[str, float]:
    from .clip_classifier import classify_scene
    return classify_scene(image_path)


def batch_classify(image_paths: List[str]) -> List[Tuple[str, Dict[str, float]]]:
    from .clip_classifier import batch_classify
    return batch_classify(image_paths)


def get_dominant_scene(image_path: str) -> str:
    from .clip_classifier import get_dominant_scene
    return get_dominant_scene(image_path)


def group_by_scene(image_paths: List[str]) -> Dict[str, List[str]]:
    from .clip_classifier import group_by_scene
    return group_by_scene(image_paths)


__all__ = [
    "classify_scene",
    "batch_classify",
    "get_dominant_scene",
    "group_by_scene",
]