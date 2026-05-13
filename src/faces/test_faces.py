"""人脸识别模块测试脚本

生成包含人脸的测试图片，验证人脸检测功能。
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image, ImageDraw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TEST_DIR = Path(__file__).parent.parent.parent / "data" / "test_faces"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "test_output"


def generate_test_images() -> list:
    """生成包含人脸模拟的测试图片

    由于无法生成真实人脸，使用简单图案模拟人脸检测测试。

    Returns:
        list: 生成的图片路径列表
    """
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = []

    # 1. 单人照片：椭圆形+特征点模拟人脸
    img1 = Image.new("RGB", (300, 400), (200, 200, 200))
    draw1 = ImageDraw.Draw(img1)
    draw1.ellipse([100, 50, 200, 200], fill=(255, 200, 150))  # 人脸区域
    draw1.ellipse([125, 100, 145, 125], fill=(0, 0, 0))  # 左眼
    draw1.ellipse([155, 100, 175, 125], fill=(0, 0, 0))  # 右眼
    draw1.ellipse([140, 135, 160, 160], fill=(0, 0, 0))  # 嘴巴
    img1.save(TEST_DIR / "single_face.jpg")
    image_paths.append(str(TEST_DIR / "single_face.jpg"))

    # 2. 多人照片：两个椭圆形模拟两个人脸
    img2 = Image.new("RGB", (500, 400), (180, 180, 200))
    draw2 = ImageDraw.Draw(img2)
    # 第一个人脸
    draw2.ellipse([50, 50, 180, 200], fill=(255, 180, 140))
    draw2.ellipse([80, 100, 100, 120], fill=(0, 0, 0))
    draw2.ellipse([120, 100, 140, 120], fill=(0, 0, 0))
    draw2.ellipse([100, 140, 130, 160], fill=(0, 0, 0))
    # 第二个人脸
    draw2.ellipse([280, 70, 430, 230], fill=(220, 160, 120))
    draw2.ellipse([310, 120, 335, 145], fill=(0, 0, 0))
    draw2.ellipse([360, 120, 385, 145], fill=(0, 0, 0))
    draw2.ellipse([340, 165, 370, 190], fill=(0, 0, 0))
    img2.save(TEST_DIR / "two_faces.jpg")
    image_paths.append(str(TEST_DIR / "two_faces.jpg"))

    # 3. 无人脸照片：纯风景
    img3 = Image.new("RGB", (400, 300), (100, 149, 237))  # 蓝色天空
    draw3 = ImageDraw.Draw(img3)
    draw3.rectangle([0, 200, 400, 300], fill=(34, 139, 34))  # 绿色地面
    draw3.ellipse([300, 30, 370, 100], fill=(255, 255, 100))  # 太阳
    img3.save(TEST_DIR / "no_face.jpg")
    image_paths.append(str(TEST_DIR / "no_face.jpg"))

    logger.info(f"生成了 {len(image_paths)} 张测试图片到 {TEST_DIR}")
    return image_paths


def test_detect_faces(image_paths: list):
    """测试人脸检测"""
    logger.info("\n=== 人脸检测测试 ===")

    from src.faces.detector import detect_faces, batch_detect_faces, count_faces

    for path in image_paths:
        name = os.path.basename(path)
        try:
            faces = detect_faces(path)
            logger.info(f"  {name:<20} 检测到 {len(faces)} 张人脸")
            for i, face in enumerate(faces):
                logger.info(f"    人脸 {i+1}: 置信度={face['confidence']:.3f}")
        except Exception as e:
            logger.warning(f"  {name:<20} 检测失败: {e}")

    # 批量检测
    results = batch_detect_faces(image_paths)
    total = sum(len(faces) for faces in results.values())
    logger.info(f"批量检测完成，共 {total} 张人脸")


def main():
    """主测试流程"""
    logger.info("=" * 50)
    logger.info("PhotoTrim 人脸识别模块测试")
    logger.info("=" * 50)

    # 生成测试图片
    image_paths = generate_test_images()

    # 测试人脸检测
    test_detect_faces(image_paths)

    logger.info("\n✅ 测试完成！")


if __name__ == "__main__":
    main()