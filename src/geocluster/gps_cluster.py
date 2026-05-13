"""GPS 与时间聚类模块

解析照片的 EXIF GPS 信息和拍摄时间，进行地点和时间聚类。
"""

import os
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import logging
import math

logger = logging.getLogger(__name__)


def _dms_to_decimal(dms: tuple, ref: str) -> float:
    """将度分秒(DMS)格式转换为十进制度数

    Args:
        dms: (度, 分, 秒) 元组
        ref: 方向参考（N/S/E/W）

    Returns:
        float: 十进制度数
    """
    degrees, minutes, seconds = dms
    decimal = float(degrees) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_gps(image_path: str) -> Optional[Dict[str, float]]:
    """从图片 EXIF 中提取 GPS 信息

    Args:
        image_path: 图片路径

    Returns:
        Optional[Dict]: {"lat": float, "lon": float} 或 None
    """
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS

        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return None

        # 查找 GPSInfo 标签
        gps_info = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == "GPSInfo":
                for gps_tag_id in value:
                    gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag_name] = value[gps_tag_id]
                break

        if not gps_info:
            return None

        # 提取经纬度
        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = _dms_to_decimal(
                gps_info["GPSLatitude"],
                gps_info.get("GPSLatitudeRef", "N")
            )
            lon = _dms_to_decimal(
                gps_info["GPSLongitude"],
                gps_info.get("GPSLongitudeRef", "E")
            )
            return {"lat": lat, "lon": lon}

        return None

    except Exception as e:
        logger.debug(f"提取 GPS 失败 {image_path}: {e}")
        return None


def extract_timestamp(image_path: str) -> Optional[str]:
    """从图片 EXIF 中提取拍摄时间

    Args:
        image_path: 图片路径

    Returns:
        Optional[str]: ISO 格式时间字符串 "YYYY-MM-DD HH:MM:SS" 或 None
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return None

        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == "DateTimeOriginal":
                return str(value)

        # 尝试 DateTime
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == "DateTime":
                return str(value)

        return None

    except Exception as e:
        logger.debug(f"提取时间戳失败 {image_path}: {e}")
        return None


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间的 Haversine 距离（公里）

    Args:
        lat1, lon1: 第一个点的经纬度
        lat2, lon2: 第二个点的经纬度

    Returns:
        float: 距离（公里）
    """
    R = 6371.0  # 地球半径（公里）
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def cluster_by_location(
    image_paths: List[str],
    distance_km: float = 1.0
) -> Dict[str, List[str]]:
    """按地理位置聚类

    将距离在 distance_km 以内的照片归为同一地点。

    Args:
        image_paths: 图片路径列表
        distance_km: 聚类距离阈值（公里）

    Returns:
        Dict[str, List[str]]: {地点名称: [图片路径列表]}
    """
    # 提取所有照片的 GPS
    gps_data = {}
    for path in image_paths:
        gps = extract_gps(path)
        if gps:
            gps_data[path] = gps

    if not gps_data:
        logger.warning("没有照片包含 GPS 信息")
        return {"无GPS信息": image_paths}

    # 简单聚类：按距离分组
    clusters = []
    assigned = set()

    for path1, gps1 in gps_data.items():
        if path1 in assigned:
            continue

        cluster = [path1]
        assigned.add(path1)

        for path2, gps2 in gps_data.items():
            if path2 in assigned:
                continue

            dist = _haversine_distance(
                gps1["lat"], gps1["lon"],
                gps2["lat"], gps2["lon"]
            )
            if dist <= distance_km:
                cluster.append(path2)
                assigned.add(path2)

        clusters.append(cluster)

    # 对没有 GPS 的照片单独分组
    no_gps = [p for p in image_paths if p not in gps_data]
    if no_gps:
        clusters.append(no_gps)

    # 命名聚类
    result = {}
    for i, cluster in enumerate(clusters):
        if cluster and cluster[0] in gps_data:
            gps = gps_data[cluster[0]]
            name = f"地点{i+1}({gps['lat']:.2f}, {gps['lon']:.2f})"
        else:
            name = f"无GPS信息" if i == len(clusters) - 1 else f"地点{i+1}"
        result[name] = cluster

    logger.info(f"地点聚类完成：{len(clusters)} 个地点")
    return result


def _parse_time(time_str: str) -> Optional[datetime]:
    """解析时间字符串"""
    formats = [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def cluster_by_time(
    image_paths: List[str],
    hour_threshold: int = 2
) -> Dict[str, List[str]]:
    """按拍摄时间聚类

    将拍摄时间在 hour_threshold 小时以内的照片归为同一时间段。

    Args:
        image_paths: 图片路径列表
        hour_threshold: 时间聚类阈值（小时）

    Returns:
        Dict[str, List[str]]: {时间段: [图片路径列表]}
    """
    # 提取所有照片的时间
    time_data = []
    no_time = []

    for path in image_paths:
        ts = extract_timestamp(path)
        if ts:
            dt = _parse_time(ts)
            if dt:
                time_data.append((path, dt))
            else:
                no_time.append(path)
        else:
            no_time.append(path)

    if not time_data:
        return {"无时间信息": image_paths}

    # 按时间排序
    time_data.sort(key=lambda x: x[1])

    # 聚类
    clusters = []
    current_cluster = [time_data[0]]
    current_start = time_data[0][1]

    for path, dt in time_data[1:]:
        hours_diff = (dt - current_start).total_seconds() / 3600
        if hours_diff <= hour_threshold:
            current_cluster.append((path, dt))
        else:
            clusters.append(current_cluster)
            current_cluster = [(path, dt)]
            current_start = dt

    if current_cluster:
        clusters.append(current_cluster)

    # 命名聚类
    result = {}
    for i, cluster in enumerate(clusters):
        start_time = cluster[0][1].strftime("%m-%d %H:%M")
        end_time = cluster[-1][1].strftime("%H:%M")
        name = f"时段{i+1}({start_time}-{end_time})"
        result[name] = [p for p, _ in cluster]

    if no_time:
        result["无时间信息"] = no_time

    logger.info(f"时间聚类完成：{len(clusters)} 个时段")
    return result


def hybrid_cluster(image_paths: List[str]) -> Dict[str, List[str]]:
    """混合聚类：先按地点，再按时间

    优先使用 GPS 信息聚类，无 GPS 的照片按时间聚类。

    Args:
        image_paths: 图片路径列表

    Returns:
        Dict[str, List[str]]: {聚类名称: [图片路径列表]}
    """
    # 先提取 GPS
    has_gps = []
    no_gps = []

    for path in image_paths:
        gps = extract_gps(path)
        if gps:
            has_gps.append(path)
        else:
            no_gps.append(path)

    result = {}

    # 有 GPS 的按地点聚类
    if has_gps:
        location_clusters = cluster_by_location(has_gps)
        result.update(location_clusters)

    # 无 GPS 的按时间聚类
    if no_gps:
        time_clusters = cluster_by_time(no_gps)
        result.update(time_clusters)

    if not result:
        # 所有照片都无信息，按文件名排序
        result["全部照片"] = sorted(image_paths)

    return result