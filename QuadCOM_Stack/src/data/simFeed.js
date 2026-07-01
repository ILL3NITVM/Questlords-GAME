/* Synthetic BTC/USD.SYN substrate. Produces the same {market, book, ticks}
 * snapshot shape the live feed emits, so every downstream module is identical
 * regardless of MODE.LIVE. Regime-driven generator with volatility clustering,
 * momentum, mean-pull, VWAP/POC, ±2.1σ band, and a synthetic depth ladder. */
import { TICK, MIN, MAX, BASE, CADENCE_MS } from "../config.js";
import { clamp } from "../util.js";

export function createSimFeed(state) {
  let timer = null, regimeUntil = 0, regimeBias = 0;

  function chooseRegime() {
    const m = state.market, r = Math.random();
    if (r < .28) { m.regime = "COMP"; m.vol = 8; regimeBias = (Math.random() - .5) * 1.4; }
    else if (r < .48) { m.regime = "DRIFT UP"; m.vol = 18; regimeBias = 3 + Math.random() * 4; }
    else if (r < .68) { m.regime = "DRIFT DN"; m.vol = 18; regimeBias = -3 - Math.random() * 4; }
    else if (r < .84) { m.regime = "IMPULSE"; m.vol = 56; regimeBias = (Math.random() < .5 ? -1 : 1) * (12 + Math.random() * 18); }
    else { m.regime = "PULLBACK"; m.vol = 30; regimeBias = (BASE - m.last) * 0.012; }
    regimeUntil = Date.now() + 2600 + Math.random() * 6500;
  }

  function step(seed = false) {
    if (Date.now() > regimeUntil || seed) chooseRegime();
    const m = state.market;
    const cluster = 1 + Math.max(0, Math.sin(state.ticks.length / 9)) * 0.9 + (Math.random() < .05 ? 1.3 : 0);
    const shock = (Math.random() - .5) * m.vol * cluster;
    const pull = (BASE - m.last) * 0.015;
    m.momentum = m.momentum * .72 + regimeBias + shock + pull;
    let next = m.last + m.momentum;
    if (next < MIN) { next = MIN + (MIN - next) * .42; m.momentum = Math.abs(m.momentum) * .36; }
    if (next > MAX) { next = MAX - (next - MAX) * .42; m.momentum = -Math.abs(m.momentum) * .36; }
    m.last = clamp(next, MIN, MAX);
    const spreadTicks = clamp(2 + Math.floor(Math.abs(m.momentum) / 7) + (m.regime === "IMPULSE" ? 6 : 0), 2, 80);
    m.spread = spreadTicks * TICK; m.mid = m.last; m.bid = m.mid - m.spread / 2; m.ask = m.mid + m.spread / 2;
    const volume = 420000 + Math.random() * 2100000 + (m.regime === "IMPULSE" ? 2800000 : 0) + (m.regime === "COMP" ? -140000 : 0);
    state.ticks.push({ t: Date.now(), p: m.last, bid: m.bid, ask: m.ask, vol: Math.max(90000, volume), regime: m.regime, mom: m.momentum });
    if (state.ticks.length > 360) state.ticks.shift();
  }

  function makeBook() {
    const m = state.market, levels = 8, bids = [], asks = [];
    const pressure = clamp(m.momentum / 70, -1, 1);
    for (let i = 1; i <= levels; i++) {
      const curve = 1 + i * .19, pulse = 1 + Math.sin((state.ticks.length + i) * .71) * .18;
      const bidSize = (280000 + i * 112000) * curve * pulse * (1 + Math.max(0, pressure) * .5);
      const askSize = (280000 + i * 108000) * curve * (2 - pulse) * (1 + Math.max(0, -pressure) * .5);
      bids.push({ px: m.bid - (i - 1) * TICK * 2, sz: Math.max(65000, bidSize), cum: 0 });
      asks.push({ px: m.ask + (i - 1) * TICK * 2, sz: Math.max(65000, askSize), cum: 0 });
    }
    bids.reduce((a, x) => x.cum = a + x.sz, 0); asks.reduce((a, x) => x.cum = a + x.sz, 0);
    const b = bids.slice(0, 3).reduce((a, x) => a + x.sz, 0), a = asks.slice(0, 3).reduce((s, x) => s + x.sz, 0);
    m.imb = (b - a) / (b + a); m.micro = (m.ask * b + m.bid * a) / (a + b);
    state.book = { bids, asks };
  }

  function calc() {
    const win = state.ticks.slice(-180), m = state.market;
    m.high = Math.max(...win.map(x => x.p)); m.low = Math.min(...win.map(x => x.p));
    const sum = win.reduce((a, x) => a + x.p * x.vol, 0), vol = win.reduce((a, x) => a + x.vol, 0);
    m.vwap = sum / vol;
    const bins = 48, bucket = Array.from({ length: bins }, () => 0), lo = m.low, hi = m.high, span = Math.max(TICK, hi - lo);
    win.forEach(x => { bucket[clamp(Math.floor((x.p - lo) / span * bins), 0, bins - 1)] += x.vol; });
    let bi = 0; bucket.forEach((v, i) => { if (v > bucket[bi]) bi = i; }); m.poc = lo + (bi + .5) / bins * span;
    const recent = win.slice(-60), avg = recent.reduce((a, x) => a + x.p, 0) / recent.length;
    const sd = Math.sqrt(recent.reduce((a, x) => a + (x.p - avg) * (x.p - avg), 0) / recent.length);
    m.upper = avg + sd * 2.1; m.lower = avg - sd * 2.1;
    makeBook();
  }

  function seed() {
    regimeUntil = 0; regimeBias = 0;
    state.market.last = BASE + (Math.random() - .5) * 260;
    for (let i = 0; i < 240; i++) step(true);
    state.market.open = state.ticks[0].p;
    calc();
  }

  return {
    kind: "SIM",
    start(onData) {
      seed(); onData();
      timer = setInterval(() => { step(); calc(); onData(); }, CADENCE_MS);
    },
    stop() { clearInterval(timer); timer = null; }
  };
}
