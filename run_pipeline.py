#!/usr/bin/env python3
"""PhotoTrim Pipeline 入口脚本

用法:
    python run_pipeline.py --input <输入目录> --output <输出目录> [--top-k 100]
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(description="PhotoTrim - 照片自动整理")
    parser.add_argument("--input", "-i", required=True, help="输入目录（原始照片）")
    parser.add_argument("--output", "-o", required=True, help="输出目录（精选照片）")
    parser.add_argument("--top-k", type=int, default=100, help="保留数量（默认 100）")
    parser.add_argument("--dhash-threshold", type=int, default=5, help="dHash 阈值（默认 5）")
    parser.add_argument("--clip-threshold", type=float, default=0.92, help="CLIP 阈值（默认 0.92）")
    parser.add_argument("--dedup-only", action="store_true", help="仅执行去重")
    parser.add_argument("--rank-only", action="store_true", help="仅执行评分排序")

    args = parser.parse_args()

    from src.pipeline.orchestrator import run_pipeline, run_dedup_only, run_aesthetic_rank, collect_images

    if args.dedup_only:
        images = collect_images(args.input)
        kept = run_dedup_only(images)
        print(f"\n去重结果: {len(images)} → {len(kept)}")
    elif args.rank_only:
        images = collect_images(args.input)
        ranked = run_aesthetic_rank(images, top_k=args.top_k)
        print(f"\n评分排序结果: 前 {len(ranked)} 张")
        for path, score in ranked[:10]:
            print(f"  {Path(path).name}: {score:.2f}")
    else:
        stats = run_pipeline(
            input_dir=args.input,
            output_dir=args.output,
            top_k=args.top_k,
            dhash_threshold=args.dhash_threshold,
            clip_threshold=args.clip_threshold,
        )
        print(f"\n处理完成: {stats['input_count']} → {stats['final_count']} 张")
        print(f"耗时: {stats['elapsed_seconds']:.1f} 秒")


if __name__ == "__main__":
    main()