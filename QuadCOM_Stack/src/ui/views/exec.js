/* EXEC view — autopilot engine, live position book, execution tape. */
import { fmt, money, now, $ } from "../../util.js";
import { governorState } from "../../engines/governor.js";
import { readout } from "../components.js";

function positionRows(state) {
  const m = state.market;
  if (!state.positions.length)
    return `<div class="tape-row"><span>${now()}</span><b>FLAT</b><span>no open positions</span></div>`;
  return state.positions.map(p => {
    const total = Math.max(1, p.expires - p.opened);
    const left = Math.max(0, (p.expires - Date.now()) / 1000);
    const rem = Math.max(0, Math.min(1, (p.expires - Date.now()) / total));
    const lead = p.dir === "CALL" ? m.bid - p.entry : p.entry - m.ask;
    const winning = lead > 0;
    const proj = winning ? p.stake * p.payout : -p.stake;
    return `<div class="tape-row pos ${winning ? "in" : "out"}"><span>${p.dir}${p.src === "AUTO" ? " A" : ""}</span><b>${fmt(p.entry)}</b><span>${left.toFixed(0)}s ${winning ? "▲" : "▼"}${fmt(Math.abs(lead))} ${(proj >= 0 ? "+" : "") + money(proj)}</span><i class="pos-prog" style="width:${(rem * 100).toFixed(1)}%"></i></div>`;
  }).join("");
}

function lifecycleRows(state, limit = 18) {
  return state.ledger.filter(x => /^(CALL|PUT|WIN|LOSS|REFUND|MAX|CASH|BLOCK|AUTO|ARM|IN|OUT)$/.test(x.tag)).slice(0, limit);
}

export function renderExec(state, ctx) {
  const s = ctx.settings(), g = governorState(state);
  $("autopilotBtn").textContent = state.autopilot ? "AUTOPILOT ENABLED" : "ENABLE AUTOPILOT";
  $("autopilotBtn").classList.toggle("on", state.autopilot);
  $("autoMode").textContent = state.autopilot ? "ON" : "OFF";
  $("autopilotReadouts").innerHTML = [
    readout("Status", g.state === "HALT" ? "HALT" : state.autoStatus, g.state === "HALT" ? "bad" : state.autopilot ? "good" : ""),
    readout("Fires", state.autoFires, "gold"),
    readout("Gate", s.gate),
    readout("Size", "1.00x", "good")
  ].join("");
  const chips = $("stakeChips");
  if (chips) {
    const bal = state.metrics.balance;
    const riskPct = bal > 0 ? (s.stake / bal * 100) : 0;
    chips.innerHTML = [["10%", .1], ["25%", .25], ["50%", .5], ["MAX", 1]]
      .map(([l, r]) => `<button class="chip" type="button" data-stakepct="${r}">${l}</button>`).join("") +
      `<span class="risk ${riskPct > 50 ? "hot" : ""}">RISK ${riskPct.toFixed(0)}%</span>`;
  }
  $("posMeta").textContent = `${state.positions.length}/${s.slots} open`;
  $("posBook").innerHTML = `<div class="tape">${positionRows(state)}</div>`;
  $("execTape").innerHTML = `<div class="tape">${lifecycleRows(state).map(x =>
    `<div class="tape-row"><span>${x.t}</span><b>${x.tag}</b><span>${x.txt}</span></div>`).join("") ||
    `<div class='tape-row'><span>${now()}</span><b>READY</b><span>lifecycle tape waiting</span></div>`}</div>`;
}
