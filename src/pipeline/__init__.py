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


__all__ = [
    "run_pipeline",
    "run_dedup_only",
    "run_aesthetic_rank",
]