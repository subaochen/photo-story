"""Pipeline 编排模块 - 延迟导入"""

from typing import List, Tuple, Dict


def run_pipeline(input_dir: str, output_dir: str, top_k: int = 100):
    from .orchestrator import run_pipeline
    return run_pipeline(input_dir, output_dir, top_k)


def run_dedup_only(image_paths: List[str]) -> List[str]:
    from .orchestrator import run_dedup_only
    return run_dedup_only(image_paths)


def run_aesthetic_rank(image_paths: List[str], top_k: int = 100) -> List[Tuple[str, float]]:
    from .orchestrator import run_aesthetic_rank
    return run_aesthetic_rank(image_paths, top_k)


def run_pipeline_verbose(
    input_dir: str,
    output_dir: str,
    top_k: int = 100,
    dhash_threshold: int = 5,
    clip_threshold: float = 0.92,
) -> dict:
    from .orchestrator import run_pipeline_verbose
    return run_pipeline_verbose(input_dir, output_dir, top_k, dhash_threshold, clip_threshold)


__all__ = [
    "run_pipeline",
    "run_dedup_only",
    "run_aesthetic_rank",
    "run_pipeline_verbose",
]