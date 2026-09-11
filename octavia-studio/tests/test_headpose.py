"""Left-tilt suppression (section 12) — the load-bearing invariant."""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.compose import Composer
from pipeline.history import DiversityHistory
from pipeline.sampler import Catalogue, Sampler
from pipeline.seeds import seed_record
from qc.headpose import HeadPoseEstimate, estimate


def _cfg():
    return yaml.safe_load((ROOT / "config/studio.yaml").read_text())


def _policy():
    return yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())


def test_roll_sign_convention():
    assert HeadPoseEstimate(0, 0, -12, "measured", 1.0).tilt_class == "left"
    assert HeadPoseEstimate(0, 0, 12, "measured", 1.0).tilt_class == "right"
    assert HeadPoseEstimate(0, 0, 0, "measured", 1.0).tilt_class == "neutral"
    assert HeadPoseEstimate(0, 0, -3.9, "measured", 1.0).tilt_class == "neutral"
    assert HeadPoseEstimate(0, 0, -4.0, "measured", 1.0).tilt_class == "left"


def test_measured_pose_wins_over_requested():
    class FakeHead:
        yaw, pitch, roll = 0.0, 0.0, -15.0

    est = estimate(FakeHead(), {"yaw": 0, "pitch": 0, "roll": 12.0}, True)
    assert est.source == "measured"
    assert est.tilt_class == "right", "measurement must override the request"


def test_requested_pose_used_as_fallback_with_low_confidence():
    class FakeHead:
        yaw, pitch, roll = 0.0, 0.0, -15.0

    est = estimate(FakeHead(), None, False)
    assert est.source == "requested"
    assert est.confidence < 1.0


def _run_campaign(count, seed, diversity="high"):
    cfg, pol = _cfg(), _policy()
    cat = Catalogue()
    hist = DiversityHistory(window=int(cfg["diversity"]["history_window"]))
    smp = Sampler(cat, hist, cfg, planned_total=count, diversity=diversity)
    comp = Composer(cat, smp, cfg, pol)
    for i in range(count):
        spec = comp.compose("T", i, seed_record(seed, "T", i))
        keys = spec.category_keys()
        keys["tilt_class"] = spec.head.tilt_class
        hist.record(keys, accepted=True)
    return hist


def test_left_tilt_stays_within_budget_across_many_seeds():
    """The 8% cap must hold for every seed, not just a lucky one."""
    failures = []
    for seed in range(30):
        hist = _run_campaign(64, seed)
        share = hist.left_tilt_share()
        if share > 0.08:
            failures.append((seed, round(share, 4)))
    assert not failures, f"left-tilt budget exceeded for seeds: {failures}"


def test_left_tilt_never_becomes_a_signature_in_small_batches():
    for seed in range(20):
        hist = _run_campaign(8, seed)
        assert hist.left_tilt_count <= 1, f"seed {seed} produced {hist.left_tilt_count} left tilts in 8"


def test_neutral_dominates_head_positions():
    hist = _run_campaign(64, 7)
    total = hist.accepted_count
    neutral = hist.total_count("tilt_class", "neutral")
    assert neutral / total > 0.5, "neutral/upright should dominate"


def test_right_tilt_occurs_naturally():
    hist = _run_campaign(64, 7)
    assert hist.total_count("tilt_class", "right") > 0, "right tilt should appear naturally"
