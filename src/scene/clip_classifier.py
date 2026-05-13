"""CLIP 零样本场景分类模块

使用 CLIP 模型对照片进行场景分类，区分风景/美食/人物/建筑等。
"""

import os
import torch
from PIL import Image
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# 预定义的场景类别（旅行照片常用）
SCENE_CATEGORIES = [
    "landscape", "cityscape", "architecture", "food",
    "portrait", "group photo", "sunset", "beach",
    "mountain", "street", "night scene", "indoor",
    "nature", "wildlife", "macro", "aerial view",
]

# 中文映射
SCENE_CN = {
    "landscape": "风景", "cityscape": "城市", "architecture": "建筑",
    "food": "美食", "portrait": "人像", "group photo": "合影",
    "sunset": "日落", "beach": "海滩", "mountain": "山景",
    "street": "街道", "night scene": "夜景", "indoor": "室内",
    "nature": "自然", "wildlife": "野生动物", "macro": "微距",
    "aerial view": "航拍",
}

# 全局缓存 CLIP 模型
_model: Optional[torch.nn.Module] = None
_processor = None
_device: Optional[torch.device] = None


def _load_model():
    """加载 CLIP 模型（懒加载）"""
    global _model, _processor, _device

    if _model is not None:
        return _model, _processor, _device

    try:
        from transformers import CLIPProcessor, CLIPModel

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"加载 CLIP 模型到 {_device}...")

        # 临时清除代理环境变量（SOCKS5 代理会干扰模型下载）
        old_env = {}
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
            old_env[key] = os.environ.pop(key, None)

        try:
            _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        finally:
            for key, val in old_env.items():
                if val is not None:
                    os.environ[key] = val
        _model.to(_device)
        _model.eval()

        logger.info("CLIP 场景分类模型加载完成")
        return _model, _processor, _device
    except Exception as e:
        logger.error(f"CLIP 模型加载失败: {e}")
        raise


def classify_scene(image_path: str) -> Dict[str, float]:
    """对单张图片进行场景分类

    返回每个场景类别的概率分数。

    Args:
        image_path: 图片路径

    Returns:
        Dict[str, float]: {场景类别: 概率分数}
    """
    try:
        model, processor, device = _load_model()
    except Exception as e:
        logger.error(f"场景分类失败（模型不可用）: {e}")
        return {"unknown": 1.0}

    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(
            text=SCENE_CATEGORIES,
            images=image,
            return_tensors="pt",
            padding=True
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

        results = {}
        for category, prob in zip(SCENE_CATEGORIES, probs):
            cn_name = SCENE_CN.get(category, category)
            results[cn_name] = float(prob)

        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))

    except Exception as e:
        logger.error(f"场景分类失败 {image_path}: {e}")
        return {"unknown": 1.0}


def batch_classify(
    image_paths: List[str],
    batch_size: int = 16
) -> List[Tuple[str, Dict[str, float]]]:
    """批量场景分类

    Args:
        image_paths: 图片路径列表
        batch_size: 批处理大小

    Returns:
        List[Tuple[str, Dict[str, float]]]: [(path, {category: prob}), ...]
    """
    results = []
    for i in range(0, len(image_paths), batch_size):
        batch = image_paths[i:i + batch_size]
        for path in batch:
            scores = classify_scene(path)
            results.append((path, scores))

    return results


def get_dominant_scene(image_path: str) -> str:
    """获取图片的主要场景类别

    Args:
        image_path: 图片路径

    Returns:
        str: 主要场景类别（中文）
    """
    scores = classify_scene(image_path)
    if not scores:
        return "未知"
    return max(scores, key=scores.get)


def group_by_scene(
    image_paths: List[str],
    threshold: float = 0.3
) -> Dict[str, List[str]]:
    """按场景对图片进行分组

    每张图片可能属于多个场景（概率超过 threshold），
    取概率最高的场景作为分组依据。

    Args:
        image_paths: 图片路径列表
        threshold: 概率阈值

    Returns:
        Dict[str, List[str]]: {场景: [图片路径列表]}
    """
    groups = defaultdict(list)
    for path in image_paths:
        scores = classify_scene(path)
        if scores:
            top_scene = max(scores, key=scores.get)
            top_prob = scores[top_scene]
            if top_prob >= threshold:
                groups[top_scene].append(path)
            else:
                groups["其他"].append(path)

    return dict(groups)