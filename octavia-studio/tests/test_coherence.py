"""Physical and photographic plausibility of a composed frame."""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.compose import BASE_LAYER_ONLY, Composer
from pipeline.history import DiversityHistory
from pipeline.sampler import Catalogue, Sampler
from pipeline.seeds import seed_record

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())
POL = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())


def _specs(count=80, seed=0):
    cat = Catalogue()
    hist = DiversityHistory(window=24)
    smp = Sampler(cat, hist, CFG, planned_total=count, diversity="high")
    comp = Composer(cat, smp, CFG, POL)
    out = []
    for i in range(count):
        s = comp.compose("C", i, seed_record(seed, "C", i))
        keys = s.category_keys()
        keys["tilt_class"] = s.head.tilt_class
        hist.record(keys, accepted=True)
        out.append(s)
    return out


def test_pose_furniture_requirements_are_satisfied():
    """A 'leaning on a sofa' pose must not be placed in a room with no sofa."""
    for s in _specs():
        needs = s.pose.get("requires_furniture", [])
        if not needs:
            continue
        affordances = " ".join(s.scene["furniture_affordances"] + s.scene["surfaces"]).lower()
        assert any(n.lower() in affordances for n in needs), \
            f"pose {s.pose['id']} needs {needs}, scene {s.scene['id']} offers none"


def test_shot_and_focal_length_agree():
    for s in _specs():
        assert s.camera["shot"]["id"] in s.camera["focal"]["suitable_shots"], \
            f"{s.camera['shot']['id']} is not suitable for {s.camera['focal']['id']}"


def test_hands_suit_the_posture():
    for s in _specs():
        assert s.pose["posture"] in s.hands["compatible_postures"], \
            f"hands {s.hands['id']} incompatible with posture {s.pose['posture']}"


def test_base_layer_garments_never_worn_alone():
    """Content policy: camisoles and bralettes are layering pieces only."""
    for s in _specs():
        if s.wardrobe.top:
            assert s.wardrobe.top["subtype"] not in BASE_LAYER_ONLY


def test_outfit_is_either_separates_or_a_dress():
    for s in _specs():
        w = s.wardrobe
        if w.mode == "one_piece":
            assert w.dress is not None and w.top is None and w.bottom is None
        else:
            assert w.dress is None and w.top is not None and w.bottom is not None


def test_outfit_colours_come_from_one_harmony():
    for s in _specs():
        allowed = set(s.wardrobe.harmony["colours"])
        for slot, colour in s.wardrobe.colours.items():
            assert colour in allowed, f"{slot} colour {colour} outside harmony"


def test_barefoot_only_indoors():
    for s in _specs():
        if s.wardrobe.footwear and s.wardrobe.footwear["id"] in ("barefoot", "socks"):
            assert s.scene["indoor"], f"{s.wardrobe.footwear['id']} outdoors in {s.scene['id']}"


def test_pendant_requires_an_open_neckline():
    for s in _specs():
        ids = {a["id"] for a in s.wardrobe.accessories}
        if "purple_crystal_pendant" in ids or "fine_gold_chain" in ids:
            garment = s.wardrobe.dress or s.wardrobe.top
            assert garment["neckline"] in (
                "v", "scoop", "square", "sweetheart", "halter", "off_shoulder", "boat", "open")


def test_no_duplicate_accessory_slots():
    for s in _specs():
        slots = [a["slot"] for a in s.wardrobe.accessories]
        assert len(slots) == len(set(slots)), "two accessories in the same slot"


def test_seated_poses_do_not_use_standing_full_body_framing():
    for s in _specs():
        if s.pose["posture"] in ("seated", "floor", "reclined"):
            assert s.camera["shot"]["id"] != "full_body"
