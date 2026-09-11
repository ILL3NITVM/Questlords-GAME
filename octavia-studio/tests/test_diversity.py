"""Anti-collapse behaviour (section 10)."""
import pathlib
import sys
from collections import Counter

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.compose import Composer
from pipeline.history import DiversityHistory
from pipeline.sampler import Catalogue, Sampler
from pipeline.seeds import seed_record

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())
POL = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())


def _campaign(count=64, seed=0, diversity="high"):
    cat = Catalogue()
    hist = DiversityHistory(window=int(CFG["diversity"]["history_window"]))
    smp = Sampler(cat, hist, CFG, planned_total=count, diversity=diversity)
    comp = Composer(cat, smp, CFG, POL)
    specs = []
    for i in range(count):
        s = comp.compose("D", i, seed_record(seed, "D", i))
        keys = s.category_keys()
        keys["tilt_class"] = s.head.tilt_class
        hist.record(keys, accepted=True)
        specs.append(s)
    return specs, hist


def test_share_caps_are_respected():
    caps = CFG["diversity"]["max_family_share"]
    failures = []
    for seed in (0, 1, 2, 3, 4):
        specs, _ = _campaign(64, seed)
        for axis, cap in caps.items():
            counter = Counter(s.category_keys().get(axis, "") for s in specs)
            counter.pop("", None)
            if not counter:
                continue
            value, n = counter.most_common(1)[0]
            share = n / sum(counter.values())
            if share > cap + 0.02:   # small tolerance for integer rounding
                failures.append((seed, axis, value, round(share, 3), cap))
    assert not failures, f"share caps exceeded: {failures}"


def test_no_immediate_scene_repetition():
    """The sliding window should stop the same room appearing back to back."""
    specs, _ = _campaign(64, 5)
    ids = [s.scene["id"] for s in specs]
    runs = sum(1 for a, b in zip(ids, ids[1:]) if a == b)
    assert runs == 0, f"{runs} consecutive identical scenes"


def test_no_immediate_pose_repetition():
    specs, _ = _campaign(64, 5)
    ids = [s.pose["id"] for s in specs]
    runs = sum(1 for a, b in zip(ids, ids[1:]) if a == b)
    assert runs == 0, f"{runs} consecutive identical poses"


def test_scene_variety_is_broad():
    specs, _ = _campaign(64, 11)
    assert len({s.scene["id"] for s in specs}) >= 18


def test_environment_palettes_are_varied():
    """Section 5: do not keep returning to the same beige apartment."""
    specs, _ = _campaign(64, 3)
    palettes = Counter(s.scene["env_palette"] for s in specs)
    assert len(palettes) >= 18
    assert palettes.most_common(1)[0][1] <= 6


def test_wardrobe_does_not_repeat_combinations():
    specs, _ = _campaign(64, 9)
    combos = Counter("+".join(s.wardrobe.families) for s in specs)
    assert combos.most_common(1)[0][1] <= 5, "an outfit combination repeats too often"


def test_camera_crops_are_varied():
    specs, _ = _campaign(64, 4)
    shots = Counter(s.camera["shot"]["id"] for s in specs)
    assert len(shots) >= 7


def test_camera_heights_are_varied():
    """Section 7: avoid consistently shooting from the same height."""
    specs, _ = _campaign(64, 4)
    heights = Counter(s.camera["height"]["id"] for s in specs)
    assert len(heights) >= 5
    assert heights.most_common(1)[0][1] / len(specs) <= 0.35


def test_expressions_are_varied_and_lip_bite_is_rare():
    specs, _ = _campaign(64, 8)
    exprs = Counter(s.expression["id"] for s in specs)
    assert len(exprs) >= 9
    # Section 6: a lip bite is acceptable but must not become a default.
    assert exprs.get("gentle_lip_bite", 0) <= 3


def test_rejected_frames_do_not_consume_diversity_budget():
    hist = DiversityHistory(window=8)
    hist.record({"scene_id": "a"}, accepted=False)
    assert hist.accepted_count == 0
    assert hist.total_count("scene_id", "a") == 0


def test_higher_pressure_increases_variety():
    low, _ = _campaign(48, 6, diversity="low")
    high, _ = _campaign(48, 6, diversity="high")
    assert len({s.scene["id"] for s in high}) >= len({s.scene["id"] for s in low})
