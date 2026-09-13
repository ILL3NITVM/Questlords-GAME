"""Build renderer-agnostic positive and negative prompts from a FrameSpec.

DESIGN
------
The prompt is assembled as a list of ``Segment`` objects rather than string
concatenation. Each segment carries a priority tier and an optional
emphasis weight. That structure buys four things string-joining cannot:

1. **Budget awareness.** CLIP encodes 77 tokens per chunk and influence
   drops sharply past chunk 1 (see pipeline/tokens.py). Segments are
   emitted in priority order and, in the tighter quality tiers, trimmed
   from the tail — so what survives is what matters, rather than whatever
   happened to be written first.

2. **Deduplication.** Repeating "photorealistic" or "adult woman" wastes
   the highest-value token positions. Segments are deduplicated on a
   normalised key before assembly.

3. **Parenthesis safety.** In ComfyUI and A1111, ``(text)`` is emphasis
   syntax, not punctuation. Material descriptions such as
   "soft fleece (soft heavy drape, broad rounded folds)" silently became
   unintended emphasis groups, and comma-splitting left unbalanced parens
   that corrupt parsing outright. All literal parentheses are now escaped
   or removed, and parentheses appear only where emphasis is intended.

4. **Grammatical integrity.** Source phrases in config/*.yaml are
   comma-free and self-contained, so joining them cannot produce orphaned
   adjectives with no referent noun.

QUALITY TIERS (``prompt.tier`` in config/studio.yaml)
-----------------------------------------------------
  compact   — fits one CLIP chunk (75 tokens). Maximum per-token influence
              and the strongest identity hold.
  standard  — two chunks. Identity plus full wardrobe, pose and scene.
  full      — no trimming. Everything, accepting chunk-7 dilution.

WHAT COMPACT CAN AND CANNOT PROMISE
-----------------------------------
The protected content alone — the subject/age clause the content policy
requires, four critical identity anchors, and the head-roll instruction
that carries the left-tilt decision — costs roughly 38 of the 75 tokens.
That leaves ~37 for wardrobe, pose, scene, camera, gaze, expression,
physique and quality at 5-10 tokens each, so compact fits about five of
those eight groups, not all of them.

This is arithmetic, not a tuning failure. Compact therefore guarantees
identity, subject and head roll, then spends what remains on whichever
groups matter most for the shot in frame (see SELECTION_ORDER). If you
need identity AND complete scene, wardrobe and camera direction, use
`standard` — that is what the second chunk buys.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pipeline.spec import FrameSpec
from pipeline.tokens import CONTENT_PER_CHUNK, budget, estimate_tokens

# Priority tiers. Lower sorts earlier and is dropped last.
P_SUBJECT = 0      # medium, subject, age — never dropped
P_IDENTITY = 1     # critical identity anchors — never dropped
P_IDENTITY_2 = 2   # important identity anchors
P_PHYSIQUE = 3
P_WARDROBE = 4
P_POSE = 5
P_SCENE = 6
P_CAMERA = 7
P_IDENTITY_3 = 8   # identity detail — sacrificed before wardrobe/pose
P_PHYSIQUE_2 = 9
P_QUALITY = 10

# Per-tier assembly profile.
#
# `quota` caps how many segments each category group may contribute. Without
# it, the compact tier spends its entire 75-token budget on identity and
# emits a prompt with no pose, scene or camera — which is not a photograph
# specification. Balance across groups matters as much as total length.
TIER_PROFILES: Dict[str, Dict[str, Any]] = {
    "compact": {
        "limit": CONTENT_PER_CHUNK,
        # Which groups use their terse phrasing. Identity is the expensive
        # one: "green-hazel eyes with an olive-green outer iris and warm
        # amber flecking near the pupil" is 26 tokens against 5 for
        # "green-hazel eyes", and the extra 21 describe iris detail a
        # diffusion model barely resolves — while costing the scene and
        # the lens entirely. Only the `full` tier can afford it.
        "compact_groups": {"*"},
        # (phrase:1.15) costs ~8 tokens — a tenth of the compact budget per
        # weighted anchor. Emphasis is therefore opt-in here, not default.
        "default_weighting": False,
        "quota": {"subject": 1, "identity": 4, "physique": 1, "wardrobe": 2,
                  "pose": 2, "head": 2, "expression": 1, "scene": 2,
                  "camera": 2, "quality": 1},
    },
    "standard": {
        "limit": CONTENT_PER_CHUNK * 2,
        "compact_groups": {"identity"},
        "default_weighting": True,
        "quota": {"subject": 2, "identity": 6, "physique": 3, "wardrobe": 4,
                  "pose": 4, "head": 4, "expression": 1, "scene": 3,
                  "camera": 3, "quality": 2},
    },
    "full": {
        "limit": None,
        "compact_groups": set(),
        "default_weighting": True,
        "quota": None,
    },
}

TIER_LIMITS = {name: prof["limit"] for name, prof in TIER_PROFILES.items()}


def _group_of(category: str) -> str:
    return category.split(":", 1)[0] if category else "other"


# Order in which groups appear in the finished prompt.
#
# `head` and `expression` are first-class groups, not pose sub-details. In a
# close portrait the gaze direction and the expression are most of the
# photograph; leaving them off this list sorted them to the end and made
# them the first thing trimmed, which is precisely backwards for the frames
# that matter most.
GROUP_ORDER = ["subject", "identity", "physique", "wardrobe", "pose",
               "head", "expression", "scene", "camera", "quality"]


def _group_rank(group: str) -> int:
    """Reading order — how the finished prompt is laid out for a human."""
    return GROUP_ORDER.index(group) if group in GROUP_ORDER else len(GROUP_ORDER)


# SELECTION order, which is a different question from reading order: when
# the budget forces a cut, what should survive? That depends on what the
# frame actually shows. On a close portrait, "rounded hips" describes
# nothing visible while the lens and gaze define the whole image.
SELECTION_ORDER = {
    # On a head-and-shoulders crop the background fills more of the frame
    # than the clothing does, so scene outranks wardrobe here.
    "face": ["subject", "identity", "head", "expression", "camera",
             "scene", "wardrobe", "pose", "physique", "quality"],
    "upper_body": ["subject", "identity", "head", "expression", "wardrobe",
                   "camera", "pose", "scene", "physique", "quality"],
    "body": ["subject", "identity", "physique", "wardrobe", "pose",
             "head", "scene", "camera", "expression", "quality"],
    "environment": ["subject", "identity", "scene", "physique", "wardrobe",
                    "pose", "camera", "head", "expression", "quality"],
    "detail": ["subject", "identity", "wardrobe", "pose", "camera",
               "head", "expression", "scene", "physique", "quality"],
}


def _selection_rank(group: str, emphasis: str) -> int:
    order = SELECTION_ORDER.get(emphasis) or GROUP_ORDER
    return order.index(group) if group in order else len(order)

QUALITY_TERMS = [
    "photorealistic photograph",
    "shot on a full-frame digital camera",
    "sharp focus on the eyes",
    "realistic colour grading",
    "high dynamic range",
]

GLOBAL_NEGATIVES = [
    "illustration", "painting", "3d render", "cgi", "anime", "cartoon",
    "plastic skin", "waxy skin", "over-smoothed skin", "blurry", "low quality",
    "jpeg artifacts", "oversaturated", "deformed", "disfigured", "mutated",
    "bad anatomy", "extra limbs", "duplicate", "cloned face", "asymmetric eyes",
    "bad hands", "extra fingers", "missing fingers", "fused fingers",
    "malformed feet", "clothing melting into skin", "impossible pose",
    "incorrect reflection", "duplicated furniture",
]

# Negative-prompt priority: identity and anatomy failures first, because
# the negative prompt is budget-constrained in exactly the same way.
NEG_TIERS = ("identity", "policy", "anatomy", "text", "global")


# ----------------------------------------------------------------------
@dataclass
class Segment:
    text: str
    priority: int
    weight: float = 1.0
    category: str = ""
    compact_text: Optional[str] = None
    rank: int = 0        # importance WITHIN the group; 0 = most important

    @property
    def key(self) -> str:
        return re.sub(r"[^a-z0-9 ]", "", self.text.lower()).strip()

    @property
    def group(self) -> str:
        return _group_of(self.category)

    def render(self, weighting: bool, compact: bool = False) -> str:
        source = (self.compact_text or self.text) if compact else self.text
        clean = sanitize(source)
        if weighting and abs(self.weight - 1.0) > 0.01:
            return f"({clean}:{self.weight:.2f})"
        return clean


_PAREN_RE = re.compile(r"[()\[\]]")


def sanitize(text: str) -> str:
    """Strip characters that carry syntactic meaning in prompt parsers.

    Parentheses and square brackets are emphasis/de-emphasis syntax in the
    common UIs. A literal parenthesis from a data file is therefore not
    punctuation — it is an instruction, and an unbalanced one corrupts the
    parse. Em-dashes and slashes are normalised too, since both read as
    separators of ambiguous scope.
    """
    out = _PAREN_RE.sub("", text)
    out = out.replace("—", " ").replace("–", " ")
    # Collapse only SPACED slashes ("olive / lime-green"), which read as an
    # ambiguous separator. A tight slash is meaningful notation — f/2.8,
    # three-quarter — and stripping it corrupts the term.
    out = re.sub(r"\s+/\s+", " ", out)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip(" ,;")


def _dig(doc: Dict[str, Any], path: str) -> Optional[str]:
    cur: Any = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur if isinstance(cur, str) else None


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


# ----------------------------------------------------------------------
def _identity_segments(identity: Dict[str, Any], policy: Dict[str, Any], mode: str,
                       trigger: str, class_token: str) -> List[Segment]:
    age_clause = policy["subject"]["age_clause"]
    token = f"{trigger} {class_token}".strip()
    segs: List[Segment] = []

    if mode == "lora_token":
        # The adapter carries identity; a competing description drags the
        # face off-model. Assert only what the adapter cannot: a single
        # adult subject, which content policy requires regardless.
        segs.append(Segment(f"photorealistic editorial photograph of {token}",
                            P_SUBJECT, 1.0, "subject",
                            compact_text=f"photo of {token}"))
        segs.append(Segment(f"a single {age_clause}", P_SUBJECT, 1.0, "age"))
        return segs

    if mode == "hybrid":
        segs.append(Segment(f"photorealistic editorial photograph of {token}",
                            P_SUBJECT, 1.0, "subject",
                            compact_text=f"photo of {token}"))
        segs.append(Segment(f"a single {age_clause}", P_SUBJECT, 1.0, "age"))
        tiers = [("critical", P_IDENTITY)]
    else:
        segs.append(Segment(f"photorealistic editorial photograph of a single {age_clause}",
                            P_SUBJECT, 1.0, "subject",
                            compact_text=f"photo of a single {age_clause}"))
        tiers = [("critical", P_IDENTITY), ("important", P_IDENTITY_2),
                 ("detail", P_IDENTITY_3)]

    prompt_cfg = identity.get("prompt", {})
    emphasis = prompt_cfg.get("emphasis", {}) or {}
    compact_map = prompt_cfg.get("compact", {}) or {}
    rank = 0
    for tier_name, priority in tiers:
        for path in prompt_cfg.get(tier_name, []) or []:
            phrase = _dig(identity, path)
            if phrase:
                segs.append(Segment(phrase, priority,
                                    float(emphasis.get(path, 1.0)), f"identity:{tier_name}",
                                    compact_text=compact_map.get(path), rank=rank))
                rank += 1
    return segs


def _physique_segments(physique: Dict[str, Any], mode: str) -> List[Segment]:
    """The physique lock survives every identity mode — a face adapter
    carries no body proportions, so dropping it would be a real hole."""
    prompt_cfg = physique.get("prompt", {})
    compact_map = prompt_cfg.get("compact", {}) or {}
    segs: List[Segment] = []
    rank = 0
    for tier_name, priority in (("critical", P_PHYSIQUE), ("important", P_PHYSIQUE),
                                ("detail", P_PHYSIQUE_2)):
        for path in prompt_cfg.get(tier_name, []) or []:
            phrase = _dig(physique, path)
            if phrase:
                segs.append(Segment(phrase, priority, 1.0, f"physique:{tier_name}",
                                    compact_text=compact_map.get(path), rank=rank))
                rank += 1
    if prompt_cfg.get("include_ratios", True):
        r = physique["ratios"]
        segs.append(Segment(
            f"shoulder-to-waist ratio about {r['shoulder_to_waist']} and "
            f"hip-to-waist ratio about {r['hip_to_waist']}", P_PHYSIQUE_2, 1.0,
            "physique:ratios", rank=rank + 2))
    # Hands are rank 1: the single most common anatomy failure, so it earns
    # a place well before decorative physique detail.
    segs.append(Segment("anatomically correct hands with exactly five fingers",
                        P_PHYSIQUE, 1.0, "physique:hands", rank=1))
    return segs


def _wardrobe_segments(spec: FrameSpec, cat) -> List[Segment]:
    w = spec.wardrobe
    cb = cat.colours_by_id
    mats = cat.materials
    segs: List[Segment] = []

    def colour(slot: str, garment: Optional[Dict[str, Any]] = None) -> str:
        """Empty when the garment's own label already names the colour.

        Observed garments are catalogued as "cream ribbed crop tank" — the
        colour is part of the name. Prefixing it again yields "cream cream
        ribbed crop tank", which wastes tokens and reads as an error.
        """
        cid = w.colours.get(slot, "")
        c = cb.get(cid)
        label = c["label"] if c else ""
        if not label:
            return ""
        if garment and label.lower() in (garment.get("label", "") or "").lower():
            return ""
        return label

    def material_phrase(label: str) -> str:
        m = mats.get(label)
        # One behaviour cue, not three — drape is the most visually decisive.
        # Drape values in data/materials carry their own connective ("that
        # hugs...", "with a liquid drape") so this joins cleanly.
        return f"{label} {m['drape']}" if m else label

    if w.mode == "one_piece" and w.dress:
        d = w.dress
        segs.append(Segment(
            f"wearing {_article(colour('dress', d) or d['label'])} "
            f"{(colour('dress', d) + ' ').lstrip()}{d['label']} "
            f"in {material_phrase(d['material'])}", P_WARDROBE, 1.0, "wardrobe:dress",
            compact_text=f"wearing {_article(colour('dress', d) or d['label'])} "
                         f"{(colour('dress', d) + ' ').lstrip()}{d['label']}",
            rank=0))
        neckline = d.get("neckline")
        if neckline:
            segs.append(Segment(
                f"{d.get('length', 'midi')} length with {_article(neckline)} "
                f"{neckline} neckline", P_WARDROBE, 1.0, "wardrobe:cut", rank=2))
    else:
        if w.top:
            t = w.top
            segs.append(Segment(
                f"wearing {_article(colour('top', t) or t['label'])} "
                f"{(colour('top', t) + ' ').lstrip()}{t['label']} "
                f"in {material_phrase(t['material'])}", P_WARDROBE, 1.0, "wardrobe:top",
                compact_text=f"wearing {_article(colour('top', t) or t['label'])} "
                             f"{(colour('top', t) + ' ').lstrip()}{t['label']}",
                rank=0))
        if w.bottom:
            b = w.bottom
            segs.append(Segment(
                f"with {(colour('bottom', b) + ' ').lstrip()}{b['label']} "
                f"in {material_phrase(b['material'])}",
                P_WARDROBE, 1.0, "wardrobe:bottom",
                compact_text=f"with {(colour('bottom', b) + ' ').lstrip()}{b['label']}",
                rank=1))
    if w.outer_layer:
        segs.append(Segment(f"layered under an open "
                            f"{(colour('outer', w.outer_layer) + ' ').lstrip()}"
                            f"{w.outer_layer['label']}",
                            P_WARDROBE, 1.0, "wardrobe:outer", rank=2))
    if w.footwear:
        segs.append(Segment("barefoot" if w.footwear["id"] == "barefoot"
                            else f"wearing {w.footwear['label']}",
                            P_WARDROBE, 1.0, "wardrobe:footwear", rank=3))
    for i, a in enumerate(w.accessories):
        segs.append(Segment(f"wearing {a['label']}", P_WARDROBE, 1.0,
                            "wardrobe:accessory", rank=4 + i))
    return segs


def _pose_segments(spec: FrameSpec) -> List[Segment]:
    p = spec.pose
    h = spec.head
    segs = [
        Segment(p["label"], P_POSE, 1.0, "pose", rank=0),
        Segment(f"{p['legs']}", P_POSE, 1.0, "pose:legs", rank=4),
        Segment(spec.hands["label"], P_POSE, 1.0, "pose:hands", rank=3),
    ]

    if h.yaw > 12:
        segs.append(Segment(f"head turned {abs(h.yaw):.0f} degrees toward her right",
                            P_POSE, 1.0, "head:yaw", rank=2))
    elif h.yaw < -12:
        segs.append(Segment(f"head turned {abs(h.yaw):.0f} degrees toward her left",
                            P_POSE, 1.0, "head:yaw", rank=2))
    else:
        segs.append(Segment("head squared to camera", P_POSE, 1.0, "head:yaw", rank=2))

    if h.pitch > 5:
        segs.append(Segment("chin slightly raised", P_POSE, 1.0, "head:pitch", rank=3))
    elif h.pitch < -5:
        segs.append(Segment("chin slightly lowered", P_POSE, 1.0, "head:pitch", rank=3))

    if h.roll >= 4:
        segs.append(Segment("head tilted gently toward her right shoulder",
                            P_POSE, 1.0, "head:roll", rank=1))
    elif h.roll <= -4:
        segs.append(Segment("head tilted gently toward her left shoulder",
                            P_POSE, 1.0, "head:roll", rank=1))
    else:
        segs.append(Segment("head level and not tilted", P_POSE, 1.0, "head:roll", rank=1))

    eye = {
        "camera": "eyes looking directly into the lens",
        "away": "eyes looking away from the camera",
        "away_up": "gaze lifted away from the camera",
        "away_down": "gaze lowered away from the camera",
        "off_camera": "eyes focused off-camera",
        "down": "eyes softly downcast",
    }.get(h.eye_direction, "eyes looking into the lens")
    segs.append(Segment(eye, P_POSE, 1.0, "head:eyes", rank=0))
    # Some expression labels already end in the word ("slightly distant
    # expression"), so appending it unconditionally yields a stutter.
    expr = spec.expression["label"]
    if "expression" not in expr.lower():
        expr = f"{expr} expression"
    segs.append(Segment(expr, P_POSE, 1.0, "expression", rank=0))
    return segs


def _scene_segments(spec: FrameSpec) -> List[Segment]:
    s, l = spec.scene, spec.lighting
    label = s["label"]
    return [
        Segment(f"in {_article(label)} {label}", P_SCENE, 1.0, "scene", rank=0),
        Segment(f"lit by {l['label']}", P_SCENE, 1.0, "lighting", rank=1),
        Segment(s.get("palette_description", ""), P_SCENE, 1.0, "scene:palette", rank=2),
        Segment(l["shadow_behaviour"], P_SCENE, 1.0, "lighting:shadow", rank=3),
    ]


def _camera_segments(spec: FrameSpec) -> List[Segment]:
    c = spec.camera
    aperture = c["aperture"]["label"].split(" ")[0]
    return [
        Segment(c["shot"]["label"], P_CAMERA, 1.0, "camera:shot", rank=0),
        Segment(f"{c['focal']['label']} lens at {aperture}", P_CAMERA, 1.0,
                "camera:focal", rank=1),
        Segment(c["height"]["label"], P_CAMERA, 1.0, "camera:height", rank=2),
        Segment(c["angle"]["label"], P_CAMERA, 1.0, "camera:angle", rank=3),
    ]


# ----------------------------------------------------------------------
def _dedupe(segments: Sequence[Segment]) -> List[Segment]:
    """Drop repeated content, keeping the highest-priority occurrence.

    Also drops a segment whose text is fully contained in an already-kept
    segment — "photorealistic" after "photorealistic photograph" buys
    nothing but costs a token in a budget that is already tight.
    """
    ordered = sorted(segments, key=lambda s: (s.priority,))
    kept: List[Segment] = []
    seen_keys: set = set()
    for seg in ordered:
        k = seg.key
        if not k or k in seen_keys:
            continue
        if any(k in prior.key for prior in kept):
            continue
        seen_keys.add(k)
        kept.append(seg)
    return kept


def _shot_adjusted_quota(quota: Optional[Dict[str, int]],
                         emphasis: str) -> Optional[Dict[str, int]]:
    """Spend the token budget on what is actually in frame.

    A close portrait shows no hips, so "rounded hips balanced with the
    shoulder line" is spent describing pixels that do not exist — while the
    gaze, expression and lens that DO define the frame get trimmed for lack
    of room. Conversely an environmental full body barely resolves an iris,
    so facial detail earns less and the scene earns more.
    """
    if quota is None:
        return None
    q = dict(quota)
    if emphasis == "face":
        q["physique"] = 1
        q["wardrobe"] = max(1, q.get("wardrobe", 2) - 1)
        q["head"] = q.get("head", 2) + 2
        q["camera"] = q.get("camera", 2) + 1
        q["expression"] = max(1, q.get("expression", 1))
    elif emphasis in ("body", "environment"):
        q["physique"] = q.get("physique", 3) + 1
        q["identity"] = max(2, q.get("identity", 6) - 1)
        if emphasis == "environment":
            q["scene"] = q.get("scene", 3) + 1
    return q


def _assemble(segments: Sequence[Segment], tier: str, weighting: bool,
              shot_emphasis: str = "") -> Tuple[str, Dict[str, Any]]:
    profile = TIER_PROFILES.get(tier, TIER_PROFILES["standard"])
    limit = profile["limit"]
    quota = _shot_adjusted_quota(profile["quota"], shot_emphasis)
    compact_groups = profile.get("compact_groups", set())

    def _is_compact(seg: Segment) -> bool:
        return "*" in compact_groups or seg.group in compact_groups
    # Round-robin by rank, then by group. This takes the single most
    # important segment of EVERY group before the second of any, so a tight
    # budget yields a balanced prompt (subject + identity + outfit + pose +
    # scene + lens) rather than a deep one that spends everything on
    # identity and emits no photograph at all.
    ordered = sorted(_dedupe(segments),
                     key=lambda s: (s.rank, _selection_rank(s.group, shot_emphasis),
                                    s.priority))

    kept: List[Segment] = []
    dropped: List[Segment] = []
    used = 0
    per_group: Dict[str, int] = {}
    for seg in ordered:
        group = seg.group
        rendered = seg.render(weighting, _is_compact(seg))
        cost = estimate_tokens(rendered) + 1
        # The subject line and EVERY critical identity anchor are protected
        # from both quota and budget. A prompt that drops Octavia's eye
        # colour or her signature highlights to satisfy a token cap has
        # failed at the one job this system exists to do — and in the
        # compact register those anchors cost ~12 tokens in total, so the
        # guarantee is cheap. Everything else competes.
        # head:roll is protected for the same reason as critical identity.
        # The left-tilt budget in pipeline/sampler.py decides Octavia's head
        # roll, but that decision only reaches the renderer through this
        # clause. Trim it and the model reverts to its own preferred tilt,
        # which is exactly the signature the system exists to suppress —
        # and the manifest would still record the roll we *asked* for.
        # Five tokens is a cheap price for the guarantee.
        protected = (seg.priority <= P_SUBJECT
                     or seg.category in ("identity:critical", "head:roll"))
        over_quota = (quota is not None
                      and per_group.get(group, 0) >= quota.get(group, 99))
        over_budget = limit is not None and used + cost > limit
        if protected or (not over_quota and not over_budget):
            kept.append(seg)
            used += cost
            per_group[group] = per_group.get(group, 0) + 1
        else:
            dropped.append(seg)

    def _join(sel: List[Segment]) -> str:
        # Selection order is round-robin; READING order should be
        # conventional, so re-sort survivors by group before joining.
        ordered_out = sorted(sel, key=lambda s: (_group_rank(s.group), s.rank, s.priority))
        return ", ".join(s.render(weighting, _is_compact(s)) for s in ordered_out)

    text = _join(kept)

    # Per-segment accounting drifts slightly from the joined string, so a
    # tier can overshoot the chunk boundary it promises. Verify against the
    # real assembled text and trim the least important droppable segment
    # until it genuinely fits. A tier that claims one chunk must deliver one
    # chunk, or the budgeting is decoration.
    if limit is not None:
        guard = 0
        while budget(text).tokens > limit and guard < 64:
            droppable = [x for x in kept
                         if not (x.priority <= P_SUBJECT
                                 or x.category in ("identity:critical", "head:roll"))]
            if not droppable:
                break
            victim = max(droppable,
                         key=lambda s: (s.rank, _selection_rank(s.group, shot_emphasis),
                                        s.priority))
            kept.remove(victim)
            dropped.append(victim)
            text = _join(kept)
            guard += 1
    meta = {
        "tier": tier,
        "weighting": weighting,
        "segments_kept": len(kept),
        "segments_dropped": len(dropped),
        "dropped_categories": sorted({s.category for s in dropped}),
        "groups_present": sorted({s.group for s in kept}),
        "budget": budget(text).to_dict(),
    }
    return text, meta


def _build_negative(identity: Dict[str, Any], physique: Dict[str, Any],
                    policy: Dict[str, Any], tier: str) -> Tuple[str, Dict[str, Any]]:
    groups = {
        "identity": list(identity.get("identity_negatives", [])),
        "anatomy": list(physique.get("physique_negatives", [])),
        "text": list(policy.get("scene_text", {}).get("negatives", []))
        if policy.get("scene_text", {}).get("suppress_all_text", True) else [],
        # Solo-subject enforcement sits in the protected policy group, not
        # the best-effort global list. A second person in frame is not a
        # quality nit — it breaks the photograph and the content policy.
        "policy": list(policy.get("explicit_content", {}).get("forbidden_terms", []))
        + ["two people", "multiple women", "crowd", "background people"],
        "global": GLOBAL_NEGATIVES,
    }
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["standard"])
    if limit is not None:
        limit = limit * 2      # negatives tolerate more chunks than positives

    seen: set = set()
    kept: List[str] = []
    dropped = 0
    used = 0
    for group in NEG_TIERS:
        for term in groups.get(group, []):
            clean = sanitize(term)
            k = clean.lower()
            if not k or k in seen:
                continue
            seen.add(k)
            cost = estimate_tokens(clean) + 1
            # Policy and identity negatives are never dropped.
            protected = group in ("identity", "policy")
            if limit is None or protected or used + cost <= limit:
                kept.append(clean)
                used += cost
            else:
                dropped += 1
    text = ", ".join(kept)
    return text, {"terms": len(kept), "dropped": dropped, "budget": budget(text).to_dict()}


# ----------------------------------------------------------------------
def build_segments(spec: FrameSpec, identity: Dict[str, Any], physique: Dict[str, Any],
                   policy: Dict[str, Any], catalogue,
                   identity_cfg: Optional[Dict[str, Any]] = None) -> List[Segment]:
    identity_cfg = identity_cfg or {}
    mode = identity_cfg.get("mode", "descriptive")
    trigger = identity_cfg.get("trigger_token", "")
    class_token = identity_cfg.get("class_token", "")
    if mode in ("lora_token", "hybrid") and not trigger:
        raise ValueError(
            f"identity.mode is {mode!r} but no identity.trigger_token is configured. "
            "Without the trigger token the adapter is never invoked and every frame "
            "would render a generic person."
        )

    segs: List[Segment] = []
    segs += _identity_segments(identity, policy, mode, trigger, class_token)
    segs += _physique_segments(physique, mode)
    segs += _wardrobe_segments(spec, catalogue)
    segs += _pose_segments(spec)
    segs += _scene_segments(spec)
    segs += _camera_segments(spec)
    segs += [Segment(q, P_QUALITY, 1.0, "quality", rank=i)
             for i, q in enumerate(QUALITY_TERMS)]
    return [s for s in segs if s.text and s.text.strip()]


def build_prompts(spec: FrameSpec, identity: Dict[str, Any], physique: Dict[str, Any],
                  policy: Dict[str, Any], catalogue,
                  identity_cfg: Optional[Dict[str, Any]] = None,
                  prompt_cfg: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    positive, negative, _ = build_prompts_verbose(
        spec, identity, physique, policy, catalogue, identity_cfg, prompt_cfg)
    return positive, negative


def build_prompts_verbose(spec: FrameSpec, identity: Dict[str, Any],
                          physique: Dict[str, Any], policy: Dict[str, Any], catalogue,
                          identity_cfg: Optional[Dict[str, Any]] = None,
                          prompt_cfg: Optional[Dict[str, Any]] = None
                          ) -> Tuple[str, str, Dict[str, Any]]:
    """Same as ``build_prompts`` but also returns assembly diagnostics."""
    prompt_cfg = prompt_cfg or {}
    tier = prompt_cfg.get("tier", "standard")
    profile = TIER_PROFILES.get(tier, TIER_PROFILES["standard"])
    weighting = bool(prompt_cfg.get("weighting", profile.get("default_weighting", False)))

    segments = build_segments(spec, identity, physique, policy, catalogue, identity_cfg)
    emphasis = (spec.camera.get("shot", {}) or {}).get("emphasis", "")
    positive, pos_meta = _assemble(segments, tier, weighting, emphasis)
    pos_meta["shot_emphasis"] = emphasis
    negative, neg_meta = _build_negative(identity, physique, policy, tier)
    return positive, negative, {"positive": pos_meta, "negative": neg_meta}
