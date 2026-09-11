"""QC rules, scoring honesty and review feedback."""
import json
import pathlib
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.history import DiversityHistory
from qc import review as review_mod
from qc.rules import DEFECT_TARGETS, apply_defect_penalties, judge
from qc.scoring import COMPUTED_METRICS, VISION_METRICS, get_scorer, overall

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())
QC = CFG["qc"]


def _scores(**over):
    base = {m: 95.0 for m in VISION_METRICS + COMPUTED_METRICS}
    base.update(over)
    return base


def test_hard_floors_reject():
    for metric, floor in QC["hard_reject"].items():
        v = judge(_scores(**{metric: floor - 1}), [], QC)
        assert not v.accepted, f"{metric} below {floor} should reject"
        assert any(metric in r for r in v.reasons)


def test_scores_at_the_floor_are_accepted():
    for metric, floor in QC["hard_reject"].items():
        v = judge(_scores(**{metric: float(floor)}), [], QC)
        assert v.accepted, f"{metric} exactly at {floor} should pass"


def test_clean_frame_is_accepted():
    assert judge(_scores(), [], QC).accepted


def test_warnings_do_not_reject():
    v = judge(_scores(hands=50.0), [], QC)
    assert v.accepted and v.warnings


def test_disqualifying_defects_reject_regardless_of_score():
    for defect in ("false_tattoos", "merged_limbs", "extra_fingers", "missing_fingers"):
        v = judge(_scores(), [defect], QC)
        assert not v.accepted, f"{defect} must be disqualifying"


def test_defect_penalties_hit_the_right_metric():
    penalties = QC["defect_penalties"]
    for defect, target in DEFECT_TARGETS.items():
        before = _scores()
        after = apply_defect_penalties(before, [defect], penalties)
        assert after[target] < before[target], f"{defect} did not penalise {target}"
        untouched = [m for m in before if m != target]
        assert all(after[m] == before[m] for m in untouched)


def test_penalties_never_go_negative():
    after = apply_defect_penalties({"hands": 5.0}, ["extra_fingers"], QC["defect_penalties"])
    assert after["hands"] == 0.0


def test_overall_weights_identity_most():
    high_id = overall(_scores(identity_consistency=100.0))
    high_light = overall(_scores(lighting=100.0))
    assert high_id > high_light, "identity must dominate the headline score"


def test_scorer_declares_its_placeholders():
    """The scorer must never let a placeholder pass as a measurement."""
    s = get_scorer(CFG)
    assert s.kind == "heuristic-stub"
    assert set(s.placeholder_metrics) == set(VISION_METRICS)
    assert not set(s.placeholder_metrics) & set(COMPUTED_METRICS)


def test_novelty_falls_when_categories_repeat():
    from pipeline.compose import Composer
    from pipeline.sampler import Catalogue, Sampler
    from pipeline.seeds import seed_record
    from qc.headpose import HeadPoseEstimate

    pol = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())
    cat = Catalogue()
    hist = DiversityHistory(window=24)
    smp = Sampler(cat, hist, CFG, planned_total=8, diversity="normal")
    comp = Composer(cat, smp, CFG, pol)
    scorer = get_scorer(CFG)
    spec = comp.compose("N", 0, seed_record(1, "N", 0))
    head = HeadPoseEstimate(0, 0, 0, "measured", 1.0)

    first, _ = scorer.score(spec, None, head, hist)
    keys = spec.category_keys()
    for _ in range(3):
        hist.record(keys, accepted=True)
    second, _ = scorer.score(spec, None, head, hist)
    assert second["novelty"] < first["novelty"]


def test_left_tilt_lowers_head_pose_novelty_once_over_budget():
    from qc.headpose import HeadPoseEstimate
    scorer = get_scorer(CFG)

    from pipeline.spec import SeedRecord

    class FakeSpec:
        frame_id = "x_000"
        seeds = SeedRecord()
        camera = {"shot": {"id": "waist_up", "emphasis": "upper_body"},
                  "focal": {"suitable_shots": ["waist_up"]},
                  "height": {"id": "eye_level"}, "angle": {"id": "frontal"}}
        pose = {"posture": "standing", "requires_furniture": []}
        scene = {"indoor": True, "furniture_affordances": [], "surfaces": []}
        lighting = {"kind": "natural", "id": "soft_window_daylight"}

        def category_keys(self):
            return {"head_position": "left_tilt"}

    hist = DiversityHistory(window=24)
    for i in range(20):
        hist.record({"tilt_class": "left" if i < 5 else "neutral"}, accepted=True)
    left = HeadPoseEstimate(0, 0, -12, "measured", 1.0)
    neutral = HeadPoseEstimate(0, 0, 0, "measured", 1.0)
    s_left, _ = scorer.score(FakeSpec(), None, left, hist)
    s_neu, _ = scorer.score(FakeSpec(), None, neutral, hist)
    assert s_left["head_pose_novelty"] < s_neu["head_pose_novelty"]


def test_review_marks_only_move_their_own_axes():
    """WARDROBE_BAD must not penalise the scene that happened to be in shot."""
    manifest = [{"index": 0, "category_keys": {
        "wardrobe_top": "ribbed_baby_tee", "scene_id": "bright_white_loft",
        "pose_id": "stand_relaxed", "colour_family": "jewel"}}]
    with tempfile.TemporaryDirectory() as td:
        fb = pathlib.Path(td) / "feedback.json"
        review_mod.apply_review(manifest, {0: "WARDROBE_BAD"}, fb, CFG)
        data = json.loads(fb.read_text())
        assert data["wardrobe_top"]["ribbed_baby_tee"] < 1.0
        assert "scene_id" not in data and "pose_id" not in data


def test_keep_mark_raises_weights():
    manifest = [{"index": 0, "category_keys": {"scene_id": "garden_terrace",
                                               "pose_id": "stand_relaxed"}}]
    with tempfile.TemporaryDirectory() as td:
        fb = pathlib.Path(td) / "feedback.json"
        review_mod.apply_review(manifest, {0: "KEEP"}, fb, CFG)
        data = json.loads(fb.read_text())
        assert data["scene_id"]["garden_terrace"] > 1.0


def test_feedback_weights_are_clamped():
    manifest = [{"index": 0, "category_keys": {"pose_id": "stand_relaxed",
                                               "pose_family": "standing_relaxed",
                                               "head_position": "upright_neutral"}}]
    with tempfile.TemporaryDirectory() as td:
        fb = pathlib.Path(td) / "feedback.json"
        for _ in range(40):
            review_mod.apply_review(manifest, {0: "POSE_DUPLICATE"}, fb, CFG)
        data = json.loads(fb.read_text())
        floor = CFG["feedback"]["weight_floor"]
        assert data["pose_id"]["stand_relaxed"] >= floor


def test_unmarked_rows_are_ignored():
    assert review_mod.read_review(pathlib.Path("/nonexistent/review.csv")) == {}
