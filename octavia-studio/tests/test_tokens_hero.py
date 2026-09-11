"""Token budgeting, hero-frame selection and render planning."""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import hero as hero_mod
from pipeline.compose import Composer
from pipeline.history import DiversityHistory
from pipeline.renderplan import default_plan
from pipeline.sampler import Catalogue, Sampler
from pipeline.seeds import seed_record
from pipeline.tokens import (CONTENT_PER_CHUNK, budget, chunk_map, count_tokens,
                             estimate_tokens, fit_segments)

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())
POL = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())


# ----------------------------------------------------------------------
# Token budgeting
# ----------------------------------------------------------------------
def test_empty_text_costs_nothing():
    assert estimate_tokens("") == 0
    assert budget("").tokens == 0


def test_estimate_grows_with_length():
    short = estimate_tokens("a soft oval face")
    long = estimate_tokens("a soft oval face with a gently tapered jawline and full lips")
    assert long > short


def test_estimator_biases_high_not_low():
    """A prompt that fits by estimate must fit in reality, so the estimate
    may over-count but must never under-count badly."""
    text = "photorealistic editorial photograph of a single adult woman"
    words = len(text.split())
    assert estimate_tokens(text) >= words - 1


def test_budget_reports_chunks():
    one = "green-hazel eyes, natural freckles"
    assert budget(one).fits_single_chunk
    assert budget(one).chunks == 1
    long = ", ".join(["a detailed descriptive clause about lighting"] * 40)
    b = budget(long)
    assert not b.fits_single_chunk
    assert b.chunks > 1
    assert b.overflow_tokens == b.tokens - CONTENT_PER_CHUNK


def test_count_tokens_declares_its_method():
    """Nothing downstream may mistake an estimate for a measurement."""
    c = count_tokens("a short prompt")
    assert c["method"] in ("clip-tokenizer", "heuristic-estimate")
    assert isinstance(c["exact"], bool)
    if c["method"] == "heuristic-estimate":
        assert c["exact"] is False


def test_fit_segments_keeps_the_head_and_drops_the_tail():
    segs = ["first important clause"] + ["padding clause here"] * 40
    result = fit_segments(segs, limit=30)
    assert result["kept"][0] == "first important clause"
    assert result["dropped"]
    assert result["tokens_used"] <= 30


def test_chunk_map_locates_segments():
    segs = ["short clause"] * 40
    cmap = chunk_map(segs)
    assert cmap[0]["chunk"] == 0
    assert cmap[-1]["chunk"] > 0


# ----------------------------------------------------------------------
# Hero objective
# ----------------------------------------------------------------------
def _spec(seed=0, index=0):
    cat = Catalogue()
    smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=1)
    return Composer(cat, smp, CFG, POL).compose("H", index, seed_record(seed, "H", index))


def _composer():
    cat = Catalogue()
    smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=64, diversity="high")
    return Composer(cat, smp, CFG, POL), cat


def test_hero_score_is_bounded():
    for i in range(30):
        sc = hero_mod.score_spec(_spec(i, i))
        assert 0.0 <= sc.total <= 100.0


def test_close_portrait_outscores_environmental_wide():
    """Identity legibility is the hero objective's dominant term."""
    comp, _ = _composer()
    ranked = hero_mod.search(comp, "R", 7, 300, cfg=CFG.get("hero", {}))
    best_shots = [s.camera["shot"]["id"] for s, _ in ranked[:12]]
    worst_shots = [s.camera["shot"]["id"] for s, _ in ranked[-12:]]
    tight = {"close_portrait", "head_and_shoulders", "waist_up"}
    assert sum(1 for x in best_shots if x in tight) > sum(1 for x in worst_shots if x in tight)


def test_search_returns_ranked_best_first():
    comp, _ = _composer()
    ranked = hero_mod.search(comp, "R", 3, 120, cfg=CFG.get("hero", {}))
    totals = [sc.total for _, sc in ranked]
    assert totals == sorted(totals, reverse=True)
    assert len(ranked) == 120


def test_search_is_reproducible_from_its_seed():
    comp1, _ = _composer()
    comp2, _ = _composer()
    a = hero_mod.search(comp1, "R", 11, 80, cfg=CFG.get("hero", {}))
    b = hero_mod.search(comp2, "R", 11, 80, cfg=CFG.get("hero", {}))
    assert [s.frame_id for s, _ in a] == [s.frame_id for s, _ in b]
    assert [round(sc.total, 4) for _, sc in a] == [round(sc.total, 4) for _, sc in b]


def test_near_profile_yaw_is_penalised_for_identity():
    comp, _ = _composer()
    ranked = hero_mod.search(comp, "R", 5, 250, cfg=CFG.get("hero", {}))
    top_yaw = sum(abs(s.head.yaw) for s, _ in ranked[:15]) / 15
    bottom_yaw = sum(abs(s.head.yaw) for s, _ in ranked[-15:]) / 15
    assert top_yaw < bottom_yaw, "high-scoring frames should face the camera more"


def test_risky_hands_are_flagged():
    comp, _ = _composer()
    ranked = hero_mod.search(comp, "R", 9, 200, cfg=CFG.get("hero", {}))
    flagged = [sc for _, sc in ranked if any("fingers prominent" in r for r in sc.risks)]
    assert flagged, "no frame flagged a prominent-hand risk across 200 candidates"
    assert all(sc.components["hand_safety"] < 1.0 for sc in flagged)


def test_mirror_scenes_are_flagged_for_reflection_risk():
    comp, _ = _composer()
    ranked = hero_mod.search(comp, "R", 13, 300, cfg=CFG.get("hero", {}))
    mirrored = [sc for s, sc in ranked
                if s.scene["family"] in ("bathroom_vanity", "walk_in_wardrobe",
                                         "dressing_room")]
    assert mirrored
    assert all(any("reflection" in r for r in sc.risks) for sc in mirrored)


def test_bare_feet_only_penalised_when_in_frame():
    comp, _ = _composer()
    ranked = hero_mod.search(comp, "R", 21, 300, cfg=CFG.get("hero", {}))
    for spec, sc in ranked:
        visible = spec.camera["shot"]["id"] in ("full_body", "environmental_full_body",
                                                "seated_full")
        barefoot = (spec.wardrobe.footwear or {}).get("id") in ("barefoot", "socks")
        if barefoot and not visible:
            assert sc.components["feet_safety"] == 1.0


def test_hero_weights_are_configurable():
    spec = _spec(4, 4)
    default = hero_mod.score_spec(spec, CFG.get("hero", {}))
    skewed = hero_mod.score_spec(spec, {"weights": {"identity_legibility": 50.0}})
    assert default.total != skewed.total


# ----------------------------------------------------------------------
# Render plan
# ----------------------------------------------------------------------
def test_default_plan_starts_with_base():
    plan = default_plan(CFG, 896, 1152)
    assert plan.passes[0].name == "base"
    assert plan.passes[0].enabled


def test_unsupported_passes_are_skipped_with_a_reason():
    """A hero frame must never claim a refinement that did not happen."""
    plan = default_plan(CFG, 896, 1152).resolve([])
    refine = [p for p in plan.passes if p.name in ("hires_fix", "face_detail") and p.enabled]
    assert refine
    for p in refine:
        assert p.skipped_reason and "capability" in p.skipped_reason


def test_supported_passes_are_kept():
    plan = default_plan(CFG, 896, 1152).resolve(["hires_fix", "face_restore"])
    for p in plan.passes:
        if p.name in ("hires_fix", "face_detail") and p.enabled:
            assert p.skipped_reason is None


def test_disabled_is_not_reported_as_unsupported():
    """Config-disabled and backend-unsupported are different facts."""
    plan = default_plan(CFG, 896, 1152).resolve([])
    upscale = [p for p in plan.passes if p.name == "upscale"][0]
    assert upscale.enabled is False
    assert upscale.skipped_reason is None


def test_hires_denoise_stays_low_enough_to_hold_identity():
    """Above ~0.5 the refinement resamples the face freely and walks the
    likeness off-model between passes."""
    plan = default_plan(CFG, 896, 1152)
    hires = [p for p in plan.passes if p.name == "hires_fix"][0]
    face = [p for p in plan.passes if p.name == "face_detail"][0]
    assert hires.params["denoise"] <= 0.5
    assert face.params["denoise"] <= 0.5


def test_plan_summary_is_readable():
    assert "base" in default_plan(CFG, 896, 1152).summary()
