/* Synthetic substrate feed. Asset-aware, seeded (reproducible from the session
 * seed), self-scheduling to honour the live tick-speed setting, and audited:
 * every printed tick advances the audit hash chain. Forward-printing only —
 * ticks are appended, never rewritten. */
import { clamp } from "../util.js";

export function createSimFeed(ctx) {
  const { state } = ctx;
  const audit = ctx.audit || { tick() {} };
  let timer = null, regimeUntil = 0, regimeBias = 0, running = false;
  const rng = () => (state.rng || Math.random)();

  function A() { return state.asset; }

  function chooseRegime() {
    const m = state.market, r = rng(), a = A();
    const volScale = a.tick; // scale volatility to the instrument tick size
    if (r < .28) { m.regime = "COMP"; m.vol = 16 * volScale; regimeBias = (rng() - .5) * 2.8 * volScale; }
    else if (r < .48) { m.regime = "DRIFT UP"; m.vol = 36 * volScale; regimeBias = (6 + rng() * 8) * volScale; }
    else if (r < .68) { m.regime = "DRIFT DN"; m.vol = 36 * volScale; regimeBias = -(6 + rng() * 8) * volScale; }
    else if (r < .84) { m.regime = "IMPULSE"; m.vol = 112 * volScale; regimeBias = (rng() < .5 ? -1 : 1) * (24 + rng() * 36) * volScale; }
    else { m.regime = "PULLBACK"; m.vol = 60 * volScale; regimeBias = (a.base - m.last) * 0.012; }
    regimeUntil = Date.now() + 2600 + rng() * 6500;
  }

  function step(seed = false) {
    const a = A(), m = state.market;
    if (Date.now() > regimeUntil || seed) chooseRegime();
    const cluster = 1 + Math.max(0, Math.sin(state.ticks.length / 9)) * 0.9 + (rng() < .05 ? 1.3 : 0);
    const shock = (rng() - .5) * m.vol * cluster;
    const pull = (a.base - m.last) * 0.015;
    m.momentum = m.momentum * .72 + regimeBias + shock + pull;
    let next = m.last + m.momentum;
    if (next < a.min) { next = a.min + (a.min - next) * .42; m.momentum = Math.abs(m.momentum) * .36; }
    if (next > a.max) { next = a.max - (next - a.max) * .42; m.momentum = -Math.abs(m.momentum) * .36; }
    m.last = clamp(next, a.min, a.max);
    const spreadTicks = clamp(2 + Math.floor(Math.abs(m.momentum) / (a.tick * 7)) + (m.regime === "IMPULSE" ? 6 : 0), 2, 80);
    m.spread = spreadTicks * a.tick; m.mid = m.last; m.bid = m.mid - m.spread / 2; m.ask = m.mid + m.spread / 2;
    const volume = 420000 + rng() * 2100000 + (m.regime === "IMPULSE" ? 2800000 : 0) + (m.regime === "COMP" ? -140000 : 0);
    state.ticks.push({ t: Date.now(), p: m.last, bid: m.bid, ask: m.ask, vol: Math.max(90000, volume), regime: m.regime, mom: m.momentum });
    if (state.ticks.length > 360) state.ticks.shift();
    if (!seed) audit.tick(m.last);
  }

  function makeBook() {
    const a = A(), m = state.market, levels = 8, bids = [], asks = [];
    const pressure = clamp(m.momentum / (a.tick * 70), -1, 1);
    for (let i = 1; i <= levels; i++) {
      const curve = 1 + i * .19, pulse = 1 + Math.sin((state.ticks.length + i) * .71) * .18;
      const bidSize = (280000 + i * 112000) * curve * pulse * (1 + Math.max(0, pressure) * .5);
      const askSize = (280000 + i * 108000) * curve * (2 - pulse) * (1 + Math.max(0, -pressure) * .5);
      bids.push({ px: m.bid - (i - 1) * a.tick * 2, sz: Math.max(65000, bidSize), cum: 0 });
      asks.push({ px: m.ask + (i - 1) * a.tick * 2, sz: Math.max(65000, askSize), cum: 0 });
    }
    bids.reduce((x, y) => y.cum = x + y.sz, 0); asks.reduce((x, y) => y.cum = x + y.sz, 0);
    const b = bids.slice(0, 3).reduce((x, y) => x + y.sz, 0), as = asks.slice(0, 3).reduce((x, y) => x + y.sz, 0);
    m.imb = (b - as) / (b + as); m.micro = (m.ask * b + m.bid * as) / (as + b);
    state.book = { bids, asks };
  }

  function calc() {
    const a = A(), m = state.market, win = state.ticks.slice(-180);
    m.high = Math.max(...win.map(x => x.p)); m.low = Math.min(...win.map(x => x.p));
    const sum = win.reduce((s, x) => s + x.p * x.vol, 0), vol = win.reduce((s, x) => s + x.vol, 0);
    m.vwap = sum / vol;
    const bins = 48, bucket = Array.from({ length: bins }, () => 0), lo = m.low, hi = m.high, span = Math.max(a.tick, hi - lo);
    win.forEach(x => { bucket[clamp(Math.floor((x.p - lo) / span * bins), 0, bins - 1)] += x.vol; });
    let bi = 0; bucket.forEach((v, i) => { if (v > bucket[bi]) bi = i; }); m.poc = lo + (bi + .5) / bins * span;
    const recent = win.slice(-60), avg = recent.reduce((s, x) => s + x.p, 0) / recent.length;
    const sd = Math.sqrt(recent.reduce((s, x) => s + (x.p - avg) * (x.p - avg), 0) / recent.length);
    m.upper = avg + sd * 2.1; m.lower = avg - sd * 2.1;
    makeBook();
  }

  function seed() {
    const a = A(), m = state.market;
    regimeUntil = 0; regimeBias = 0;
    state.ticks.length = 0;
    m.last = a.base + (rng() - .5) * (a.max - a.min) * 0.06;
    m.momentum = 0;
    for (let i = 0; i < 240; i++) step(true);
    m.open = state.ticks[0].p;
    calc();
  }

  let dataCb = null;
  function schedule() {
    if (!running) return;
    const delay = clamp(Number(state.settings.tickSpeed) || 650, 120, 4000);
    timer = setTimeout(() => { step(); calc(); dataCb && dataCb(); schedule(); }, delay);
  }

  return {
    kind: "SIM",
    start(onData) { dataCb = onData; running = true; seed(); onData(); schedule(); },
    stop() { running = false; clearTimeout(timer); timer = null; },
    reseed() { seed(); dataCb && dataCb(); }
  };
}
