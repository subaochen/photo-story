"""场景分类模块测试脚本

生成不同场景的测试图片，验证 CLIP 零样本分类效果。
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image, ImageDraw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TEST_DIR = Path(__file__).parent.parent.parent / "data" / "test_scene"


def generate_test_images() -> list:
    """生成不同场景的测试图片"""
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    image_paths = []

    # 风景：蓝天下绿色地面
    img1 = Image.new("RGB", (400, 300), (100, 149, 237))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([0, 180, 400, 300], fill=(34, 139, 34))
    draw1.ellipse([320, 30, 380, 90], fill=(255, 255, 100))
    img1.save(TEST_DIR / "landscape.jpg")
    image_paths.append(str(TEST_DIR / "landscape.jpg"))

    # 室内：灰色背景
    img2 = Image.new("RGB", (400, 300), (180, 170, 160))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([50, 30, 350, 270], fill=(200, 190, 180))
    draw2.rectangle([100, 50, 300, 250], fill=(160, 140, 120))
    img2.save(TEST_DIR / "indoor.jpg")
    image_paths.append(str(TEST_DIR / "indoor.jpg"))

    # 美食：暖色调
    img3 = Image.new("RGB", (400, 300), (255, 200, 150))
    draw3 = ImageDraw.Draw(img3)
    draw3.ellipse([100, 80, 300, 250], fill=(255, 180, 100))
    draw3.ellipse([150, 120, 250, 220], fill=(255, 100, 50))
    img3.save(TEST_DIR / "food.jpg")
    image_paths.append(str(TEST_DIR / "food.jpg"))

    logger.info(f"生成了 {len(image_paths)} 张测试图片到 {TEST_DIR}")
    return image_paths


def test_classify(image_paths: list):
    """测试场景分类"""
    logger.info("\n=== 场景分类测试 ===")

    from src.scene.clip_classifier import classify_scene, get_dominant_scene

    for path in image_paths:
        name = os.path.basename(path)
        try:
            top_scene = get_dominant_scene(path)
            scores = classify_scene(path)
            logger.info(f"  {name:<20} → 主要场景: {top_scene}")
            # 显示前3个场景
            top3 = list(scores.items())[:3]
            for scene, prob in top3:
                logger.info(f"    {scene}: {prob:.3f}")
        except Exception as e:
            logger.warning(f"  {name:<20} 分类失败: {e}")


def main():
    """主测试流程"""
    logger.info("=" * 50)
    logger.info("PhotoTrim 场景分类模块测试")
    logger.info("=" * 50)

    image_paths = generate_test_images()
    test_classify(image_paths)

    logger.info("\n✅ 测试完成！")


if __name__ == "__main__":
    main()