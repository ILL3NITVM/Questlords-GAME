/* LIVE venture adapter for real market data.
 *
 * This is the production seam that engages when MODE.LIVE === true. It connects
 * to a real market-data websocket and maps each message into the exact same
 * {market, book, ticks} state shape the synthetic feed produces — so nothing
 * downstream (engines, chart, views) changes.
 *
 * Wire LIVE.feedWs / LIVE.feedRest in src/config.js to your venue, then flip
 * MODE.LIVE. The mapping below is intentionally explicit so a real payload can
 * be dropped in directly. */
import { LIVE, TICK } from "../config.js";
import { clamp } from "../util.js";

export function createLiveFeed(state) {
  let ws = null, onDataRef = null, retry = 0;

  function ingest(px, bid, ask, bidsDepth, asksDepth) {
    const m = state.market;
    m.last = px; m.bid = bid; m.ask = ask; m.mid = (bid + ask) / 2; m.spread = ask - bid;
    state.ticks.push({ t: Date.now(), p: px, bid, ask, vol: 1, regime: m.regime, mom: m.momentum });
    if (state.ticks.length > 360) state.ticks.shift();

    // Depth ladder from the venue book (fallback: synth around top-of-book).
    const bids = (bidsDepth || []).map(([p, s], i) => ({ px: p, sz: s, cum: 0 }));
    const asks = (asksDepth || []).map(([p, s], i) => ({ px: p, sz: s, cum: 0 }));
    bids.reduce((a, x) => x.cum = a + x.sz, 0); asks.reduce((a, x) => x.cum = a + x.sz, 0);
    if (bids.length && asks.length) {
      const b = bids.slice(0, 3).reduce((a, x) => a + x.sz, 0), a = asks.slice(0, 3).reduce((s, x) => s + x.sz, 0);
      m.imb = (b - a) / (b + a); m.micro = (m.ask * b + m.bid * a) / (a + b);
      state.book = { bids, asks };
    }

    // Rolling analytics identical to the sim path.
    const win = state.ticks.slice(-180);
    m.high = Math.max(...win.map(x => x.p)); m.low = Math.min(...win.map(x => x.p));
    m.vwap = win.reduce((s, x) => s + x.p, 0) / win.length;
    const recent = win.slice(-60), avg = recent.reduce((a, x) => a + x.p, 0) / recent.length;
    const sd = Math.sqrt(recent.reduce((a, x) => a + (x.p - avg) ** 2, 0) / Math.max(1, recent.length));
    m.upper = avg + sd * 2.1; m.lower = avg - sd * 2.1; m.poc = avg;
    m.momentum = px - (state.ticks.at(-2)?.p ?? px);
    m.regime = Math.abs(m.momentum) > 8 ? "IMPULSE" : m.momentum > 1 ? "DRIFT UP" : m.momentum < -1 ? "DRIFT DN" : "COMP";
    if (onDataRef) onDataRef();
  }

  function connect() {
    try {
      ws = new WebSocket(LIVE.feedWs);
      ws.onopen = () => { retry = 0; state.sw = state.sw; };
      ws.onmessage = ev => {
        // TODO: replace with your venue's payload schema.
        try {
          const d = JSON.parse(ev.data);
          ingest(+d.price, +d.bid, +d.ask, d.bids, d.asks);
        } catch (_) { /* ignore malformed frames */ }
      };
      ws.onclose = () => { if (retry++ < 6) setTimeout(connect, Math.min(16000, 1000 * 2 ** retry)); };
      ws.onerror = () => { try { ws.close(); } catch (_) {} };
    } catch (_) {
      // Endpoint not configured — surface clearly rather than crash.
      console.warn("[liveFeed] LIVE.feedWs is not reachable; configure src/config.js before going live.");
    }
  }

  return {
    kind: "LIVE",
    start(onData) { onDataRef = onData; connect(); },
    stop() { try { ws && ws.close(); } catch (_) {} ws = null; }
  };
}
