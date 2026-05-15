"""NIMA 美学评分模块

使用 MobileNetV2 作为 backbone 的 NIMA（Neural Image Assessment）模型，
预测图片的美学评分（1-10 分）。
"""

import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
from PIL import Image
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# 全局缓存模型
_model: Optional[nn.Module] = None
_device: Optional[torch.device] = None
_transform: Optional[transforms.Compose] = None


class NIMA(nn.Module):
    """NIMA 模型：MobileNetV2 backbone + 10分类头"""

    def __init__(self):
        super().__init__()
        backbone = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1)
        self.features = backbone.features
        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(0.75),
            nn.Linear(1280, 10),
            nn.Softmax(dim=1),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


def _load_model() -> Tuple[nn.Module, torch.device, transforms.Compose]:
    """加载 NIMA 模型（懒加载，全局缓存）"""
    global _model, _device, _transform

    if _model is not None and _device is not None:
        return _model, _device, _transform

    try:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"加载 NIMA 模型到 {_device}...")

        _model = NIMA()
        _model.to(_device)
        _model.eval()

        _transform = transforms.Compose([
            transforms.Resize(224),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        logger.info("NIMA 模型加载完成")
        return _model, _device, _transform

    except Exception as e:
        logger.error(f"NIMA 模型加载失败: {e}")
        raise


def predict_aesthetic_score(image_path: str) -> float:
    """预测单张图片的美学评分

    输出为 1-10 分的加权平均。

    Args:
        image_path: 图片路径

    Returns:
        float: 1-10 分
    """
    try:
        model, device, transform = _load_model()
    except Exception:
        logger.warning("NIMA 模型不可用，降级到启发式规则")
        from .heuristic import heuristic_aesthetic_score
        return heuristic_aesthetic_score(image_path) * 10.0

    try:
        image = Image.open(image_path).convert("RGB")
        input_tensor = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(input_tensor)
            # 计算加权平均（1-10 分）
            weights = torch.arange(1, 11, dtype=torch.float32).to(device)
            score = (output * weights).sum().item()

        return score

    except Exception as e:
        logger.error(f"美学评分失败 {image_path}: {e}")
        # 降级到启发式规则
        from .heuristic import heuristic_aesthetic_score
        return heuristic_aesthetic_score(image_path) * 10.0


def batch_predict(
    image_paths: List[str],
    batch_size: int = 32,
) -> List[Tuple[str, float]]:
    """批量预测美学评分

    Args:
        image_paths: 图片路径列表
        batch_size: 批处理大小

    Returns:
        List[Tuple[str, float]]: [(path, score), ...]
    """
    try:
        model, device, transform = _load_model()
    except Exception:
        logger.warning("NIMA 模型不可用，降级到启发式规则")
        from .heuristic import batch_heuristic
        results = batch_heuristic(image_paths)
        return [(p, s * 10.0) for p, s in results]

    results = []
    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i + batch_size]
        batch_tensors = []
        valid_paths = []

        for path in batch_paths:
            try:
                image = Image.open(path).convert("RGB")
                tensor = transform(image)
                batch_tensors.append(tensor)
                valid_paths.append(path)
            except Exception as e:
                logger.warning(f"无法处理图片 {path}: {e}")
                # 使用启发式规则作为该张图片的降级
                from .heuristic import heuristic_aesthetic_score
                score = heuristic_aesthetic_score(path) * 10.0
                results.append((path, score))

        if not batch_tensors:
            continue

        batch = torch.stack(batch_tensors).to(device)
        with torch.no_grad():
            outputs = model(batch)
            weights = torch.arange(1, 11, dtype=torch.float32).to(device)
            scores = (outputs * weights).sum(dim=1).cpu().numpy()

        for path, score in zip(valid_paths, scores):
            results.append((path, float(score)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def rank_by_aesthetics(
    image_paths: List[str],
    top_k: int = 100,
) -> List[Tuple[str, float]]:
    """按美学评分排序，取前 top_k 张

    Args:
        image_paths: 图片路径列表
        top_k: 保留数量

    Returns:
        List[Tuple[str, float]]: 评分最高的 top_k 张 [(path, score)]
    """
    results = batch_predict(image_paths)
    return results[:top_k]


def rank_with_details(
    image_paths: List[str],
    top_k: int = 100,
) -> dict:
    """按美学评分排序（verbose 版本）

    返回带排名信息的评分结果，包含：
    - 每张照片的评分
    - 排名
    - 统计信息（平均分、最高分、最低分）

    Args:
        image_paths: 图片路径列表
        top_k: 保留数量

    Returns:
        dict: 包含评分、排名和统计信息的字典
    """
    logger.info(f"美学评分（verbose）开始：{len(image_paths)} 张")

    results = batch_predict(image_paths)
    total_count = len(results)

    if total_count == 0:
        return {
            "ranking": [],
            "statistics": {
                "total": 0,
                "top_k": 0,
                "average_score": 0,
                "max_score": 0,
                "min_score": 0
            },
            "metadata": {
                "input_count": len(image_paths),
                "processed_count": 0
            }
        }

    # 计算统计信息
    scores = [score for _, score in results]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    min_score = min(scores)

    # 构建排名结果
    ranking = []
    for i, (path, score) in enumerate(results[:top_k], 1):
        ranking.append({
            "rank": i,
            "path": path,
            "score": score
        })

    logger.info(f"美学评分（verbose）完成：选出前 {len(ranking)} 张")

    return {
        "ranking": ranking,
        "statistics": {
            "total": total_count,
            "top_k": len(ranking),
            "average_score": round(avg_score, 2),
            "max_score": round(max_score, 2),
            "min_score": round(min_score, 2)
        },
        "metadata": {
            "input_count": len(image_paths),
            "processed_count": total_count
        }
    }