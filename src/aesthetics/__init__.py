"""美学评分模块

提供 NIMA 模型评分和启发式规则评分两种方案。
当 NIMA 模型不可用时自动降级到启发式规则。
"""

from typing import List, Tuple


def load_nima_model():
    from .nima import _load_model
    return _load_model()


def predict_aesthetic_score(image_path: str) -> float:
    from .nima import predict_aesthetic_score
    return predict_aesthetic_score(image_path)


def batch_predict(image_paths: List[str], batch_size: int = 32) -> List[Tuple[str, float]]:
    from .nima import batch_predict
    return batch_predict(image_paths, batch_size)


def rank_by_aesthetics(image_paths: List[str], top_k: int = 100) -> List[Tuple[str, float]]:
    from .nima import rank_by_aesthetics
    return rank_by_aesthetics(image_paths, top_k)


def heuristic_aesthetic_score(image_path: str) -> float:
    from .heuristic import heuristic_aesthetic_score
    return heuristic_aesthetic_score(image_path)


def batch_heuristic(image_paths: List[str]) -> List[Tuple[str, float]]:
    from .heuristic import batch_heuristic
    return batch_heuristic(image_paths)


def brightness_score(image):
    from .heuristic import brightness_score
    return brightness_score(image)


def sharpness_score(image):
    from .heuristic import sharpness_score
    return sharpness_score(image)


def color_score(image):
    from .heuristic import color_score
    return color_score(image)


__all__ = [
    "load_nima_model",
    "predict_aesthetic_score",
    "batch_predict",
    "rank_by_aesthetics",
    "heuristic_aesthetic_score",
    "batch_heuristic",
    "brightness_score",
    "sharpness_score",
    "color_score",
]