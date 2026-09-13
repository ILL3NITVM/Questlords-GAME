"""Weighted, history-aware sampling of every variable axis of a frame.

The core of section 10 (anti-collapse) and section 12 (left-tilt suppression).

Weighting model for a candidate ``c`` on axis ``a``::

    w(c) = base(c)
         * feedback(a, c)                       # human review, section 13
         * (1 / (1 + window_count(a, c))) ** pressure
         * (1 / (1 + 0.5 * total_count(a, c))) ** (pressure * 0.5)
         * cap_penalty(a, c)                    # 0.02 once a share cap is hit

The window term suppresses local repetition; the totals term suppresses
campaign-wide over-representation; the cap term is a near-hard stop. Weights
are never driven to exactly zero — if every candidate on an axis is capped we
still need to return something, and renormalisation handles that gracefully.
"""
from __future__ import annotations

import json
import logging
import pathlib
import random
from typing import Any, Callable, Dict, List, Optional, Sequence

from pipeline.history import DiversityHistory

log = logging.getLogger("octavia.sampler")

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------
def _load(relpath: str) -> Dict[str, Any]:
    with open(DATA / relpath, "r", encoding="utf-8") as fh:
        return json.load(fh)


class Catalogue:
    """All sampleable data, loaded once."""

    def __init__(self, prefer_observed: bool = False) -> None:
        self.observed = False
        self.outerwear: List[Dict[str, Any]] = []
        obs = DATA / "wardrobe/observed"
        if prefer_observed and obs.is_dir() and any(obs.glob("*.json")):
            # Garments actually observed in Octavia's photographs, imported
            # from the octavia_studio catalogue. Strictly better than the
            # invented set: these are clothes she demonstrably has.
            def _obs(name: str) -> List[Dict[str, Any]]:
                path = obs / f"{name}.json"
                if not path.is_file():
                    return []
                return json.loads(path.read_text(encoding="utf-8"))["items"]

            self.tops = _obs("tops")
            self.bottoms = _obs("bottoms")
            self.dresses = _obs("dresses") + _obs("onepiece")
            self.footwear = _obs("footwear")
            self.accessories = _obs("accessories") or _load(
                "wardrobe/accessories.json")["items"]
            self.outerwear = _obs("outerwear")
            self.observed = True
            if not (self.tops and self.bottoms):
                log.warning("observed wardrobe incomplete; falling back to the "
                            "invented set")
                self.observed = False
        if not self.observed:
            self.tops = _load("wardrobe/tops.json")["items"]
            self.bottoms = _load("wardrobe/bottoms.json")["items"]
            self.dresses = _load("wardrobe/dresses.json")["items"]
            self.footwear = _load("wardrobe/footwear.json")["items"]
            self.accessories = _load("wardrobe/accessories.json")["items"]
        self.materials = {m["label"]: m for m in _load("materials/materials.json")["items"]}
        self.colours = _load("palettes/colours.json")["items"]
        self.colours_by_id = {c["id"]: c for c in self.colours}
        self.harmonies = _load("palettes/harmonies.json")["items"]
        self.scenes = _load("scenes/scenes.json")["items"]
        self.lighting = _load("scenes/lighting.json")["items"]
        self.focal = _load("scenes/camera_focal.json")["items"]
        self.shots = _load("scenes/camera_shots.json")["items"]
        geom = _load("scenes/camera_geometry.json")
        self.heights = geom["heights"]
        self.angles = geom["angles"]
        self.apertures = geom["apertures"]
        self.poses = _load("poses/poses.json")["items"]
        self.head_positions = _load("poses/head_positions.json")["items"]
        self.hands = _load("poses/hands.json")["items"]
        self.expressions = _load("poses/expressions.json")["items"]


# ----------------------------------------------------------------------
# Weighted choice
# ----------------------------------------------------------------------
def catalogue_for(config: Dict[str, Any]) -> "Catalogue":
    """Build a Catalogue honouring `wardrobe.prefer_observed`.

    Every call site goes through here so the wardrobe source cannot differ
    between the runner, the CLI and the hero search — a split that would
    silently produce runs sampled from different clothes.
    """
    return Catalogue(prefer_observed=bool(
        (config or {}).get("wardrobe", {}).get("prefer_observed", False)))


def weighted_choice(rng: random.Random, items: Sequence[Dict[str, Any]],
                    weights: Sequence[float]) -> Dict[str, Any]:
    total = sum(weights)
    if total <= 0:
        return rng.choice(list(items))
    r = rng.random() * total
    acc = 0.0
    for item, w in zip(items, weights):
        acc += w
        if r <= acc:
            return item
    return items[-1]


class Sampler:
    """Samples one axis at a time, with anti-collapse pressure applied."""

    def __init__(self, catalogue: Catalogue, history: DiversityHistory,
                 config: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None,
                 planned_total: int = 64, diversity: str = "normal") -> None:
        self.cat = catalogue
        self.history = history
        self.config = config
        self.feedback = feedback or {}
        self.planned_total = max(1, planned_total)
        div = config.get("diversity", {})
        self.pressure = float(div.get("pressure", {}).get(diversity, 1.2))
        self.max_share = div.get("max_family_share", {})
        self.hard_caps = div.get("hard_caps", {})
        hp = config.get("head_pose", {})
        self.left_target = float(hp.get("left_tilt_target_share", 0.08))
        self.left_exhausted_penalty = float(hp.get("exhausted_penalty", 0.02))
        self.base_left_weight = float(hp.get("base_left_weight", 0.25))
        self.feedback_floor = float(config.get("feedback", {}).get("weight_floor", 0.15))
        self.feedback_ceiling = float(config.get("feedback", {}).get("weight_ceiling", 3.0))

    # ------------------------------------------------------------------
    def _feedback_multiplier(self, axis: str, value: str) -> float:
        m = self.feedback.get(axis, {}).get(value)
        if m is None:
            return 1.0
        return max(self.feedback_floor, min(self.feedback_ceiling, float(m)))

    def _cap_multiplier(self, axis: str, value: str) -> float:
        """Near-hard stop once a value would exceed its configured share."""
        cap = self.max_share.get(axis)
        if cap is None or not value or self.history.accepted_count < 8:
            return 1.0
        tot = self.history.total_count(axis, value)
        projected = (tot + 1) / (self.history.accepted_count + 1)
        return 0.02 if projected > float(cap) else 1.0

    def weight_for(self, axis: str, value: str, base: float,
                   cap_keys: Optional[Dict[str, str]] = None) -> float:
        """Apply history repulsion, share caps and human feedback to a base weight.

        ``cap_keys`` carries the OTHER category axes this candidate implies —
        picking a pose by ``pose_id`` also commits to its ``pose_family``, and
        the family cap has to be checked or it never binds. Getting this wrong
        is exactly how a pose family silently climbs past its share limit.
        """
        if base <= 0:
            return 0.0
        w = base * self._feedback_multiplier(axis, value)

        win = self.history.window_count(axis, value)
        w *= (1.0 / (1.0 + win)) ** self.pressure

        tot = self.history.total_count(axis, value)
        w *= (1.0 / (1.0 + 0.5 * tot)) ** (self.pressure * 0.5)

        w *= self._cap_multiplier(axis, value)

        # Hard block on immediate repetition of the previous frame's value.
        if value and self.history.last_value(axis) == value:
            w *= 1e-6

        for extra_axis, extra_value in (cap_keys or {}).items():
            w *= self._cap_multiplier(extra_axis, extra_value)
            # Implied axes also get a softer repulsion term, so a family
            # spreads across its members instead of clustering on one.
            extra_win = self.history.window_count(extra_axis, extra_value)
            w *= (1.0 / (1.0 + extra_win)) ** (self.pressure * 0.5)

        return max(w, 1e-9)

    def pick(self, rng: random.Random, axis: str, items: Sequence[Dict[str, Any]],
             predicate: Optional[Callable[[Dict[str, Any]], bool]] = None,
             base_key: str = "weight",
             implies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Pick one item from ``items``.

        ``implies`` maps a category axis to the FIELD on the item that supplies
        its value, e.g. ``{"pose_family": "family"}`` when sampling poses by id.
        """
        pool = [i for i in items if predicate(i)] if predicate else list(items)
        if not pool:
            # Falling back to the unfiltered pool silently breaks whatever
            # constraint the predicate encoded. Surface it instead of hiding it.
            log.warning("sampler: no candidates on axis %r satisfied the predicate; "
                        "falling back to the full pool of %d (this indicates a data gap)",
                        axis, len(items))
            pool = list(items)
        weights = []
        for i in pool:
            cap_keys = {a: str(i.get(f, "")) for a, f in (implies or {}).items()}
            weights.append(self.weight_for(axis, i.get("id", ""),
                                           float(i.get(base_key, 1.0)), cap_keys))
        return weighted_choice(rng, pool, weights)

    # ------------------------------------------------------------------
    # Head position — section 12
    # ------------------------------------------------------------------
    def pick_head_position(self, rng: random.Random) -> Dict[str, Any]:
        """Left tilt is down-weighted at baseline and near-eliminated once the
        run's left-tilt budget is spent."""
        budget_left = self.history.left_budget_remaining(self.planned_total, self.left_target)
        # Projected share if we were to add one more left tilt right now.
        projected_left = (self.history.left_tilt_count + 1) / max(1, self.history.accepted_count + 1)
        cap = float(self.hard_caps.get("head_roll_left", self.left_target))

        pool = self.cat.head_positions
        weights: List[float] = []
        for hp in pool:
            base = float(hp.get("weight", 1.0))
            if hp.get("is_left_tilt"):
                base *= self.base_left_weight
                if budget_left <= 0 or projected_left > cap:
                    base *= self.left_exhausted_penalty
            weights.append(self.weight_for("head_position", hp["id"], base))
        return weighted_choice(rng, pool, weights)
