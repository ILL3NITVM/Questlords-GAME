"""Structured specification objects for a single Octavia photograph.

A ``FrameSpec`` is the complete, serialisable description of one image.
Given the same ``SeedRecord`` and the same data/ + config/ contents, the
sampler must reproduce an identical ``FrameSpec`` — that is the
reproducibility contract described in section 9 of the brief.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

SEED_AXES = (
    "identity_seed",
    "wardrobe_seed",
    "colour_seed",
    "material_seed",
    "scene_seed",
    "pose_seed",
    "camera_seed",
    "lighting_seed",
    "expression_seed",
)


@dataclass
class SeedRecord:
    """Per-axis seeds. Every axis is sampled from its own RNG stream so that
    changing (say) the wardrobe seed does not cascade into the pose choice."""

    identity_seed: int = 0
    wardrobe_seed: int = 0
    colour_seed: int = 0
    material_seed: int = 0
    scene_seed: int = 0
    pose_seed: int = 0
    camera_seed: int = 0
    lighting_seed: int = 0
    expression_seed: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SeedRecord":
        return cls(**{k: int(d[k]) for k in SEED_AXES if k in d})


@dataclass
class WardrobeSelection:
    mode: str = "separates"            # "separates" | "one_piece"
    top: Optional[Dict[str, Any]] = None
    bottom: Optional[Dict[str, Any]] = None
    dress: Optional[Dict[str, Any]] = None
    outer_layer: Optional[Dict[str, Any]] = None
    footwear: Optional[Dict[str, Any]] = None
    accessories: List[Dict[str, Any]] = field(default_factory=list)
    harmony: Optional[Dict[str, Any]] = None
    colours: Dict[str, str] = field(default_factory=dict)   # slot -> colour id
    families: List[str] = field(default_factory=list)


@dataclass
class HeadPose:
    """Estimated head orientation in degrees. See data/poses/head_positions.json
    for the sign convention (negative roll == tilt toward her LEFT)."""

    position_id: str = "upright_neutral"
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    tilt_class: str = "neutral"        # left | neutral | right
    eye_direction: str = "camera"

    @property
    def is_left_tilt(self) -> bool:
        return self.tilt_class == "left"


@dataclass
class FrameSpec:
    run_id: str
    index: int
    frame_id: str
    campaign: str
    seeds: SeedRecord

    wardrobe: WardrobeSelection = field(default_factory=WardrobeSelection)
    scene: Dict[str, Any] = field(default_factory=dict)
    lighting: Dict[str, Any] = field(default_factory=dict)
    pose: Dict[str, Any] = field(default_factory=dict)
    head: HeadPose = field(default_factory=HeadPose)
    hands: Dict[str, Any] = field(default_factory=dict)
    expression: Dict[str, Any] = field(default_factory=dict)
    camera: Dict[str, Any] = field(default_factory=dict)

    prompt: str = ""
    negative_prompt: str = ""
    width: int = 896
    height: int = 1152

    # Category keys used by the diversity tracker
    def category_keys(self) -> Dict[str, str]:
        return {
            "wardrobe_family": "+".join(self.wardrobe.families) or "unknown",
            "wardrobe_top": (self.wardrobe.top or {}).get("id", ""),
            "wardrobe_bottom": (self.wardrobe.bottom or {}).get("id", ""),
            "wardrobe_dress": (self.wardrobe.dress or {}).get("id", ""),
            "colour_family": self.wardrobe.harmony.get("id", "") if self.wardrobe.harmony else "",
            "scene_family": self.scene.get("family", ""),
            "scene_id": self.scene.get("id", ""),
            "env_palette": self.scene.get("env_palette", ""),
            "pose_family": self.pose.get("family", ""),
            "pose_id": self.pose.get("id", ""),
            "head_position": self.head.position_id,
            "tilt_class": self.head.tilt_class,
            "hands": self.hands.get("id", ""),
            "expression": self.expression.get("id", ""),
            "camera_shot": self.camera.get("shot", {}).get("id", ""),
            "camera_focal": self.camera.get("focal", {}).get("id", ""),
            "camera_height": self.camera.get("height", {}).get("id", ""),
            "lighting": self.lighting.get("id", ""),
        }

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["seeds"] = self.seeds.to_dict()
        d["category_keys"] = self.category_keys()
        return d
