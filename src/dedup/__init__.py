# 延迟导入，避免因缺少 torch/scikit-learn 等依赖导致导入失败

def compute_dhash(image_path):
    from .dhash import compute_dhash as _func
    return _func(image_path)

def hamming_distance(hash1, hash2):
    from .dhash import hamming_distance as _func
    return _func(hash1, hash2)

def dedup_by_dhash(image_paths, threshold=5):
    from .dhash import dedup_by_dhash as _func
    return _func(image_paths, threshold)

def compute_clip_embeddings(image_paths):
    from .clip_sim import compute_clip_embeddings as _func
    return _func(image_paths)

def dedup_by_clip(image_paths, threshold=0.92, batch_size=32):
    from .clip_sim import dedup_by_clip as _func
    return _func(image_paths, threshold, batch_size)

def hybrid_dedup(image_paths, dhash_threshold=5, clip_threshold=0.92, batch_size=32):
    from .clip_sim import hybrid_dedup as _func
    return _func(image_paths, dhash_threshold, clip_threshold, batch_size)

__all__ = [
    "compute_dhash",
    "hamming_distance",
    "dedup_by_dhash",
    "compute_clip_embeddings",
    "dedup_by_clip",
    "hybrid_dedup",
]
