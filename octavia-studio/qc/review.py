"""Human review ingestion and feedback weighting (section 13).

Review marks are transcribed into runs/<RUN_ID>/review.csv, one row per
frame. ``apply_review`` converts those marks into per-category weight
multipliers stored in data/feedback.json, which the sampler reads on the next
run. Marks are targeted: WARDROBE_BAD only moves wardrobe weights, SCENE_BAD
only moves scene weights, so one bad outfit does not poison an innocent room.
"""
from __future__ import annotations

import csv
import json
import pathlib
from collections import defaultdict
from typing import Any, Dict, List

MARKS = ["KEEP", "REJECT", "IDENTITY_DRIFT", "BODY_DRIFT",
         "POSE_DUPLICATE", "WARDROBE_BAD", "SCENE_BAD"]

# Which category axes each mark should influence.
MARK_TARGETS: Dict[str, List[str]] = {
    "KEEP": ["wardrobe_top", "wardrobe_bottom", "wardrobe_dress", "scene_id",
             "pose_id", "head_position", "colour_family", "camera_shot", "expression"],
    "REJECT": ["wardrobe_top", "wardrobe_bottom", "wardrobe_dress", "scene_id", "pose_id"],
    "IDENTITY_DRIFT": ["camera_focal", "camera_shot", "lighting"],
    "BODY_DRIFT": ["camera_focal", "camera_height", "pose_id"],
    "POSE_DUPLICATE": ["pose_id", "pose_family", "head_position"],
    "WARDROBE_BAD": ["wardrobe_top", "wardrobe_bottom", "wardrobe_dress", "colour_family"],
    "SCENE_BAD": ["scene_id", "scene_family", "env_palette", "lighting"],
}


def write_review_template(manifest: List[Dict[str, Any]], path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["index", "frame_id", "overall_score", "accepted",
                    "wardrobe", "scene", "pose", "head", "tilt", "MARK", "note"])
        for rec in manifest:
            k = rec.get("category_keys", {})
            hp = rec.get("head_pose", {})
            w.writerow([
                rec.get("index"), rec.get("frame_id"), rec.get("overall_score"),
                rec.get("verdict", {}).get("accepted"),
                k.get("wardrobe_family", ""), k.get("scene_id", ""),
                k.get("pose_id", ""), k.get("head_position", ""),
                hp.get("tilt_class", ""), "", "",
            ])
    return path


def read_review(path: pathlib.Path) -> Dict[int, str]:
    if not path.is_file():
        return {}
    marks: Dict[int, str] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            mark = (row.get("MARK") or "").strip().upper()
            if mark in MARKS:
                try:
                    marks[int(row["index"])] = mark
                except (ValueError, KeyError, TypeError):
                    continue
    return marks


def apply_review(manifest: List[Dict[str, Any]], marks: Dict[int, str],
                 feedback_path: pathlib.Path, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fold review marks into the persistent feedback weights."""
    fb_cfg = config.get("feedback", {})
    deltas = fb_cfg.get("weight_delta", {})
    floor = float(fb_cfg.get("weight_floor", 0.15))
    ceiling = float(fb_cfg.get("weight_ceiling", 3.0))

    feedback: Dict[str, Dict[str, float]] = {}
    if feedback_path.is_file():
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))

    by_index = {r.get("index"): r for r in manifest}
    applied = defaultdict(int)

    for index, mark in marks.items():
        rec = by_index.get(index)
        if not rec:
            continue
        multiplier = float(deltas.get(mark, 1.0))
        for axis in MARK_TARGETS.get(mark, []):
            value = rec.get("category_keys", {}).get(axis)
            if not value:
                continue
            current = feedback.setdefault(axis, {}).get(value, 1.0)
            feedback[axis][value] = max(floor, min(ceiling, current * multiplier))
            applied[mark] += 1

    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(json.dumps(feedback, indent=2, sort_keys=True), encoding="utf-8")

    return {"marks_read": len(marks), "adjustments": dict(applied),
            "axes_touched": sorted(feedback), "feedback_file": str(feedback_path)}
