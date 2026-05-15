"""地点聚类模块 - 延迟导入"""

from typing import List, Tuple, Dict


def extract_gps(image_path: str) -> dict:
    from .gps_cluster import extract_gps
    return extract_gps(image_path)


def extract_timestamp(image_path: str) -> str:
    from .gps_cluster import extract_timestamp
    return extract_timestamp(image_path)


def cluster_by_location(image_paths: List[str], distance_km: float = 1.0) -> Dict[str, List[str]]:
    from .gps_cluster import cluster_by_location
    return cluster_by_location(image_paths, distance_km)


def cluster_by_time(image_paths: List[str], hour_threshold: int = 2) -> Dict[str, List[str]]:
    from .gps_cluster import cluster_by_time
    return cluster_by_time(image_paths, hour_threshold)


def hybrid_cluster(image_paths: List[str]) -> Dict[str, List[str]]:
    from .gps_cluster import hybrid_cluster
    return hybrid_cluster(image_paths)


def cluster_images(image_paths: List[str]) -> dict:
    from .gps_cluster import cluster_images
    return cluster_images(image_paths)


__all__ = [
    "extract_gps",
    "extract_timestamp",
    "cluster_by_location",
    "cluster_by_time",
    "hybrid_cluster",
    "cluster_images",
]