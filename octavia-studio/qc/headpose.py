"""Head-pose estimation and left-tilt tracking (section 12).

Two sources of head pose, in priority order:

1. A *measured* estimate from the renderer or an estimator backend. This is
   the truthful one — it reflects what was actually drawn.
2. The *requested* pose from the FrameSpec, used as a fallback.

The distinction matters a great deal. A diffusion model does not always obey
a requested head angle. If the studio tracks only what it asked for, the
left-tilt budget will silently drift as the model reverts to its own
preferred pose. ``estimate()`` therefore reports which source was used, and
``LEFT_TILT_UNVERIFIED`` is raised into QC notes when only the request is
available from a non-deterministic backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

LEFT_ROLL_THRESHOLD = -4.0
RIGHT_ROLL_THRESHOLD = 4.0


@dataclass
class HeadPoseEstimate:
    yaw: float
    pitch: float
    roll: float
    source: str            # "measured" | "requested"
    confidence: float      # 0..1

    @property
    def tilt_class(self) -> str:
        if self.roll <= LEFT_ROLL_THRESHOLD:
            return "left"
        if self.roll >= RIGHT_ROLL_THRESHOLD:
            return "right"
        return "neutral"

    @property
    def is_left_tilt(self) -> bool:
        return self.tilt_class == "left"

    def to_dict(self) -> Dict[str, Any]:
        return {"yaw": round(self.yaw, 1), "pitch": round(self.pitch, 1),
                "roll": round(self.roll, 1), "tilt_class": self.tilt_class,
                "source": self.source, "confidence": round(self.confidence, 2)}


def estimate(spec_head: Any, measured: Optional[Dict[str, float]],
             backend_is_deterministic: bool) -> HeadPoseEstimate:
    if measured:
        return HeadPoseEstimate(
            yaw=float(measured.get("yaw", 0.0)),
            pitch=float(measured.get("pitch", 0.0)),
            roll=float(measured.get("roll", 0.0)),
            source="measured",
            confidence=1.0 if backend_is_deterministic else 0.85,
        )
    return HeadPoseEstimate(
        yaw=float(getattr(spec_head, "yaw", 0.0)),
        pitch=float(getattr(spec_head, "pitch", 0.0)),
        roll=float(getattr(spec_head, "roll", 0.0)),
        source="requested",
        confidence=0.5,
    )


def head_pose_novelty(est: HeadPoseEstimate, history) -> float:
    """0-100. Punishes repeating the same head geometry, and punishes left
    tilt hard once it is over-represented."""
    score = 100.0
    recent_same = history.window_count("head_position", getattr(est, "position_id", "")) \
        if hasattr(est, "position_id") else 0
    score -= min(45.0, recent_same * 18.0)

    if est.is_left_tilt:
        share = history.left_tilt_share()
        if share > 0.08:
            score -= 55.0
        elif share > 0.05:
            score -= 25.0
        else:
            score -= 8.0
    return max(0.0, min(100.0, score))
