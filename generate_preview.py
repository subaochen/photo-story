#!/usr/bin/env python3
"""生成照片筛选可视化预览页面

展示：
1. 保留的照片（缩略图 + 美学评分 + 保留理由）
2. 被剔除的照片（缩略图 + 剔除原因 + 相似保留照片对比）
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import cv2
import numpy as np
from PIL import Image


def compute_dhash(image_path: str) -> str:
    """Compute 64-bit dHash"""
    img = cv2.imread(image_path)
    if img is None:
        return ""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (9, 8))
    bits = []
    for row in resized:
        for i in range(8):
            bits.append('1' if row[i + 1] > row[i] else '0')
    return ''.join(bits)


def hamming_distance(hash1: str, hash2: str) -> int:
    if len(hash1) != len(hash2):
        return 65
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def compute_clip_similarity(image_path1: str, image_path2: str) -> float:
    """Compute CLIP cosine similarity between two images"""
    import torch
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
    
    try:
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        model.eval()
        
        img1 = Image.open(image_path1).convert("RGB")
        img2 = Image.open(image_path2).convert("RGB")
        
        inputs = processor(images=[img1, img2], return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
        
        # Cosine similarity
        sim = torch.cosine_similarity(features[0:1], features[1:2]).item()
        return sim
    except Exception as e:
        print(f"CLIP similarity error: {e}")
        return 0.0


def aesthetic_score_heuristic(image_path: str) -> float:
    """Simple heuristic aesthetic score (0-1)"""
    img = cv2.imread(image_path)
    if img is None:
        return 0.0
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Sharpness (Laplacian variance)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = laplacian.var()
    sharpness_score = 1.0 / (1.0 + np.exp(-0.05 * (sharpness - 50)))
    
    # Brightness (avoid over/under exposure)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()
    over_exposed = hist[230:].sum()
    under_exposed = hist[:25].sum()
    brightness_score = 1.0 - (over_exposed + under_exposed)
    
    # Color saturation
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].mean() / 255.0
    if saturation < 0.1:
        color_score = 0.1
    elif saturation < 0.3:
        color_score = saturation * 2.0
    elif saturation < 0.7:
        color_score = 1.0
    else:
        color_score = max(0.5, 1.0 - (saturation - 0.7) * 1.5)
    
    # Combined score
    total = sharpness_score * 0.4 + brightness_score * 0.3 + color_score * 0.3
    return float(total)


def generate_preview(
    input_dir: str,
    output_dir: str,
    preview_html: str = "preview.html",
    top_k: int = 100,
    dhash_threshold: int = 5,
    clip_threshold: float = 0.92,
):
    """Generate HTML preview of photo selection results"""
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Collect all images
    extensions = {'.jpg', '.jpeg', '.png', '.heic'}
    all_images = sorted([
        str(p) for p in input_path.rglob('*')
        if p.suffix.lower() in extensions
    ])
    
    print(f"Found {len(all_images)} images in {input_dir}")
    
    # Step 1: Compute dHash for all images
    print("Computing dHash...")
    image_hashes = {}
    for img_path in all_images:
        h = compute_dhash(img_path)
        if h:
            image_hashes[img_path] = h
    
    # Step 2: dHash deduplication
    print("Running dHash dedup...")
    kept_after_dhash = []
    removed_by_dhash = {}  # {removed_path: kept_path}
    
    for img_path in all_images:
        h = image_hashes.get(img_path, "")
        if not h:
            continue
        
        is_duplicate = False
        duplicate_of = None
        for kept_path in kept_after_dhash:
            dist = hamming_distance(h, image_hashes[kept_path])
            if dist < dhash_threshold:
                is_duplicate = True
                duplicate_of = kept_path
                break
        
        if is_duplicate:
            removed_by_dhash[img_path] = {
                "reason": f"dHash 去重（与 {Path(duplicate_of).name} 海明距离={hamming_distance(h, image_hashes[duplicate_of])} < {dhash_threshold}）",
                "similar_to": duplicate_of,
            }
        else:
            kept_after_dhash.append(img_path)
    
    print(f"dHash: {len(all_images)} → {len(kept_after_dhash)} (removed {len(removed_by_dhash)})")
    
    # Step 3: Compute aesthetic scores for kept images
    print("Computing aesthetic scores...")
    scores = {}
    for img_path in kept_after_dhash:
        scores[img_path] = aesthetic_score_heuristic(img_path)
    
    # Sort by score
    ranked = sorted(kept_after_dhash, key=lambda p: scores[p], reverse=True)
    final_kept = ranked[:top_k]
    removed_by_score = ranked[top_k:]
    
    print(f"Aesthetic ranking: {len(kept_after_dhash)} → {len(final_kept)} (removed {len(removed_by_score)})")
    
    # Step 4: Copy final results
    for i, img_path in enumerate(final_kept, 1):
        ext = Path(img_path).suffix
        dst = output_path / f"selected_{i:04d}{ext}"
        shutil.copy2(img_path, dst)
    
    # Step 5: Generate HTML preview
    print("Generating HTML preview...")
    
    # Create thumbs directory
    thumbs_dir = output_path / "thumbs"
    thumbs_dir.mkdir(exist_ok=True)
    
    # Generate thumbnails
    def make_thumb(src_path: str, dst_path: str, size: int = 200):
        try:
            img = Image.open(src_path)
            img.thumbnail((size, size))
            img.save(dst_path)
            return True
        except:
            return False
    
    thumb_map = {}  # {original_path: thumb_relative_path}
    
    for img_path in all_images:
        thumb_name = Path(img_path).stem + "_thumb.jpg"
        thumb_path = thumbs_dir / thumb_name
        if make_thumb(img_path, str(thumb_path)):
            thumb_map[img_path] = f"thumbs/{thumb_name}"
    
    # Build HTML
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>照片筛选预览 - PhotoTrim</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 28px; color: #333; }
        .stats { display: flex; justify-content: center; gap: 30px; margin: 20px 0; }
        .stat-card { background: white; padding: 15px 30px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .stat-card .number { font-size: 32px; font-weight: bold; }
        .stat-card .label { font-size: 14px; color: #666; }
        .stat-kept .number { color: #4CAF50; }
        .stat-removed .number { color: #f44336; }
        .section { margin-bottom: 40px; }
        .section-title { font-size: 22px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #ddd; }
        .photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }
        .photo-card { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .photo-card:hover { transform: translateY(-3px); }
        .photo-card img { width: 100%; height: 180px; object-fit: cover; }
        .photo-info { padding: 12px; }
        .photo-name { font-size: 13px; font-weight: 500; color: #333; margin-bottom: 5px; word-break: break-all; }
        .photo-score { font-size: 12px; color: #666; }
        .score-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
        .score-high { background: #e8f5e9; color: #2e7d32; }
        .score-mid { background: #fff3e0; color: #e65100; }
        .score-low { background: #ffebee; color: #c62828; }
        .reason { font-size: 11px; color: #888; margin-top: 5px; }
        .removed-section { opacity: 0.85; }
        .comparison { display: flex; gap: 10px; align-items: flex-start; margin: 10px 0; padding: 10px; background: #fafafa; border-radius: 8px; }
        .comparison img { width: 100px; height: 100px; object-fit: cover; border-radius: 5px; }
        .comparison-info { flex: 1; }
        .vs { font-size: 18px; font-weight: bold; color: #999; }
        .filter { display: flex; gap: 10px; margin-bottom: 20px; justify-content: center; }
        .filter button { padding: 8px 20px; border: 1px solid #ddd; background: white; border-radius: 20px; cursor: pointer; }
        .filter button.active { background: #2196F3; color: white; border-color: #2196F3; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📸 照片筛选预览</h1>
        <p>输入目录: """ + input_dir + """</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="number">""" + str(len(all_images)) + """</div>
            <div class="label">原始照片</div>
        </div>
        <div class="stat-card stat-kept">
            <div class="number">""" + str(len(final_kept)) + """</div>
            <div class="label">保留</div>
        </div>
        <div class="stat-card stat-removed">
            <div class="number">""" + str(len(all_images) - len(final_kept)) + """</div>
            <div class="label">剔除</div>
        </div>
    </div>
""")
    
    # Kept photos section
    html_parts.append('    <div class="section">')
    html_parts.append(f'        <h2 class="section-title">✅ 保留的照片（{len(final_kept)} 张）</h2>')
    html_parts.append('        <div class="photo-grid">')
    
    for img_path in final_kept:
        thumb = thumb_map.get(img_path, "")
        score = scores.get(img_path, 0)
        score_pct = int(score * 100)
        score_class = "score-high" if score > 0.7 else ("score-mid" if score > 0.5 else "score-low")
        name = Path(img_path).name
        
        html_parts.append(f"""            <div class="photo-card">
                <img src="{thumb}" alt="{name}">
                <div class="photo-info">
                    <div class="photo-name">{name}</div>
                    <div class="photo-score">
                        美学评分: <span class="score-badge {score_class}">{score_pct}%</span>
                    </div>
                    <div class="reason">✅ 去重后保留，评分排名前 {len(final_kept)}</div>
                </div>
            </div>""")
    
    html_parts.append('        </div>')
    html_parts.append('    </div>')
    
    # Removed by dHash section
    if removed_by_dhash:
        html_parts.append('    <div class="section removed-section">')
        html_parts.append(f'        <h2 class="section-title">❌ dHash 去重剔除（{len(removed_by_dhash)} 张）</h2>')
        html_parts.append(f'        <p style="color:#666;margin-bottom:15px;">以下照片因与保留照片过于相似（dHash 海明距离 < {dhash_threshold}）被剔除：</p>')
        html_parts.append('        <div class="photo-grid">')
        
        for removed_path, info in removed_by_dhash.items():
            thumb = thumb_map.get(removed_path, "")
            similar_thumb = thumb_map.get(info["similar_to"], "")
            name = Path(removed_path).name
            similar_name = Path(info["similar_to"]).name
            
            html_parts.append(f"""            <div class="photo-card">
                <img src="{thumb}" alt="{name}">
                <div class="photo-info">
                    <div class="photo-name">{name}</div>
                    <div class="reason">❌ {info["reason"]}</div>
                    <div class="reason">相似保留: {similar_name}</div>
                </div>
            </div>""")
        
        html_parts.append('        </div>')
        html_parts.append('    </div>')
    
    # Removed by score section
    if removed_by_score:
        html_parts.append('    <div class="section removed-section">')
        html_parts.append(f'        <h2 class="section-title">❌ 美学评分剔除（{len(removed_by_score)} 张）</h2>')
        html_parts.append(f'        <p style="color:#666;margin-bottom:15px;">以下照片因美学评分较低未被选入前 {top_k} 名：</p>')
        html_parts.append('        <div class="photo-grid">')
        
        for img_path in removed_by_score:
            thumb = thumb_map.get(img_path, "")
            score = scores.get(img_path, 0)
            score_pct = int(score * 100)
            score_class = "score-low"
            name = Path(img_path).name
            
            html_parts.append(f"""            <div class="photo-card">
                <img src="{thumb}" alt="{name}">
                <div class="photo-info">
                    <div class="photo-name">{name}</div>
                    <div class="photo-score">
                        美学评分: <span class="score-badge {score_class}">{score_pct}%</span>
                    </div>
                    <div class="reason">❌ 评分未进入前 {top_k}</div>
                </div>
            </div>""")
        
        html_parts.append('        </div>')
        html_parts.append('    </div>')
    
    html_parts.append("""
</body>
</html>""")
    
    # Write HTML
    html_path = output_path / preview_html
    html_path.write_text('\n'.join(html_parts), encoding='utf-8')
    
    print(f"\n✅ 预览页面已生成: {html_path}")
    print(f"   打开浏览器查看: file://{html_path.absolute()}")
    
    return {
        "total": len(all_images),
        "kept": len(final_kept),
        "removed_dhash": len(removed_by_dhash),
        "removed_score": len(removed_by_score),
        "preview_html": str(html_path),
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生成照片筛选预览")
    parser.add_argument("--input", "-i", required=True, help="输入目录")
    parser.add_argument("--output", "-o", default="preview_output", help="输出目录")
    parser.add_argument("--top-k", type=int, default=100, help="保留数量")
    parser.add_argument("--dhash-threshold", type=int, default=5, help="dHash 阈值")
    
    args = parser.parse_args()
    
    result = generate_preview(
        input_dir=args.input,
        output_dir=args.output,
        top_k=args.top_k,
        dhash_threshold=args.dhash_threshold,
    )
    
    print(f"\n统计: {result}")
