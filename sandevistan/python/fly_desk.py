#!/usr/bin/env python3
"""Fly Desk — Kenyon-cell momentum on a BTC demo book.

The fly is convinced this is the real market.
The account is a demo. Everybody still gets poop when it prints.
"""

from __future__ import annotations

import json
import sys

BUY_NOTES = (
    "Kenyon cells vote up. Poop inbound if this prints.",
    "Antennae like this tick. Demo long, real appetite.",
    "The fly insists it is real. The desk remains a demo.",
    "Here then there — but first, a tidy long.",
)
SELL_NOTES = (
    "Lock it in. Poop is for thriving, not for greed.",
    "Descending neurons say walk. Keep the stash.",
    "Take the gift. Diminishing poop is a known risk.",
)
HOLD_NOTES = (
    "Mushroom body is chewing. No rush.",
    "Waiting is also a strategy. The pile can wait.",
    "Isotope stable. Watching the next crumb of price.",
)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def decide(closes: list[float]) -> dict:
    if len(closes) < 8:
        return {
            "side": "hold",
            "confidence": 0.12,
            "note": "Warming Kenyon cells. A few more ticks.",
            "fast": closes[-1] if closes else 0.0,
            "slow": closes[-1] if closes else 0.0,
            "momentum": 0.0,
        }
    fast = mean(closes[-3:])
    slow = mean(closes[-8:])
    prior = closes[-5] if len(closes) >= 5 else closes[0]
    mom = (closes[-1] / prior - 1.0) if prior else 0.0
    spread = (fast - slow) / slow if slow else 0.0
    seed = int(abs(closes[-1] * 100) % 97)
    if spread > 0.00025 and mom > 0.0002:
        conf = min(1.0, abs(spread) * 800 + abs(mom) * 400)
        return {
            "side": "buy",
            "confidence": round(conf, 3),
            "note": BUY_NOTES[seed % len(BUY_NOTES)],
            "fast": round(fast, 2),
            "slow": round(slow, 2),
            "momentum": round(mom * 100, 4),
        }
    if spread < -0.00025 and mom < -0.0002:
        conf = min(1.0, abs(spread) * 800 + abs(mom) * 400)
        return {
            "side": "sell",
            "confidence": round(conf, 3),
            "note": SELL_NOTES[seed % len(SELL_NOTES)],
            "fast": round(fast, 2),
            "slow": round(slow, 2),
            "momentum": round(mom * 100, 4),
        }
    return {
        "side": "hold",
        "confidence": 0.22,
        "note": HOLD_NOTES[seed % len(HOLD_NOTES)],
        "fast": round(fast, 2),
        "slow": round(slow, 2),
        "momentum": round(mom * 100, 4),
    }


def main() -> None:
    raw = sys.stdin.read() or "{}"
    payload = json.loads(raw)
    closes = [float(x) for x in payload.get("closes") or []]
    out = decide(closes)
    out["engine"] = "python"
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
