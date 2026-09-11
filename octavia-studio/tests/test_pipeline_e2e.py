"""End-to-end run through the mock renderer, plus the renderer contract."""
import json
import pathlib
import sys
import tempfile

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.runner import Run, load_manifest
from renderers.base import Renderer, RendererUnavailable
from renderers.registry import available_backends, get_renderer

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())
IDN = yaml.safe_load((ROOT / "config/identity.yaml").read_text())
PHY = yaml.safe_load((ROOT / "config/physique.yaml").read_text())
POL = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())


def _run(tmp, count=16, seed=4242, run_id="T"):
    r = Run(pathlib.Path(tmp), run_id, CFG, IDN, PHY, POL)
    summary = r.execute(count=count, campaign="wardrobe", diversity="high",
                        master_seed=seed, backend="mock")
    return r, summary


def test_end_to_end_run_produces_images_and_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        r, summary = _run(tmp)
        assert summary["accepted"] + summary["rejected"] + summary["failed"] == 16
        manifest = load_manifest(r.dir)
        assert len(manifest) == 16
        for rec in manifest:
            assert rec["render_ok"]
            assert pathlib.Path(rec["image_path"]).is_file()


def test_manifest_records_every_seed_axis():
    from pipeline.spec import SEED_AXES
    with tempfile.TemporaryDirectory() as tmp:
        r, _ = _run(tmp, count=4)
        for rec in load_manifest(r.dir):
            assert set(rec["seeds"]) == set(SEED_AXES)


def test_run_is_reproducible_from_its_master_seed():
    """Section 9: a photograph must be reproducible from its seed record."""
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        ra, _ = _run(a, count=12, seed=999, run_id="REPRO")
        rb, _ = _run(b, count=12, seed=999, run_id="REPRO")
        ma, mb = load_manifest(ra.dir), load_manifest(rb.dir)
        assert [x["seeds"] for x in ma] == [x["seeds"] for x in mb]
        assert [x["prompt"] for x in ma] == [x["prompt"] for x in mb]
        assert [x["category_keys"] for x in ma] == [x["category_keys"] for x in mb]


def test_different_master_seeds_give_different_runs():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        ra, _ = _run(a, count=8, seed=1, run_id="X")
        rb, _ = _run(b, count=8, seed=2, run_id="X")
        assert [x["prompt"] for x in load_manifest(ra.dir)] != \
               [x["prompt"] for x in load_manifest(rb.dir)]


def test_left_tilt_share_reported_and_within_target():
    with tempfile.TemporaryDirectory() as tmp:
        _, summary = _run(tmp, count=64, seed=77)
        assert summary["left_tilt_share"] <= CFG["head_pose"]["left_tilt_target_share"]


def test_summary_flags_placeholder_metrics():
    """A run must never imply its identity scores were measured."""
    with tempfile.TemporaryDirectory() as tmp:
        _, summary = _run(tmp, count=4)
        assert summary["scorer"] == "heuristic-stub"
        assert summary["scorer_placeholder_metrics"]


def test_contact_sheets_build():
    from qc.contact_sheet import build_contact_sheet
    with tempfile.TemporaryDirectory() as tmp:
        r, _ = _run(tmp, count=8)
        out = r.sheets_dir / "01.jpg"
        build_contact_sheet(load_manifest(r.dir), out, 1, "T")
        assert out.is_file() and out.stat().st_size > 5000


def test_review_template_round_trips():
    import csv
    from qc import review as review_mod
    with tempfile.TemporaryDirectory() as tmp:
        r, _ = _run(tmp, count=6)
        manifest = load_manifest(r.dir)
        path = r.dir / "review.csv"
        review_mod.write_review_template(manifest, path)
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        assert len(rows) == 6
        rows[0]["MARK"] = "KEEP"
        rows[1]["MARK"] = "SCENE_BAD"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        marks = review_mod.read_review(path)
        assert marks == {0: "KEEP", 1: "SCENE_BAD"}


# ----------------------------------------------------------------------
# Renderer contract
# ----------------------------------------------------------------------
def test_all_backends_are_constructible():
    with tempfile.TemporaryDirectory() as tmp:
        for name in available_backends():
            r = get_renderer(name, CFG, pathlib.Path(tmp) / name)
            assert isinstance(r, Renderer)


def test_unknown_backend_raises():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError):
            get_renderer("nope", CFG, pathlib.Path(tmp))


def test_unconfigured_backends_raise_unavailable_not_crash():
    """Preflight must fail cleanly so `doctor` can report rather than explode."""
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("comfyui", "api"):
            r = get_renderer(name, CFG, pathlib.Path(tmp) / name)
            with pytest.raises(RendererUnavailable):
                r.preflight()


def test_mock_renderer_echoes_head_pose():
    from pipeline.compose import Composer
    from pipeline.history import DiversityHistory
    from pipeline.sampler import Catalogue, Sampler
    from pipeline.seeds import seed_record
    from renderers.mock import MockRenderer
    with tempfile.TemporaryDirectory() as tmp:
        cat = Catalogue()
        hist = DiversityHistory(24)
        smp = Sampler(cat, hist, CFG, planned_total=1)
        spec = Composer(cat, smp, CFG, POL).compose("M", 0, seed_record(5, "M", 0))
        res = MockRenderer(CFG, pathlib.Path(tmp)).generate_image(spec)
        assert res.ok
        assert res.measured_head_pose["roll"] == spec.head.roll


def test_api_renderer_response_path_digging():
    from renderers.api import APIRenderer
    doc = {"data": [{"b64_json": "AAA"}]}
    assert APIRenderer._dig(doc, "data.0.b64_json") == "AAA"
    assert APIRenderer._dig(doc, "data.9.b64_json") is None
    assert APIRenderer._dig(doc, "nope") is None
