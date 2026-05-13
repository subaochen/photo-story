"""CLIP 相似度去重模块

使用 CLIP ViT-B/32 模型计算图片语义相似度，
基于余弦相似度进行精细去重。
"""

import numpy as np
from typing import List, Optional
from sklearn.metrics.pairwise import cosine_similarity
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# 全局缓存 CLIP 模型（只加载一次）
_model: Optional[CLIPModel] = None
_processor: Optional[CLIPProcessor] = None
_device: Optional[torch.device] = None


def _load_model() -> tuple:
    """加载 CLIP ViT-B/32 模型（懒加载，全局缓存）"""
    global _model, _processor, _device

    if _model is not None and _processor is not None:
        return _model, _processor

    try:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"加载 CLIP ViT-B/32 模型到 {_device}...")

        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _model.to(_device)
        _model.eval()

        logger.info("CLIP 模型加载完成")
        return _model, _processor
    except Exception as e:
        logger.error(f"CLIP 模型加载失败: {e}")
        raise


def compute_clip_embeddings(image_paths: List[str]) -> np.ndarray:
    """批量计算图片的 CLIP 嵌入向量

    Args:
        image_paths: 图片路径列表

    Returns:
        np.ndarray: 嵌入向量矩阵，形状 (n, 512)
    """
    model, processor = _load_model()

    embeddings = []
    batch_size = 32  # 批处理大小，减少显存占用

    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i + batch_size]
        batch_images = []

        for path in batch_paths:
            try:
                image = Image.open(path).convert("RGB")
                batch_images.append(image)
            except Exception as e:
                logger.warning(f"无法读取图片 {path}: {e}")
                continue

        if not batch_images:
            continue

        inputs = processor(
            images=batch_images,
            return_tensors="pt",
            padding=True
        ).to(_device)

        with torch.no_grad():
            outputs = model.get_image_features(**inputs)
            batch_embeddings = outputs.cpu().numpy()
            embeddings.append(batch_embeddings)

    if not embeddings:
        return np.array([])

    return np.vstack(embeddings)


def dedup_by_clip(
    image_paths: List[str],
    threshold: float = 0.92,
    batch_size: int = 32
) -> List[str]:
    """基于 CLIP 余弦相似度去重

    对于余弦相似度 > threshold 的图片对，只保留第一张。

    Args:
        image_paths: 图片路径列表
        threshold: 余弦相似度阈值（默认 0.92）
        batch_size: 批处理大小

    Returns:
        List[str]: 保留的图片路径列表
    """
    logger.info(f"CLIP 去重：{len(image_paths)} 张图片，阈值 {threshold}")

    try:
        embeddings = compute_clip_embeddings(image_paths)
    except Exception as e:
        logger.error(f"CLIP 嵌入计算失败，跳过 CLIP 去重: {e}")
        return image_paths

    if len(embeddings) == 0:
        return image_paths

    # 计算余弦相似度矩阵
    sim_matrix = cosine_similarity(embeddings)

    # 贪心去重：保留第一张，删除与之相似度超过阈值的后续图片
    keep_indices = set(range(len(image_paths)))
    removed = set()

    for i in range(len(image_paths)):
        if i in removed:
            continue
        for j in range(i + 1, len(image_paths)):
            if j in removed:
                continue
            if sim_matrix[i][j] > threshold:
                removed.add(j)
                logger.debug(f"  删除相似图片 [{j}]: {image_paths[j]}")

    kept = [image_paths[i] for i in range(len(image_paths)) if i not in removed]
    logger.info(f"CLIP 去重完成：{len(image_paths)} → {len(kept)}（删除了 {len(removed)} 张）")
    return kept


def hybrid_dedup(
    image_paths: List[str],
    dhash_threshold: int = 5,
    clip_threshold: float = 0.92,
    batch_size: int = 32
) -> List[str]:
    """混合策略去重

    1. 先用 dHash 粗筛（快速去重高度相似照片）
    2. 再用 CLIP 精筛（去除语义相似照片）

    Args:
        image_paths: 图片路径列表
        dhash_threshold: dHash 海明距离阈值（默认 5）
        clip_threshold: CLIP 余弦相似度阈值（默认 0.92）
        batch_size: CLIP 批处理大小

    Returns:
        List[str]: 保留的图片路径列表
    """
    from .dhash import dedup_by_dhash

    logger.info(f"混合去重开始：{len(image_paths)} 张")

    # Stage 1: dHash 粗筛
    stage1 = dedup_by_dhash(image_paths, threshold=dhash_threshold)
    logger.info(f"dHash 粗筛：{len(image_paths)} → {len(stage1)}")

    # Stage 2: CLIP 精筛
    stage2 = dedup_by_clip(stage1, threshold=clip_threshold, batch_size=batch_size)
    logger.info(f"CLIP 精筛：{len(stage1)} → {len(stage2)}")

    logger.info(f"混合去重完成：{len(image_paths)} → {len(stage2)}")
    return stage2