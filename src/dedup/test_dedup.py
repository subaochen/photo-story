"""相似度去重模块测试脚本

生成模拟测试图片并验证 dHash 和 CLIP 去重效果。
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image, ImageDraw
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TEST_DIR = Path(__file__).parent.parent.parent / "data" / "test_input"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "test_output"


def generate_test_images(count: int = 20) -> list:
    """生成模拟测试图片

    生成策略：
    - 10 张完全不同的图片（不同颜色、形状）
    - 5 对相似图片（同一场景微小差异）
    - 预期：dHash 应该识别出相似对并去重

    Returns:
        list: 生成的图片路径列表
    """
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = []
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (128, 0, 0), (0, 128, 0), (0, 0, 128),
        (128, 128, 0),
    ]

    # 10 张完全不同的图片
    for i, color in enumerate(colors):
        img = Image.new("RGB", (200, 200), color)
        draw = ImageDraw.Draw(img)
        # 每个图片加不同的图案
        draw.ellipse([50, 50, 150, 150], fill=(255, 255, 255), outline=None)
        img.save(TEST_DIR / f"unique_{i}.jpg")
        image_paths.append(str(TEST_DIR / f"unique_{i}.jpg"))

    # 5 对相似图片（同一场景，微小差异）
    for pair_id in range(5):
        base_color = (100 + pair_id * 30, 50 + pair_id * 20, 150)
        # 原始版本
        img1 = Image.new("RGB", (200, 200), base_color)
        draw1 = ImageDraw.Draw(img1)
        draw1.rectangle([30, 30, 170, 170], fill=(200, 200, 200), outline=None)
        img1.save(TEST_DIR / f"similar_{pair_id}_a.jpg")
        image_paths.append(str(TEST_DIR / f"similar_{pair_id}_a.jpg"))

        # 相似版本（亮度微调 + 位置偏移 1px）
        adjusted_color = tuple(min(c + 10, 255) for c in base_color)
        img2 = Image.new("RGB", (200, 200), adjusted_color)
        draw2 = ImageDraw.Draw(img2)
        draw2.rectangle([31, 31, 171, 171], fill=(200, 200, 200), outline=None)
        img2.save(TEST_DIR / f"similar_{pair_id}_b.jpg")
        image_paths.append(str(TEST_DIR / f"similar_{pair_id}_b.jpg"))

    logger.info(f"生成了 {len(image_paths)} 张测试图片到 {TEST_DIR}")
    return image_paths


def test_dhash(image_paths: list):
    """测试 dHash 去重"""
    logger.info("\n=== dHash 去重测试 ===")

    from src.dedup.dhash import compute_dhash, hamming_distance, dedup_by_dhash

    # 计算所有图片的 dHash
    hashes = {}
    for path in image_paths:
        try:
            h = compute_dhash(path)
            hashes[path] = h
        except Exception as e:
            logger.error(f"计算 dHash 失败 {path}: {e}")

    logger.info(f"成功计算 {len(hashes)} 张图片的 dHash 值")

    # 找出相似图片对
    similar_pairs = []
    paths_list = list(hashes.keys())
    for i in range(len(paths_list)):
        for j in range(i + 1, len(paths_list)):
            dist = hamming_distance(hashes[paths_list[i]], hashes[paths_list[j]])
            if dist < 5:
                similar_pairs.append((paths_list[i], paths_list[j], dist))

    logger.info(f"发现 {len(similar_pairs)} 对相似图片（海明距离 < 5）:")
    for p1, p2, dist in similar_pairs[:10]:
        logger.info(f"  {os.path.basename(p1)} <-> {os.path.basename(p2)} 距离={dist}")

    # 执行去重
    kept = dedup_by_dhash(image_paths, threshold=5)
    logger.info(f"dHash 去重结果：{len(image_paths)} → {len(kept)}（删除了 {len(image_paths) - len(kept)} 张）")
    return kept


def test_clip(image_paths: list):
    """测试 CLIP 去重"""
    logger.info("\n=== CLIP 去重测试 ===")

    from src.dedup.clip_sim import dedup_by_clip

    try:
        kept = dedup_by_clip(image_paths, threshold=0.92)
        logger.info(f"CLIP 去重结果：{len(image_paths)} → {len(kept)}（删除了 {len(image_paths) - len(kept)} 张）")
        return kept
    except Exception as e:
        logger.warning(f"CLIP 去重失败（模型可能未下载）: {e}")
        return image_paths


def test_hybrid(image_paths: list):
    """测试混合去重"""
    logger.info("\n=== 混合去重测试 ===")

    from src.dedup.clip_sim import hybrid_dedup

    try:
        kept = hybrid_dedup(image_paths, dhash_threshold=5, clip_threshold=0.92)
        logger.info(f"混合去重结果：{len(image_paths)} → {len(kept)}（删除了 {len(image_paths) - len(kept)} 张）")
        return kept
    except Exception as e:
        logger.error(f"混合去重失败: {e}")
        return image_paths


def main():
    """主测试流程"""
    logger.info("=" * 50)
    logger.info("PhotoTrim 相似度去重模块测试")
    logger.info("=" * 50)

    # 生成测试图片
    image_paths = generate_test_images(count=20)
    logger.info(f"测试图片总数: {len(image_paths)}")

    # 测试 dHash
    dhash_kept = test_dhash(image_paths)
    dhash_removed = len(image_paths) - len(dhash_kept)
    dhash_expected = 10  # 5对相似图片，每对应删除1张
    dhash_accuracy = min(dhash_removed / dhash_expected * 100, 100)
    logger.info(f"dHash 去重准确率: {dhash_accuracy:.0f}%（预期删除 {dhash_expected} 张，实际删除 {dhash_removed} 张）")

    # 测试 CLIP
    clip_kept = test_clip(dhash_kept)
    clip_removed = len(dhash_kept) - len(clip_kept)

    # 测试混合
    hybrid_kept = test_hybrid(image_paths)
    hybrid_removed = len(image_paths) - len(hybrid_kept)

    # 汇总
    logger.info("\n" + "=" * 50)
    logger.info("测试汇总")
    logger.info("=" * 50)
    logger.info(f"输入图片: {len(image_paths)}")
    logger.info(f"dHash 去重后: {len(dhash_kept)}（移除 {dhash_removed} 张）")
    logger.info(f"CLIP 精筛后: {len(clip_kept)}（移除 {clip_removed} 张）")
    logger.info(f"混合去重后: {len(hybrid_kept)}（移除 {hybrid_removed} 张）")

    logger.info("\n✅ 测试完成！")


if __name__ == "__main__":
    main()