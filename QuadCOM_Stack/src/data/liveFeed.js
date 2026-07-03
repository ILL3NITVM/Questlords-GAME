/* LIVE feed adapter — HARVESTED (Phase 7C) from predecessor QuadCOMv40Complete
 * -> app/connectors/BinanceConnector.js, refit into QuadCOM_Stack's feed seam.
 *
 * What was harvested: the proven read-only public market-data websocket logic
 * (aggTrade stream), exponential-backoff reconnect, and the 24h-ticker
 * top-of-book cache. What was NOT copied: nothing here places orders — there
 * is no broker execution path. This adapter engages only when MODE.LIVE is
 * flipped in src/config.js (ships false); the product posture stays lab-only.
 * Lab entries still settle locally against the printed tape. */
import { MODE, LIVE } from "../config.js";
import { clamp } from "../util.js";

const MAX_RECONNECT = 5;

export function createLiveFeed(ctx) {
  const state = ctx.state;
  const audit = ctx.audit || { tick() {} };
  let ws = null, onDataRef = null, reconnects = 0, closed = false;
  const depthCache = { bid: 0, ask: 0, bidQty: 0, askQty: 0 };

  // Map the active synthetic symbol to a public stream symbol (read-only data).
  function streamSymbol() {
    const raw = (state.asset.symbol || "BTCUSD.SYN").replace(".SYN", "").replace("/", "");
    return raw.toLowerCase() + "usdt".slice(raw.toLowerCase().endsWith("usd") ? 3 : 0);
  }

  async function primeDepth() {
    try {
      const sym = streamSymbol().toUpperCase().replace("USD", "USDT");
      const r = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${sym}`);
      const d = await r.json();
      depthCache.bid = parseFloat(d.bidPrice); depthCache.ask = parseFloat(d.askPrice);
      depthCache.bidQty = parseFloat(d.bidQty); depthCache.askQty = parseFloat(d.askQty);
    } catch (_) { /* depth cache stays soft — tick mid +/- spread fallback */ }
  }

  function ingest(px, qty) {
    const a = state.asset, m = state.market;
    const half = (a.tick * (a.spreadTicks || 2)) / 2;
    m.last = px;
    m.bid = depthCache.bid || px - half;
    m.ask = depthCache.ask || px + half;
    m.mid = (m.bid + m.ask) / 2; m.spread = m.ask - m.bid;
    m.momentum = px - (state.ticks.at(-1)?.p ?? px);
    state.ticks.push({ t: Date.now(), p: px, bid: m.bid, ask: m.ask, vol: Math.max(1, qty || 1), regime: m.regime, mom: m.momentum });
    if (state.ticks.length > 360) state.ticks.shift();
    audit.tick(px);

    // Rolling analytics — identical shape to the synthetic path.
    const win = state.ticks.slice(-180);
    m.high = Math.max(...win.map(x => x.p)); m.low = Math.min(...win.map(x => x.p));
    m.vwap = win.reduce((s, x) => s + x.p * x.vol, 0) / Math.max(1, win.reduce((s, x) => s + x.vol, 0));
    const recent = win.slice(-60), avg = recent.reduce((s, x) => s + x.p, 0) / Math.max(1, recent.length);
    const sd = Math.sqrt(recent.reduce((s, x) => s + (x.p - avg) ** 2, 0) / Math.max(1, recent.length));
    m.upper = avg + sd * 2.1; m.lower = avg - sd * 2.1; m.poc = avg; m.micro = m.mid;
    const mt = Math.abs(m.momentum) / (a.tick || 1);
    m.regime = mt > 16 ? "IMPULSE" : m.momentum > a.tick ? "DRIFT UP" : m.momentum < -a.tick ? "DRIFT DN" : "COMP";
    m.imb = clamp((depthCache.bidQty - depthCache.askQty) / Math.max(1, depthCache.bidQty + depthCache.askQty), -1, 1);
    if (onDataRef) onDataRef();
  }

  function connect() {
    if (closed) return;
    try {
      const base = LIVE.feedWs && !LIVE.feedWs.includes("REPLACE_ME")
        ? LIVE.feedWs
        : "wss://stream.binance.com:9443/ws";
      ws = new WebSocket(`${base}/${streamSymbol()}@aggTrade`);
      ws.onopen = () => { reconnects = 0; primeDepth(); };
      ws.onmessage = ev => {
        try {
          const d = JSON.parse(ev.data);
          if (d.p !== undefined) ingest(parseFloat(d.p), parseFloat(d.q));
        } catch (_) { /* ignore malformed frames */ }
      };
      ws.onclose = () => reconnect();
      ws.onerror = () => { try { ws.close(); } catch (_) {} };
    } catch (_) {
      console.warn("[liveFeed] live stream unavailable — check src/config.js LIVE settings.");
    }
  }
  function reconnect() {
    if (closed || reconnects >= MAX_RECONNECT) return;
    reconnects++;
    setTimeout(connect, Math.min(30000, 1000 * 2 ** (reconnects - 1)));
  }

  return {
    kind: "LIVE",
    start(onData) { onDataRef = onData; closed = false; connect(); },
    stop() { closed = true; try { ws && ws.close(); } catch (_) {} ws = null; },
    reseed() { /* a live tape owns its own history — nothing to reseed */ }
  };
}
