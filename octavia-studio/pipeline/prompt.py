"""Build renderer-agnostic positive and negative prompts from a FrameSpec.

Prompt ordering is deliberate. Diffusion models weight earlier tokens more
heavily, so the identity block leads and the environment trails:

    1. medium + subject + age        (identity anchor, highest weight)
    2. face / hair / skin            (the recognisable part of Octavia)
    3. physique                      (proportion lock)
    4. wardrobe + materials
    5. pose + head orientation + expression
    6. scene + lighting
    7. camera
    8. quality terms

The negative prompt is assembled from four sources that must all be present:
identity negatives, physique negatives, content-policy terms, and the
scene-text suppression list.
"""
from __future__ import annotations

from typing import Any, Dict, List

from pipeline.spec import FrameSpec

QUALITY_TERMS = [
    "photorealistic", "photograph", "shot on a full-frame digital camera",
    "natural skin texture with visible pores", "sharp focus on the eyes",
    "realistic colour grading", "fine detail", "high dynamic range",
]

GLOBAL_NEGATIVES = [
    "illustration", "painting", "3d render", "cgi", "anime", "cartoon",
    "plastic skin", "waxy skin", "over-smoothed skin", "blurry", "low quality",
    "jpeg artifacts", "oversaturated", "harsh hdr", "deformed", "disfigured",
    "mutated", "bad anatomy", "extra limbs", "duplicate", "cloned face",
    "asymmetric eyes", "cross-eyed", "lazy eye", "bad hands", "extra fingers",
    "missing fingers", "fused fingers", "malformed feet", "extra toes",
    "clothing melting into skin", "floating limbs", "impossible pose",
    "broken mirror reflection", "incorrect reflection", "duplicated furniture",
]


def _describe_material(catalogue_materials: Dict[str, Any], label: str) -> str:
    m = catalogue_materials.get(label)
    if not m:
        return label
    return f"{label} ({m['drape']}, {m['wrinkling']})"


def _colour_word(colours_by_id: Dict[str, Any], cid: str) -> str:
    c = colours_by_id.get(cid)
    return c["label"] if c else cid.replace("_", " ")


def _head_clause(spec: FrameSpec) -> str:
    h = spec.head
    parts = []
    if h.yaw > 12:
        parts.append(f"head turned {abs(h.yaw):.0f} degrees toward her right")
    elif h.yaw < -12:
        parts.append(f"head turned {abs(h.yaw):.0f} degrees toward her left")
    else:
        parts.append("head squared to camera")

    if h.pitch > 5:
        parts.append("chin slightly raised")
    elif h.pitch < -5:
        parts.append("chin slightly lowered")

    if h.roll >= 4:
        parts.append("head tilted gently toward her right shoulder")
    elif h.roll <= -4:
        parts.append("head tilted gently toward her left shoulder")
    else:
        parts.append("head level, not tilted")

    eye = {
        "camera": "eyes looking directly into the lens",
        "away": "eyes looking away from the camera",
        "away_up": "gaze lifted away from the camera",
        "away_down": "gaze lowered away from the camera",
        "off_camera": "eyes focused off-camera",
        "down": "eyes softly downcast",
    }.get(h.eye_direction, "eyes looking into the lens")
    parts.append(eye)
    return ", ".join(parts)


def _wardrobe_clause(spec: FrameSpec, cat) -> str:
    w = spec.wardrobe
    bits: List[str] = []
    cb = cat.colours_by_id
    mats = cat.materials

    if w.mode == "one_piece" and w.dress:
        d = w.dress
        bits.append(
            f"wearing a {_colour_word(cb, w.colours.get('dress',''))} {d['label']} "
            f"in {_describe_material(mats, d['material'])}, {d['cut']} cut, "
            f"{d['length']} length, {d['neckline']} neckline, {d['sleeve']} sleeves"
        )
    else:
        if w.top:
            t = w.top
            bits.append(
                f"wearing a {_colour_word(cb, w.colours.get('top',''))} {t['label']} "
                f"in {_describe_material(mats, t['material'])}, {t['fit']} fit, "
                f"{t['neckline']} neckline, {t['sleeve']} sleeves"
            )
        if w.bottom:
            b = w.bottom
            bits.append(
                f"with {_colour_word(cb, w.colours.get('bottom',''))} {b['label']} "
                f"in {_describe_material(mats, b['material'])}, {b['cut']} cut, "
                f"{b['waist']} waist"
            )
    if w.outer_layer:
        o = w.outer_layer
        bits.append(f"layered under an open {_colour_word(cb, w.colours.get('outer',''))} {o['label']}")
    if w.footwear and w.footwear["id"] != "barefoot":
        bits.append(f"wearing {w.footwear['label']}")
    elif w.footwear:
        bits.append("barefoot")
    if w.accessories:
        bits.append("accessorised with " + " and ".join(a["label"] for a in w.accessories))
    if w.harmony:
        bits.append(f"outfit colours in a {w.harmony['label']} palette")
    return ", ".join(bits)


def _scene_clause(spec: FrameSpec) -> str:
    s = spec.scene
    l = spec.lighting
    parts = [
        f"in a {s['label']}",
        s.get("palette_description", ""),
        "surfaces: " + ", ".join(s.get("surfaces", [])[:3]),
        f"lit by {l['label']} ({l['quality']} quality, {l['temperature']} temperature, {l['shadow_behaviour']})",
    ]
    return ", ".join(p for p in parts if p)


def _camera_clause(spec: FrameSpec) -> str:
    c = spec.camera
    return (f"{c['focal']['label']} lens at {c['aperture']['label'].split(' —')[0]}, "
            f"{c['shot']['label']}, {c['height']['label']}, {c['angle']['label']}, "
            f"{c['focal']['description']}")


def _pose_clause(spec: FrameSpec) -> str:
    p = spec.pose
    return (f"{p['label']}, shoulders {p['shoulder_rotation']}, spine {p['spine_orientation']}, "
            f"hips {p['hip_orientation']}, {p['legs']}, {spec.hands['label']}")


def build_prompts(spec: FrameSpec, identity: Dict[str, Any], physique: Dict[str, Any],
                  policy: Dict[str, Any], catalogue) -> tuple[str, str]:
    face = identity["face"]
    hair = identity["hair"]
    inv = identity["invariants"]
    ratios = physique["ratios"]
    desc = physique["descriptors"]

    positive: List[str] = []

    # 1. medium + subject
    positive.append(
        f"photorealistic editorial photograph of a single {policy['subject']['age_clause']}, "
        f"{inv['sex_presentation']}, {inv['apparent_age_band']}"
    )

    # 2. face + hair + skin (identity anchor)
    positive.append(
        f"face: {face['geometry']['face_shape']}, {face['geometry']['nose']}, "
        f"{face['geometry']['lips']}, {face['geometry']['jaw']}"
    )
    positive.append(
        f"eyes: {face['eyes']['colour']}, {face['eyes']['shape']}, {face['eyes']['symmetry']}"
    )
    positive.append(f"eyebrows: {face['brows']['shape']}, {face['brows']['colour']}")
    positive.append(
        f"skin: {face['skin']['tone']}, {face['skin']['freckles']}, {face['skin']['texture']}"
    )
    positive.append(
        f"hair: {hair['length']} {hair['base_colour']}, {hair['texture']}, with "
        f"{hair['signature_highlight']['description']} "
        f"({hair['signature_highlight']['placement']}, {hair['signature_highlight']['intensity']})"
    )

    # 3. physique lock
    positive.append(
        f"physique: {desc['frame']}, {desc['shoulders']}, {desc['waist']}, {desc['hips']}, "
        f"{desc['arms']}, {desc['legs']}, shoulder-to-waist ratio approximately "
        f"{ratios['shoulder_to_waist']}, hip-to-waist ratio approximately {ratios['hip_to_waist']}, "
        f"anatomically correct hands with exactly five fingers"
    )

    # 4-7
    positive.append(_wardrobe_clause(spec, catalogue))
    positive.append(_pose_clause(spec))
    positive.append(_head_clause(spec))
    positive.append(f"expression: {spec.expression['label']}")
    positive.append(_scene_clause(spec))
    positive.append(_camera_clause(spec))
    positive.append(", ".join(QUALITY_TERMS))

    # ---- negative --------------------------------------------------------
    negative: List[str] = []
    negative += identity.get("identity_negatives", [])
    negative += physique.get("physique_negatives", [])
    negative += policy.get("explicit_content", {}).get("forbidden_terms", [])
    if policy.get("scene_text", {}).get("suppress_all_text", True):
        negative += policy["scene_text"]["negatives"]
    negative += GLOBAL_NEGATIVES
    # Multi-subject guard — these are solo portraits.
    negative += ["two people", "multiple women", "crowd", "background people"]

    seen, ordered = set(), []
    for n in negative:
        k = n.lower().strip()
        if k not in seen:
            seen.add(k)
            ordered.append(n)

    return ", ".join(p for p in positive if p), ", ".join(ordered)
