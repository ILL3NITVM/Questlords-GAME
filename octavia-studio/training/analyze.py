"""Training-set curation and bias analysis.

WHY THIS EXISTS
---------------
A LoRA learns whatever is over-represented in its training set, at the
weights level. If 40% of the source photographs are mirror selfies with a
leftward head tilt in warm indoor light, the adapter learns "Octavia" to
mean partly "leftward tilt in warm indoor light" — and no amount of
prompt-side pose balancing in pipeline/sampler.py will pull that back out.
Prompt weighting cannot override a bias baked into the weights.

So the studio's anti-collapse discipline has to start one stage earlier,
at the dataset. This module reports what the set is skewed toward and
optionally rebalances by capping over-represented clusters.

WHAT IS MEASURED HERE vs WHAT NEEDS A VISION MODEL
--------------------------------------------------
Computed now, honestly, with Pillow alone:
    near-duplicate clusters, resolution and aspect distribution,
    exposure and contrast distribution, colour-temperature proxy,
    aspect-bucket balance

Requires a vision model (reported as UNMEASURED, never guessed):
    head pose / tilt distribution, framing and crop distribution,
    expression distribution, wardrobe and scene variety

The unmeasured axes are exactly the ones most likely to carry the bias
that matters. `analyze` says so plainly rather than implying the set is
clean because the measurable axes look fine.
"""
from __future__ import annotations

import pathlib
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence

from training.ingest import ImageRecord, hamming

UNMEASURED_AXES = [
    ("head_pose / tilt", "face landmark model (MediaPipe FaceMesh, DWPose)"),
    ("framing / crop", "body keypoint model"),
    ("expression", "face analysis model"),
    ("wardrobe variety", "CLIP or a captioning model"),
    ("scene variety", "CLIP or a captioning model"),
]


def cluster_near_duplicates(records: Sequence[ImageRecord], threshold: int = 6) -> int:
    """Union-find clustering on perceptual-hash Hamming distance.

    Near-duplicates are the most common way a dataset silently over-weights
    one look: twenty frames from the same burst read as twenty independent
    examples during training.
    """
    usable = [r for r in records if r.dhash and set(r.dhash) != {"0"}]
    parent = {id(r): id(r) for r in usable}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(usable):
        for b in usable[i + 1:]:
            if hamming(a.dhash, b.dhash) <= threshold:
                union(id(a), id(b))

    groups: Dict[int, List[ImageRecord]] = defaultdict(list)
    for r in usable:
        groups[find(id(r))].append(r)

    for cid, members in enumerate(sorted(groups.values(), key=lambda m: -len(m))):
        for r in members:
            r.cluster = cid
    for r in records:
        if r.cluster is None:
            r.cluster = -1
    return sum(1 for m in groups.values() if len(m) > 1)


def _hist(values: Sequence[float], edges: Sequence[float]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for i, lo in enumerate(edges[:-1]):
        hi = edges[i + 1]
        label = f"{lo:g}-{hi:g}"
        out[label] = sum(1 for v in values if lo <= v < hi)
    return out


def analyze(records: Sequence[ImageRecord], cfg: Dict[str, Any]) -> Dict[str, Any]:
    readable = [r for r in records if "unreadable" not in r.flags]
    dup_clusters = cluster_near_duplicates(
        readable, threshold=int(cfg.get("dedupe", {}).get("hamming_threshold", 6)))

    cluster_sizes = Counter(r.cluster for r in readable if r.cluster is not None and r.cluster >= 0)
    largest = cluster_sizes.most_common(5)

    flags = Counter(f.split("(")[0] for r in readable for f in r.flags)
    buckets = Counter(r.bucket for r in readable)
    total = max(1, len(readable))

    report: Dict[str, Any] = {
        "total_files": len(records),
        "readable": len(readable),
        "unreadable": len(records) - len(readable),
        "quality_flags": dict(flags),
        "near_duplicate_clusters": dup_clusters,
        "images_in_duplicate_clusters": sum(n for _, n in cluster_sizes.items() if n > 1),
        "largest_clusters": [{"cluster": c, "size": n} for c, n in largest if n > 1],
        "aspect_buckets": {
            b: {"count": n, "share": round(n / total, 3)}
            for b, n in buckets.most_common()
        },
        "resolution": {
            "min_side_min": min((min(r.width, r.height) for r in readable), default=0),
            "min_side_median": sorted(min(r.width, r.height) for r in readable)[len(readable) // 2]
            if readable else 0,
            "min_side_max": max((min(r.width, r.height) for r in readable), default=0),
        },
        "exposure_histogram": _hist([r.mean_luma for r in readable],
                                    [0, 40, 70, 100, 130, 160, 190, 220, 256]),
        "contrast_histogram": _hist([r.rms_contrast for r in readable],
                                    [0, 20, 35, 50, 65, 80, 200]),
        "saturation_histogram": _hist([r.saturation for r in readable],
                                      [0, 30, 60, 90, 120, 256]),
        "unmeasured_axes": [
            {"axis": a, "requires": req, "status": "UNMEASURED"} for a, req in UNMEASURED_AXES
        ],
    }

    warnings: List[str] = []
    caps = cfg.get("balance", {})

    dup_share = report["images_in_duplicate_clusters"] / total
    if dup_share > float(caps.get("max_duplicate_share", 0.20)):
        warnings.append(
            f"{dup_share:.0%} of the set sits in near-duplicate clusters. Training on "
            f"these over-weights whatever they depict. Run `dataset curate` to cap "
            f"cluster contribution.")

    for bucket, info in report["aspect_buckets"].items():
        if info["share"] > float(caps.get("max_bucket_share", 0.70)):
            warnings.append(
                f"{info['share']:.0%} of the set is aspect bucket {bucket}. The LoRA will "
                f"favour that framing; generations at other aspect ratios will be weaker.")

    lowres = flags.get("low_resolution", 0)
    if lowres / total > 0.25:
        warnings.append(
            f"{lowres}/{total} images are below the minimum side length. Low-resolution "
            f"training data caps the detail the adapter can reproduce.")

    exp = report["exposure_histogram"]
    dominant_exp = max(exp.items(), key=lambda kv: kv[1]) if exp else ("", 0)
    if dominant_exp[1] / total > 0.60:
        warnings.append(
            f"{dominant_exp[1]/total:.0%} of the set falls in one exposure band "
            f"({dominant_exp[0]}). The adapter may bind Octavia's identity to that "
            f"lighting level and resist the studio's lighting variety.")

    # A flag that fires on nearly everything is far more likely to be a
    # miscalibrated threshold than a universally bad dataset. Saying
    # "42 images flagged" without this note sends people deleting good data.
    for flag, n in flags.items():
        if total >= 10 and n / total > 0.90:
            warnings.append(
                f"'{flag}' fired on {n}/{total} images ({n/total:.0%}). A flag that hits "
                f"almost everything usually means the corresponding threshold in "
                f"config/training.yaml (quality.*) is miscalibrated for this set, not that "
                f"every image is bad. Check the threshold before discarding anything.")

    if len(readable) < int(cfg.get("training", {}).get("min_images", 20)):
        warnings.append(
            f"Only {len(readable)} usable images. Below ~20 a LoRA tends to overfit "
            f"to incidental detail rather than learning identity.")

    report["warnings"] = warnings
    report["critical_note"] = (
        "Head pose, framing, expression, wardrobe and scene distribution are the axes "
        "most likely to carry harmful bias, and NONE of them are measured here. A clean "
        "report on the measurable axes is not evidence the set is balanced. Review the "
        "contact sheet by eye before training."
    )
    return report


def curate(records: List[ImageRecord], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Apply selection decisions in place. Never deletes source files."""
    q = cfg.get("quality", {})
    balance = cfg.get("balance", {})
    drop_flags = set(q.get("reject_flags", ["unreadable", "low_resolution", "extreme_aspect"]))
    max_per_cluster = int(balance.get("max_per_duplicate_cluster", 3))

    for r in records:
        r.selected = True
        r.reject_reason = None

    for r in records:
        hit = [f for f in r.flags if f.split("(")[0] in drop_flags]
        if hit:
            r.selected = False
            r.reject_reason = "quality: " + ", ".join(hit)

    # Cap how much any one near-duplicate cluster can contribute. Keep the
    # highest-resolution members — they carry the most trainable detail.
    by_cluster: Dict[int, List[ImageRecord]] = defaultdict(list)
    for r in records:
        if r.selected and r.cluster is not None and r.cluster >= 0:
            by_cluster[r.cluster].append(r)

    capped = 0
    for cid, members in by_cluster.items():
        if len(members) <= max_per_cluster:
            continue
        members.sort(key=lambda r: (r.width * r.height, r.rms_contrast), reverse=True)
        for r in members[max_per_cluster:]:
            r.selected = False
            r.reject_reason = f"duplicate cluster {cid} capped at {max_per_cluster}"
            capped += 1

    selected = [r for r in records if r.selected]
    return {
        "total": len(records),
        "selected": len(selected),
        "rejected_quality": sum(1 for r in records
                                if not r.selected and (r.reject_reason or "").startswith("quality")),
        "rejected_duplicates": capped,
        "buckets": dict(Counter(r.bucket for r in selected)),
    }
