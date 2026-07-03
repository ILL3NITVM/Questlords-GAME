/* Canvas renderers: the main price chart (rolling walls, SAR-style momentum
 * dots, VWAP/POC/BID/ASK refs, live position markers + tracking rays, hover
 * crosshair) and the cumulative depth curve. Reads state only. */
import { fmt, clamp, $ } from "../util.js";

const FONT = () => getComputedStyle(document.body).fontFamily || "monospace";
const varGet = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function fitCanvas(c) {
  const r = c.getBoundingClientRect(), d = Math.min(3, window.devicePixelRatio || 1);
  const w = Math.max(1, Math.floor(r.width * d)), h = Math.max(1, Math.floor(r.height * d));
  if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
  const ctx = c.getContext("2d");
  ctx.setTransform(d, 0, 0, d, 0, 0);
  return { ctx, w: r.width, h: r.height };
}
function line(ctx, x1, y1, x2, y2, stroke, width = 1, dash = []) {
  ctx.save(); ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.setLineDash(dash);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); ctx.restore();
}

export function drawChart(state) {
  const c = $("chart"); if (!c) return;
  const { ctx, w, h } = fitCanvas(c); if (w < 10 || h < 10) return;
  ctx.clearRect(0, 0, w, h);
  const data = state.ticks.slice(-190), m = state.market;
  if (data.length < 2) return;
  const L = 7, R = 64, T = 13, B = 18, cw = w - L - R, ch = h - T - B;
  let lo = Math.min(m.low, m.lower, ...data.map(x => x.p)), hi = Math.max(m.high, m.upper, ...data.map(x => x.p));
  // Tick-relative vertical framing (Phase 7C) so every instrument fills the
  // stage: 520 ticks minimum window, 70-tick breathing room.
  const tick = (state.asset && state.asset.tick) || 0.5;
  const minRange = tick * 520, mid = (hi + lo) / 2;
  if (hi - lo < minRange) { hi = mid + minRange / 2; lo = mid - minRange / 2; }
  hi += tick * 70; lo -= tick * 70;
  const xAt = i => L + i / (data.length - 1) * cw, yAt = p => T + (hi - p) / (hi - lo) * ch;
  const f = FONT();

  const grad = ctx.createLinearGradient(0, T, 0, h); grad.addColorStop(0, "#0c111a"); grad.addColorStop(1, "#020304");
  ctx.fillStyle = grad; ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 5; i++) { const y = T + i / 4 * ch; line(ctx, L, y, L + cw, y, "rgba(255,255,255,.055)", 1); }
  for (let i = 0; i < 7; i++) { const x = L + i / 6 * cw; line(ctx, x, T, x, T + ch, "rgba(255,255,255,.035)", 1); }

  data.forEach((d, i) => {
    if (i % 8) return;
    const x = xAt(i), ww = cw / data.length * 8;
    let col = "rgba(78,161,255,.035)";
    if (d.regime === "IMPULSE") col = "rgba(216,183,63,.055)";
    if (d.regime === "DRIFT UP") col = "rgba(49,209,123,.035)";
    if (d.regime === "DRIFT DN") col = "rgba(240,93,82,.035)";
    ctx.fillStyle = col; ctx.fillRect(x, T, ww, ch);
  });

  const highWall = clamp(yAt(m.high), T, T + ch), lowWall = clamp(yAt(m.low), T, T + ch);
  ctx.fillStyle = "rgba(240,93,82,.16)"; ctx.fillRect(L, Math.max(T, highWall - 18), cw, 30);
  ctx.fillStyle = "rgba(49,209,123,.16)"; ctx.fillRect(L, Math.min(T + ch - 30, lowWall - 12), cw, 30);
  for (let x = L; x < L + cw; x += 12) {
    line(ctx, x, Math.max(T, highWall - 18), x + 8, Math.max(T, highWall - 18) + 30, "rgba(240,93,82,.26)", 1);
    line(ctx, x, Math.min(T + ch - 30, lowWall - 12) + 30, x + 8, Math.min(T + ch - 30, lowWall - 12), "rgba(49,209,123,.25)", 1);
  }
  ctx.fillStyle = "rgba(240,93,82,.82)"; ctx.font = "bold 7px " + f;
  ctx.fillText(`HIGH ROLLING WALL ${fmt(m.high)}`, L + 4, Math.max(T + 8, highWall - 7));
  ctx.fillStyle = "rgba(49,209,123,.82)";
  ctx.fillText(`LOW ROLLING WALL ${fmt(m.low)}`, L + 4, Math.min(T + ch - 5, lowWall + 14));

  const band = ctx.createLinearGradient(0, yAt(m.upper), 0, yAt(m.lower));
  band.addColorStop(0, "rgba(216,183,63,.08)"); band.addColorStop(.5, "rgba(216,183,63,.02)"); band.addColorStop(1, "rgba(78,161,255,.06)");
  ctx.fillStyle = band; ctx.fillRect(L, yAt(m.upper), cw, Math.max(2, yAt(m.lower) - yAt(m.upper)));

  [[m.high, "rgba(240,93,82,.10)"], [m.low, "rgba(49,209,123,.10)"], [m.poc, "rgba(216,183,63,.13)"]].forEach(([p, col]) => {
    const y = yAt(p); ctx.fillStyle = col; ctx.fillRect(L, y - 5, cw, 10);
  });
  const refs = [
    [m.high, "HIGH", "rgba(240,93,82,.72)", []], [m.low, "LOW", "rgba(49,209,123,.72)", []],
    [m.vwap, "VWAP", "rgba(78,161,255,.78)", [3, 3]], [m.poc, "POC", "rgba(216,183,63,.86)", [5, 3]],
    [m.bid, "BID", "rgba(49,209,123,.32)", [2, 2]], [m.ask, "ASK", "rgba(240,93,82,.32)", [2, 2]]
  ];
  refs.forEach(([p, label, col, dash]) => {
    const y = yAt(p); line(ctx, L, y, L + cw, y, col, 1, dash);
    ctx.fillStyle = col; ctx.font = "6px " + f; ctx.fillText(label, L + 2, y - 2);
  });

  ctx.save(); ctx.beginPath();
  data.forEach((d, i) => { const x = xAt(i), y = yAt(d.p); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.lineWidth = 4; ctx.strokeStyle = "rgba(216,183,63,.10)"; ctx.stroke();
  ctx.lineWidth = 1.4; ctx.strokeStyle = "#f2cc58"; ctx.stroke(); ctx.restore();

  ctx.save();
  data.forEach((d, i) => {
    if (i % 5) return;
    const x = xAt(i), y = yAt(d.p), yy = y + (d.mom >= 0 ? 8 : -8);
    ctx.fillStyle = d.mom >= 0 ? "rgba(49,209,123,.62)" : "rgba(240,93,82,.62)";
    ctx.beginPath(); ctx.arc(x, yy, 1.5, 0, Math.PI * 2); ctx.fill();
  });
  ctx.restore();

  // Past trade-order history markers — mapped by open timestamp so they hold
  // their real chart position as the tick buffer scrolls; skipped once aged out.
  if (state.tradeHistory && state.tradeHistory.length) {
    const t0 = data[0].t, tN = data[data.length - 1].t, tSpan = (tN - t0) || 1;
    const outCol = { WIN: "#2ecc71", LOSS: "#ef4d3f", REFUND: "#f0a43a" };
    state.tradeHistory.forEach(hh => {
      if (hh.t < t0) return;
      const x = L + clamp((hh.t - t0) / tSpan, 0, 1) * cw, y = yAt(hh.entry);
      const col = outCol[hh.out] || "#7a8494";
      ctx.save();
      ctx.globalAlpha = .85;
      ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 1;
      const s = 3;
      ctx.beginPath(); // diamond marker at entry
      ctx.moveTo(x, y - s); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s); ctx.lineTo(x - s, y); ctx.closePath();
      if (hh.out === "WIN") ctx.fill(); else ctx.stroke();
      // tiny dir notch above/below the diamond
      ctx.beginPath();
      if (hh.dir === "CALL") { ctx.moveTo(x, y - s - 3); ctx.lineTo(x - 2, y - s); ctx.lineTo(x + 2, y - s); }
      else { ctx.moveTo(x, y + s + 3); ctx.lineTo(x - 2, y + s); ctx.lineTo(x + 2, y + s); }
      ctx.closePath(); ctx.fill();
      ctx.restore();
    });
  }

  state.positions.forEach(p => {
    const idx = clamp(p.idx - (state.ticks.length - data.length), 0, data.length - 1), x = xAt(idx), y = yAt(p.entry);
    const col = p.dir === "CALL" ? (varGet("--green") || "#2ecc71") : (varGet("--red") || "#ef4d3f");
    line(ctx, x, y, L + cw, y, col, .9, [4, 3]);
    ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#000"; ctx.font = "5px " + f; ctx.fillText(p.dir[0], x - 1.8, y + 1.8);
  });

  line(ctx, L, yAt(m.last), L + cw, yAt(m.last), "rgba(255,255,255,.38)", 1, [2, 2]);
  ctx.fillStyle = "#050609"; ctx.fillRect(w - R, 0, R, h);
  ctx.strokeStyle = "rgba(216,183,63,.35)"; ctx.beginPath(); ctx.moveTo(w - R, T); ctx.lineTo(w - R, T + ch); ctx.stroke();
  for (let i = 0; i < 6; i++) {
    const p = hi - i / 5 * (hi - lo), y = yAt(p);
    ctx.fillStyle = "rgba(255,255,255,.68)"; ctx.font = "7px " + f; ctx.fillText(fmt(p), w - R + 4, y + 2);
  }
  const ly = yAt(m.last);
  ctx.fillStyle = "#d8b73f"; ctx.fillRect(w - R + 1, ly - 8, R - 1, 16);
  ctx.fillStyle = "#020304"; ctx.font = "bold 8px " + f; ctx.fillText(fmt(m.last), w - R + 5, ly + 3);

  if (state.pointer) {
    const px = clamp(state.pointer.x, L, L + cw), py = clamp(state.pointer.y, T, T + ch);
    line(ctx, px, T, px, T + ch, "rgba(255,255,255,.22)", 1, [2, 3]);
    line(ctx, L, py, L + cw, py, "rgba(255,255,255,.18)", 1, [2, 3]);
    const ix = clamp(Math.round((px - L) / cw * (data.length - 1)), 0, data.length - 1), d = data[ix];
    const tip = $("tip");
    if (tip && d) {
      tip.style.display = "block";
      tip.style.left = clamp(px + 8, 6, w - 112) + "px";
      tip.style.top = clamp(py - 45, 6, h - 58) + "px";
      tip.innerHTML = `<b>${fmt(d.p)}</b><br>${d.regime}<br>spread ${fmt(d.ask - d.bid)}`;
    }
  }
}

export function drawDepth(state) {
  const c = $("depth"); if (!c) return;
  const { ctx, w, h } = fitCanvas(c); if (w < 10 || h < 10) return;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#020304"; ctx.fillRect(0, 0, w, h);
  const bids = state.book.bids, asks = state.book.asks;
  if (!bids.length || !asks.length) return;
  const max = Math.max(bids.at(-1).cum, asks.at(-1).cum), pad = 10;
  for (let i = 0; i < 4; i++) line(ctx, pad, pad + i * (h - 2 * pad) / 3, w - pad, pad + i * (h - 2 * pad) / 3, "rgba(255,255,255,.05)", 1);
  const curve = (rows, col, flip) => {
    ctx.beginPath();
    rows.forEach((r, i) => {
      const x = pad + r.cum / max * (w - 2 * pad), y = pad + i / (rows.length - 1) * (h - 2 * pad);
      const xx = flip ? w - x : x; i ? ctx.lineTo(xx, y) : ctx.moveTo(xx, y);
    });
    ctx.lineWidth = 2; ctx.strokeStyle = col; ctx.stroke();
  };
  curve(bids, "#31d17b", true); curve(asks, "#f05d52", false);
  line(ctx, w / 2, pad, w / 2, h - pad, "rgba(216,183,63,.35)", 1, [3, 3]);
}
