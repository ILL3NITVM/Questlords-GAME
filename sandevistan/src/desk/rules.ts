import type { FlyBrain } from "@/game/brain";
import type { DeskSignal } from "@/game/strategy";

/** Shared by the live book and the backtest replay. One set of rules. */

export type Side = "long" | "short";
export type ExitKind = "tp" | "sl";

export type Ticket = {
  id: string;
  side: Side;
  qty: number;
  spend: number;
  entry: number;
  tp: number;
  sl: number;
  vote: number;
  openedAt: number;
  note: string;
};

export type Senses = {
  smell: number;
  glare: number;
  hunger: number;
  vote: number;
};

export type Held = { olf: number; visL: number; visR: number; threat: number; speed: number };

export const MAX_OPEN = 4;
export const COOLDOWN_MS = 12000;
export const RESERVE = 0.15;
export const VOTE_GATE = 0.18;
/** Same side needs the vote to move at least this much before another ticket. */
export const FRESH_VOTE = 0.05;
export const MIN_SL = 0.0006;
export const MIN_BIAS = 0.7;

export function clamp(v: number, a: number, b: number) {
  return Math.max(a, Math.min(b, v));
}

function stdev(xs: number[]) {
  if (xs.length < 2) return 0;
  const m = xs.reduce((a, b) => a + b, 0) / xs.length;
  const v = xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length;
  return Math.sqrt(v);
}

export function kenyonOf(signal: DeskSignal) {
  return signal.side === "buy" ? signal.confidence : signal.side === "sell" ? -signal.confidence : 0;
}

/** Hunger stays up while there is room under the cap. */
export function readSenses(
  closes: number[],
  signal: DeskSignal,
  change24: number,
  openCount: number,
  hungryForMs: number,
): Senses {
  const rets: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    const prev = closes[i - 1];
    if (prev) rets.push(closes[i] / prev - 1);
  }
  const vol = stdev(rets.slice(-12));
  const mom = signal.momentum / 100;
  const smell = clamp(mom / 0.0015 + kenyonOf(signal) * 0.65 + change24 * 0.4, -1, 1);
  const glare = clamp(vol / 0.0016, 0, 1);
  const hunger = openCount < MAX_OPEN ? clamp(hungryForMs / 90000, 0, 1) : 0;
  return { smell, glare, hunger, vote: 0 };
}

export function heldFrom(senses: Senses, openCount: number): Held {
  return {
    olf: clamp(0.5 + senses.smell * 0.5, 0, 1),
    visL: senses.glare * (senses.smell < 0 ? 1 : 0.3),
    visR: senses.glare * (senses.smell > 0 ? 1 : 0.3),
    threat: senses.glare,
    speed: openCount >= MAX_OPEN ? 0.45 : senses.hunger,
  };
}

/** Steps the brain 10 × 0.06s and returns the raw vote. */
export function think(brain: FlyBrain, held: Held, signal: DeskSignal) {
  for (let i = 0; i < 10; i++) brain.step(0.06, held);
  const nose = brain.olfactory - brain.visual * 0.55 + (brain.motorR - brain.motorL) * 0.35;
  return nose * 0.7 + kenyonOf(signal) * 0.45;
}

export function sideFor(vote: number): Side | null {
  if (vote > VOTE_GATE) return "long";
  if (vote < -VOTE_GATE) return "short";
  return null;
}

/** No stacking the same side on the same vote. */
export function isFreshVote(open: Ticket[], side: Side, vote: number) {
  return !open.some((t) => t.side === side && Math.abs(t.vote - vote) < FRESH_VOTE);
}

/** `bias` < 1 tightens both widths; the stop never goes under MIN_SL. */
export function levels(side: Side, entry: number, glare: number, vote: number, bias: number) {
  const base = clamp(0.0007 + glare * 0.0028, 0.00065, 0.004);
  const slPct = Math.max(MIN_SL, base * bias);
  const tpPct = slPct * (1.45 + Math.min(1, Math.abs(vote)) * 0.9);
  const tp = side === "long" ? entry * (1 + tpPct) : entry * (1 - tpPct);
  const sl = side === "long" ? entry * (1 - slPct) : entry * (1 + slPct);
  return { tp, sl };
}

/** Sized off free cash; RESERVE of equity stays unspent. */
export function spendFor(cash: number, equity: number, firing: number, hunger: number) {
  const frac = clamp(0.14 + firing * 0.22 + hunger * 0.08, 0.12, 0.38);
  const free = Math.max(0, cash - equity * RESERVE);
  return free * frac;
}

export function pnlAt(t: Ticket, price: number) {
  return t.side === "long" ? t.qty * (price - t.entry) : t.qty * (t.entry - price);
}

/** Last price only. Same tick both sides: stop wins. */
export function exitKind(t: Ticket, price: number): ExitKind | null {
  if (t.side === "long") {
    if (price <= t.sl) return "sl";
    if (price >= t.tp) return "tp";
    return null;
  }
  if (price >= t.sl) return "sl";
  if (price <= t.tp) return "tp";
  return null;
}

export function ticketNote(side: Side) {
  return side === "long"
    ? "Smell is up. Long, stop under the crumb, target the next one."
    : "Glare on the bid. Short, stop above the crumb, target the fade.";
}
