import { FlyBrain } from "@/game/brain";
import type { MarketTick } from "@/game/strategy";

export const BOOK_KEY = "sandevistan-fly-book-v1";

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
  openedAt: number;
  note: string;
};

export type Closed = Ticket & {
  exit: number;
  pnl: number;
  kind: ExitKind;
  closedAt: number;
};

export type Senses = {
  smell: number;
  glare: number;
  hunger: number;
  vote: number;
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
  open: Ticket | null;
  history: Closed[];
  senses: Senses;
  banner: string;
  status: "warming" | "live" | "stale";
};

function clamp(v: number, a: number, b: number) {
  return Math.max(a, Math.min(b, v));
}

function stdev(xs: number[]) {
  if (xs.length < 2) return 0;
  const m = xs.reduce((a, b) => a + b, 0) / xs.length;
  const v = xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length;
  return Math.sqrt(v);
}

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
    cash: 10000,
    equity: 10000,
    pnlOpen: 0,
    poop: 2,
    armed: true,
    open: null,
    history: [],
    senses: emptySenses,
    banner: "",
    status: "warming",
  };
}

export class FlyBook {
  brain = new FlyBrain();
  private cash = 10000;
  private poop = 2;
  private armed = true;
  private open: Ticket | null = null;
  private history: Closed[] = [];
  private flatSince = Date.now();
  private lastEntry = 0;
  private banner = "";
  private bannerAt = 0;
  private snap: BookSnap = freshSnap();
  private listeners = new Set<() => void>();
  private held: { olf: number; visL: number; visR: number; threat: number; speed: number } = {
    olf: 0.2,
    visL: 0.1,
    visR: 0.1,
    threat: 0.1,
    speed: 0,
  };

  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  getSnapshot = () => this.snap;

  load() {
    try {
      const raw = localStorage.getItem(BOOK_KEY);
      if (!raw) return;
      const s = JSON.parse(raw) as {
        cash?: number;
        poop?: number;
        open?: Ticket | null;
        history?: Closed[];
        flatSince?: number;
      };
      if (typeof s.cash === "number" && s.cash > 0) this.cash = s.cash;
      if (typeof s.poop === "number") this.poop = s.poop;
      this.open = s.open ?? null;
      this.history = Array.isArray(s.history) ? s.history.slice(0, 40) : [];
      if (typeof s.flatSince === "number") this.flatSince = s.flatSince;
      this.publish(this.snap.price ? this.snap : { ...this.snap, cash: this.cash, equity: this.mark(this.snap.price || 0), poop: this.poop, open: this.open, history: this.history });
    } catch {
      /* ignore */
    }
  }

  setArmed(v: boolean) {
    this.armed = v;
    this.banner = v ? "ANTENNAE LIVE" : "ENTRIES HALTED";
    this.bannerAt = Date.now();
    this.publish({
      ...this.snap,
      armed: v,
      banner: this.banner,
    });
  }

  /** Keep the connectome twitching between ticks. */
  senseStep(dt: number) {
    this.brain.step(dt, this.held);
  }

  apply(tick: MarketTick) {
    if (!Number.isFinite(tick.price) || tick.price <= 0) return;
    const senses = this.readSenses(tick);
    this.held = {
      olf: clamp(0.5 + senses.smell * 0.5, 0, 1),
      visL: senses.glare * (senses.smell < 0 ? 1 : 0.3),
      visR: senses.glare * (senses.smell > 0 ? 1 : 0.3),
      threat: senses.glare,
      speed: this.open ? 0.45 : senses.hunger,
    };
    for (let i = 0; i < 10; i++) this.brain.step(0.06, this.held);

    const nose =
      this.brain.olfactory -
      this.brain.visual * 0.55 +
      (this.brain.motorR - this.brain.motorL) * 0.35;
    const kenyon =
      tick.signal.side === "buy" ? tick.signal.confidence : tick.signal.side === "sell" ? -tick.signal.confidence : 0;
    const vote = nose * 0.7 + kenyon * 0.45;
    senses.vote = clamp(vote, -1, 1);

    const hi = Math.max(tick.high, tick.price);
    const lo = Math.min(tick.low, tick.price);
    this.resolve(tick.price);

    if (this.armed && !this.open && Date.now() - this.lastEntry > 20000) {
      if (vote > 0.18) this.enter("long", tick, senses, vote);
      else if (vote < -0.18) this.enter("short", tick, senses, vote);
    }

    if (this.equity(tick.price) < 800) {
      this.cash = 10000;
      this.open = null;
      this.poop = Math.max(1, this.poop);
      this.banner = "DEMO REFILL · THE FLY NEVER GOES HUNGRY";
      this.bannerAt = Date.now();
    }

    const note = this.open
      ? this.open.note
      : tick.signal.note;
    this.publish({
      price: tick.price,
      change24: tick.change24,
      high: hi,
      low: lo,
      closes: tick.closes,
      source: tick.source,
      engine: tick.signal.engine,
      note,
      cash: this.cash,
      equity: this.equity(tick.price),
      pnlOpen: this.openPnl(tick.price),
      poop: this.poop,
      armed: this.armed,
      open: this.open,
      history: this.history,
      senses,
      banner: Date.now() - this.bannerAt < 2800 ? this.banner : "",
      status: "live",
    });
    this.save();
  }

  markStale() {
    if (this.snap.status === "warming") return;
    this.publish({ ...this.snap, status: "stale" });
  }

  private readSenses(tick: MarketTick): Senses {
    const c = tick.closes;
    const rets: number[] = [];
    for (let i = 1; i < c.length; i++) {
      const prev = c[i - 1];
      const cur = c[i];
      if (prev) rets.push(cur / prev - 1);
    }
    const vol = stdev(rets.slice(-12));
    const mom = tick.signal.momentum / 100;
    const kenyon =
      tick.signal.side === "buy" ? tick.signal.confidence : tick.signal.side === "sell" ? -tick.signal.confidence : 0;
    const smell = clamp(mom / 0.0015 + kenyon * 0.65 + tick.change24 * 0.4, -1, 1);
    const glare = clamp(vol / 0.0016, 0, 1);
    const hunger = this.open ? 0 : clamp((Date.now() - this.flatSince) / 90000, 0, 1);
    return { smell, glare, hunger, vote: 0 };
  }

  private enter(side: Side, tick: MarketTick, senses: Senses, vote: number) {
    const vol = senses.glare;
    const slPct = clamp(0.0007 + vol * 0.0028, 0.00065, 0.004);
    const tpPct = slPct * (1.45 + Math.min(1, Math.abs(vote)) * 0.9);
    const entry = tick.price;
    const tp = side === "long" ? entry * (1 + tpPct) : entry * (1 - tpPct);
    const sl = side === "long" ? entry * (1 - slPct) : entry * (1 + slPct);
    const frac = clamp(0.14 + this.brain.firing * 0.22 + senses.hunger * 0.08, 0.12, 0.38);
    const spend = this.cash * frac;
    if (spend < 25) return;
    const qty = spend / entry;
    this.cash -= spend;
    const ticket: Ticket = {
      id: `t-${Date.now().toString(36)}`,
      side,
      qty,
      spend,
      entry,
      tp,
      sl,
      openedAt: Date.now(),
      note:
        side === "long"
          ? "Smell is up. Long, stop under the wick, target the next crumb."
          : "Glare on the bid. Short, stop above the wick, target the fade.",
    };
    this.open = ticket;
    this.lastEntry = Date.now();
    this.banner = side === "long" ? "OPEN LONG · TP / SL SET" : "OPEN SHORT · TP / SL SET";
    this.bannerAt = Date.now();
  }

  private resolve(price: number) {
    const t = this.open;
    if (!t) return;
    let kind: ExitKind | null = null;
    if (t.side === "long") {
      if (price <= t.sl) kind = "sl";
      else if (price >= t.tp) kind = "tp";
    } else if (price >= t.sl) {
      kind = "sl";
    } else if (price <= t.tp) {
      kind = "tp";
    }
    if (!kind) return;
    const exit = kind === "tp" ? t.tp : t.sl;
    const pnl = t.side === "long" ? t.qty * (exit - t.entry) : t.qty * (t.entry - exit);
    this.cash += t.spend + pnl;
    if (kind === "tp") this.poop += 1;
    else this.poop = Math.max(0, this.poop - 1);
    const closed: Closed = { ...t, exit, pnl, kind, closedAt: Date.now() };
    this.history = [closed, ...this.history].slice(0, 40);
    this.open = null;
    this.flatSince = Date.now();
    this.banner = kind === "tp" ? "TAKE PROFIT · FRASS UP" : "STOP · DIMINISHING POOP";
    this.bannerAt = Date.now();
  }

  private openPnl(price: number) {
    const t = this.open;
    if (!t || !price) return 0;
    return t.side === "long" ? t.qty * (price - t.entry) : t.qty * (t.entry - price);
  }

  private equity(price: number) {
    return this.cash + (this.open ? this.open.spend + this.openPnl(price) : 0);
  }

  private mark(price: number) {
    return this.equity(price);
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
          open: this.open,
          history: this.history,
          flatSince: this.flatSince,
        }),
      );
    } catch {
      /* ignore */
    }
  }
}
