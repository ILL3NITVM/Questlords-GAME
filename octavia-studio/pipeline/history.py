"""Category-frequency bookkeeping that drives anti-collapse sampling.

``DiversityHistory`` holds two views of what has already been generated:

* ``totals``  — every accepted frame in the run, used for hard share caps.
* ``window``  — the most recent N frames, used for the soft repulsion term.

The distinction matters. A share cap is about the finished campaign ("no
scene family may exceed 12% of 64 images"); the sliding window is about
local texture ("do not shoot the same sofa three frames running").
"""
from __future__ import annotations

from collections import Counter, deque
from typing import Any, Deque, Dict, Iterable, List


class DiversityHistory:
    def __init__(self, window: int = 24):
        self.window_size = window
        self.totals: Dict[str, Counter] = {}
        self._recent: Deque[Dict[str, str]] = deque(maxlen=window)
        self.accepted_count = 0
        self.left_tilt_count = 0

    # ------------------------------------------------------------------
    def record(self, category_keys: Dict[str, str], accepted: bool = True) -> None:
        """Register a frame. Only accepted frames shape future sampling —
        a rejected frame should not consume a category's budget."""
        if not accepted:
            return
        self.accepted_count += 1
        self._recent.append(dict(category_keys))
        for axis, value in category_keys.items():
            if not value:
                continue
            self.totals.setdefault(axis, Counter())[value] += 1
        if category_keys.get("tilt_class") == "left":
            self.left_tilt_count += 1

    # ------------------------------------------------------------------
    def window_count(self, axis: str, value: str) -> int:
        return sum(1 for frame in self._recent if frame.get(axis) == value)

    def last_value(self, axis: str) -> str:
        """The value on ``axis`` in the most recently accepted frame.

        Used to make back-to-back repetition a hard block rather than a merely
        improbable one — a soft weight penalty still fires occasionally, and
        two identical consecutive frames is the most visible form of collapse.
        """
        return self._recent[-1].get(axis, "") if self._recent else ""

    def total_count(self, axis: str, value: str) -> int:
        return self.totals.get(axis, Counter()).get(value, 0)

    def share(self, axis: str, value: str) -> float:
        if self.accepted_count == 0:
            return 0.0
        return self.total_count(axis, value) / self.accepted_count

    def left_tilt_share(self) -> float:
        if self.accepted_count == 0:
            return 0.0
        return self.left_tilt_count / self.accepted_count

    # ------------------------------------------------------------------
    def projected_left_budget(self, planned_total: int, target_share: float) -> int:
        """How many left-tilt frames the whole run may contain."""
        return int(planned_total * target_share)

    def left_budget_remaining(self, planned_total: int, target_share: float) -> int:
        return max(0, self.projected_left_budget(planned_total, target_share) - self.left_tilt_count)

    # ------------------------------------------------------------------
    def report(self, axes: Iterable[str] | None = None) -> Dict[str, Any]:
        axes = list(axes) if axes else sorted(self.totals)
        out: Dict[str, Any] = {
            "accepted": self.accepted_count,
            "left_tilt_count": self.left_tilt_count,
            "left_tilt_share": round(self.left_tilt_share(), 4),
            "axes": {},
        }
        for axis in axes:
            counter = self.totals.get(axis)
            if not counter:
                continue
            total = sum(counter.values())
            out["axes"][axis] = {
                "distinct": len(counter),
                "total": total,
                "top": [
                    {"value": v, "count": c, "share": round(c / total, 4)}
                    for v, c in counter.most_common(8)
                ],
            }
        return out

    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_size": self.window_size,
            "accepted_count": self.accepted_count,
            "left_tilt_count": self.left_tilt_count,
            "totals": {a: dict(c) for a, c in self.totals.items()},
            "recent": list(self._recent),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DiversityHistory":
        h = cls(window=int(d.get("window_size", 24)))
        h.accepted_count = int(d.get("accepted_count", 0))
        h.left_tilt_count = int(d.get("left_tilt_count", 0))
        h.totals = {a: Counter(c) for a, c in d.get("totals", {}).items()}
        for frame in d.get("recent", []):
            h._recent.append(frame)
        return h
