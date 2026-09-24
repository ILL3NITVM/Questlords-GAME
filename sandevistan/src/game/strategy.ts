export type SignalSide = "buy" | "sell" | "hold";

export type DeskSignal = {
  side: SignalSide;
  confidence: number;
  note: string;
  fast: number;
  slow: number;
  momentum: number;
  engine: "python" | "ts";
};

export type MarketTick = {
  price: number;
  change24: number;
  high: number;
  low: number;
  closes: number[];
  signal: DeskSignal;
  source: string;
};

const BUY_NOTES = [
  "Kenyon cells vote up. Poop inbound if this prints.",
  "Antennae like this tick. Demo long, real appetite.",
  "The fly insists it is real. The desk remains a demo.",
  "Here then there — but first, a tidy long.",
];
const SELL_NOTES = [
  "Lock it in. Poop is for thriving, not for greed.",
  "Descending neurons say walk. Keep the stash.",
  "Take the gift. Diminishing poop is a known risk.",
];
const HOLD_NOTES = [
  "Mushroom body is chewing. No rush.",
  "Waiting is also a strategy. The pile can wait.",
  "Isotope stable. Watching the next crumb of price.",
];

function mean(xs: number[]) {
  if (!xs.length) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

/** Same Kenyon-cell momentum as python/fly_desk.py */
export function decide(closes: number[], engine: "python" | "ts" = "ts"): DeskSignal {
  if (closes.length < 8) {
    const px = closes[closes.length - 1] ?? 0;
    return {
      side: "hold",
      confidence: 0.12,
      note: "Warming Kenyon cells. A few more ticks.",
      fast: px,
      slow: px,
      momentum: 0,
      engine,
    };
  }
  const fast = mean(closes.slice(-3));
  const slow = mean(closes.slice(-8));
  const prior = closes[closes.length - 5] ?? closes[0] ?? 1;
  const last = closes[closes.length - 1] ?? prior;
  const mom = prior ? last / prior - 1 : 0;
  const spread = slow ? (fast - slow) / slow : 0;
  const seed = Math.abs(Math.floor(last * 100)) % 97;
  if (spread > 0.00025 && mom > 0.0002) {
    const conf = Math.min(1, Math.abs(spread) * 800 + Math.abs(mom) * 400);
    return {
      side: "buy",
      confidence: Number(conf.toFixed(3)),
      note: BUY_NOTES[seed % BUY_NOTES.length]!,
      fast: Number(fast.toFixed(2)),
      slow: Number(slow.toFixed(2)),
      momentum: Number((mom * 100).toFixed(4)),
      engine,
    };
  }
  if (spread < -0.00025 && mom < -0.0002) {
    const conf = Math.min(1, Math.abs(spread) * 800 + Math.abs(mom) * 400);
    return {
      side: "sell",
      confidence: Number(conf.toFixed(3)),
      note: SELL_NOTES[seed % SELL_NOTES.length]!,
      fast: Number(fast.toFixed(2)),
      slow: Number(slow.toFixed(2)),
      momentum: Number((mom * 100).toFixed(4)),
      engine,
    };
  }
  return {
    side: "hold",
    confidence: 0.22,
    note: HOLD_NOTES[seed % HOLD_NOTES.length]!,
    fast: Number(fast.toFixed(2)),
    slow: Number(slow.toFixed(2)),
    momentum: Number((mom * 100).toFixed(4)),
    engine,
  };
}
