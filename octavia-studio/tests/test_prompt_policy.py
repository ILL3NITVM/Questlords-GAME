"""Identity lock, physique lock and content policy must reach every prompt."""
import pathlib
import sys

import pytest
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


def _prompts(count=40, seed=0, tier="standard"):
    cat = Catalogue()
    hist = DiversityHistory(window=24)
    smp = Sampler(cat, hist, CFG, planned_total=count, diversity="high")
    comp = Composer(cat, smp, CFG, POL)
    out = []
    for i in range(count):
        s = comp.compose("P", i, seed_record(seed, "P", i))
        pos, neg = build_prompts(s, IDN, PHY, POL, cat, CFG.get("identity", {}),
                                 {"tier": tier})
        keys = s.category_keys()
        keys["tilt_class"] = s.head.tilt_class
        hist.record(keys, accepted=True)
        out.append((s, pos, neg))
    return out


@pytest.mark.parametrize("tier", ["compact", "standard", "full"])
def test_every_prompt_carries_the_identity_anchors(tier):
    """Critical anchors are protected from both quota and token budget."""
    for _, pos, _ in _prompts(tier=tier):
        low = pos.lower()
        assert "green-hazel" in low, "eye colour anchor missing"
        assert "freckles" in low, "freckle anchor missing"
        assert "lime-green" in low, "signature highlight anchor missing"
        assert "brunette" in low, "hair colour anchor missing"


@pytest.mark.parametrize("tier", ["compact", "standard", "full"])
def test_head_roll_clause_always_survives(tier):
    """The left-tilt budget only reaches the renderer through this clause."""
    for spec, pos, _ in _prompts(tier=tier):
        low = pos.lower()
        assert ("tilted gently toward" in low) or ("head level and not tilted" in low), \
            f"head-roll instruction trimmed at tier {tier}"


def test_prompt_has_no_unbalanced_parentheses():
    """In ComfyUI and A1111 a parenthesis is emphasis syntax, not
    punctuation, so an unbalanced one corrupts the parse."""
    for _, pos, neg in _prompts(tier="full"):
        for text in (pos, neg):
            assert text.count("(") == text.count(")"), f"unbalanced parens: {text[:120]}"
            assert "[" not in text and "]" not in text


def test_no_duplicate_clauses():
    """Repeating a term wastes the highest-value token positions."""
    for _, pos, _ in _prompts(tier="full"):
        clauses = [c.strip().lower() for c in pos.split(",") if c.strip()]
        assert len(clauses) == len(set(clauses)), "duplicate clause in prompt"


def test_tier_budgets_are_respected():
    from pipeline.tokens import budget
    for tier, cap in (("compact", 75), ("standard", 150)):
        for _, pos, _ in _prompts(count=25, tier=tier):
            assert budget(pos).tokens <= cap, \
                f"{tier} tier promised <= {cap} tokens, produced {budget(pos).tokens}"


def test_compact_tier_keeps_breadth_within_its_arithmetic_limit():
    """Compact cannot fit all eight content groups in 75 tokens — protected
    identity and policy content alone costs ~38. It must still stay BROAD:
    identity plus at least five groups, never a prompt that is only
    identity."""
    from pipeline.prompt import build_prompts_verbose
    cat = Catalogue()
    for i in range(25):
        smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=1)
        spec = Composer(cat, smp, CFG, POL).compose("C", i, seed_record(i, "C", i))
        _, _, meta = build_prompts_verbose(spec, IDN, PHY, POL, cat,
                                           CFG.get("identity", {}), {"tier": "compact"})
        groups = set(meta["positive"]["groups_present"])
        assert {"subject", "identity"} <= groups
        assert len(groups) >= 5, f"compact collapsed to {sorted(groups)}"


def test_standard_tier_covers_the_core_content_groups():
    """The second chunk is what buys complete scene, wardrobe and camera."""
    from pipeline.prompt import build_prompts_verbose
    cat = Catalogue()
    for i in range(25):
        smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=1)
        spec = Composer(cat, smp, CFG, POL).compose("S", i, seed_record(i, "S", i))
        _, _, meta = build_prompts_verbose(spec, IDN, PHY, POL, cat,
                                           CFG.get("identity", {}), {"tier": "standard"})
        groups = set(meta["positive"]["groups_present"])
        for required in ("subject", "identity", "wardrobe", "scene", "pose"):
            assert required in groups, f"standard lost {required}: {sorted(groups)}"


def test_physique_lock_reaches_prompts_that_show_the_body():
    """On a close portrait the hips are not in frame, so spending scarce
    tokens describing them is waste. The lock applies where it is visible."""
    seen = 0
    for spec, pos, _ in _prompts(count=60, tier="full"):
        if spec.camera["shot"]["emphasis"] in ("body", "environment"):
            low = pos.lower()
            assert "shoulder-to-waist ratio" in low
            assert "five fingers" in low
            seen += 1
    assert seen > 0, "no body-emphasis frames sampled"


def test_full_tier_always_carries_the_complete_physique_lock():
    for _, pos, _ in _prompts(count=20, tier="full"):
        assert "shoulder-to-waist ratio" in pos.lower()


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
    """Solo enforcement sits in the protected policy group, so it survives
    the negative-prompt budget at every tier."""
    for tier in ("compact", "standard", "full"):
        for _, _, neg in _prompts(10, tier=tier):
            low = neg.lower()
            assert "two people" in low and "crowd" in low


def test_identity_spec_excludes_variable_axes():
    """The identity file must not overfit clothing, pose, camera or scene."""
    blob = str(IDN).lower()
    for leaked in ("mirror selfie", "sofa", "85mm", "beige apartment", "smiling at the camera"):
        assert leaked not in blob, f"identity spec overfits: {leaked!r}"


def test_head_clause_matches_the_sampled_roll():
    for spec, pos, _ in _prompts(40, seed=3, tier="full"):
        low = pos.lower()
        if spec.head.roll <= -4:
            assert "toward her left shoulder" in low
        elif spec.head.roll >= 4:
            assert "toward her right shoulder" in low
        else:
            assert "head level and not tilted" in low


def test_material_behaviour_reaches_the_prompt():
    """Section 4: materials must visibly affect drape. The full tier keeps
    the behaviour clause; compact drops it to buy pose and scene."""
    for _, pos, _ in _prompts(20, tier="full"):
        assert any(k in pos.lower() for k in ("drape", "folds", "creas", "wrinkl",
                                              "stands away", "pools", "floats",
                                              "holds", "skims", "hugs", "follows",
                                              "second skin", "fits like")), pos[:200]


# ----------------------------------------------------------------------
# Identity mode (descriptive / hybrid / lora_token)
# ----------------------------------------------------------------------
def _one_prompt(mode, trigger="ohwx_octavia", class_token="woman", tier="full"):
    from pipeline.seeds import seed_record
    cat = Catalogue()
    hist = DiversityHistory(24)
    smp = Sampler(cat, hist, CFG, planned_total=1)
    spec = Composer(cat, smp, CFG, POL).compose("M", 0, seed_record(1, "M", 0))
    ic = {"mode": mode, "trigger_token": trigger, "class_token": class_token}
    return build_prompts(spec, IDN, PHY, POL, cat, ic, {"tier": tier})


def test_descriptive_mode_spells_identity_out():
    pos, _ = _one_prompt("descriptive")
    low = pos.lower()
    assert "green-hazel" in low and "freckles" in low and "brunette" in low


def test_lora_token_mode_drops_the_descriptive_block():
    """A descriptive block competes with the adapter and pulls the face off-model."""
    pos, _ = _one_prompt("lora_token")
    low = pos.lower()
    assert "ohwx_octavia" in low
    assert "green-hazel" not in low, "eye description should not compete with the LoRA"
    assert "almond" not in low
    assert "cupid's bow" not in low


def test_hybrid_mode_keeps_only_high_signal_anchors():
    pos, _ = _one_prompt("hybrid")
    low = pos.lower()
    assert "ohwx_octavia" in low
    assert "green-hazel" in low and "freckles" in low
    assert "cupid's bow" not in low, "hybrid should be minimal, not full descriptive"


def test_all_modes_keep_the_physique_lock_and_age_clause():
    """Neither is carried by a face LoRA, so both must survive every mode."""
    for mode in ("descriptive", "hybrid", "lora_token"):
        pos, neg = _one_prompt(mode, tier="full")
        assert "shoulder-to-waist ratio" in pos.lower(), mode
        assert POL["subject"]["age_clause"].lower() in pos.lower(), mode
        for term in ("child", "minor", "nude"):
            assert term in neg.lower(), f"{mode} lost policy negative {term!r}"


def test_lora_mode_without_a_trigger_token_is_refused():
    """Silently rendering a generic person is far worse than failing loudly."""
    import pytest
    for mode in ("lora_token", "hybrid"):
        with pytest.raises(ValueError, match="trigger_token"):
            _one_prompt(mode, trigger="")


def test_lora_mode_carries_fewer_identity_tokens():
    """The saving is in the identity block specifically; at a fixed budget
    the freed tokens are spent on other groups, so total length is not the
    right measure."""
    from pipeline.prompt import build_segments
    from pipeline.seeds import seed_record
    cat = Catalogue()
    smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=1)
    spec = Composer(cat, smp, CFG, POL).compose("M", 0, seed_record(1, "M", 0))

    def identity_tokens(mode):
        from pipeline.tokens import estimate_tokens
        ic = {"mode": mode, "trigger_token": "ohwx_octavia", "class_token": "woman"}
        segs = build_segments(spec, IDN, PHY, POL, cat, ic)
        return sum(estimate_tokens(s.text) for s in segs if s.group == "identity")

    assert identity_tokens("lora_token") < identity_tokens("hybrid") \
        < identity_tokens("descriptive")
