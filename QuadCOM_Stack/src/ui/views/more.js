/* MORE view — session overview + holistic module map. */
import { fmt, money, $ } from "../../util.js";
import { MODE } from "../../config.js";
import { governorState } from "../../engines/governor.js";
import { winRate, edgePoints } from "../../engines/account.js";
import { analytics } from "../../engines/analytics.js";
import { drawSparkline } from "../sparkline.js";
import { readout } from "../components.js";

export function renderMore(state, { wallet }) {
  const m = state.market, g = governorState(state), net = g.equity - g.capital;
  const slots = Number(document.getElementById("slots")?.value) || 2;
  const a = analytics(state);
  const pf = !isFinite(a.profitFactor) ? "∞" : a.profitFactor.toFixed(2);
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
  </div>
  <section class="panel-card perf"><div class="panel-head"><span>Session Performance</span><span>${a.trades} closed</span></div><div class="panel-body">
    <div class="spark-wrap"><canvas id="equitySpark"></canvas><span class="spark-label">EQUITY CURVE</span></div>
    <div class="readout-grid" style="margin-top:8px">
      ${readout("Profit Factor", pf, a.profitFactor >= 1 && a.trades ? "good" : a.trades ? "bad" : "")}
      ${readout("Expectancy", money(a.expectancy), a.expectancy >= 0 ? "good" : "bad")}
      ${readout("Avg Win", money(a.avgWin), "good")}
      ${readout("Avg Loss", money(a.avgLoss), "bad")}
      ${readout("Max Drawdown", a.maxDD.toFixed(1) + "%", a.maxDD > 10 ? "bad" : "")}
      ${readout("Best / Worst", money(a.best) + " / " + money(a.worst))}
    </div>
  </div></section>
  <div class="module-map">
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
  const accent = getComputedStyle(document.documentElement).getPropertyValue("--gold2").trim() || "#f2cc58";
  drawSparkline("equitySpark", state.equityCurve, accent);
}
