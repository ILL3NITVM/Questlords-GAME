/* GOV view — business-grade capital governor.
 * States: risk / exposure / capital / integrity / autopilot, plus a plain
 * reason for the current hold or clear, the last governor event, and what
 * would unlock action. The governor never rewrites the record; losses stay. */
import { money, now, $ } from "../../util.js";
import { governorState } from "../../engines/governor.js";
import { readout } from "../components.js";

function holdReason(state, s) {
  const c = state.council;
  if (!state.sessionReady) return "Gateway locked — connect an operator to open the lab.";
  if (state.metrics.balance <= 0 && !state.positions.length) return "Awaiting deposit — fund lab capital via the faucet rail.";
  if (state.positions.length >= s.slots) return "Exposure limit reached — waiting for open positions to resolve.";
  if (c.conf < s.gate) return "Confidence below threshold — execution held.";
  if (!state.armed) return "Lab disarmed — arm the lab to allow entries.";
  return "Clear — structure, capital, and gate all permit action.";
}

function unlockHint(state, s) {
  const c = state.council;
  if (!state.sessionReady) return "Connect via the secure gateway.";
  if (state.metrics.balance <= 0 && !state.positions.length) return "Deposit lab capital from the faucet.";
  if (state.positions.length >= s.slots) return "An open position resolving frees a slot.";
  if (c.conf < s.gate) return `Confidence rising to ${s.gate}+ unlocks the gate.`;
  if (!state.armed) return "Tap ARM LAB in the top bar.";
  return "Nothing — action is already unlocked.";
}

function lastGovEvent(state) {
  const e = [...state.auditLog].reverse().find(x => x.type === "GOVERNOR_CLEAR" || x.type === "GOVERNOR_BLOCK");
  if (!e) return "No governor events yet this session.";
  return `${new Date(e.t).toLocaleTimeString([], { hour12: false })} · ${e.type === "GOVERNOR_BLOCK" ? "HOLD" : "CLEAR"} — ${e.data && e.data.reason ? e.data.reason : ""}`;
}

function transferRows(state, limit = 8) {
  return state.transfers.slice(0, limit).map(x =>
    `<div class="tape-row ${x.side === "IN" ? "in" : "out"}"><span>${x.t}</span><b>${x.side === "IN" ? "+ IN" : "- OUT"}</b><span>${money(x.amount)} | bal ${money(x.balance)}</span></div>`
  ).join("") || `<div class="tape-row"><span>${now()}</span><b>LEDGER</b><span>no wallet transfers recorded</span></div>`;
}

export function renderGov(state, ctx) {
  const { wallet } = ctx;
  const s = ctx.settings();
  const g = governorState(state), net = g.equity - g.capital;
  const c = state.council;
  const holding = !holdReason(state, s).startsWith("Clear");
  const riskState = state.metrics.lossStreak >= 3 ? "ELEVATED" : "NOMINAL";
  const expoState = state.positions.length >= s.slots ? "FULL" : state.positions.length ? "ACTIVE" : "FLAT";
  const capState = state.metrics.balance > 0 || state.positions.length ? "FUNDED" : "AWAITING DEPOSIT";
  document.querySelectorAll("[data-gov-tab]").forEach(b => b.classList.toggle("active", b.dataset.govTab === state.govTab));

  if (state.govTab === "capital") {
    $("govBody").innerHTML =
      `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Capital Governor</span><span>${wallet.label()}</span></div><div class="panel-body">` +
      `<div class="gov-state ${holding ? "hold" : ""}">${holding ? "HOLDING" : "CLEAR"}</div>` +
      `<div class="verdict" style="margin-top:8px">${holdReason(state, s)}</div>` +
      `<div class="readout-grid" style="margin-top:8px">` +
      readout("Risk State", riskState, riskState === "NOMINAL" ? "good" : "bad") +
      readout("Exposure State", expoState, expoState === "FULL" ? "bad" : "good") +
      readout("Capital State", capState, capState === "FUNDED" ? "good" : "bad") +
      readout("Integrity", state.session ? state.session.integrity : "CLEAR", "good") +
      readout("Autopilot", state.autopilot ? "ON" : "OFF", state.autopilot ? "good" : "") +
      readout("Gate", `${c.conf.toFixed(0)}/${s.gate}`, c.conf >= s.gate ? "good" : "gold") +
      `</div>` +
      `<div class="gov-lines">` +
      `<div class="gov-line"><span>Last governor event</span><b>${lastGovEvent(state)}</b></div>` +
      `<div class="gov-line"><span>What would unlock action</span><b>${unlockHint(state, s)}</b></div>` +
      `</div>` +
      `<div class="transfer-rail"><input id="transferAmount" inputmode="decimal" value="${state.transferDraft}" aria-label="Transfer amount"><button id="depositBtn" class="deposit" type="button">Deposit Faucet</button><button id="withdrawBtn" class="withdraw" type="button">Withdraw</button></div>` +
      `<div class="ledger-tape"><div class="tape">${transferRows(state)}</div></div>` +
      `</div></section></div>`;
  } else if (state.govTab === "pressure") {
    $("govBody").innerHTML =
      `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Pressure Metrics</span><span>${holding ? "HOLDING" : "CLEAR"}</span></div><div class="panel-body"><div class="readout-grid">` +
      readout("Drawdown %", g.drawdown.toFixed(2) + "%", g.drawdown > 5 ? "bad" : "good") +
      readout("Exposure %", g.exposure.toFixed(1) + "%", g.exposure > 30 ? "bad" : "") +
      readout("Loss Streak", g.lossStreak, g.lossStreak > 3 ? "bad" : "good") +
      readout("Open", state.positions.length + "/" + s.slots) +
      readout("Peak Equity", money(g.peak), "gold") +
      readout("Capital Basis", money(g.capital)) +
      readout("Net", (net >= 0 ? "+" : "-") + money(Math.abs(net)), net >= 0 ? "good" : "bad") +
      readout("Turnover", money(state.metrics.turnover), "gold") +
      `</div></div></section></div>`;
  } else {
    $("govBody").innerHTML =
      `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Guard Contract</span><span>EXEC ${holding ? "HELD" : "CLEAR"}</span></div><div class="panel-body"><div class="tape">` +
      `<div class="tape-row"><span>${now()}</span><b>TAPE</b><span>forward-printing — no rewrite after print</span></div>` +
      `<div class="tape-row"><span>${now()}</span><b>DD</b><span>drawdown ${g.drawdown.toFixed(2)}% — informational, no forced halt</span></div>` +
      `<div class="tape-row"><span>${now()}</span><b>STREAK</b><span>loss streak ${g.lossStreak} — losses remain in the record</span></div>` +
      `<div class="tape-row"><span>${now()}</span><b>GATE</b><span>${c.conf >= s.gate ? "confidence above gate — entries permitted" : "confidence below threshold — execution held"}</span></div>` +
      `<div class="tape-row"><span>${now()}</span><b>AUDIT</b><span>session ${state.session ? state.session.id : "—"} · ${state.session ? state.session.tickCount : 0} ticks chained</span></div>` +
      `</div></div></section></div>`;
  }
}
