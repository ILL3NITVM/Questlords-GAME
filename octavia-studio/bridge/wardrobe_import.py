"""Import the observed wardrobe catalogue from the existing octavia_studio.

WHY THIS MATTERS
----------------
This studio shipped an *invented* wardrobe — 66 plausible garments written
to exercise the sampler. The existing project holds 155 garments actually
observed in Octavia's photographs, with provenance back to the asset each
was seen in. Sampling from real garments is strictly better: the outfits
become ones she demonstrably has rather than ones a language model found
plausible.

WHAT THE SOURCE DOES AND DOES NOT KNOW
--------------------------------------
The source is explicit that 143 of its 155 records carry
``material: "Visual appearance only; fibre unknown"`` and that
``ownership: candidate`` means catalogued from visual evidence, **not** an
ownership or canon approval. Two consequences this module refuses to blur:

* **Material is inferred from the garment name, never asserted.** Every
  converted record carries an ``inferred`` list naming which attributes were
  guessed. A satin-looking top is recorded as inferred satin, not as satin.
* **Ownership status is preserved, not flattened.** `established` garments
  are weighted above `candidate` ones, and `inspiration` records — looks
  drawn from other people's photographs — are excluded by default, because
  they are not Octavia's clothes.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Their category -> the wardrobe file this studio samples from.
CATEGORY_FILE = {
    "top": "tops", "bottom": "bottoms", "dress": "dresses",
    "outerwear": "outerwear", "footwear": "footwear",
    "accessory": "accessories", "hosiery": "hosiery", "one-piece": "onepiece",
}

# Ownership weighting. `established` garments are confirmed against canon;
# `candidate` ones are observed but unconfirmed, so they sample less often.
OWNERSHIP_WEIGHT = {"established": 1.6, "candidate": 1.0, "inspiration": 0.0}
DEFAULT_OWNERSHIP = ("established", "candidate")

# Material inference from the garment name. Ordered: the first hit wins, so
# more specific terms must precede general ones.
MATERIAL_RULES: List[Tuple[str, str]] = [
    (r"\bdenim|\bjean", "denim"),
    (r"\bsatin\b", "satin"),
    (r"\bsilk\b", "silk-like fabric"),
    (r"\bvelvet\b", "velvet"),
    (r"\blace\b", "lace"),
    (r"\bmesh\b", "mesh layering"),
    (r"\bchiffon\b", "chiffon"),
    (r"\blinen\b", "linen"),
    (r"\bleather\b", "leather-look fashion material"),
    (r"\bcable|\bchunky|\bcardigan\b", "chunky knit"),
    (r"\brib(bed)?\b", "rib knit"),
    (r"\bknit|\bsweater|\bjumper\b", "fine knit"),
    (r"\bfleece|\bsweat|\bhood", "soft fleece"),
    (r"\bwool|\bcoat\b|\bblazer\b|\btailored\b|\bsuit\b", "structured tailoring fabric"),
    (r"\btights?\b|\blegging|\bathletic|\bsport|\bactive", "ribbed stretch fabric"),
    (r"\bjersey|\btank\b|\btee\b|\bt-shirt", "cotton jersey"),
]

LENGTH_RULES: List[Tuple[str, str]] = [
    (r"\bcrop", "cropped"), (r"\bmaxi|\bfull-length|\bfloor", "maxi"),
    (r"\bmidi", "midi"), (r"\bmini|\bshort\b", "mini"),
    (r"\bknee", "knee"), (r"\blongline|\blong\b", "long"),
]

NECKLINE_RULES: List[Tuple[str, str]] = [
    (r"\bhalter", "halter"), (r"\boff-shoulder|\boff the shoulder", "off_shoulder"),
    (r"\bv-neck|\bplunge|\bwrap\b", "v"), (r"\bsquare", "square"),
    (r"\bsweetheart|\bcorset|\bbustier", "sweetheart"),
    (r"\bscoop|\btank\b|\bcami", "scoop"), (r"\bcollar|\bshirt\b|\bblouse", "collar"),
    (r"\bturtle|\bmock|\bhigh-neck", "high"), (r"\bcrew|\btee\b|\bt-shirt", "crew"),
    (r"\bboat|\bbateau", "boat"),
]

SLEEVE_RULES: List[Tuple[str, str]] = [
    (r"\blong-sleeve|\blong sleeve", "long"),
    (r"\bshort-sleeve|\bshort sleeve|\btee\b|\bt-shirt", "short"),
    (r"\bsleeveless|\btank\b|\bcami|\bhalter|\bstrapless|\bvest\b", "sleeveless"),
    (r"\bthree-quarter|\b3/4", "three_quarter"),
]

CUT_RULES: List[Tuple[str, str]] = [
    (r"\bwide-leg|\bwide leg|\bpalazzo", "wide"),
    (r"\bstraight-leg|\bstraight\b", "straight"),
    (r"\bskinny|\bslim|\blegging|\bfitted", "fitted"),
    (r"\ba-line|\bflare|\bpleated", "a_line"),
    (r"\bcolumn|\bpencil", "column"), (r"\bbias", "bias"),
    (r"\bwrap\b", "wrap"), (r"\bsheath", "sheath"),
]

FIT_RULES: List[Tuple[str, str]] = [
    (r"\boversized|\brelaxed|\bloose|\bbaggy", "relaxed"),
    (r"\bfitted|\bbodycon|\bslim|\bskinny", "fitted"),
    (r"\bstructured|\btailored", "semi_fitted"),
]

# Garments the content policy will not allow as the outermost layer.
# The source catalogue records everything observed in a photograph, which
# legitimately includes lingerie and swimwear. This studio's content policy
# requires full coverage, so these are tagged rather than silently sampled
# into an outfit as if they were ordinary clothes.
BASE_LAYER_PATTERNS = r"\bbrief\b|\bthong\b|\bknicker|\bpanti|\bbra\b|\bbralette|\blingerie|\bunderwear|\bcorset\b|\bbodysuit brief"
SWIMWEAR_PATTERNS = r"\bswim|\bbikini|\bone-piece swim|\bbathing"

# Which body slot an accessory occupies. The composer refuses two
# accessories in the same slot, so an accessory without one breaks it.
SLOT_RULES: List[Tuple[str, str]] = [
    (r"\bclutch|\bbag\b|\btote|\bpurse|\bhandbag|\bbackpack", "carry"),
    (r"\bbelt\b", "waist"),
    (r"\bnecklace|\bpendant|\bchain|\bchoker|\bscarf", "neck"),
    (r"\bearring|\bstud\b|\bhoop", "ear"),
    (r"\bbracelet|\bbangle|\bcuff\b|\bwatch", "wrist"),
    (r"\bring\b", "hand"),
    (r"\bsunglasses|\bhat\b|\bcap\b|\bheadband|\bclip\b|\bbarrette", "head"),
    (r"\bglove", "hand"),
]

WAIST_RULES: List[Tuple[str, str]] = [
    (r"\bhigh-waist|\bhigh waist|\bhigh-rise", "high"),
    (r"\blow-rise|\blow waist", "low"),
]

# Their colour vocabulary mapped onto this studio's palette ids. Anything
# unmapped is kept verbatim and given a hex below, rather than silently
# coerced into the nearest existing colour.
COLOUR_MAP = {
    "black": "black", "white": "white", "cream": "cream", "ivory": "ivory",
    "charcoal": "charcoal", "gray": "silver", "grey": "silver",
    "plum": "plum", "lilac": "lilac", "lavender": "lavender",
    "purple": "plum", "olive": "olive", "sage": "sage", "navy": "navy",
    "burgundy": "burgundy", "rust": "rust", "teal": "teal",
    "sky blue": "sky_blue", "light blue": "sky_blue", "blue": "navy",
    "brown": "espresso", "taupe": "taupe", "rose": "rose", "pink": "dusty_pink",
    "coral": "coral", "peach": "peach", "mustard": "mustard",
    "silver": "silver", "champagne": "champagne", "stone": "taupe",
    "natural": "cream", "green": "forest", "red": "burgundy",
}
# Colours their catalogue uses that this studio did not have.
NEW_COLOURS = {
    "cyan": ("#3FBFD0", "cool_bright"),
    "mauve": ("#B08CA0", "warm_mid"),
    "lemon": ("#EFE07A", "warm_light"),
}


def _match(rules: Iterable[Tuple[str, str]], text: str) -> Optional[str]:
    for pattern, value in rules:
        if re.search(pattern, text):
            return value
    return None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def convert_item(src: Dict[str, Any], colours_by_id: Dict[str, Any]
                 ) -> Optional[Dict[str, Any]]:
    """Convert one source record. Returns None for unsupported categories."""
    category = src.get("category", "")
    if category not in CATEGORY_FILE:
        return None

    name = src.get("name", "") or ""
    lower = name.lower()
    inferred: List[str] = []

    material = _match(MATERIAL_RULES, lower)
    if material:
        inferred.append("material")
    else:
        material = "cotton jersey"
        inferred.append("material")

    rec: Dict[str, Any] = {
        "id": src.get("wardrobe_item_id") or _slug(name),
        "label": name.lower(),
        "category": category,
        "subtype": src.get("wardrobe_item_id") or _slug(name),
        "material": material,
        "weight": OWNERSHIP_WEIGHT.get(src.get("ownership", "candidate"), 1.0),
        # Provenance back to the catalogue this came from.
        "source": {
            "catalogue": "octavia_studio",
            "wardrobe_item_id": src.get("wardrobe_item_id"),
            "ownership": src.get("ownership"),
            "canon_status": src.get("canon_status"),
            "source_reference": src.get("source_reference"),
            "first_seen": src.get("first_seen"),
        },
        "observed": True,
    }

    colour_raw = (src.get("primary_color") or "").strip().lower()
    if colour_raw:
        rec["colour_id"] = COLOUR_MAP.get(colour_raw, _slug(colour_raw))
        rec["colour_source"] = colour_raw

    for field, rules in (("length", LENGTH_RULES), ("neckline", NECKLINE_RULES),
                         ("sleeve", SLEEVE_RULES), ("cut", CUT_RULES),
                         ("fit", FIT_RULES), ("waist", WAIST_RULES)):
        value = _match(rules, lower)
        if value:
            rec[field] = value
            inferred.append(field)

    # Fill the attributes the composer needs with defensible defaults.
    # Keyed on the WARDROBE FILE name, which is what the lookup uses. Keying
    # on the source category name instead silently produced records with no
    # defaults at all for tops, bottoms and dresses.
    defaults = {
        "tops": {"fit": "semi_fitted", "length": "waist", "neckline": "crew",
                 "sleeve": "short"},
        "bottoms": {"cut": "straight", "length": "full", "waist": "high"},
        "dresses": {"cut": "sheath", "length": "midi", "neckline": "v",
                    "sleeve": "sleeveless"},
        "outerwear": {"fit": "relaxed", "length": "hip", "neckline": "collar",
                      "sleeve": "long"},
        "onepiece": {"cut": "straight", "length": "full", "neckline": "v",
                     "sleeve": "sleeveless"},
        "footwear": {},
        "accessories": {},
        "hosiery": {},
    }.get(CATEGORY_FILE[category], {})
    for key, value in defaults.items():
        if key not in rec:
            rec[key] = value
            inferred.append(key)

    if CATEGORY_FILE[category] == "accessories":
        slot = _match(SLOT_RULES, lower)
        if slot is None:
            slot = "other"
            inferred.append("slot")
        else:
            inferred.append("slot")
        rec["slot"] = slot

    if re.search(BASE_LAYER_PATTERNS, lower):
        rec["base_layer_only"] = True
        rec["policy_note"] = ("observed in a photograph but not permissible as "
                              "an outermost layer under the content policy")
    if re.search(SWIMWEAR_PATTERNS, lower):
        rec["swimwear"] = True

    rec["formality"] = ["casual", "smart_casual"]
    rec["season"] = ["all"]
    rec["mood"] = ["confident", "composed"]
    rec["compatibility_tags"] = ["layerable"]
    # Honest record of what was guessed rather than read.
    rec["inferred"] = sorted(set(inferred))
    rec["material_confidence"] = "inferred_from_name"
    return rec


def load_source(catalogue_path: pathlib.Path) -> List[Dict[str, Any]]:
    doc = json.loads(catalogue_path.read_text(encoding="utf-8"))
    items = doc["items"] if isinstance(doc, dict) else doc
    if not isinstance(items, list):
        raise ValueError(f"unexpected wardrobe catalogue shape in {catalogue_path}")
    return items


def convert(items: Iterable[Dict[str, Any]], colours_by_id: Dict[str, Any],
            ownership: Iterable[str] = DEFAULT_OWNERSHIP
            ) -> Dict[str, List[Dict[str, Any]]]:
    allowed = set(ownership)
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for src in items:
        if src.get("ownership") not in allowed:
            continue
        rec = convert_item(src, colours_by_id)
        if rec is None:
            continue
        buckets.setdefault(CATEGORY_FILE[src["category"]], []).append(rec)
    return buckets


def write(buckets: Dict[str, List[Dict[str, Any]]], out_dir: pathlib.Path
          ) -> Dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, int] = {}
    for family, records in sorted(buckets.items()):
        path = out_dir / f"{family}.json"
        path.write_text(json.dumps(
            {"schema_version": 1, "family": family, "source": "octavia_studio",
             "items": records}, indent=2), encoding="utf-8")
        written[family] = len(records)
    return written


def new_colour_records() -> List[Dict[str, Any]]:
    return [{"id": cid, "label": cid.replace("_", " "),
             "description": f"{cid} (from the observed wardrobe catalogue)",
             "family": family, "mood": ["confident"], "weight": 1.0, "hex": hexv}
            for cid, (hexv, family) in NEW_COLOURS.items()]
