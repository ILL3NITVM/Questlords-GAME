"""Hero-frame search: find the single spec with the highest chance of an
excellent render.

A campaign optimises for DIVERSITY. A hero frame optimises for QUALITY, and
the two objectives disagree almost everywhere. Diversity sampling
deliberately reaches for the unusual crop, the awkward furniture contact,
the wide lens — exactly the choices most likely to produce an artefact.

This module scores candidate specs against a risk model of where diffusion
models actually fail, then returns the best. The risk weights below are
informed priors, not measurements: they encode well-known failure modes
(hands, feet, reflections, extreme perspective, small faces) rather than
anything this system has measured on your renderer. Treat them as a
starting policy and tune `config/studio.yaml: hero` against real output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pipeline.compose import Composer
from pipeline.spec import FrameSpec

# ----------------------------------------------------------------------
# Framing: a face rendered across more pixels is a face rendered better,
# and identity legibility is the whole point of a hero frame.
SHOT_SCORE = {
    "close_portrait": 1.00,
    "head_and_shoulders": 0.98,
    "waist_up": 0.92,
    "three_quarter": 0.80,
    "seated_full": 0.62,
    "full_body": 0.55,
    "candid_detail": 0.50,
    "environmental_full_body": 0.34,
    "mirror_selfie": 0.28,      # reflection consistency is a known weak point
}

FOCAL_SCORE = {
    "85mm": 1.00,
    "105mm": 0.94,
    "50mm": 0.88,
    "35mm": 0.72,
    "24mm": 0.48,               # wide-angle facial distortion
}

APERTURE_SCORE = {"f2.8": 1.00, "f4": 0.95, "f1.8": 0.86, "f5.6": 0.80, "f8": 0.70}

# Light that models the face cleanly, without extreme contrast.
LIGHTING_SCORE = {
    "soft_window_daylight": 1.00, "beauty_dish": 0.98, "softbox_key": 0.97,
    "open_shade": 0.94, "rim_and_fill": 0.90, "golden_hour": 0.88,
    "broad_flat_studio": 0.85, "overcast_soft": 0.82, "bulb_mirror": 0.78,
    "warm_lamplight": 0.72, "dappled_canopy": 0.55, "city_practicals": 0.52,
    "hard_window_shaft": 0.50, "low_key_pooled": 0.46, "blue_hour": 0.44,
}

# Poses with awkward weight-bearing, motion blur risk or heavy occlusion.
POSE_RISK = {
    "walking_candid": 0.30, "crouch_low": 0.38, "reaching_shelf": 0.30,
    "mirror_selfie": 0.35, "floor_knees_up": 0.20, "stair_seated": 0.18,
    "turning_toward_camera": 0.16, "sofa_lounge": 0.12, "floor_seated": 0.14,
}

# Hand placements that put fingers large and central in frame. Hands remain
# the most common visible failure in photoreal generation.
HAND_RISK = {
    "one_hand_hair": 0.26, "adjusting_sleeve": 0.24, "adjusting_hem": 0.24,
    "holding_mug": 0.30, "holding_phone_mirror": 0.34, "touching_collarbone": 0.22,
    "hand_behind_neck": 0.24, "both_hands_hips": 0.18, "mid_gesture": 0.20,
    "hands_clasped_front": 0.16, "one_arm_crossed": 0.12, "arms_folded": 0.14,
    "hands_in_pockets": 0.02, "relaxed_at_sides": 0.04, "hands_in_lap": 0.08,
    "one_hand_hip": 0.08,
}


@dataclass
class HeroScore:
    total: float
    components: Dict[str, float] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"total": round(self.total, 2),
                "components": {k: round(v, 3) for k, v in self.components.items()},
                "risks": self.risks, "notes": self.notes}


def score_spec(spec: FrameSpec, cfg: Optional[Dict[str, Any]] = None) -> HeroScore:
    cfg = cfg or {}
    w = cfg.get("weights", {})
    shot = spec.camera["shot"]["id"]
    focal = spec.camera["focal"]["id"]
    aperture = spec.camera["aperture"]["id"].replace("/", "")
    lighting = spec.lighting["id"]
    pose_id = spec.pose["id"]
    hands_id = spec.hands["id"]

    comp: Dict[str, float] = {}
    risks: List[str] = []
    notes: List[str] = []

    comp["framing"] = SHOT_SCORE.get(shot, 0.6)
    comp["focal"] = FOCAL_SCORE.get(focal, 0.7)
    comp["aperture"] = APERTURE_SCORE.get(aperture, 0.8)
    comp["lighting"] = LIGHTING_SCORE.get(lighting, 0.7)

    pose_risk = POSE_RISK.get(pose_id, 0.06)
    hand_risk = HAND_RISK.get(hands_id, 0.10)
    comp["pose_safety"] = 1.0 - pose_risk
    comp["hand_safety"] = 1.0 - hand_risk
    if pose_risk >= 0.25:
        risks.append(f"pose {pose_id} is motion- or balance-heavy")
    if hand_risk >= 0.22:
        risks.append(f"hand placement {hands_id} puts fingers prominent in frame")

    # Feet are only a risk when actually in frame.
    feet_visible = shot in ("full_body", "environmental_full_body", "seated_full")
    barefoot = (spec.wardrobe.footwear or {}).get("id") in ("barefoot", "socks")
    if feet_visible and barefoot:
        comp["feet_safety"] = 0.62
        risks.append("bare feet visible in a full-length crop")
    elif feet_visible:
        comp["feet_safety"] = 0.88
    else:
        comp["feet_safety"] = 1.0

    # Identity legibility: a face turned far from camera matches references
    # poorly, and eye contact is the strongest identity cue available.
    yaw = abs(spec.head.yaw)
    if yaw > 60:
        comp["identity_legibility"] = 0.45
        risks.append(f"near-profile head yaw {spec.head.yaw:.0f} degrees weakens identity match")
    elif yaw > 35:
        comp["identity_legibility"] = 0.74
    elif yaw > 15:
        comp["identity_legibility"] = 0.92
    else:
        comp["identity_legibility"] = 1.0
    if spec.head.eye_direction == "camera":
        comp["identity_legibility"] = min(1.0, comp["identity_legibility"] + 0.06)
    else:
        notes.append("gaze is off-camera; identity reads less strongly")

    # Scene complexity: reflective and heavily-furnished rooms invite
    # geometry errors. Seamless and simple backdrops are the safe choice.
    scene_family = spec.scene.get("family", "")
    if scene_family in ("fashion_studio", "minimal_studio", "gallery"):
        comp["scene_safety"] = 1.0
    elif scene_family in ("bathroom_vanity", "walk_in_wardrobe", "dressing_room"):
        comp["scene_safety"] = 0.62
        risks.append(f"{scene_family} contains mirrors; reflections are error-prone")
    elif scene_family in ("hotel_lobby", "cafe_interior", "modern_kitchen"):
        comp["scene_safety"] = 0.78
    else:
        comp["scene_safety"] = 0.88

    # Furniture contact is where limbs intersect geometry incorrectly.
    needs = spec.pose.get("requires_furniture", [])
    comp["contact_safety"] = 0.80 if needs else 1.0
    if needs:
        notes.append(f"pose contacts {', '.join(needs)}; check intersection in the render")

    # Outfit complexity: more layers and accessories, more to get wrong.
    pieces = len(spec.wardrobe.families) + len(spec.wardrobe.accessories)
    comp["wardrobe_simplicity"] = max(0.55, 1.0 - 0.10 * max(0, pieces - 2))

    default_w = {
        "framing": 1.8, "focal": 1.4, "aperture": 0.7, "lighting": 1.5,
        "pose_safety": 1.2, "hand_safety": 1.4, "feet_safety": 0.9,
        "identity_legibility": 2.2, "scene_safety": 1.0,
        "contact_safety": 0.7, "wardrobe_simplicity": 0.6,
    }
    weights = {k: float(w.get(k, v)) for k, v in default_w.items()}
    num = sum(comp[k] * weights[k] for k in comp if k in weights)
    den = sum(weights[k] for k in comp if k in weights)
    return HeroScore(total=100.0 * num / den if den else 0.0,
                     components=comp, risks=risks, notes=notes)


def search(composer: Composer, run_id: str, master_seed: int, candidates: int,
           campaign: str = "editorial", cfg: Optional[Dict[str, Any]] = None,
           ) -> List[Tuple[FrameSpec, HeroScore]]:
    """Compose ``candidates`` specs and return them ranked best-first.

    Candidate generation uses the ordinary composer, so every coherence rule
    (furniture affordances, focal/shot agreement, colour harmony, content
    policy) still holds. The hero objective only decides which of the valid
    specs is most likely to render beautifully.
    """
    from pipeline.seeds import seed_record

    scored: List[Tuple[FrameSpec, HeroScore]] = []
    for i in range(candidates):
        spec = composer.compose(run_id, i, seed_record(master_seed, run_id, i),
                                campaign=campaign)
        scored.append((spec, score_spec(spec, cfg)))
    scored.sort(key=lambda pair: pair[1].total, reverse=True)
    return scored
