import json
import os
from dataclasses import dataclass, asdict, is_dataclass
from typing import List
from pathlib import Path
from datetime import datetime


@dataclass
class DedupGroup:
    group_id: int
    kept: List[str]
    trimmed: List[str]
    reason: str
    similarity: float


@dataclass
class AestheticScore:
    path: str
    score: float
    rank: int


def export_pipeline_results(
    input_dir: str,
    top_k: int = 100,
    dhash_threshold: int = 5,
    clip_threshold: float = 0.92,
) -> dict:
    from src.pipeline.orchestrator import (
        collect_images,
        run_dedup_only_verbose,
        run_aesthetic_rank_verbose,
    )

    start_time = datetime.now()

    all_images = collect_images(input_dir)

    dedup_result = run_dedup_only_verbose(
        all_images,
        dhash_threshold=dhash_threshold,
        clip_threshold=clip_threshold,
    )

    dedup_groups = _build_dedup_groups(dedup_result)

    dedup_kept = [
        r["path"]
        for r in dedup_result["final_results"]
        if r.get("status") == "kept"
    ]

    aesthetic_result = run_aesthetic_rank_verbose(
        [{"path": p, "status": "kept"} for p in dedup_kept],
        top_k=top_k,
    )

    aesthetic_scores = _build_aesthetic_scores(aesthetic_result)
    final_top_k = aesthetic_scores[:top_k]

    summary = dedup_result.get("summary", {})
    elapsed = (datetime.now() - start_time).total_seconds()

    stats = {
        "input_count": len(all_images),
        "after_dedup": len(dedup_kept),
        "final_count": len(final_top_k),
        "dedup_removed": len(all_images) - len(dedup_kept),
        "aesthetic_removed": len(dedup_kept) - len(final_top_k),
        "total_removed": len(all_images) - len(final_top_k),
        "elapsed_seconds": elapsed,
    }

    return {
        "input_images": all_images,
        "dedup_groups": dedup_groups,
        "aesthetic_scores": aesthetic_scores,
        "final_top_k": final_top_k,
        "stats": stats,
    }


def _build_dedup_groups(dedup_result: dict) -> List[DedupGroup]:
    clip_groups = dedup_result.get("clip_groups", [])
    final_results = dedup_result.get("final_results", [])

    groups: List[DedupGroup] = []
    group_id = 0

    grouped_paths = set()
    for cg in clip_groups:
        for member in cg.get("members", []):
            grouped_paths.add(member)

    for cg in clip_groups:
        members = cg.get("members", [])
        sims = cg.get("clip_similarities", [1.0])
        representative = cg.get("representative", members[0] if members else "")

        kept = [representative] if representative in members else [members[0]]
        trimmed = [m for m in members if m not in kept]
        trimmed_sims = [
            sims[members.index(m)] for m in trimmed if m in members
        ]
        max_sim = max(trimmed_sims) if trimmed_sims else 1.0

        groups.append(DedupGroup(
            group_id=group_id,
            kept=kept,
            trimmed=trimmed,
            reason="clip_similarity",
            similarity=round(max_sim, 4),
        ))
        group_id += 1

    for fr in final_results:
        if fr.get("status") == "kept" and fr["path"] not in grouped_paths:
            groups.append(DedupGroup(
                group_id=group_id,
                kept=[fr["path"]],
                trimmed=[],
                reason="unique",
                similarity=1.0,
            ))
            group_id += 1

    return groups


def _build_aesthetic_scores(aesthetic_result: dict) -> List[AestheticScore]:
    ranking = aesthetic_result.get("ranking", [])
    return [
        AestheticScore(
            path=item["path"],
            score=item["score"],
            rank=item["rank"],
        )
        for item in ranking
    ]


def save_to_json(data: dict, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    def _convert(obj):
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, list):
            return [_convert(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        return obj

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(_convert(data), f, ensure_ascii=False, indent=2)
