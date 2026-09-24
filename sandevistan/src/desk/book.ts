import { FlyBrain } from "@/game/brain";
import type { MarketTick } from "@/game/strategy";
import { backtestReason, replay, type BacktestResult } from "./backtest";
import {
  COOLDOWN_MS,
  MAX_OPEN,
  MIN_BIAS,
  clamp,
  exitKind,
  heldFrom,
  isFreshVote,
  levels,
  pnlAt,
  readSenses,
  sideFor,
  spendFor,
  think,
  ticketNote,
  type ExitKind,
  type Held,
  type Senses,
  type Side,
  type Ticket,
} from "./rules";

export type { ExitKind, Senses, Side, Ticket } from "./rules";
export { MAX_OPEN } from "./rules";

export const BOOK_KEY = "sandevistan-fly-book-v2";
const OLD_KEY = "sandevistan-fly-book-v1";
const START = 10000;
const AUTO_BACKTEST_MS = 4 * 60 * 1000;
const REFUSAL = "Mushroom body is full. No backtest.";

export type Closed = Ticket & {
  exit: number;
  pnl: number;
  kind: ExitKind;
  closedAt: number;
};

export type BacktestView = {
  line: string;
  running: boolean;
  error: string;
  result: BacktestResult | null;
};

export type BookSnap = {
  price: number;
  change24: number;
  high: number;
  low: number;
  closes: number[];
  source: string;
  engine: "python" | "ts";
  note: string;
  cash: number;
  equity: number;
  pnlOpen: number;
  poop: number;
  armed: boolean;
  open: Ticket[];
  history: Closed[];
  senses: Senses;
  bias: number;
  backtest: BacktestView;
  banner: string;
  status: "warming" | "live" | "stale" | "asleep";
};

const emptySenses: Senses = { smell: 0, glare: 0, hunger: 0, vote: 0 };

function freshSnap(): BookSnap {
  return {
    price: 0,
    change24: 0,
    high: 0,
    low: 0,
    closes: [],
    source: "",
    engine: "ts",
    note: "Antennae warming. No ticket yet.",
    cash: START,
    equity: START,
    pnlOpen: 0,
    poop: 2,
    armed: true,
    open: [],
    history: [],
    senses: emptySenses,
    bias: 1,
    backtest: { line: "", running: false, error: "", result: null },
    banner: "",
    status: "warming",
  };
}

const num = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** Accepts v1 tickets (no vote) and drops anything malformed. */
function toTicket(v: unknown): Ticket | null {
  if (!v || typeof v !== "object") return null;
  const t = v as Partial<Ticket>;
  if (t.side !== "long" && t.side !== "short") return null;
  if (!num(t.qty) || !num(t.spend) || !num(t.entry) || !num(t.tp) || !num(t.sl)) return null;
  return {
    id: typeof t.id === "string" ? t.id : `t-${Math.random().toString(36).slice(2, 8)}`,
    side: t.side,
    qty: t.qty,
    spend: t.spend,
    entry: t.entry,
    tp: t.tp,
    sl: t.sl,
    vote: num(t.vote) ? t.vote : t.side === "long" ? 0.18 : -0.18,
    openedAt: num(t.openedAt) ? t.openedAt : Date.now(),
    note: typeof t.note === "string" ? t.note : ticketNote(t.side),
  };
}

function toClosed(v: unknown): Closed | null {
  const t = toTicket(v);
  if (!t) return null;
  const c = v as Partial<Closed>;
  if (!num(c.exit) || !num(c.pnl) || (c.kind !== "tp" && c.kind !== "sl")) return null;
  return { ...t, exit: c.exit, pnl: c.pnl, kind: c.kind, closedAt: num(c.closedAt) ? c.closedAt : t.openedAt };
}

type Saved = {
  cash?: unknown;
  poop?: unknown;
  armed?: unknown;
  open?: unknown;
  history?: unknown;
  hungrySince?: unknown;
  flatSince?: unknown;
  lastEntry?: unknown;
  bias?: unknown;
  lastPrice?: unknown;
  backtest?: unknown;
  savedAt?: unknown;
};

function readSaved(): Saved | null {
  for (const key of [BOOK_KEY, OLD_KEY]) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) continue;
      const s = JSON.parse(raw) as unknown;
      if (s && typeof s === "object") return s as Saved;
    } catch {
      /* bad JSON: try the next key, else start fresh */
    }
  }
  return null;
}

export class FlyBook {
  brain = new FlyBrain();
  private cash = START;
  private poop = 2;
  private armed = true;
  private open: Ticket[] = [];
  private history: Closed[] = [];
  private hungrySince = Date.now();
  private lastEntry = 0;
  private bias = 1;
  private lastPrice = 0;
  private edgelessSince = 0;
  private waking = false;
  private lastAsk = 0;
  private backtest: BacktestView = { line: "", running: false, error: "", result: null };
  private banner = "";
  private bannerUntil = 0;
  private snap: BookSnap = freshSnap();
  private listeners = new Set<() => void>();
  private held: Held = { olf: 0.2, visL: 0.1, visR: 0.1, threat: 0.1, speed: 0 };

  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  getSnapshot = () => this.snap;

  /**
   * Load the book exactly as saved. Clocks shift by the time away so the fly
   * wakes as hungry as it fell asleep. The next tick only marks, never fills.
   */
  load() {
    const s = readSaved();
    if (!s) return;
    const away = num(s.savedAt) ? Math.max(0, Date.now() - s.savedAt) : 0;
    if (num(s.cash) && s.cash >= 0) this.cash = s.cash;
    if (num(s.poop)) this.poop = Math.max(0, Math.round(s.poop));
    if (typeof s.armed === "boolean") this.armed = s.armed;
    const rawOpen = Array.isArray(s.open) ? s.open : s.open ? [s.open] : [];
    this.open = rawOpen.map(toTicket).filter((t): t is Ticket => t !== null).slice(0, MAX_OPEN);
    this.history = Array.isArray(s.history)
      ? s.history.map(toClosed).filter((c): c is Closed => c !== null).slice(0, 40)
      : [];
    const hungry = num(s.hungrySince) ? s.hungrySince : num(s.flatSince) ? s.flatSince : Date.now();
    this.hungrySince = Math.min(Date.now(), hungry + away);
    this.lastEntry = num(s.lastEntry) ? s.lastEntry + away : 0;
    if (num(s.bias)) this.bias = clamp(s.bias, MIN_BIAS, 1);
    if (num(s.lastPrice) && s.lastPrice > 0) this.lastPrice = s.lastPrice;
    const bt = s.backtest as Partial<BacktestResult> | undefined;
    if (bt && num(bt.trades) && num(bt.winRate) && num(bt.net) && num(bt.maxDrawdown) && num(bt.at)) {
      this.backtest = { ...this.backtest, result: bt as BacktestResult };
    }
    this.edgelessSince = 0;
    this.waking = true;
    const px = this.lastPrice || this.snap.price;
    this.publish({
      ...this.snap,
      price: this.snap.price || this.lastPrice,
      ...this.bookFields(px),
    });
  }

  /** Tab hidden: freeze and save. Nothing resolves until the tab is back. */
  sleep() {
    this.save();
    if (this.snap.status !== "warming") this.publish({ ...this.snap, status: "asleep" });
  }

  wake() {
    this.load();
    this.waking = true;
  }

  setArmed(v: boolean) {
    this.armed = v;
    this.edgelessSince = 0;
    this.flash(v ? "ANTENNAE LIVE" : "ENTRIES HALTED");
    this.publish({ ...this.snap, armed: v, banner: this.banner });
    this.save();
  }

  /** Keep the connectome twitching between ticks. */
  senseStep(dt: number) {
    this.brain.step(dt, this.held);
  }

  apply(tick: MarketTick) {
    if (!Number.isFinite(tick.price) || tick.price <= 0) return;
    const now = Date.now();
    const senses = readSenses(tick.closes, tick.signal, tick.change24, this.open.length, now - this.hungrySince);
    this.held = heldFrom(senses, this.open.length);
    const vote = think(this.brain, this.held, tick.signal);
    senses.vote = clamp(vote, -1, 1);

    if (this.waking) {
      // The fly was asleep. Mark to this price, do not walk the missed tape.
      this.waking = false;
      this.flash("TAB WAS SHUT · BOOK UNCHANGED", 5000);
    } else {
      this.resolve(tick.price, now);
      const side = sideFor(vote);
      if (
        this.armed &&
        side &&
        this.open.length < MAX_OPEN &&
        now - this.lastEntry >= COOLDOWN_MS &&
        isFreshVote(this.open, side, vote)
      ) {
        this.enter(side, tick.price, senses, vote, now);
      }
      if (this.equity(tick.price) < 800) {
        this.cash = START;
        this.open = [];
        this.poop = Math.max(1, this.poop);
        this.flash("DEMO REFILL · THE FLY NEVER GOES HUNGRY");
      }
    }

    if (this.armed && Math.abs(senses.vote) < 0.08) this.edgelessSince ||= now;
    else this.edgelessSince = 0;

    this.lastPrice = tick.price;
    const newest = this.open[this.open.length - 1];
    this.publish({
      price: tick.price,
      change24: tick.change24,
      high: Math.max(tick.high, tick.price),
      low: Math.min(tick.low, tick.price),
      closes: tick.closes,
      source: tick.source,
      engine: tick.signal.engine,
      note: newest ? newest.note : tick.signal.note,
      ...this.bookFields(tick.price),
      senses,
      banner: now < this.bannerUntil ? this.banner : "",
      status: "live",
    });
    this.save();
  }

  markStale() {
    if (this.snap.status === "warming" || this.snap.status === "asleep") return;
    this.publish({ ...this.snap, status: "stale" });
  }

  /** Called after a poll resolves. At most once per few minutes. */
  shouldAutoAsk() {
    return !this.backtest.running && Date.now() - this.lastAsk > AUTO_BACKTEST_MS && this.snap.status === "live";
  }

  /**
   * The fly decides. If it wants a backtest it pulls candles and replays the
   * live rules on a separate $10,000 paper book. Never touches the live book
   * except to tighten the TP/SL bias.
   */
  async askBacktest(fetchCloses: () => Promise<number[]>) {
    if (this.backtest.running) return;
    this.lastAsk = Date.now();
    const reason = backtestReason({
      glare: this.snap.senses.glare,
      lastKinds: this.history.map((h) => h.kind),
      armed: this.armed,
      edgelessMs: this.edgelessSince ? Date.now() - this.edgelessSince : 0,
    });
    if (!reason) {
      this.setBacktest({ line: REFUSAL, running: false, error: "" });
      return;
    }
    this.setBacktest({ line: reason, running: true, error: "" });
    try {
      const closes = await fetchCloses();
      if (closes.length < 40) throw new Error(`Only ${closes.length} candles came back. Not enough to replay.`);
      // Yield so the tape poll and paint are never blocked behind the replay.
      await new Promise((r) => setTimeout(r, 0));
      const result = replay(closes, this.bias);
      this.bias = result.biasAfter;
      this.setBacktest({
        line:
          result.verdict === "tighten"
            ? "Win rate under 40%. Tightening TP and SL a little."
            : "Widths hold. Keeping TP and SL as they are.",
        running: false,
        error: "",
        result,
      });
      this.save();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Candle fetch failed.";
      this.setBacktest({ line: "Backtest failed. No candles, no guesses.", running: false, error: message });
    }
  }

  private setBacktest(next: Partial<BacktestView>) {
    this.backtest = { ...this.backtest, ...next };
    this.publish({ ...this.snap, backtest: this.backtest, bias: this.bias });
  }

  private bookFields(price: number) {
    return {
      cash: this.cash,
      equity: this.equity(price),
      pnlOpen: this.openPnl(price),
      poop: this.poop,
      armed: this.armed,
      open: this.open,
      history: this.history,
      bias: this.bias,
      backtest: this.backtest,
    };
  }

  private flash(text: string, ms = 2800) {
    this.banner = text;
    this.bannerUntil = Date.now() + ms;
  }

  private enter(side: Side, price: number, senses: Senses, vote: number, now: number) {
    const spend = spendFor(this.cash, this.equity(price), this.brain.firing, senses.hunger);
    if (spend < 25) return;
    const { tp, sl } = levels(side, price, senses.glare, vote, this.bias);
    this.cash -= spend;
    this.open = [
      ...this.open,
      {
        id: `t-${now.toString(36)}-${this.open.length}`,
        side,
        qty: spend / price,
        spend,
        entry: price,
        tp,
        sl,
        vote,
        openedAt: now,
        note: ticketNote(side),
      },
    ];
    this.lastEntry = now;
    this.hungrySince = now;
    this.flash(`${side === "long" ? "OPEN LONG" : "OPEN SHORT"} · ${this.open.length} OF ${MAX_OPEN} LIVE`);
  }

  private resolve(price: number, now: number) {
    if (!this.open.length) return;
    const still: Ticket[] = [];
    const closed: Closed[] = [];
    for (const t of this.open) {
      const kind = exitKind(t, price);
      if (!kind) {
        still.push(t);
        continue;
      }
      const exit = kind === "tp" ? t.tp : t.sl;
      const pnl = pnlAt(t, exit);
      this.cash += t.spend + pnl;
      if (kind === "tp") this.poop += 1;
      else this.poop = Math.max(0, this.poop - 1);
      closed.push({ ...t, exit, pnl, kind, closedAt: now });
    }
    if (!closed.length) return;
    this.open = still;
    this.history = [...closed.reverse(), ...this.history].slice(0, 40);
    const last = closed[0];
    this.flash(last.kind === "tp" ? "TAKE PROFIT · FRASS UP" : "STOP · DIMINISHING POOP");
  }

  private openPnl(price: number) {
    if (!price) return 0;
    return this.open.reduce((s, t) => s + pnlAt(t, price), 0);
  }

  private equity(price: number) {
    return this.cash + this.open.reduce((s, t) => s + t.spend, 0) + this.openPnl(price);
  }

  private publish(next: BookSnap) {
    this.snap = next;
    for (const l of this.listeners) l();
  }

  private save() {
    try {
      localStorage.setItem(
        BOOK_KEY,
        JSON.stringify({
          cash: this.cash,
          poop: this.poop,
          armed: this.armed,
          open: this.open,
          history: this.history,
          hungrySince: this.hungrySince,
          lastEntry: this.lastEntry,
          bias: this.bias,
          lastPrice: this.lastPrice,
          backtest: this.backtest.result,
          savedAt: Date.now(),
        }),
      );
    } catch {
      /* storage full or blocked: keep trading in memory */
    }
  }
}
