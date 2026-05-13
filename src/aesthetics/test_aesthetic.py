"""美学评分模块测试脚本

生成不同质量的照片，验证启发式评分和 NIMA 评分的区分能力。
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image, ImageDraw, ImageFilter
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TEST_DIR = Path(__file__).parent.parent.parent / "data" / "test_aesthetic"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "test_output"


def generate_test_images() -> list:
    """生成测试图片，包含不同质量的照片

    生成策略：
    - 2 张高清晰度、好构图的照片（预期高分）
    - 2 张中等质量照片
    - 2 张模糊/过曝/欠曝照片（预期低分）

    Returns:
        list: 生成的图片路径列表
    """
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = []

    # 1. 高质量照片：清晰、色彩丰富、构图好
    img = Image.new("RGB", (400, 300), (135, 206, 235))  # 蓝天背景
    draw = ImageDraw.Draw(img)
    draw.ellipse([100, 100, 300, 250], fill=(34, 139, 34))  # 绿色主体
    draw.ellipse([180, 60, 220, 100], fill=(255, 215, 0))   # 黄色太阳
    img.save(TEST_DIR / "high_quality_1.jpg")
    image_paths.append(str(TEST_DIR / "high_quality_1.jpg"))

    img2 = Image.new("RGB", (400, 300), (100, 149, 237))
    draw2 = ImageDraw.Draw(img2)
    draw2.polygon([(200, 50), (50, 250), (350, 250)], fill=(255, 140, 0))
    draw2.rectangle([0, 250, 400, 300], fill=(34, 139, 34))
    img2.save(TEST_DIR / "high_quality_2.jpg")
    image_paths.append(str(TEST_DIR / "high_quality_2.jpg"))

    # 2. 中等质量照片
    img3 = Image.new("RGB", (400, 300), (200, 200, 200))
    draw3 = ImageDraw.Draw(img3)
    draw3.rectangle([100, 50, 300, 250], fill=(150, 150, 150))
    img3.save(TEST_DIR / "medium_quality_1.jpg")
    image_paths.append(str(TEST_DIR / "medium_quality_1.jpg"))

    img4 = Image.new("RGB", (400, 300), (180, 180, 200))
    draw4 = ImageDraw.Draw(img4)
    draw4.ellipse([50, 50, 350, 250], fill=(160, 160, 180))
    img4.save(TEST_DIR / "medium_quality_2.jpg")
    image_paths.append(str(TEST_DIR / "medium_quality_2.jpg"))

    # 3. 低质量照片：模糊、过曝
    img5 = Image.new("RGB", (400, 300), (255, 255, 255))  # 全白（过曝）
    img5.save(TEST_DIR / "overexposed.jpg")
    image_paths.append(str(TEST_DIR / "overexposed.jpg"))

    img6 = Image.new("RGB", (400, 300), (5, 5, 5))  # 全黑（欠曝）
    img6.save(TEST_DIR / "underexposed.jpg")
    image_paths.append(str(TEST_DIR / "underexposed.jpg"))

    # 模糊照片（对高质量图片1做模糊处理）
    blur_img = img.filter(ImageFilter.GaussianBlur(radius=8))
    blur_img.save(TEST_DIR / "blurry.jpg")
    image_paths.append(str(TEST_DIR / "blurry.jpg"))

    logger.info(f"生成了 {len(image_paths)} 张测试图片到 {TEST_DIR}")
    return image_paths


def test_heuristic(image_paths: list):
    """测试启发式美学评分"""
    logger.info("\n=== 启发式美学评分测试 ===")

    from src.aesthetics.heuristic import batch_heuristic

    results = batch_heuristic(image_paths)

    logger.info(f"{'文件名':<25} {'评分':<8} {'评价':<10}")
    logger.info("-" * 45)
    for path, score in results:
        name = os.path.basename(path)
        if score >= 0.7:
            rating = "好"
        elif score >= 0.4:
            rating = "中"
        else:
            rating = "差"
        logger.info(f"{name:<25} {score:.4f}  {rating:<10}")

    return results


def test_nima(image_paths: list):
    """测试 NIMA 评分"""
    logger.info("\n=== NIMA 评分测试 ===")

    from src.aesthetics.nima import batch_predict

    try:
        results = batch_predict(image_paths)
        logger.info(f"{'文件名':<25} {'评分(1-10)':<12} {'评价':<10}")
        logger.info("-" * 47)
        for path, score in results:
            name = os.path.basename(path)
            if score >= 7:
                rating = "好"
            elif score >= 4:
                rating = "中"
            else:
                rating = "差"
            logger.info(f"{name:<25} {score:.2f}        {rating:<10}")
        return results
    except Exception as e:
        logger.warning(f"NIMA 评分失败（已降级到启发式规则）: {e}")
        return []


def main():
    """主测试流程"""
    logger.info("=" * 50)
    logger.info("PhotoTrim 美学评分模块测试")
    logger.info("=" * 50)

    # 生成测试图片
    image_paths = generate_test_images()

    # 测试启发式评分
    heuristic_results = test_heuristic(image_paths)

    # 测试 NIMA 评分
    nima_results = test_nima(image_paths)

    # 汇总
    logger.info("\n" + "=" * 50)
    logger.info("测试汇总")
    logger.info("=" * 50)
    logger.info(f"测试图片总数: {len(image_paths)}")

    # 启发式评分统计
    if heuristic_results:
        high = sum(1 for _, s in heuristic_results if s >= 0.7)
        mid = sum(1 for _, s in heuristic_results if 0.4 <= s < 0.7)
        low = sum(1 for _, s in heuristic_results if s < 0.4)
        logger.info(f"启发式评分分布: 好={high} 中={mid} 差={low}")

    # NIMA 评分统计
    if nima_results:
        high = sum(1 for _, s in nima_results if s >= 7)
        mid = sum(1 for _, s in nima_results if 4 <= s < 7)
        low = sum(1 for _, s in nima_results if s < 4)
        logger.info(f"NIMA 评分分布: 好={high} 中={mid} 差={low}")

    logger.info("\n✅ 测试完成！")


if __name__ == "__main__":
    main()