"""Pipeline 编排模块

将相似度去重、美学评分、人脸识别、场景分类、地点聚类
串联成完整的端到端处理流程。
"""

import os
import shutil
import logging
from typing import List, Tuple, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def collect_images(
    input_dir: str,
    extensions: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".heic")
) -> List[str]:
    """收集目录下的所有图片

    Args:
        input_dir: 输入目录
        extensions: 支持的图片格式

    Returns:
        List[str]: 图片路径列表
    """
    images = []
    input_path = Path(input_dir)

    for ext in extensions:
        images.extend([str(p) for p in input_path.rglob(f"*{ext}")])
        images.extend([str(p) for p in input_path.rglob(f"*{ext.upper()}")])

    images.sort()
    logger.info(f"收集到 {len(images)} 张图片")
    return images


def copy_results(
    kept_images: List[str],
    output_dir: str,
    prefix: str = "selected"
) -> None:
    """将精选结果复制到输出目录

    Args:
        kept_images: 保留的图片路径列表
        output_dir: 输出目录
        prefix: 文件名前缀
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for i, src_path in enumerate(kept_images, 1):
        ext = Path(src_path).suffix
        dst_name = f"{prefix}_{i:04d}{ext}"
        dst_path = output_path / dst_name
        try:
            shutil.copy2(src_path, dst_path)
        except Exception as e:
            logger.warning(f"复制失败 {src_path}: {e}")

    logger.info(f"已复制 {len(kept_images)} 张精选照片到 {output_dir}")


def run_dedup_only(image_paths: List[str]) -> List[str]:
    """仅执行相似度去重

    使用 dHash + CLIP 混合策略。

    Args:
        image_paths: 输入图片路径列表

    Returns:
        List[str]: 去重后的图片路径列表
    """
    from src.dedup.clip_sim import hybrid_dedup

    logger.info(f"开始去重: {len(image_paths)} 张")
    kept = hybrid_dedup(image_paths)
    logger.info(f"去重完成: {len(image_paths)} → {len(kept)}")
    return kept


def run_aesthetic_rank(
    image_paths: List[str],
    top_k: int = 100
) -> List[Tuple[str, float]]:
    """按美学评分排序

    Args:
        image_paths: 输入图片路径列表
        top_k: 保留数量

    Returns:
        List[Tuple[str, float]]: 评分最高的 top_k 张
    """
    from src.aesthetics.nima import rank_by_aesthetics

    logger.info(f"开始美学评分: {len(image_paths)} 张")
    results = rank_by_aesthetics(image_paths, top_k=top_k)
    logger.info(f"美学评分完成: 选出前 {len(results)} 张")
    return results


def detect_faces_in_collection(
    image_paths: List[str]
) -> dict:
    """批量检测人脸

    Args:
        image_paths: 图片路径列表

    Returns:
        dict: {image_path: [face1, face2, ...]}
    """
    from src.faces.detector import batch_detect_faces

    logger.info(f"开始人脸检测: {len(image_paths)} 张")
    results = batch_detect_faces(image_paths)
    total_faces = sum(len(faces) for faces in results.values())
    logger.info(f"人脸检测完成: 共 {total_faces} 张人脸")
    return results


def classify_scenes(image_paths: List[str]) -> dict:
    """批量场景分类

    Args:
        image_paths: 图片路径列表

    Returns:
        dict: {image_path: {category: probability}}
    """
    from src.scene.clip_classifier import batch_classify

    logger.info(f"开始场景分类: {len(image_paths)} 张")
    results = batch_classify(image_paths)
    logger.info(f"场景分类完成")
    # 确保返回 dict 类型（batch_classify 可能返回 list）
    return results if isinstance(results, dict) else {}


def run_pipeline(
    input_dir: str,
    output_dir: str,
    top_k: int = 100,
    dhash_threshold: int = 5,
    clip_threshold: float = 0.92,
) -> dict:
    """端到端处理流程

    完整流程：
    1. 收集图片
    2. 相似度去重（dHash + CLIP 混合策略）
    3. 美学评分排序
    4. 复制结果到输出目录
    5. 生成统计报告

    Args:
        input_dir: 输入目录（原始照片）
        output_dir: 输出目录（精选照片）
        top_k: 最终保留的精选照片数量
        dhash_threshold: dHash 海明距离阈值
        clip_threshold: CLIP 余弦相似度阈值

    Returns:
        dict: 处理统计信息
    """
    start_time = datetime.now()
    logger.info(f"\n{'='*50}")
    logger.info(f"PhotoTrim Pipeline 启动")
    logger.info(f"{'='*50}")
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"目标数量: {top_k} 张")

    # Stage 1: 收集图片
    logger.info(f"\n--- Stage 1: 收集图片 ---")
    all_images = collect_images(input_dir)
    stage1_count = len(all_images)

    # Stage 2: 相似度去重
    logger.info(f"\n--- Stage 2: 相似度去重 ---")
    deduped = run_dedup_only(all_images)
    stage2_count = len(deduped)

    # Stage 3: 美学评分排序
    logger.info(f"\n--- Stage 3: 美学评分 ---")
    ranked = run_aesthetic_rank(deduped, top_k=top_k)
    final_images = [path for path, _ in ranked]
    stage3_count = len(final_images)

    # Stage 4: 复制结果
    logger.info(f"\n--- Stage 4: 输出结果 ---")
    copy_results(final_images, output_dir)

    # Stage 5: 统计报告
    elapsed = (datetime.now() - start_time).total_seconds()
    stats = {
        "input_count": stage1_count,
        "after_dedup": stage2_count,
        "final_count": stage3_count,
        "dedup_removed": stage1_count - stage2_count,
        "aesthetic_removed": stage2_count - stage3_count,
        "total_removed": stage1_count - stage3_count,
        "elapsed_seconds": elapsed,
        "output_dir": output_dir,
        "timestamp": start_time.isoformat(),
    }

    logger.info(f"\n{'='*50}")
    logger.info(f"Pipeline 完成!")
    logger.info(f"{'='*50}")
    logger.info(f"输入: {stats['input_count']} 张")
    logger.info(f"去重后: {stats['after_dedup']} 张 (-{stats['dedup_removed']})")
    logger.info(f"精选: {stats['final_count']} 张 (-{stats['aesthetic_removed']})")
    logger.info(f"总计移除: {stats['total_removed']} 张")
    logger.info(f"耗时: {elapsed:.1f} 秒")
    logger.info(f"输出: {output_dir}")

    return stats

def run_pipeline_verbose(
    input_dir: str,
    output_dir: str,
    top_k: int = 100,
    dhash_threshold: int = 5,
    clip_threshold: float = 0.92,
) -> dict:
    """端到端处理流程（verbose 版本）

    返回完整的分析结果，包含：
    - 去重分组信息
    - 美学评分详情
    - 人脸检测结果
    - 场景分类结果
    - 地点/时间聚类
    - 完整统计信息

    Args:
        input_dir: 输入目录（原始照片）
        output_dir: 输出目录（精选照片）
        top_k: 最终保留的精选照片数量
        dhash_threshold: dHash 海明距离阈值
        clip_threshold: CLIP 余弦相似度阈值

    Returns:
        dict: 包含完整分析结果的字典
    """
    start_time = datetime.now()
    logger.info(f"\n{'='*50}")
    logger.info(f"PhotoTrim Pipeline (Verbose) 启动")
    logger.info(f"{'='*50}")
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"目标数量: {top_k} 张")

    # Stage 1: 收集图片
    logger.info(f"\n--- Stage 1: 收集图片 ---")
    all_images = collect_images(input_dir)
    stage1_count = len(all_images)

    # Stage 2: 相似度去重（verbose）
    logger.info(f"\n--- Stage 2: 相似度去重（verbose） ---")
    dedup_result = run_dedup_only_verbose(all_images, dhash_threshold, clip_threshold)
    stage2_count = dedup_result["summary"]["final_count"]

    # Stage 3: 美学评分（verbose）
    logger.info(f"\n--- Stage 3: 美学评分（verbose） ---")
    aesthetic_result = run_aesthetic_rank_verbose(
        dedup_result["final_results"],
        top_k=top_k
    )
    final_images = [item["path"] for item in aesthetic_result["ranking"]]
    stage3_count = len(final_images)

    # Stage 4: 人脸检测
    logger.info(f"\n--- Stage 4: 人脸检测 ---")
    face_result = detect_faces_in_collection(final_images)

    # Stage 5: 场景分类
    logger.info(f"\n--- Stage 5: 场景分类 ---")
    scene_result = classify_scenes(final_images)

    # Stage 6: 地点/时间聚类
    logger.info(f"\n--- Stage 6: 地点/时间聚类 ---")
    cluster_result = cluster_by_location_and_time(final_images)

    # Stage 7: 复制结果
    logger.info(f"\n--- Stage 7: 输出结果 ---")
    copy_results(final_images, output_dir)

    # Stage 8: 统计报告
    elapsed = (datetime.now() - start_time).total_seconds()
    stats = {
        "input_count": stage1_count,
        "after_dedup": stage2_count,
        "final_count": stage3_count,
        "dedup_removed": stage1_count - stage2_count,
        "aesthetic_removed": stage2_count - stage3_count,
        "total_removed": stage1_count - stage3_count,
        "elapsed_seconds": elapsed,
        "output_dir": output_dir,
        "timestamp": start_time.isoformat(),
    }

    logger.info(f"\n{'='*50}")
    logger.info(f"Pipeline (Verbose) 完成!")
    logger.info(f"{'='*50}")
    logger.info(f"输入: {stats['input_count']} 张")
    logger.info(f"去重后: {stats['after_dedup']} 张 (-{stats['dedup_removed']})")
    logger.info(f"精选: {stats['final_count']} 张 (-{stats['aesthetic_removed']})")
    logger.info(f"总计移除: {stats['total_removed']} 张")
    logger.info(f"耗时: {elapsed:.1f} 秒")
    logger.info(f"输出: {output_dir}")

    return {
        "pipeline_stats": stats,
        "dedup": dedup_result,
        "aesthetics": aesthetic_result,
        "faces": face_result,
        "scenes": scene_result,
        "clusters": cluster_result,
    }


def run_dedup_only_verbose(
    image_paths: List[str],
    dhash_threshold: int = 5,
    clip_threshold: float = 0.92,
) -> dict:
    """仅执行相似度去重（verbose 版本）

    Args:
        image_paths: 输入图片路径列表
        dhash_threshold: dHash 海明距离阈值
        clip_threshold: CLIP 余弦相似度阈值

    Returns:
        dict: 去重结果（包含详细分组信息）
    """
    from src.dedup.clip_sim import hybrid_dedup_verbose

    logger.info(f"开始去重（verbose）: {len(image_paths)} 张")
    return hybrid_dedup_verbose(
        image_paths,
        dhash_threshold=dhash_threshold,
        clip_threshold=clip_threshold
    )


def run_aesthetic_rank_verbose(
    image_path_results: List[dict],
    top_k: int = 100,
) -> dict:
    """按美学评分排序（verbose 版本）

    Args:
        image_path_results: 包含 path 和 status 的结果列表
        top_k: 保留数量

    Returns:
        dict: 美学评分结果（包含详细排名信息）
    """
    from src.aesthetics.nima import rank_with_details

    # 提取为保留的照片路径
    kept_paths = [item["path"] for item in image_path_results if item.get("status") == "kept"]

    logger.info(f"开始美学评分（verbose）: {len(kept_paths)} 张")
    return rank_with_details(kept_paths, top_k=top_k)


def cluster_by_location_and_time(
    image_paths: List[str]
) -> dict:
    """按地点和时间聚类

    Args:
        image_paths: 图片路径列表

    Returns:
        dict: {clusters: [...], summary: {...}}
    """
    from src.geocluster import cluster_images

    logger.info(f"开始地点/时间聚类: {len(image_paths)} 张")
    results = cluster_images(image_paths)
    logger.info(f"地点/时间聚类完成: {results.get('summary', {}).get('cluster_count', 0)} 个簇")
    return results
