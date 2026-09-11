"""CLIP token budgeting for prompt construction.

WHY THIS MATTERS MORE THAN IT LOOKS
-----------------------------------
CLIP text encoders process 77 tokens at a time (75 content + BOS/EOS).
Longer prompts are split into chunks, each encoded separately and then
concatenated. The practical consequence: a term's influence drops sharply
once it falls past the first chunk, and terms in chunk 4 barely register.

A 800-token prompt is therefore not "a very detailed prompt" — it is a
75-token prompt followed by 700 tokens of decreasingly-effective noise.
For a persistent-identity system this is fatal in a specific way: if the
identity anchors overrun chunk 1, the very thing that must dominate is the
thing being diluted.

So prompt building has to be budget-aware, and identity has to be
guaranteed a place in chunk 1.

ESTIMATION ACCURACY
-------------------
`estimate_tokens` approximates CLIP's BPE without shipping the vocabulary.
It is typically within ~10% on ordinary English prompt text and is
deliberately biased to OVER-count, so a prompt that fits by this estimate
fits in reality. If `transformers` is installed, `exact_tokens` uses the
real tokenizer; `count_tokens` prefers it automatically and reports which
method was used, so nothing downstream mistakes an estimate for a fact.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

CHUNK_SIZE = 77
CONTENT_PER_CHUNK = 75          # BOS + EOS consume two slots

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+|[^\sA-Za-z\d]")

# Common prompt words that BPE encodes as a single token despite length.
_SINGLE_TOKEN_LONG = {
    "photorealistic", "photograph", "photography", "portrait", "lighting",
    "background", "beautiful", "detailed", "realistic", "natural", "texture",
    "shoulders", "expression", "editorial", "cinematic", "composition",
}


def _word_tokens(word: str) -> int:
    """Estimated BPE tokens for one word."""
    if not word.isalpha():
        return 1
    lower = word.lower()
    if lower in _SINGLE_TOKEN_LONG:
        return 1
    n = len(word)
    if n <= 4:
        return 1
    if n <= 7:
        return 1
    if n <= 11:
        return 2
    return math.ceil(n / 4.5)


def estimate_tokens(text: str) -> int:
    """Approximate CLIP token count. Biased to over-count."""
    if not text.strip():
        return 0
    return sum(_word_tokens(tok) for tok in _WORD_RE.findall(text))


def exact_tokens(text: str) -> Optional[int]:
    """Real CLIP token count, if transformers is available."""
    try:
        from transformers import CLIPTokenizerFast
    except ImportError:
        return None
    try:
        tok = exact_tokens._tokenizer                      # type: ignore[attr-defined]
    except AttributeError:
        try:
            tok = CLIPTokenizerFast.from_pretrained("openai/clip-vit-large-patch14")
        except Exception:
            return None
        exact_tokens._tokenizer = tok                      # type: ignore[attr-defined]
    return len(tok(text, add_special_tokens=False)["input_ids"])


def count_tokens(text: str) -> Dict[str, Any]:
    exact = exact_tokens(text)
    if exact is not None:
        return {"tokens": exact, "method": "clip-tokenizer", "exact": True}
    return {"tokens": estimate_tokens(text), "method": "heuristic-estimate",
            "exact": False}


@dataclass
class BudgetReport:
    tokens: int
    method: str
    exact: bool
    chunks: int
    fits_single_chunk: bool
    tokens_in_first_chunk: int
    overflow_tokens: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokens": self.tokens, "method": self.method, "exact": self.exact,
            "chunks": self.chunks, "fits_single_chunk": self.fits_single_chunk,
            "tokens_in_first_chunk": self.tokens_in_first_chunk,
            "overflow_tokens": self.overflow_tokens,
        }


def budget(text: str) -> BudgetReport:
    c = count_tokens(text)
    n = c["tokens"]
    chunks = max(1, math.ceil(n / CONTENT_PER_CHUNK)) if n else 0
    return BudgetReport(
        tokens=n, method=c["method"], exact=c["exact"], chunks=chunks,
        fits_single_chunk=n <= CONTENT_PER_CHUNK,
        tokens_in_first_chunk=min(n, CONTENT_PER_CHUNK),
        overflow_tokens=max(0, n - CONTENT_PER_CHUNK),
    )


def fit_segments(segments: Sequence[str], limit: int = CONTENT_PER_CHUNK) -> Dict[str, Any]:
    """Greedily take segments in order until the token limit is reached.

    Segments are assumed pre-sorted by priority, so this keeps the most
    important material and drops the tail rather than truncating mid-phrase
    (which is what the encoder itself would do, often mid-word).
    """
    kept: List[str] = []
    dropped: List[str] = []
    used = 0
    for seg in segments:
        cost = estimate_tokens(seg) + 1        # + separator
        if used + cost <= limit:
            kept.append(seg)
            used += cost
        else:
            dropped.append(seg)
    return {"kept": kept, "dropped": dropped, "tokens_used": used,
            "limit": limit, "headroom": limit - used}


def chunk_map(segments: Sequence[str]) -> List[Dict[str, Any]]:
    """Which CLIP chunk each segment lands in — the diagnostic that shows
    whether identity actually made it into chunk 1."""
    out: List[Dict[str, Any]] = []
    running = 0
    for seg in segments:
        start = running
        cost = estimate_tokens(seg) + 1
        running += cost
        out.append({
            "segment": seg[:60],
            "tokens": cost,
            "chunk": start // CONTENT_PER_CHUNK,
            "position": start,
        })
    return out
