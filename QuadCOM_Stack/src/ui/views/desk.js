/* DESK view — order book, depth curve, microprice, structure, regime
 * timeline (Phase 9, after the predecessor RegimeDetectionEngine concept) and
 * the multi-instrument watch strip (Phase 15). */
import { fmt, sizeFmt, $ } from "../../util.js";
import { ASSETS } from "../../config.js";
import { drawDepth } from "../chart.js";

const REGIME_COLOR = { "COMP": "#3b4658", "DRIFT UP": "#2ecc71", "DRIFT DN": "#ef4d3f", "IMPULSE": "#f2cc58", "PULLBACK": "#3498db" };

function regimeStrip(state) {
  const win = state.ticks.slice(-90);
  if (win.length < 2) return "";
  const segs = win.map(t => `<i style="background:${REGIME_COLOR[t.regime] || "#3b4658"}"></i>`).join("");
  const m = state.market;
  return `<div class="module wide"><div class="mh"><span>Regime timeline</span><span>${m.regime} · last 90 prints</span></div>
    <div class="mb"><div class="regime-strip">${segs}</div>
    <div class="regime-key">${Object.entries(REGIME_COLOR).map(([k, c]) => `<span><i style="background:${c}"></i>${k}</span>`).join("")}</div></div></div>`;
}

function watchStrip(state) {
  // Synthetic reference prints for sibling instruments — light deterministic
  // drift around base so the desk reads as a multi-instrument venue.
  const sibs = Object.values(ASSETS).filter(a => a.symbol !== state.asset.symbol).slice(0, 8);
  const t = Date.now();
  const rows = sibs.slice(0, 4).map((a, i) => {
    const drift = Math.sin(t / 9700 + i * 2.1) * 0.004 + Math.sin(t / 3100 + i) * 0.0012;
    const px = a.base * (1 + drift);
    const dec = a.decimals;
    return `<div class="watch-cell ${drift >= 0 ? "up" : "dn"}"><span>${a.symbol}</span><b>${px.toFixed(dec)}</b><i>${drift >= 0 ? "▲" : "▼"}${(Math.abs(drift) * 100).toFixed(2)}%</i></div>`;
  }).join("");
  return `<div class="module wide"><div class="mh"><span>Watch</span><span>synthetic reference prints</span></div><div class="mb"><div class="watch-strip">${rows}</div></div></div>`;
}

export function renderDesk(state) {
  const m = state.market, book = state.book;
  if (!book.bids.length || !book.asks.length) return;
  const askRows = book.asks.slice().reverse().map((x, i) =>
    `<tr class="ask ${i === book.asks.length - 1 ? "best" : ""}"><td class="cum">${sizeFmt(x.cum)}</td><td class="sz">${sizeFmt(x.sz)}</td><td class="px">${fmt(x.px)}</td></tr>`).join("");
  const bidRows = book.bids.map((x, i) =>
    `<tr class="bid ${i === 0 ? "best" : ""}"><td class="cum">${sizeFmt(x.cum)}</td><td class="sz">${sizeFmt(x.sz)}</td><td class="px">${fmt(x.px)}</td></tr>`).join("");
  const topDepth = book.bids[0].sz + book.asks[0].sz;
  $("deskBody").innerHTML = `
    <div class="module book"><div class="mh"><span>Order book</span><span>${state.asset.symbol}</span></div><div class="mb"><table class="ladder"><tbody>${askRows}${bidRows}</tbody></table></div></div>
    <div class="module"><div class="mh"><span>Depth</span><span>cum curve</span></div><div class="mb"><div class="depth-wrap"><canvas id="depth"></canvas><div class="legend"><span><i class="dot g"></i>bid</span><span><i class="dot r"></i>ask</span></div></div></div></div>
    <div class="module"><div class="mh"><span>Microprice</span><span>${fmt(m.micro)}</span></div><div class="mb"><div class="kv">
      <div><span>Best bid</span><b>${fmt(book.bids[0].px)}</b></div><div><span>Best ask</span><b>${fmt(book.asks[0].px)}</b></div>
      <div><span>Spread</span><b>${fmt(m.spread)}</b></div><div><span>Mid</span><b>${fmt(m.mid)}</b></div>
      <div><span>Imbalance</span><b>${(m.imb * 100).toFixed(1)}%</b></div><div><span>Top depth</span><b>${sizeFmt(topDepth)}</b></div>
    </div></div></div>
    <div class="module"><div class="mh"><span>Structure</span><span>${m.regime}</span></div><div class="mb"><div class="kv">
      <div><span>High</span><b>${fmt(m.high)}</b></div><div><span>Low</span><b>${fmt(m.low)}</b></div>
      <div><span>VWAP</span><b>${fmt(m.vwap)}</b></div><div><span>POC</span><b>${fmt(m.poc)}</b></div>
      <div><span>Band upper</span><b>${fmt(m.upper)}</b></div><div><span>Band lower</span><b>${fmt(m.lower)}</b></div>
    </div></div></div>
    ${regimeStrip(state)}
    ${watchStrip(state)}`;
  drawDepth(state);
}
