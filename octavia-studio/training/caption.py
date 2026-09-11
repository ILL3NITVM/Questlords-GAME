"""Caption generation for LoRA training.

THE CENTRAL RULE, AND IT IS COUNTERINTUITIVE
--------------------------------------------
During LoRA training, a caption tells the model "this part of the image is
explained by these words." Anything you NAME becomes a variable the model
binds to that word. Anything you LEAVE OUT but that is consistently present
gets absorbed into the trigger token.

So for a persistent-identity LoRA the strategy inverts what you would
expect:

    DO NOT caption identity.  Never write "green hazel eyes", "freckles",
    "lime-green highlights", "brunette". Naming them binds them to those
    words, so they only appear when you say the words, and they drift when
    you do not. Omitting them binds them to the trigger token, which is
    exactly what a persistent persona needs.

    DO caption everything variable.  Pose, framing, clothing, scene,
    lighting, expression. Naming these lets the model factor them OUT of
    the identity, so the trigger token means "Octavia" rather than
    "Octavia in a pink crop top indoors".

This is the exact inverse of pipeline/prompt.py, which spells identity out
in full because it has no adapter to lean on. Once a LoRA exists, that
descriptive block becomes redundant and actively harmful — it competes
with the adapter. Switch config/studio.yaml to
`identity.mode: lora_token` at that point; prompt.py handles the rest.

WHAT THIS MODULE CAN AND CANNOT DO
----------------------------------
Writing an accurate variable-axis caption requires SEEING the image. This
module therefore does two things:

  * `template_captions()` — emits correct, trigger-token-anchored caption
    scaffolds with the variable slots left as TODO markers, plus a CSV for
    bulk human editing. Honest, immediately usable, no model required.

  * `CaptionBackend` — the interface a real captioner (BLIP2, CogVLM,
    WD14 tagger, or a vision LLM) implements to fill those slots
    automatically. `FilterCaptionBackend` wraps any such captioner and
    strips identity terms from its output, which is the part people get
    wrong when they point an off-the-shelf tagger at a persona dataset.
"""
from __future__ import annotations

import abc
import csv
import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from training.ingest import ImageRecord

# Terms that must never survive into a training caption, because each one
# is part of Octavia's fixed identity. Sourced conceptually from
# config/identity.yaml; kept here as patterns because captioners phrase
# things loosely ("greenish eyes", "freckled face").
IDENTITY_TERM_PATTERNS = [
    r"\b(green|hazel|greenish|emerald)[- ]?(eyed|eyes)\b",
    r"\bfreckle\w*\b",
    r"\b(lime|olive|chartreuse|neon)[- ]?green\s+(hair|highlights?|streaks?|strands?)\b",
    r"\bhighlights?\b",
    r"\b(brunette|brown[- ]haired|dark[- ]haired|long[- ]haired)\b",
    r"\b(brown|dark|black|espresso)\s+hair\b",
    r"\bhair\s+colou?r\b",
    r"\b(thick|dark|expressive)\s+(eyebrows?|brows?)\b",
    r"\b(olive|tan|light|fair|warm)\s+skin(\s+tone)?\b",
    r"\bskin\s+tone\b",
    r"\bpurple\s+(crystal\s+)?(pendant|necklace)\b",
    r"\b(beautiful|pretty|attractive|gorgeous|stunning)\b",   # aesthetic noise
    r"\b(woman|girl|lady|female)\b",                          # carried by the token
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in IDENTITY_TERM_PATTERNS]

# Variable axes a good training caption SHOULD describe.
CAPTION_SLOTS = [
    ("framing", "close portrait | head and shoulders | waist up | three-quarter | full body"),
    ("pose", "standing | seated | leaning | walking | what the hands and body are doing"),
    ("head", "facing camera | three-quarter left | three-quarter right | profile | looking away"),
    ("expression", "neutral | slight smile | warm smile | laughing | thoughtful"),
    ("clothing", "garment type, colour, material — the OUTFIT, not the body"),
    ("setting", "where it was shot"),
    ("lighting", "soft window light | golden hour | studio softbox | warm lamplight"),
]


# Words that carry no meaning on their own. A clause left holding only
# these after identity terms are removed is debris and gets dropped.
_FUNCTION_WORDS = {
    "a", "an", "the", "with", "and", "or", "of", "in", "on", "at", "to",
    "her", "his", "their", "its", "she", "he", "they", "is", "are", "was",
    "were", "has", "have", "had", "who", "that", "which", "very", "quite",
    "some", "this", "these", "those", "as", "by", "for",
}

# Words that are fine mid-clause but carry nothing when a clause collapses
# to just them — usually the verb whose object was an identity term.
_DANGLING_ALONE = {
    "wearing", "holding", "featuring", "showing", "depicting", "having",
    "photo", "photograph", "image", "picture", "portrait of", "shot",
}


def _clean_clause(clause: str) -> str:
    """Strip identity terms from one clause; return '' if nothing survives."""
    out = clause
    for rx in _COMPILED:
        out = rx.sub(" ", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,;")
    if not out:
        return ""
    # Drop leading/trailing dangling function words left by the removal.
    tokens = out.split()
    while tokens and tokens[0].lower().strip(".,") in _FUNCTION_WORDS:
        tokens.pop(0)
    while tokens and tokens[-1].lower().strip(".,") in _FUNCTION_WORDS:
        tokens.pop()
    if not tokens:
        return ""
    # A clause that is now nothing but function words carries no information.
    if all(t.lower().strip(".,") in _FUNCTION_WORDS for t in tokens):
        return ""
    # A single leftover verb or medium-word whose object was stripped.
    if len(tokens) == 1 and tokens[0].lower().strip(".,") in _DANGLING_ALONE:
        return ""
    return " ".join(tokens).strip(" ,;")


def strip_identity_terms(caption: str) -> str:
    """Remove identity vocabulary from a caption produced by any captioner.

    Works clause by clause so that removing a term does not leave
    ungrammatical debris ("a with and") in the training caption. A clause
    that consisted only of identity description is dropped entirely.
    """
    clauses = [c for c in re.split(r"\s*,\s*", caption) if c.strip()]
    kept = [c for c in (_clean_clause(c) for c in clauses) if c]
    return ", ".join(kept)


def compose_caption(trigger: str, parts: Sequence[str], class_token: str = "") -> str:
    """Trigger token always leads; class token (if any) immediately follows."""
    head = trigger if not class_token else f"{trigger} {class_token}"
    cleaned = [strip_identity_terms(p) for p in parts]
    cleaned = [p for p in cleaned if p]
    return ", ".join([head] + cleaned)


# ----------------------------------------------------------------------
class CaptionBackend(abc.ABC):
    """Interface for an automatic captioner."""

    name = "base"

    @abc.abstractmethod
    def describe(self, image_path: pathlib.Path) -> str:
        """Return a free-text description of the VARIABLE content."""


class FilterCaptionBackend(CaptionBackend):
    """Wraps any captioner and enforces the identity-omission rule.

    Point this at BLIP2, CogVLM, WD14 or a vision LLM. Off-the-shelf
    captioners will happily emit "a brunette woman with green eyes and
    freckles" — precisely the terms that must not be in a persona caption.
    This strips them before the caption reaches the training set.
    """

    def __init__(self, inner: CaptionBackend, trigger: str, class_token: str = "") -> None:
        self.inner = inner
        self.trigger = trigger
        self.class_token = class_token
        self.name = f"filtered({inner.name})"

    def describe(self, image_path: pathlib.Path) -> str:
        return compose_caption(self.trigger, [self.inner.describe(image_path)],
                               self.class_token)


# ----------------------------------------------------------------------
def template_caption(trigger: str, class_token: str = "") -> str:
    head = trigger if not class_token else f"{trigger} {class_token}"
    slots = ", ".join(f"TODO_{name}" for name, _ in CAPTION_SLOTS)
    return f"{head}, {slots}"


def write_caption_sheet(records: Sequence[ImageRecord], path: pathlib.Path,
                        trigger: str, class_token: str = "") -> pathlib.Path:
    """CSV for bulk human captioning — one row per selected image."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["filename", "width", "height", "bucket", "cluster"] +
                   [name for name, _ in CAPTION_SLOTS] + ["final_caption"])
        for r in records:
            if not r.selected:
                continue
            w.writerow([r.filename, r.width, r.height, r.bucket, r.cluster] +
                       ["" for _ in CAPTION_SLOTS] + [""])
    return path


def read_caption_sheet(path: pathlib.Path, trigger: str,
                       class_token: str = "") -> Dict[str, str]:
    """Assemble captions from a filled-in sheet.

    ``final_caption`` wins if present; otherwise the per-axis columns are
    joined. Identity terms are stripped either way — a human filling the
    sheet is just as likely to write "green eyes" out of habit.
    """
    if not path.is_file():
        return {}
    out: Dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("filename") or "").strip()
            if not name:
                continue
            final = (row.get("final_caption") or "").strip()
            if final:
                caption = final if final.startswith(trigger) else \
                    compose_caption(trigger, [final], class_token)
                out[name] = strip_identity_terms(caption) if final.startswith(trigger) \
                    else caption
            else:
                parts = [(row.get(slot) or "").strip() for slot, _ in CAPTION_SLOTS]
                parts = [p for p in parts if p]
                if parts:
                    out[name] = compose_caption(trigger, parts, class_token)
    return out


def apply_captions(records: Sequence[ImageRecord], captions: Dict[str, str],
                   trigger: str, class_token: str = "",
                   backend: Optional[CaptionBackend] = None) -> Dict[str, Any]:
    filled = templated = 0
    for r in records:
        if not r.selected:
            continue
        if r.filename in captions:
            r.caption = captions[r.filename]
            filled += 1
        elif backend is not None:
            r.caption = compose_caption(trigger, [backend.describe(pathlib.Path(r.path))],
                                        class_token)
            filled += 1
        else:
            r.caption = template_caption(trigger, class_token)
            templated += 1
    return {"captioned": filled, "templated": templated,
            "backend": backend.name if backend else None}
