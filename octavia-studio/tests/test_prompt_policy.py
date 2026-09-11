"""Identity lock, physique lock and content policy must reach every prompt."""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.compose import Composer
from pipeline.history import DiversityHistory
from pipeline.prompt import build_prompts
from pipeline.sampler import Catalogue, Sampler
from pipeline.seeds import seed_record

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())
POL = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())
IDN = yaml.safe_load((ROOT / "config/identity.yaml").read_text())
PHY = yaml.safe_load((ROOT / "config/physique.yaml").read_text())


def _prompts(count=40, seed=0):
    cat = Catalogue()
    hist = DiversityHistory(window=24)
    smp = Sampler(cat, hist, CFG, planned_total=count, diversity="high")
    comp = Composer(cat, smp, CFG, POL)
    out = []
    for i in range(count):
        s = comp.compose("P", i, seed_record(seed, "P", i))
        pos, neg = build_prompts(s, IDN, PHY, POL, cat)
        keys = s.category_keys()
        keys["tilt_class"] = s.head.tilt_class
        hist.record(keys, accepted=True)
        out.append((s, pos, neg))
    return out


def test_every_prompt_carries_the_identity_anchors():
    for _, pos, _ in _prompts():
        low = pos.lower()
        assert "green-hazel" in low, "eye colour anchor missing"
        assert "freckles" in low, "freckle anchor missing"
        assert "olive / lime-green face-framing sections" in low or "lime-green" in low
        assert "brunette" in low, "hair colour anchor missing"


def test_every_prompt_carries_the_physique_lock():
    for _, pos, _ in _prompts():
        low = pos.lower()
        assert "shoulder-to-waist ratio" in low
        assert "hip-to-waist ratio" in low
        assert "five fingers" in low


def test_every_prompt_asserts_adult_age():
    clause = POL["subject"]["age_clause"].lower()
    for _, pos, _ in _prompts():
        assert clause in pos.lower()


def test_negative_prompt_blocks_minors_and_explicit_content():
    for _, _, neg in _prompts():
        low = neg.lower()
        for term in ("child", "minor", "teen", "nude", "explicit", "underage"):
            assert term in low, f"negative prompt missing {term!r}"


def test_negative_prompt_blocks_identity_violations():
    for _, _, neg in _prompts():
        low = neg.lower()
        for term in ("tattoo", "blonde hair", "blue eyes", "different woman"):
            assert term in low


def test_negative_prompt_suppresses_scene_text():
    """Section 5: no nonsense signage, posters or product labels."""
    for _, _, neg in _prompts():
        low = neg.lower()
        for term in ("text", "watermark", "gibberish writing", "book titles"):
            assert term in low


def test_negative_prompt_has_no_duplicates():
    for _, _, neg in _prompts(10):
        terms = [t.strip().lower() for t in neg.split(",")]
        assert len(terms) == len(set(terms)), "duplicate negative terms"


def test_prompts_are_solo_subject():
    for _, _, neg in _prompts(10):
        assert "two people" in neg.lower()


def test_identity_spec_excludes_variable_axes():
    """The identity file must not overfit clothing, pose, camera or scene."""
    blob = str(IDN).lower()
    for leaked in ("mirror selfie", "sofa", "85mm", "beige apartment", "smiling at the camera"):
        assert leaked not in blob, f"identity spec overfits: {leaked!r}"


def test_head_clause_matches_the_sampled_roll():
    for spec, pos, _ in _prompts(40, seed=3):
        low = pos.lower()
        if spec.head.roll <= -4:
            assert "toward her left shoulder" in low
        elif spec.head.roll >= 4:
            assert "toward her right shoulder" in low
        else:
            assert "head level, not tilted" in low


def test_material_behaviour_reaches_the_prompt():
    """Section 4: materials must visibly affect drape and wrinkling."""
    for _, pos, _ in _prompts(20):
        assert any(k in pos.lower() for k in ("drape", "folds", "creas", "wrinkl",
                                              "stands away", "pools", "floats",
                                              "holds", "skims", "hugs", "follows"))
