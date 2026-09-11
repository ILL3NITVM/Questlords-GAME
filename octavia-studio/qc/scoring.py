"""QC scoring.

HONESTY NOTE — read this before trusting any number this module emits.

The fourteen QC metrics in section 11 fall into two groups:

  COMPUTABLE NOW (no vision model needed) — these are real measurements:
      novelty              : distance from recent frames in category space
      head_pose_novelty    : head-geometry repetition + left-tilt over-use
      composition          : internal coherence of shot/focal/height/pose
      scene_quality        : scene/lighting/pose affordance agreement

  REQUIRES A VISION MODEL — these cannot be honestly scored without one:
      identity_consistency, face_consistency, physique_consistency,
      anatomy, hands, feet, pose_naturalness, clothing_integrity,
      photorealism, lighting

``HeuristicScorer`` returns real values for the first group and clearly
flagged placeholder values for the second. Every result carries
``scorer_kind`` and a ``placeholder_metrics`` list so nothing downstream can
mistake a placeholder for a measurement. ``studio.py doctor`` reports this as
a blocking item for real generation.

To make the second group real, implement ``Scorer`` with:
  * a face-embedding model (ArcFace/InsightFace) compared against
    assets/octavia/face_reference/ -> identity_consistency, face_consistency
  * a pose/keypoint model (MediaPipe, DWPose) -> anatomy, hands, feet,
    pose_naturalness, and a MEASURED head pose for qc/headpose.py
  * body-keypoint ratios vs config/physique.yaml -> physique_consistency
  * an aesthetic/realism classifier -> photorealism, lighting
and register it in ``get_scorer()``.
"""
from __future__ import annotations

import abc
import hashlib
from typing import Any, Dict, List, Optional, Tuple

from pipeline.spec import FrameSpec
from qc.headpose import HeadPoseEstimate

VISION_METRICS = [
    "identity_consistency", "face_consistency", "physique_consistency",
    "anatomy", "hands", "feet", "pose_naturalness", "clothing_integrity",
    "photorealism", "lighting",
]
COMPUTED_METRICS = ["novelty", "head_pose_novelty", "composition", "scene_quality"]
ALL_METRICS = VISION_METRICS + COMPUTED_METRICS


class Scorer(abc.ABC):
    kind = "base"
    placeholder_metrics: List[str] = []

    @abc.abstractmethod
    def score(self, spec: FrameSpec, image_path, head: HeadPoseEstimate,
              history) -> Tuple[Dict[str, float], List[str]]:
        """Return (scores 0-100 keyed by metric, detected defect flags)."""


class HeuristicScorer(Scorer):
    """Real numbers where they can be computed; flagged placeholders elsewhere."""

    kind = "heuristic-stub"
    placeholder_metrics = list(VISION_METRICS)

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    # ------------------------------------------------------------------
    def score(self, spec: FrameSpec, image_path, head: HeadPoseEstimate,
              history) -> Tuple[Dict[str, float], List[str]]:
        scores: Dict[str, float] = {}
        keys = spec.category_keys()

        # ---- REAL: novelty against recent history -----------------------
        tracked = ["scene_id", "scene_family", "pose_id", "pose_family",
                   "wardrobe_top", "wardrobe_bottom", "wardrobe_dress",
                   "colour_family", "camera_shot", "expression", "hands",
                   "camera_focal", "camera_height", "lighting"]
        penalty = 0.0
        for axis in tracked:
            value = keys.get(axis)
            if not value:
                continue
            recent = history.window_count(axis, value)
            weight = 8.0 if axis in ("scene_id", "pose_id") else 4.0
            penalty += min(weight * 2, recent * weight)
        scores["novelty"] = max(0.0, 100.0 - penalty)

        # ---- REAL: head-pose novelty + left-tilt discipline -------------
        hp = 100.0
        hp -= min(45.0, history.window_count("head_position", keys.get("head_position", "")) * 18.0)
        if head.is_left_tilt:
            share = history.left_tilt_share()
            hp -= 55.0 if share > 0.08 else (25.0 if share > 0.05 else 8.0)
        if head.source == "requested":
            # We are trusting the request rather than a measurement; cap the
            # confidence this metric can claim.
            hp = min(hp, 88.0)
        scores["head_pose_novelty"] = max(0.0, hp)

        # ---- REAL: internal composition coherence -----------------------
        comp = 88.0
        shot = spec.camera.get("shot", {})
        focal = spec.camera.get("focal", {})
        if shot.get("id") not in focal.get("suitable_shots", []):
            comp -= 25.0
        posture = spec.pose.get("posture", "")
        if posture in ("seated", "floor") and shot.get("id") == "full_body":
            comp -= 15.0
        if shot.get("emphasis") == "face" and spec.camera.get("height", {}).get("id") == "low_floor":
            comp -= 12.0
        if abs(head.yaw) > 65 and spec.camera.get("angle", {}).get("id") == "frontal":
            comp -= 10.0
        scores["composition"] = max(0.0, min(100.0, comp))

        # ---- REAL: scene/pose/lighting agreement ------------------------
        sq = 90.0
        needs = spec.pose.get("requires_furniture", [])
        affordances = " ".join(spec.scene.get("furniture_affordances", []) +
                               spec.scene.get("surfaces", [])).lower()
        if needs and not any(n.lower() in affordances for n in needs):
            sq -= 35.0
        if not spec.scene.get("indoor", True) and \
                spec.lighting.get("kind") == "studio":
            sq -= 20.0
        if spec.scene.get("indoor", True) and spec.lighting.get("id") in ("golden_hour", "blue_hour"):
            sq -= 6.0
        scores["scene_quality"] = max(0.0, min(100.0, sq))

        # ---- PLACEHOLDER: everything needing a vision model -------------
        # Deterministic pseudo-values so runs are reproducible and contact
        # sheets are populated. NOT MEASUREMENTS.
        #
        # The digest keys off the SEED RECORD, not just the frame id. Keying on
        # the frame id alone would make a rerolled frame score identically to
        # the frame it replaced, so `reroll --rejected-only` could never clear
        # a rejection and the review loop would be untestable in mock mode.
        seed_blob = "|".join(str(v) for v in spec.seeds.to_dict().values())
        digest = hashlib.blake2b(f"{spec.frame_id}|{seed_blob}".encode(),
                                 digest_size=16).digest()
        for i, metric in enumerate(VISION_METRICS):
            byte = digest[i % len(digest)]
            scores[metric] = round(84.0 + (byte / 255.0) * 14.0, 1)  # 84-98

        defects: List[str] = []
        return scores, defects


def get_scorer(config: Dict[str, Any], kind: Optional[str] = None) -> Scorer:
    kind = (kind or config.get("qc", {}).get("scorer", "heuristic")).lower()
    if kind in ("heuristic", "heuristic-stub", "stub"):
        return HeuristicScorer(config)
    raise ValueError(
        f"Unknown scorer {kind!r}. Only the heuristic stub ships today; see the "
        "module docstring for what a real vision scorer must implement."
    )


def overall(scores: Dict[str, float]) -> float:
    """Weighted headline score. Identity and physique dominate by design."""
    weights = {
        "identity_consistency": 3.0, "physique_consistency": 2.5, "face_consistency": 2.0,
        "anatomy": 2.0, "photorealism": 2.0, "hands": 1.5, "feet": 1.0,
        "pose_naturalness": 1.2, "clothing_integrity": 1.2, "scene_quality": 1.0,
        "composition": 1.0, "lighting": 1.0, "novelty": 1.5, "head_pose_novelty": 1.5,
    }
    num = sum(scores.get(m, 0.0) * w for m, w in weights.items() if m in scores)
    den = sum(w for m, w in weights.items() if m in scores)
    return round(num / den, 1) if den else 0.0
