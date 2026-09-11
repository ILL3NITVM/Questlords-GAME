"""Compose a complete FrameSpec from a SeedRecord.

Coherence rules enforced here (these are what stop the output reading as
random noun soup):

* A pose that needs furniture is only chosen if the scene actually offers it.
* Shot type and focal length must be mutually suitable.
* Outfit colours are drawn from one harmony so separates agree.
* Base-layer-only garments (camisole, bralette) never appear unlayered.
* Hand placement must suit the pose's posture.
* Head yaw is constrained when the shot is a clean profile or over-shoulder.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from pipeline.history import DiversityHistory
from pipeline.sampler import Catalogue, Sampler
from pipeline.seeds import rng_for
from pipeline.spec import FrameSpec, HeadPose, SeedRecord, WardrobeSelection

# Garments that may never be the outermost layer on the torso.
BASE_LAYER_ONLY = {"camisole", "bralette", "sports bra", "satin_camisole"}


def _jitter(rng: random.Random, rng_range: List[float]) -> float:
    lo, hi = float(rng_range[0]), float(rng_range[1])
    return round(rng.uniform(lo, hi), 1)


class Composer:
    def __init__(self, catalogue: Catalogue, sampler: Sampler, config: Dict[str, Any],
                 policy: Dict[str, Any]) -> None:
        self.cat = catalogue
        self.sampler = sampler
        self.config = config
        self.policy = policy

    # ------------------------------------------------------------------
    def compose(self, run_id: str, index: int, seeds: SeedRecord,
                campaign: str = "wardrobe") -> FrameSpec:
        frame_id = f"{run_id}_{index:03d}"
        spec = FrameSpec(run_id=run_id, index=index, frame_id=frame_id,
                         campaign=campaign, seeds=seeds)

        # --- scene first: it constrains pose (furniture) and lighting -----
        scene = self._pick_scene(seeds, campaign)
        spec.scene = scene
        spec.lighting = self._pick_lighting(seeds, scene)

        # --- pose, constrained by what the scene can physically support ---
        pose = self._pick_pose(seeds, scene)
        spec.pose = pose
        spec.hands = self._pick_hands(seeds, pose)

        # --- head + expression -------------------------------------------
        head_rng = rng_for(seeds.pose_seed ^ 0x5EED)
        hp = self.sampler.pick_head_position(head_rng)
        spec.head = HeadPose(
            position_id=hp["id"],
            yaw=_jitter(head_rng, hp["yaw_range"]),
            pitch=_jitter(head_rng, hp["pitch_range"]),
            roll=_jitter(head_rng, hp["roll_range"]),
            tilt_class=hp["tilt_class"],
            eye_direction=hp["eye_direction"],
        )
        spec.expression = self.sampler.pick(
            rng_for(seeds.expression_seed), "expression", self.cat.expressions)

        # --- camera, constrained by pose and head -------------------------
        spec.camera = self._pick_camera(seeds, pose, spec.head)

        # --- wardrobe -----------------------------------------------------
        spec.wardrobe = self._pick_wardrobe(seeds, scene, pose)

        out = self.config.get("output", {})
        spec.width = int(out.get("width", 896))
        spec.height = int(out.get("height", 1152))
        return spec

    # ------------------------------------------------------------------
    def _pick_scene(self, seeds: SeedRecord, campaign: str) -> Dict[str, Any]:
        rng = rng_for(seeds.scene_seed)
        pool = self.cat.scenes
        if campaign == "outdoor":
            pool = [s for s in pool if not s["indoor"]] or pool
        elif campaign == "studio":
            pool = [s for s in pool if s["family"] in
                    ("minimal_studio", "fashion_studio", "gallery")] or pool
        scene = self.sampler.pick(rng, "scene_id", pool,
                                  implies={"scene_family": "family",
                                           "env_palette": "env_palette"})
        # Independently vary the palette-consistent lighting per visit, so the
        # same room does not always look identical.
        return dict(scene)

    def _pick_lighting(self, seeds: SeedRecord, scene: Dict[str, Any]) -> Dict[str, Any]:
        rng = rng_for(seeds.lighting_seed)
        allowed = set(scene.get("lighting_options", []))
        # Map the scene's freeform lighting hints onto the lighting catalogue.
        def suits(l: Dict[str, Any]) -> bool:
            if not allowed:
                return True
            label = l["label"].lower()
            return any(any(tok in label for tok in hint.lower().split())
                       for hint in allowed)
        pool = [l for l in self.cat.lighting if suits(l)]
        if not pool:
            pool = [l for l in self.cat.lighting
                    if (l["kind"] == "natural") == bool(scene.get("indoor", True)) or True]
        return self.sampler.pick(rng, "lighting", pool)

    # ------------------------------------------------------------------
    def _pick_pose(self, seeds: SeedRecord, scene: Dict[str, Any]) -> Dict[str, Any]:
        rng = rng_for(seeds.pose_seed)
        affordances = " ".join(scene.get("furniture_affordances", []) +
                               scene.get("surfaces", [])).lower()

        def supported(p: Dict[str, Any]) -> bool:
            needs = p.get("requires_furniture", [])
            if not needs:
                return True
            return any(n.lower() in affordances for n in needs)

        return self.sampler.pick(rng, "pose_id", self.cat.poses, predicate=supported,
                                 implies={"pose_family": "family"})

    def _pick_hands(self, seeds: SeedRecord, pose: Dict[str, Any]) -> Dict[str, Any]:
        rng = rng_for(seeds.pose_seed ^ 0xA11D)
        posture = pose.get("posture", "standing")

        def suits(h: Dict[str, Any]) -> bool:
            return posture in h.get("compatible_postures", [])

        return self.sampler.pick(rng, "hands", self.cat.hands, predicate=suits)

    # ------------------------------------------------------------------
    def _pick_camera(self, seeds: SeedRecord, pose: Dict[str, Any],
                     head: HeadPose) -> Dict[str, Any]:
        rng = rng_for(seeds.camera_seed)
        posture = pose.get("posture", "standing")

        shot = self.sampler.pick(rng, "camera_shot", self.cat.shots)
        # Seated postures should not claim a standing full-body framing.
        if posture in ("seated", "floor", "reclined") and shot["id"] == "full_body":
            shot = next(s for s in self.cat.shots if s["id"] == "seated_full")
        if pose.get("family") == "mirror_selfie":
            shot = next(s for s in self.cat.shots if s["id"] == "mirror_selfie")

        focal_pool = [f for f in self.cat.focal if shot["id"] in f["suitable_shots"]]
        if not focal_pool:
            focal_pool = self.cat.focal
        focal = self.sampler.pick(rng, "camera_focal", focal_pool)

        height = self.sampler.pick(rng, "camera_height", self.cat.heights)
        if posture in ("seated", "floor") and height["id"] in ("low_floor",):
            height = next(h for h in self.cat.heights if h["id"] == "eye_level")

        angle = self.sampler.pick(rng, "camera_angle", self.cat.angles)
        # A clean profile head pose reads wrong from a square frontal camera.
        if abs(head.yaw) > 65 and angle["id"] == "frontal":
            angle = next(a for a in self.cat.angles if a["id"] == "side")

        aperture = self.sampler.pick(rng, "camera_aperture", self.cat.apertures)
        if shot["id"] == "environmental_full_body" and aperture["id"] in ("f1.8", "f2.8"):
            aperture = next(a for a in self.cat.apertures if a["id"] == "f4")

        return {"shot": shot, "focal": focal, "height": height,
                "angle": angle, "aperture": aperture}

    # ------------------------------------------------------------------
    def _pick_wardrobe(self, seeds: SeedRecord, scene: Dict[str, Any],
                       pose: Dict[str, Any]) -> WardrobeSelection:
        rng = rng_for(seeds.wardrobe_seed)
        crng = rng_for(seeds.colour_seed)
        sel = WardrobeSelection()

        scene_moods = set(scene.get("mood", []))
        indoor = bool(scene.get("indoor", True))

        harmony = self.sampler.pick(crng, "colour_family", self.cat.harmonies)
        sel.harmony = harmony
        palette = [self.cat.colours_by_id[c] for c in harmony["colours"]
                   if c in self.cat.colours_by_id]

        def pick_colour(exclude: Optional[set] = None) -> str:
            pool = [c for c in palette if not exclude or c["id"] not in exclude] or palette
            weights = [self.sampler.weight_for("colour", c["id"], float(c.get("weight", 1.0)))
                       for c in pool]
            from pipeline.sampler import weighted_choice
            return weighted_choice(crng, pool, weights)["id"]

        # one-piece vs separates
        one_piece = rng.random() < 0.28
        if one_piece:
            def dress_ok(d: Dict[str, Any]) -> bool:
                return bool(set(d.get("mood", [])) & scene_moods) or not scene_moods
            dress = self.sampler.pick(rng, "wardrobe_dress", self.cat.dresses,
                                      predicate=dress_ok)
            sel.mode = "one_piece"
            sel.dress = dress
            sel.colours["dress"] = pick_colour()
            sel.families = [dress["subtype"]]
        else:
            def top_ok(t: Dict[str, Any]) -> bool:
                if t["subtype"] in BASE_LAYER_ONLY:
                    return False
                return True
            top = self.sampler.pick(rng, "wardrobe_top", self.cat.tops, predicate=top_ok,
                                    implies={"wardrobe_subtype": "subtype"})
            top_compat = set(top.get("compatibility_tags", []))

            def bottom_ok(b: Dict[str, Any]) -> bool:
                tags = set(b.get("compatibility_tags", []))
                if "cropped_top" in tags and top.get("length") not in ("cropped", "waist"):
                    return False
                if "skirt_friendly" in top_compat and "skirt_friendly" in tags:
                    return True
                if "tailored_bottom" in top_compat and "tailored_bottom" in tags:
                    return True
                if "slim_bottom" in top_compat and b["cut"] in ("fitted", "straight", "column"):
                    return True
                if "leggings_friendly" in top_compat and b["id"] == "leggings":
                    return True
                return "layerable" in top_compat or not top_compat & {
                    "skirt_friendly", "tailored_bottom", "slim_bottom", "leggings_friendly"}

            bottom = self.sampler.pick(rng, "wardrobe_bottom", self.cat.bottoms,
                                       predicate=bottom_ok,
                                       implies={"wardrobe_subtype": "subtype"})
            sel.top, sel.bottom = top, bottom
            sel.colours["top"] = pick_colour()
            sel.colours["bottom"] = pick_colour(exclude={sel.colours["top"]})
            sel.families = [top["subtype"], bottom["subtype"]]

            # optional outer layer
            if rng.random() < 0.30:
                outers = [t for t in self.cat.tops
                          if "layer_over" in t.get("compatibility_tags", [])
                          and t["id"] != top["id"]]
                if outers:
                    outer = self.sampler.pick(rng, "wardrobe_outer", outers)
                    sel.outer_layer = outer
                    sel.colours["outer"] = pick_colour()
                    sel.families.append(outer["subtype"])

        # footwear — barefoot only makes sense indoors
        def shoe_ok(s: Dict[str, Any]) -> bool:
            tags = s.get("compatibility_tags", [])
            if not indoor and ("indoor_only" in tags):
                return False
            return True

        sel.footwear = self.sampler.pick(rng, "footwear", self.cat.footwear, predicate=shoe_ok)

        # accessories — the pendant needs an open neckline
        neckline = ""
        if sel.dress:
            neckline = sel.dress.get("neckline", "")
        elif sel.top:
            neckline = sel.top.get("neckline", "")
        open_neck = neckline in ("v", "scoop", "square", "sweetheart", "halter",
                                 "off_shoulder", "boat", "open")

        def acc_ok(a: Dict[str, Any]) -> bool:
            tags = a.get("compatibility_tags", [])
            if "open_neckline" in tags and not open_neck:
                return False
            if "outdoor_ok" in tags and indoor:
                return False
            return True

        n_acc = rng.choices([0, 1, 2], weights=[0.18, 0.52, 0.30])[0]
        chosen: List[Dict[str, Any]] = []
        used_slots = set()
        for _ in range(n_acc):
            a = self.sampler.pick(rng, "accessory", self.cat.accessories, predicate=acc_ok)
            if a["id"] == "none" or a["slot"] in used_slots:
                continue
            used_slots.add(a["slot"])
            chosen.append(a)
        sel.accessories = chosen
        return sel
