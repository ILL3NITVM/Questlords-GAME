"""Deterministic per-axis seed derivation.

Every axis of a frame gets its own RNG stream, derived from
(master_seed, run_id, frame_index, axis_name) via BLAKE2b. Two consequences:

* Reproducibility — re-running a run id with the same master seed and the
  same data/ + config/ contents rebuilds byte-identical FrameSpecs.
* Independence — re-rolling only the pose axis of frame 17 leaves its
  wardrobe, scene and camera choices untouched.
"""
from __future__ import annotations

import hashlib
import random
import secrets
from typing import Optional

from pipeline.spec import SEED_AXES, SeedRecord

_MASK = (1 << 32) - 1


def new_master_seed() -> int:
    return secrets.randbits(32)


def derive(master_seed: int, run_id: str, index: int, axis: str) -> int:
    """Derive a stable 32-bit seed for one axis of one frame."""
    payload = f"{master_seed}|{run_id}|{index}|{axis}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") & _MASK


def seed_record(master_seed: int, run_id: str, index: int) -> SeedRecord:
    return SeedRecord(**{axis: derive(master_seed, run_id, index, axis) for axis in SEED_AXES})


def rng_for(seed: int) -> random.Random:
    return random.Random(seed)


def reroll_axes(record: SeedRecord, axes, master_seed: int, run_id: str,
                index: int, salt: int = 1) -> SeedRecord:
    """Return a copy of ``record`` with only ``axes`` re-derived.

    Used by ``studio.py reroll`` so a rejected frame can keep everything that
    was good about it and change only the part that failed QC.
    """
    data = record.to_dict()
    for axis in axes:
        if axis not in SEED_AXES:
            raise ValueError(f"unknown seed axis: {axis}")
        data[axis] = derive(master_seed, f"{run_id}#reroll{salt}", index, axis)
    return SeedRecord.from_dict(data)


def resolve_master_seed(explicit: Optional[int]) -> int:
    return int(explicit) if explicit is not None else new_master_seed()
