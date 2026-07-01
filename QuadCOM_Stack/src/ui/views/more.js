/* MORE view — session overview + holistic module map. */
import { fmt, money, $ } from "../../util.js";
import { MODE } from "../../config.js";
import { governorState } from "../../engines/governor.js";
import { winRate, edgePoints } from "../../engines/account.js";
import { readout } from "../components.js";

export function renderMore(state, { wallet }) {
  const m = state.market, g = governorState(state), net = g.equity - g.capital;
  const slots = Number(document.getElementById("slots")?.value) || 2;
  $("mapBody").innerHTML = `<div class="map-metrics">
    ${readout("Balance", money(state.metrics.balance), state.metrics.balance > 0 ? "good" : "bad")}
    ${readout("Net", (net >= 0 ? "+" : "-") + money(Math.abs(net)), net >= 0 ? "good" : "bad")}
    ${readout("Turnover", money(state.metrics.turnover), "gold")}
    ${readout("Win Rate", winRate(state).toFixed(0) + "%")}
    ${readout("Edge", edgePoints(state).toFixed(1) + "pt", edgePoints(state) >= 0 ? "good" : "bad")}
    ${readout("Governor", g.state, g.state === "CLEAR" ? "good" : "bad")}
    ${readout("Open", `${state.positions.length}/${slots}`)}
    ${readout("Exposure", g.exposure.toFixed(1) + "%", g.exposure > 30 ? "bad" : "")}
    ${readout("Autopilot", state.autopilot ? "ON" : "OFF", state.autopilot ? "good" : "")}
  </div><div class="module-map">
    <div class="module-card"><b>Chart</b><span>${fmt(m.high)} - ${m.regime}</span><small>overview - chart - runtime</small></div>
    <div class="module-card"><b>Micro</b><span>Depth ${state.book.bids.length ? Math.round(state.book.bids.at(-1).cum) : 0} - Skew ${Math.round(m.imb * 100)}</span><small>depth - spread - flow</small></div>
    <div class="module-card"><b>Heat</b><span>${state.council.allowed ? "STRUCTURE CLEAR" : "STRUCTURE WAIT"}</span><small>zones - walls - ladder</small></div>
    <div class="module-card"><b>Breath</b><span>Compress ${Math.round(state.council.structure)}</span><small>phase - rhythm - fatigue</small></div>
    <div class="module-card"><b>Council</b><span>${state.council.action} - CONF ${state.council.conf.toFixed(0)}</span><small>votes - consensus - chamber</small></div>
    <div class="module-card"><b>Doctrine</b><span>${state.council.allowed ? "MODEL ALIGNED" : "CONF BELOW"}</span><small>rules - gate - language</small></div>
    <div class="module-card"><b>Exec</b><span>${state.autopilot ? "AUTO ON" : "AUTO OFF"} - ${state.autoStatus}</span><small>rail - book - tape</small></div>
    <div class="module-card"><b>Wallet</b><span>${state.transfers.length} transfers - ${wallet.label()}</span><small>deposit - withdraw - ledger</small></div>
    <div class="module-card"><b>Runtime</b><span>${MODE.LIVE ? "LIVE" : "SIM"} - ${state.mode} - SW ${state.sw}</span><small>kernel - cache - heartbeat</small></div>
  </div>`;
}
