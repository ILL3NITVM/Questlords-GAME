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
