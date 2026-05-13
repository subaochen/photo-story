"""地点聚类模块测试脚本"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TEST_DIR = Path(__file__).parent.parent.parent / "data" / "test_geocluster"


def test_extract_gps():
    """测试 GPS 提取"""
    logger.info("\n=== GPS 提取测试 ===")

    from src.geocluster.gps_cluster import extract_gps, extract_timestamp

    # 测试无 EXIF 的图片
    test_img = TEST_DIR / "test.jpg"
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    from PIL import Image
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(test_img)

    gps = extract_gps(str(test_img))
    ts = extract_timestamp(str(test_img))
    logger.info(f"  无EXIF图片 - GPS: {gps}, 时间: {ts}")

    if gps is None and ts is None:
        logger.info("  ✅ 无EXIF时返回None（预期行为）")
    else:
        logger.info("  ⚠️ 结果与预期不一致")


def test_cluster():
    """测试聚类算法"""
    logger.info("\n=== 聚类算法测试 ===")

    from src.geocluster.gps_cluster import (
        _haversine_distance, cluster_by_location, cluster_by_time
    )

    # 测试 Haversine 距离
    dist = _haversine_distance(39.9042, 116.4074, 31.2304, 121.4737)
    logger.info(f"  北京到上海距离: {dist:.0f} km")
    assert dist > 1000, "北京到上海应大于1000km"

    # 测试相同点
    dist_same = _haversine_distance(39.9042, 116.4074, 39.9042, 116.4074)
    logger.info(f"  相同点距离: {dist_same:.0f} km")
    assert dist_same == 0, "相同点距离应为0"

    logger.info("  ✅ 距离计算正确")


def test_hybrid():
    """测试混合聚类"""
    logger.info("\n=== 混合聚类测试 ===")

    from src.geocluster.gps_cluster import hybrid_cluster

    # 用测试图片
    test_dir = Path(__file__).parent.parent.parent / "data" / "test_input"
    if test_dir.exists():
        images = sorted([str(p) for p in test_dir.glob("*.jpg")])
        if images:
            result = hybrid_cluster(images)
            logger.info(f"  聚类结果: {len(result)} 个分组")
            for name, paths in result.items():
                logger.info(f"    {name}: {len(paths)} 张")


def main():
    """主测试流程"""
    logger.info("=" * 50)
    logger.info("PhotoTrim 地点聚类模块测试")
    logger.info("=" * 50)

    test_extract_gps()
    test_cluster()
    test_hybrid()

    logger.info("\n✅ 测试完成！")


if __name__ == "__main__":
    main()