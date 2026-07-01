/* GOV view — capital status, faucet rail, pressure metrics, guard contract. */
import { fmt, money, now, $ } from "../../util.js";
import { governorState } from "../../engines/governor.js";
import { readout } from "../components.js";

function transferRows(state, limit = 8) {
  return state.transfers.slice(0, limit).map(x =>
    `<div class="tape-row ${x.side === "IN" ? "in" : "out"}"><span>${x.t}</span><b>${x.side === "IN" ? "+ IN" : "- OUT"}</b><span>${money(x.amount)} | bal ${money(x.balance)}</span></div>`
  ).join("") || `<div class="tape-row"><span>${now()}</span><b>LEDGER</b><span>no wallet transfers recorded</span></div>`;
}

export function renderGov(state, { wallet }) {
  const g = governorState(state), net = g.equity - g.capital;
  document.querySelectorAll("[data-gov-tab]").forEach(b => b.classList.toggle("active", b.dataset.govTab === state.govTab));
  if (state.govTab === "capital") {
    $("govBody").innerHTML = `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Capital Status</span><span>${wallet.label()}</span></div><div class="panel-body"><div class="gov-state ${g.state === "HALT" ? "halt" : ""}">${g.state}</div><div class="readout-grid" style="margin-top:8px">${readout("Balance", money(state.metrics.balance), g.state === "CLEAR" ? "good" : "bad")}${readout("Equity", money(g.equity), g.state === "CLEAR" ? "good" : "bad")}${readout("Net", (net >= 0 ? "+" : "-") + money(Math.abs(net)), net >= 0 ? "good" : "bad")}${readout("Reason", g.reason)}</div><div class="transfer-rail"><input id="transferAmount" inputmode="decimal" value="${state.transferDraft}" aria-label="Transfer amount"><button id="depositBtn" class="deposit" type="button">Deposit Faucet</button><button id="withdrawBtn" class="withdraw" type="button">Withdraw</button></div><div class="ledger-tape"><div class="tape">${transferRows(state)}</div></div></div></section></div>`;
  } else if (state.govTab === "pressure") {
    $("govBody").innerHTML = `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Pressure Metrics</span><span>${g.state}</span></div><div class="panel-body"><div class="readout-grid">${readout("Drawdown %", g.drawdown.toFixed(2) + "%", g.drawdown > 5 ? "bad" : "good")}${readout("Exposure %", g.exposure.toFixed(1) + "%", g.exposure > 30 ? "bad" : "")}${readout("Loss Streak", g.lossStreak, g.lossStreak > 3 ? "bad" : "good")}${readout("Open", state.positions.length + "/" + (Number(document.getElementById("slots")?.value) || 2))}${readout("Peak Equity", money(g.peak), "gold")}${readout("Capital Basis", money(g.capital))}</div></div></section></div>`;
  } else {
    $("govBody").innerHTML = `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Guard Contract</span><span>EXEC CLEAR</span></div><div class="panel-body"><div class="tape"><div class="tape-row"><span>${now()}</span><b>DD</b><span>drawdown ${g.drawdown.toFixed(2)}% — informational, no halt</span></div><div class="tape-row"><span>${now()}</span><b>STREAK</b><span>loss streak ${g.lossStreak} — never halts execution</span></div><div class="tape-row"><span>${now()}</span><b>AUTO</b><span>allowed through gate stack</span></div></div></div></section></div>`;
  }
}
