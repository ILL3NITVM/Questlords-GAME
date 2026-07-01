/* DESK view — order book, depth curve, microprice, structure. */
import { fmt, sizeFmt, $ } from "../../util.js";
import { INSTRUMENT } from "../../config.js";
import { drawDepth } from "../chart.js";

export function renderDesk(state) {
  const m = state.market, book = state.book;
  if (!book.bids.length || !book.asks.length) return;
  const askRows = book.asks.slice().reverse().map((x, i) =>
    `<tr class="ask ${i === book.asks.length - 1 ? "best" : ""}"><td class="cum">${sizeFmt(x.cum)}</td><td class="sz">${sizeFmt(x.sz)}</td><td class="px">${fmt(x.px)}</td></tr>`).join("");
  const bidRows = book.bids.map((x, i) =>
    `<tr class="bid ${i === 0 ? "best" : ""}"><td class="cum">${sizeFmt(x.cum)}</td><td class="sz">${sizeFmt(x.sz)}</td><td class="px">${fmt(x.px)}</td></tr>`).join("");
  const topDepth = book.bids[0].sz + book.asks[0].sz;
  $("deskBody").innerHTML = `
    <div class="module book"><div class="mh"><span>Order book</span><span>${INSTRUMENT}</span></div><div class="mb"><table class="ladder"><tbody>${askRows}${bidRows}</tbody></table></div></div>
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
    </div></div></div>`;
  drawDepth(state);
}
