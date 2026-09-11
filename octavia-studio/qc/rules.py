"""Hard-reject and defect rules (section 11).

This module owns *policy*, not measurement. It takes a score dict plus a set
of detected defect flags and decides accept / reject / warn. Keeping the
decision separate from the scorer means you can swap in a real vision-based
scorer later without touching the thresholds you have tuned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

DEFECT_TARGETS = {
    "extra_fingers": "hands",
    "missing_fingers": "hands",
    "merged_limbs": "anatomy",
    "warped_feet": "feet",
    "asymmetric_eyes": "face_consistency",
    "false_tattoos": "identity_consistency",
    "random_writing": "scene_quality",
    "duplicated_objects": "scene_quality",
    "broken_mirror": "scene_quality",
    "incorrect_reflection": "scene_quality",
    "impossible_furniture_contact": "pose_naturalness",
    "clothing_melting_into_skin": "clothing_integrity",
}


@dataclass
class Verdict:
    accepted: bool
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    defects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"accepted": self.accepted, "reasons": self.reasons,
                "warnings": self.warnings, "defects": self.defects}


def apply_defect_penalties(scores: Dict[str, float], defects: List[str],
                           penalties: Dict[str, int]) -> Dict[str, float]:
    out = dict(scores)
    for d in defects:
        target = DEFECT_TARGETS.get(d)
        if target and target in out:
            out[target] = max(0.0, out[target] - float(penalties.get(d, 20)))
    return out


def judge(scores: Dict[str, float], defects: List[str], qc_config: Dict[str, Any]) -> Verdict:
    hard = qc_config.get("hard_reject", {})
    warn = qc_config.get("warn_below", {})

    reasons, warnings = [], []
    for metric, floor in hard.items():
        value = scores.get(metric)
        if value is not None and value < float(floor):
            reasons.append(f"{metric} {value:.1f} < {floor} (hard floor)")

    # A handful of defects are disqualifying regardless of the numbers —
    # a false tattoo is an identity violation, not a quality nit.
    for d in ("false_tattoos", "merged_limbs", "extra_fingers", "missing_fingers"):
        if d in defects:
            reasons.append(f"disqualifying defect: {d}")

    for metric, floor in warn.items():
        value = scores.get(metric)
        if value is not None and value < float(floor):
            warnings.append(f"{metric} {value:.1f} < {floor}")

    return Verdict(accepted=not reasons, reasons=reasons,
                   warnings=warnings, defects=list(defects))
