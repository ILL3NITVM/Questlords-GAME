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

function readyConditions(state, s) {
  const c = state.council;
  return [
    ["Lab funded", state.metrics.balance >= s.stake],
    ["Open slot free", state.positions.length < s.slots],
    [`Confidence ≥ gate (${c.conf.toFixed(0)}/${s.gate})`, c.conf >= s.gate],
    ["Lab armed", state.armed],
    ["Autopilot lab on", state.autopilot],
    ["Spacing clear", (Date.now() - state.lastAuto) >= 4200]
  ];
}

function whyNotFiring(state, s) {
  const c = state.council;
  if (!state.autopilot) return "Autopilot lab is off — manual CALL / PUT lab entries only.";
  if (!state.armed) return "Lab is disarmed — arm the lab to allow autopilot entries.";
  if (c.conf < s.gate) return `Confidence below threshold — execution held (${c.conf.toFixed(0)} < ${s.gate}).`;
  if (state.positions.length >= s.slots) return "Exposure limit reached — waiting for open positions to resolve.";
  if (state.metrics.balance < s.stake) return "Lab capital below stake — fund via GOV faucet.";
  if ((Date.now() - state.lastAuto) < 4200) return "Spacing window — pacing entries between prints.";
  return "Ready — autopilot lab will fire on the next qualifying tick.";
}

export function renderExec(state, ctx) {
  const s = ctx.settings(), g = governorState(state);
  $("autopilotBtn").textContent = state.autopilot ? "AUTOPILOT LAB ENABLED" : "ENABLE AUTOPILOT LAB";
  $("autopilotBtn").classList.toggle("on", state.autopilot);
  $("autoMode").textContent = state.autopilot ? "ON" : "OFF";
  $("autopilotReadouts").innerHTML = [
    readout("Status", g.state === "HALT" ? "HALT" : state.autoStatus, g.state === "HALT" ? "bad" : state.autopilot ? "good" : ""),
    readout("Fires", state.autoFires, "gold"),
    readout("Gate", s.gate),
    readout("Size", "1.00x", "good")
  ].join("");
  const fs = $("fireStatus");
  if (fs) {
    const ready = whyNotFiring(state, s).startsWith("Ready");
    fs.innerHTML =
      `<div class="why ${ready ? "ok" : ""}"><b>Why not firing?</b> ${whyNotFiring(state, s)}</div>` +
      `<div class="ready-list">` + readyConditions(state, s).map(([l, ok]) =>
        `<div class="ready-row ${ok ? "on" : ""}"><i>${ok ? "✓" : "○"}</i>${l}</div>`).join("") + `</div>`;
  }
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
