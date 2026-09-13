"""Bridge to the existing octavia_studio catalogue."""
import json
import pathlib
import sys
import tempfile

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bridge import shoot_export as br_export
from bridge import wardrobe_import as br_wardrobe

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())
PHY = yaml.safe_load((ROOT / "config/physique.yaml").read_text())
OBSERVED = ROOT / "data/wardrobe/observed"


def _src(**over):
    base = {"wardrobe_item_id": "black-tee", "name": "Black fitted short-sleeve tee",
            "category": "top", "primary_color": "black", "secondary_color": "",
            "material": "Visual appearance only; fibre unknown",
            "fit": "visible design", "canon_status": "candidate",
            "ownership": "candidate", "source_reference": "a-1234",
            "first_seen": "2026-09-11T00:00:00+00:00"}
    base.update(over)
    return base


# ----------------------------------------------------------------------
# Wardrobe import
# ----------------------------------------------------------------------
def test_material_is_marked_inferred_never_asserted():
    """The source says fibre is unknown for almost every garment. Converting
    that into a confident material claim would launder a guess into fact."""
    rec = br_wardrobe.convert_item(_src(), {})
    assert rec["material_confidence"] == "inferred_from_name"
    assert "material" in rec["inferred"]


def test_material_inference_reads_the_name():
    cases = {"Blue straight-leg jeans": "denim",
             "Plum satin slip dress": "satin",
             "Cream cable-knit jumper": "chunky knit",
             "Black leather ankle boots": "leather-look fashion material"}
    for name, expected in cases.items():
        cat = "bottom" if "jeans" in name else ("dress" if "dress" in name
                                                else ("footwear" if "boots" in name
                                                      else "top"))
        rec = br_wardrobe.convert_item(_src(name=name, category=cat), {})
        assert rec["material"] == expected, f"{name} -> {rec['material']}"


def test_ownership_status_is_preserved_and_weighted():
    established = br_wardrobe.convert_item(_src(ownership="established"), {})
    candidate = br_wardrobe.convert_item(_src(ownership="candidate"), {})
    assert established["weight"] > candidate["weight"]
    assert established["source"]["ownership"] == "established"


def test_inspiration_records_are_excluded_by_default():
    """Inspiration records are looks from other people's photographs, not
    Octavia's clothes."""
    items = [_src(ownership="inspiration", wardrobe_item_id="x"),
             _src(ownership="candidate", wardrobe_item_id="y")]
    buckets = br_wardrobe.convert(items, {})
    ids = [r["id"] for recs in buckets.values() for r in recs]
    assert ids == ["y"]


def test_provenance_survives_conversion():
    rec = br_wardrobe.convert_item(_src(), {})
    assert rec["source"]["wardrobe_item_id"] == "black-tee"
    assert rec["source"]["source_reference"] == "a-1234"
    assert rec["source"]["catalogue"] == "octavia_studio"


def test_every_category_gets_the_fields_the_composer_needs():
    """Keying the defaults table on the source category rather than the
    wardrobe file silently left tops, bottoms and dresses with none."""
    needed = {"tops": ("fit", "length", "neckline", "sleeve"),
              "bottoms": ("cut", "length", "waist"),
              "dresses": ("cut", "length", "neckline", "sleeve")}
    for category, family in (("top", "tops"), ("bottom", "bottoms"),
                             ("dress", "dresses")):
        rec = br_wardrobe.convert_item(_src(category=category, name="Plain item"), {})
        for field in needed[family]:
            assert field in rec, f"{family} missing {field}"


def test_accessories_get_a_slot():
    """The composer refuses two accessories in one slot; a record without a
    slot raised a KeyError instead."""
    for name, slot in (("Black roomy tote", "carry"),
                       ("Black rectangular-buckle belt", "waist"),
                       ("Amethyst pendant on silver chain", "neck")):
        rec = br_wardrobe.convert_item(_src(name=name, category="accessory"), {})
        assert rec["slot"] == slot, f"{name} -> {rec['slot']}"


def test_lingerie_is_tagged_as_base_layer_only():
    """The source catalogues everything seen in a photograph, lingerie
    included. The content policy requires full coverage."""
    for name in ("Black lace brief", "Plum embroidered lace bra"):
        rec = br_wardrobe.convert_item(_src(name=name, category="top"), {})
        assert rec.get("base_layer_only") is True, name


def test_swimwear_is_tagged():
    rec = br_wardrobe.convert_item(
        _src(name="Plum square-neck one-piece swim garment", category="dress"), {})
    assert rec.get("swimwear") is True


def test_unsupported_category_is_skipped_not_guessed():
    assert br_wardrobe.convert_item(_src(category="furniture"), {}) is None


# ----------------------------------------------------------------------
# The imported catalogue as actually written
# ----------------------------------------------------------------------
@pytest.mark.skipif(not OBSERVED.is_dir(), reason="observed wardrobe not imported")
def test_observed_catalogue_loads_and_is_complete():
    from pipeline.sampler import Catalogue
    cat = Catalogue(prefer_observed=True)
    assert cat.observed
    assert len(cat.tops) > 20 and len(cat.bottoms) > 20
    for item in cat.tops + cat.bottoms:
        assert item["source"]["catalogue"] == "octavia_studio"


@pytest.mark.skipif(not OBSERVED.is_dir(), reason="observed wardrobe not imported")
def test_no_base_layer_garment_is_ever_worn_as_an_outer_layer():
    from pipeline.compose import Composer
    from pipeline.history import DiversityHistory
    from pipeline.sampler import Sampler, catalogue_for
    from pipeline.seeds import seed_record
    pol = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())
    cat = catalogue_for(CFG)
    for i in range(60):
        smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=1)
        spec = Composer(cat, smp, CFG, pol).compose("B", i, seed_record(i, "B", i))
        for key in ("top", "bottom", "dress", "outer_layer"):
            item = getattr(spec.wardrobe, key)
            if item:
                assert not item.get("base_layer_only"), f"{item['label']} worn as {key}"


@pytest.mark.skipif(not OBSERVED.is_dir(), reason="observed wardrobe not imported")
def test_real_garments_keep_their_own_colour():
    """An invented garment's colour is a free variable; a real garment's
    colour is a property of the item."""
    from pipeline.compose import Composer
    from pipeline.history import DiversityHistory
    from pipeline.sampler import Sampler, catalogue_for
    from pipeline.seeds import seed_record
    pol = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())
    cat = catalogue_for(CFG)
    checked = 0
    for i in range(40):
        smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=1)
        spec = Composer(cat, smp, CFG, pol).compose("K", i, seed_record(i, "K", i))
        for slot, key in (("top", "top"), ("bottom", "bottom"), ("dress", "dress")):
            item = getattr(spec.wardrobe, key)
            if item and item.get("colour_id"):
                assert spec.wardrobe.colours.get(slot) == item["colour_id"]
                checked += 1
    assert checked > 0


@pytest.mark.skipif(not OBSERVED.is_dir(), reason="observed wardrobe not imported")
def test_prompt_does_not_repeat_the_colour_already_in_the_name():
    """Observed garments are named "cream ribbed crop tank"; prefixing the
    colour again yields "cream cream ribbed crop tank"."""
    import re
    from pipeline.compose import Composer
    from pipeline.history import DiversityHistory
    from pipeline.prompt import build_prompts
    from pipeline.sampler import Sampler, catalogue_for
    from pipeline.seeds import seed_record
    pol = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())
    idn = yaml.safe_load((ROOT / "config/identity.yaml").read_text())
    cat = catalogue_for(CFG)
    for i in range(30):
        smp = Sampler(cat, DiversityHistory(24), CFG, planned_total=1)
        spec = Composer(cat, smp, CFG, pol).compose("P", i, seed_record(i, "P", i))
        prompt, _ = build_prompts(spec, idn, PHY, pol, cat, CFG.get("identity", {}),
                                  {"tier": "full"})
        m = re.search(r"\b(\w+) \1\b", prompt)
        assert m is None, f"repeated word {m.group(0)!r} in: {prompt[:160]}"


# ----------------------------------------------------------------------
# Canon alignment
# ----------------------------------------------------------------------
def test_numeric_ratios_are_not_asserted_in_prompts():
    """Established canon: preserve her shape without estimating numerical
    measurements. The ratios remain for QC, which measures an output rather
    than dictating a measurement to the model."""
    assert PHY["prompt"]["include_ratios"] is False
    assert PHY["ratios"]["shoulder_to_waist"], "ratios still available to QC"


def test_clothes_adapt_to_her_not_the_reverse():
    negatives = [n.lower() for n in PHY["physique_negatives"]]
    assert any("reshaped to fit" in n for n in negatives)


# ----------------------------------------------------------------------
# Shoot export
# ----------------------------------------------------------------------
def _record(tmp, idx=0):
    img = pathlib.Path(tmp) / f"f{idx}.png"
    from PIL import Image
    Image.new("RGB", (64, 80), (90, 90, 100)).save(img)
    return {
        "frame_id": f"R_{idx:03d}", "index": idx, "image_path": str(img),
        "prompt": "a prompt", "negative_prompt": "a negative",
        "seeds": {"identity_seed": 1}, "overall_score": 91.2, "scorer": "heuristic-stub",
        "spec": {
            "pose": {"label": "standing relaxed"},
            "camera": {"shot": {"label": "waist-up framing"}},
            "expression": {"label": "a small smile"},
            "scene": {"label": "a bright loft"},
            "head": {"roll": 1.0, "yaw": -2.0},
            "lighting": {"label": "soft window daylight"},
            "wardrobe": {
                "top": {"id": "x", "source": {"wardrobe_item_id": "black-tee"}},
                "accessories": [{"id": "purple_crystal_pendant"}],
            },
        },
    }


def test_export_bundle_has_the_expected_files():
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "bundle"
        result = br_export.build_bundle([_record(tmp)], out, "sh-1", "RUN")
        assert result["frames"] == 1
        for name in ("import.sh", "annotate.sh", "intent.json", "README.md"):
            assert (out / name).is_file(), name


def test_intent_is_labelled_as_intent_not_observation():
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "b"
        br_export.build_bundle([_record(tmp)], out, "sh-1", "RUN")
        doc = json.loads((out / "intent.json").read_text())
        assert "REQUESTED" in doc["WARNING"]
        assert doc["frames"][0]["intent"]["pose"] == "standing relaxed"


def test_annotation_commands_are_commented_out():
    """This studio knows what was requested; the catalogue records what is
    observed. Auto-recording intent as observation would corrupt continuity."""
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "b"
        br_export.build_bundle([_record(tmp)], out, "sh-1", "RUN")
        for line in (out / "annotate.sh").read_text().splitlines():
            if "asset annotate" in line:
                assert line.lstrip().startswith("#"), f"live annotate line: {line}"


def test_pendant_is_unknown_even_when_requested():
    """Canon: unknown is not absence, and a request is not evidence."""
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "b"
        br_export.build_bundle([_record(tmp)], out, "sh-1", "RUN")
        text = (out / "annotate.sh").read_text()
        assert "--pendant unknown" in text
        assert "--pendant present" not in text
        doc = json.loads((out / "intent.json").read_text())
        assert doc["frames"][0]["intent"]["pendant_requested"] is True


def test_import_script_creates_the_shoot_and_imports_each_frame():
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "b"
        records = [_record(tmp, i) for i in range(3)]
        br_export.build_bundle(records, out, "sh-2", "RUN")
        text = (out / "import.sh").read_text()
        assert "shoot create sh-2" in text
        assert text.count("octavia.py import") == 3


def test_frames_without_a_real_image_are_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        good = _record(tmp, 0)
        missing = _record(tmp, 1)
        missing["image_path"] = str(pathlib.Path(tmp) / "nope.png")
        result = br_export.build_bundle([good, missing], pathlib.Path(tmp) / "b",
                                        "sh-3", "RUN")
        assert result["frames"] == 1


def test_placeholder_qc_scores_are_flagged_to_the_catalogue():
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "b"
        br_export.build_bundle([_record(tmp)], out, "sh-1", "RUN")
        doc = json.loads((out / "intent.json").read_text())
        qc = doc["frames"][0]["studio_qc"]
        assert qc["placeholder_metrics"] is True
        assert "placeholders" in qc["note"]
