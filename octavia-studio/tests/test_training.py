"""Training-set curation, captioning and export."""
import json
import pathlib
import sys
import tempfile

import pytest
import yaml
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from training import analyze as tr_analyze
from training import caption as tr_caption
from training import export as tr_export
from training import ingest as tr_ingest

TCFG = yaml.safe_load((ROOT / "config/training.yaml").read_text())


def _img(path, w=896, h=1152, base=(140, 120, 110), seed=0, blobs=8):
    import random
    rng = random.Random(seed)
    im = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(im)
    for _ in range(blobs):
        x, y = rng.randrange(w), rng.randrange(h)
        r = rng.randrange(30, max(40, w // 3))
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=tuple(max(0, min(255, b + rng.randrange(-90, 90))) for b in base))
    im.save(path)
    return path


# ----------------------------------------------------------------------
# Perceptual hashing / duplicate detection
# ----------------------------------------------------------------------
def test_dhash_is_scale_invariant():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "a.png", 896, 1152, seed=1)
        big = Image.open(p / "a.png").resize((1792, 2304))
        big.save(p / "b.png")
        ha = tr_ingest.dhash(Image.open(p / "a.png"))
        hb = tr_ingest.dhash(Image.open(p / "b.png"))
        assert tr_ingest.hamming(ha, hb) <= 4, "rescale should not change the hash much"


def test_dhash_separates_different_images():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "a.png", seed=1, base=(200, 60, 60))
        _img(p / "b.png", seed=99, base=(40, 60, 200))
        ha = tr_ingest.dhash(Image.open(p / "a.png"))
        hb = tr_ingest.dhash(Image.open(p / "b.png"))
        assert tr_ingest.hamming(ha, hb) > 8


def test_near_duplicate_clustering_groups_a_burst():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "base.png", seed=5)
        src = Image.open(p / "base.png")
        for i in range(5):
            src.resize((896 + i * 3, 1152 + i * 3)).resize((896, 1152)).save(p / f"dup_{i}.png")
        for i in range(4):
            _img(p / f"other_{i}.png", seed=100 + i * 37, base=(50 + i * 40, 90, 160))
        records = tr_ingest.scan(p, TCFG)
        tr_analyze.cluster_near_duplicates(records, threshold=6)
        sizes = {}
        for r in records:
            sizes[r.cluster] = sizes.get(r.cluster, 0) + 1
        assert max(sizes.values()) >= 6, "the burst plus its base should cluster together"


# ----------------------------------------------------------------------
# Quality flags and curation
# ----------------------------------------------------------------------
def test_low_resolution_is_flagged():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "small.png", 320, 400)
        rec = tr_ingest.inspect(p / "small.png", TCFG)
        assert any("low_resolution" in f for f in rec.flags)


def test_underexposed_is_flagged():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        Image.new("RGB", (896, 1152), (6, 6, 8)).save(p / "dark.png")
        rec = tr_ingest.inspect(p / "dark.png", TCFG)
        assert any("underexposed" in f for f in rec.flags)


def test_extreme_aspect_is_flagged():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "pano.png", 2400, 600)
        rec = tr_ingest.inspect(p / "pano.png", TCFG)
        assert any("extreme_aspect" in f for f in rec.flags)


def test_unreadable_file_does_not_crash_the_scan():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "ok.png")
        (p / "broken.png").write_bytes(b"garbage")
        records = tr_ingest.scan(p, TCFG)
        assert len(records) == 2
        broken = [r for r in records if r.filename == "broken.png"][0]
        assert "unreadable" in broken.flags and not broken.selected


def test_curate_caps_duplicate_clusters():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "base.png", seed=5)
        src = Image.open(p / "base.png")
        for i in range(8):
            src.resize((896 + i * 3, 1152 + i * 3)).resize((896, 1152)).save(p / f"dup_{i}.png")
        records = tr_ingest.scan(p, TCFG)
        tr_analyze.cluster_near_duplicates(records, threshold=6)
        result = tr_analyze.curate(records, TCFG)
        cap = TCFG["balance"]["max_per_duplicate_cluster"]
        assert result["selected"] <= cap, f"cluster should be capped at {cap}"
        assert result["rejected_duplicates"] > 0


def test_curate_never_deletes_source_files():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        for i in range(4):
            _img(p / f"x{i}.png", 320, 400)     # all will be rejected as low-res
        before = sorted(f.name for f in p.iterdir())
        records = tr_ingest.scan(p, TCFG)
        tr_analyze.cluster_near_duplicates(records)
        tr_analyze.curate(records, TCFG)
        assert sorted(f.name for f in p.iterdir()) == before
        assert all(not r.selected for r in records)


def test_analyze_warns_on_flag_saturation():
    """A flag firing on ~everything means a bad threshold, not bad data."""
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        for i in range(12):
            _img(p / f"s{i}.png", 400, 500, seed=i)   # all below min_side
        records = tr_ingest.scan(p, TCFG)
        report = tr_analyze.analyze(records, TCFG)
        assert any("miscalibrated" in w for w in report["warnings"])


def test_analyze_reports_unmeasured_axes_honestly():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        for i in range(6):
            _img(p / f"x{i}.png", seed=i)
        report = tr_analyze.analyze(tr_ingest.scan(p, TCFG), TCFG)
        axes = {a["axis"] for a in report["unmeasured_axes"]}
        assert "head_pose / tilt" in axes
        assert all(a["status"] == "UNMEASURED" for a in report["unmeasured_axes"])
        assert "none of them are measured here" in report["critical_note"].lower()


# ----------------------------------------------------------------------
# Captioning — the identity-omission rule
# ----------------------------------------------------------------------
@pytest.mark.parametrize("term", [
    "green eyes", "hazel eyes", "freckles", "brunette", "dark hair",
    "lime green highlights", "olive skin tone", "purple crystal pendant",
    "thick eyebrows", "beautiful", "woman",
])
def test_identity_terms_are_stripped(term):
    caption = f"a {term}, waist up, standing, soft window light"
    out = tr_caption.strip_identity_terms(caption)
    assert term.split()[-1] not in out.lower() or term.split()[-1] in ("up",), \
        f"{term!r} survived stripping: {out!r}"


def test_variable_axis_terms_survive_stripping():
    """The things a caption SHOULD describe must not be removed."""
    caption = ("waist up, three-quarter right, slight smile, black off-shoulder top, "
               "bright loft, soft window light")
    out = tr_caption.strip_identity_terms(caption)
    for keep in ("waist up", "three-quarter right", "slight smile",
                 "black off-shoulder top", "bright loft", "soft window light"):
        assert keep in out, f"{keep!r} was wrongly stripped"


def test_stripping_leaves_no_grammatical_debris():
    caption = "a beautiful brunette woman with green eyes and freckles, seated on a sofa"
    out = tr_caption.strip_identity_terms(caption)
    assert out == "seated on a sofa", f"debris left: {out!r}"


def test_compose_caption_leads_with_trigger_token():
    out = tr_caption.compose_caption("ohwx_octavia", ["waist up", "bright loft"], "woman")
    assert out.startswith("ohwx_octavia woman,")


def test_caption_sheet_round_trip_strips_identity():
    import csv
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        _img(p / "a.png")
        records = tr_ingest.scan(p, TCFG)
        sheet = p / "captions.csv"
        tr_caption.write_caption_sheet(records, sheet, "ohwx_octavia", "woman")

        rows = list(csv.DictReader(open(sheet)))
        rows[0]["clothing"] = "brunette woman with green eyes wearing a pink tee"
        rows[0]["framing"] = "waist up"
        with open(sheet, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)

        caps = tr_caption.read_caption_sheet(sheet, "ohwx_octavia", "woman")
        cap = caps["a.png"]
        assert cap.startswith("ohwx_octavia woman")
        assert "green eyes" not in cap and "brunette" not in cap
        assert "pink tee" in cap and "waist up" in cap


def test_filter_backend_cleans_any_captioner_output():
    class Noisy(tr_caption.CaptionBackend):
        name = "noisy"

        def describe(self, image_path):
            return "a gorgeous brunette woman with green eyes, seated, warm lamplight"

    backend = tr_caption.FilterCaptionBackend(Noisy(), "ohwx_octavia", "woman")
    out = backend.describe(pathlib.Path("x.png"))
    assert out.startswith("ohwx_octavia woman")
    assert "brunette" not in out and "green eyes" not in out
    assert "seated" in out and "warm lamplight" in out


# ----------------------------------------------------------------------
# Export
# ----------------------------------------------------------------------
def _prepared(td, n=8):
    p = pathlib.Path(td) / "src"
    p.mkdir(parents=True)
    for i in range(n):
        _img(p / f"x{i}.png", seed=i * 17, base=(60 + i * 18, 100, 150))
    records = tr_ingest.scan(p, TCFG)
    tr_analyze.cluster_near_duplicates(records, threshold=6)
    tr_analyze.curate(records, TCFG)
    tr_caption.apply_captions(records, {}, "ohwx_octavia", "woman")
    return records


def test_lora_export_produces_kohya_layout():
    with tempfile.TemporaryDirectory() as td:
        records = _prepared(td)
        out = pathlib.Path(td) / "out"
        result = tr_export.export_lora(records, out, TCFG)
        img_dir = pathlib.Path(result["image_dir"])
        images = list(img_dir.glob("*.png"))
        texts = list(img_dir.glob("*.txt"))
        assert len(images) == len(texts) == result["exported"]
        for img in images:
            assert img.with_suffix(".txt").is_file(), "every image needs a caption file"
        assert (out / "dataset.toml").is_file()
        assert (out / "hyperparameters.json").is_file()


def test_lora_export_does_not_move_source_files():
    with tempfile.TemporaryDirectory() as td:
        records = _prepared(td)
        src = pathlib.Path(td) / "src"
        before = sorted(f.name for f in src.iterdir())
        tr_export.export_lora(records, pathlib.Path(td) / "out", TCFG)
        assert sorted(f.name for f in src.iterdir()) == before


def test_lora_export_flags_placeholder_captions():
    """Training on TODO_ markers teaches the model the literal string."""
    with tempfile.TemporaryDirectory() as td:
        records = _prepared(td)
        result = tr_export.export_lora(records, pathlib.Path(td) / "out", TCFG)
        assert result["placeholder_captions"] == result["exported"]


def test_repeats_scale_with_dataset_size():
    small = tr_export._repeats_for(10, 200)
    large = tr_export._repeats_for(200, 200)
    assert small > large and large >= 1


def test_ipadapter_subset_spans_distinct_clusters():
    with tempfile.TemporaryDirectory() as td:
        records = _prepared(td, n=10)
        out = pathlib.Path(td) / "ip"
        result = tr_export.export_ipadapter(records, out, TCFG)
        assert result["exported"] > 0
        assert len(list(out.iterdir())) == result["exported"]


def test_export_with_nothing_selected_errors_cleanly():
    with tempfile.TemporaryDirectory() as td:
        records = _prepared(td)
        for r in records:
            r.selected = False
        result = tr_export.export_lora(records, pathlib.Path(td) / "out", TCFG)
        assert "error" in result


# ----------------------------------------------------------------------
# Incremental batch intake
# ----------------------------------------------------------------------
def test_batch_intake_is_idempotent():
    """Re-sending a batch must not duplicate images. A duplicate silently
    doubles that image's weight during training."""
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"
        incoming.mkdir()
        for i in range(4):
            _img(incoming / f"p{i}.png", seed=i)
        dest = pathlib.Path(td) / "set"

        first = tr_intake.add_batch([incoming], dest, "b1")
        again = tr_intake.add_batch([incoming], dest, "b2")

        assert first["added"] == 4
        assert again["added"] == 0
        assert again["duplicates_skipped"] == 4
        assert again["total_in_set"] == 4


def test_overlapping_batches_only_add_the_new_images():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        a = pathlib.Path(td) / "a"; a.mkdir()
        b = pathlib.Path(td) / "b"; b.mkdir()
        for i in range(3):
            _img(a / f"x{i}.png", seed=i)
        # b repeats one of a's images byte-for-byte, plus two new ones.
        import shutil
        shutil.copy2(a / "x0.png", b / "same.png")
        for i in range(3, 5):
            _img(b / f"y{i}.png", seed=i)

        dest = pathlib.Path(td) / "set"
        tr_intake.add_batch([a], dest, "b1")
        second = tr_intake.add_batch([b], dest, "b2")
        assert second["added"] == 2
        assert second["duplicates_skipped"] == 1
        assert second["total_in_set"] == 5


def test_intake_copies_and_never_moves():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"; incoming.mkdir()
        for i in range(3):
            _img(incoming / f"p{i}.png", seed=i)
        before = sorted(f.name for f in incoming.iterdir())
        tr_intake.add_batch([incoming], pathlib.Path(td) / "set", "b1")
        assert sorted(f.name for f in incoming.iterdir()) == before


def test_dry_run_copies_nothing():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"; incoming.mkdir()
        _img(incoming / "p.png")
        dest = pathlib.Path(td) / "set"
        result = tr_intake.add_batch([incoming], dest, "b1", dry_run=True)
        assert result["added"] == 1
        assert not dest.exists() or not list(dest.glob("*.png"))


def test_intake_accepts_files_and_directories():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td) / "in"
        nested = root / "sub"
        nested.mkdir(parents=True)
        _img(root / "top.png", seed=1)
        _img(nested / "deep.png", seed=2)
        loose = pathlib.Path(td) / "loose.png"
        _img(loose, seed=3)

        dest = pathlib.Path(td) / "set"
        result = tr_intake.add_batch([root, loose], dest, "b1")
        assert result["added"] == 3, "should recurse into directories and take loose files"


def test_non_images_are_ignored():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"; incoming.mkdir()
        _img(incoming / "good.png")
        (incoming / "notes.txt").write_text("not an image")
        (incoming / "archive.zip").write_bytes(b"PK\x03\x04")
        result = tr_intake.add_batch([incoming], pathlib.Path(td) / "set", "b1")
        assert result["added"] == 1


def test_ledger_records_batch_provenance():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"; incoming.mkdir()
        for i in range(2):
            _img(incoming / f"p{i}.png", seed=i)
        dest = pathlib.Path(td) / "set"
        tr_intake.add_batch([incoming], dest, "monday-shoot")
        for i in range(2, 4):
            _img(incoming / f"q{i}.png", seed=i)
        tr_intake.add_batch([incoming], dest, "tuesday-shoot")

        summary = tr_intake.ledger_summary(dest)
        assert summary["batches"] == 2
        assert summary["unique_images"] == 4
        assert summary["files_on_disk"] == 4
        assert [b["batch_id"] for b in summary["recent"]] == ["monday-shoot", "tuesday-shoot"]


def test_stored_filenames_carry_batch_and_hash():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"; incoming.mkdir()
        _img(incoming / "original_name.png")
        dest = pathlib.Path(td) / "set"
        tr_intake.add_batch([incoming], dest, "shoot-a")
        stored = [f.name for f in dest.glob("*.png")]
        assert len(stored) == 1
        assert stored[0].startswith("shoot-a_")


def test_unreadable_file_is_reported_not_fatal():
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"; incoming.mkdir()
        _img(incoming / "ok.png")
        bad = incoming / "bad.png"
        bad.write_bytes(b"not a real png")
        result = tr_intake.add_batch([incoming], pathlib.Path(td) / "set", "b1")
        # A corrupt file still hashes fine; it is the curation stage that
        # rejects it. Intake only fails on genuinely unreadable paths.
        assert result["added"] == 2
        assert result["failed"] == 0


def test_ingest_picks_up_newly_added_batches():
    """Intake and curation have to compose: adding a batch then re-ingesting
    must see the new images."""
    from training import intake as tr_intake
    with tempfile.TemporaryDirectory() as td:
        incoming = pathlib.Path(td) / "in"; incoming.mkdir()
        dest = pathlib.Path(td) / "set"
        for i in range(3):
            _img(incoming / f"p{i}.png", seed=i)
        tr_intake.add_batch([incoming], dest, "b1")
        assert len(tr_ingest.scan(dest, TCFG)) == 3

        more = pathlib.Path(td) / "in2"; more.mkdir()
        for i in range(3, 7):
            _img(more / f"q{i}.png", seed=i)
        tr_intake.add_batch([more], dest, "b2")
        assert len(tr_ingest.scan(dest, TCFG)) == 7
