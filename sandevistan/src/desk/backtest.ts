import { FlyBrain } from "@/game/brain";
import { decide } from "@/game/strategy";
import {
  COOLDOWN_MS,
  MAX_OPEN,
  MIN_BIAS,
  exitKind,
  heldFrom,
  isFreshVote,
  levels,
  pnlAt,
  readSenses,
  sideFor,
  spendFor,
  think,
  type ExitKind,
  type Ticket,
} from "./rules";

export type BacktestResult = {
  candles: number;
  trades: number;
  winRate: number;
  net: number;
  maxDrawdown: number;
  verdict: "keep" | "tighten";
  biasBefore: number;
  biasAfter: number;
  at: number;
};

const WINDOW = 30;
const CANDLE_MS = 60000;
const START = 10000;

/** The fly only backtests when something feels off. Returns why, or null. */
export function backtestReason(input: {
  glare: number;
  lastKinds: ExitKind[];
  armed: boolean;
  edgelessMs: number;
}): string | null {
  if (input.glare > 0.6) return "Glare is high. Checking the widths.";
  if (input.lastKinds.length >= 3 && input.lastKinds.slice(0, 3).every((k) => k === "sl")) {
    return "Three stops in a row. Rewinding the tape.";
  }
  if (input.armed && input.edgelessMs > 90000) return "No edge for a while. Rewinding the tape.";
  return null;
}

/**
 * Walk forward over 1m closes with a fresh $10,000 paper book and its own brain.
 * Each step only sees closes up to and including itself.
 */
export function replay(closes: number[], bias: number): BacktestResult {
  const brain = new FlyBrain();
  let cash = START;
  let open: Ticket[] = [];
  let lastEntry = -Infinity;
  let hungrySince = 0;
  let trades = 0;
  let wins = 0;
  let peak = START;
  let maxDrawdown = 0;
  let equity = START;

  for (let i = WINDOW - 1; i < closes.length; i++) {
    const now = i * CANDLE_MS;
    const price = closes[i];
    const window = closes.slice(i - WINDOW + 1, i + 1);
    const signal = decide(window, "ts");
    const senses = readSenses(window, signal, 0, open.length, now - hungrySince);
    const vote = think(brain, heldFrom(senses, open.length), signal);

    const still: Ticket[] = [];
    for (const t of open) {
      const kind = exitKind(t, price);
      if (!kind) {
        still.push(t);
        continue;
      }
      const exit = kind === "tp" ? t.tp : t.sl;
      cash += t.spend + pnlAt(t, exit);
      trades++;
      if (kind === "tp") wins++;
    }
    open = still;

    const side = sideFor(vote);
    if (side && open.length < MAX_OPEN && now - lastEntry >= COOLDOWN_MS && isFreshVote(open, side, vote)) {
      const eq = cash + open.reduce((s, t) => s + t.spend + pnlAt(t, price), 0);
      const spend = spendFor(cash, eq, brain.firing, senses.hunger);
      if (spend >= 25) {
        const { tp, sl } = levels(side, price, senses.glare, vote, bias);
        cash -= spend;
        open.push({ id: `bt-${i}`, side, qty: spend / price, spend, entry: price, tp, sl, vote, openedAt: now, note: "" });
        lastEntry = now;
        hungrySince = now;
      }
    }

    equity = cash + open.reduce((s, t) => s + t.spend + pnlAt(t, price), 0);
    if (equity < 800) {
      cash = START;
      open = [];
      equity = START;
    }
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak > 0 ? (peak - equity) / peak : 0);
  }

  const winRate = trades ? wins / trades : 0;
  const tighten = trades >= 3 && winRate < 0.4;
  const biasAfter = tighten ? Math.max(MIN_BIAS, bias * 0.92) : bias;
  return {
    candles: closes.length,
    trades,
    winRate,
    net: equity - START,
    maxDrawdown,
    verdict: tighten && biasAfter < bias ? "tighten" : "keep",
    biasBefore: bias,
    biasAfter,
    at: Date.now(),
  };
}
