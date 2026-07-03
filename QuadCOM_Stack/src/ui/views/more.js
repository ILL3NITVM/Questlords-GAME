/* MORE view — the product hub. Session overview, performance, and a card grid
 * where every card opens a real route or product page (no dead UI). */
import { fmt, money, $ } from "../../util.js";
import { MODE, BRAND } from "../../config.js";
import { governorState } from "../../engines/governor.js";
import { winRate, edgePoints } from "../../engines/account.js";
import { analytics } from "../../engines/analytics.js";
import { drawSparkline } from "../sparkline.js";
import { readout } from "../components.js";

const card = (open, title, value, small) =>
  `<button class="module-card" type="button" data-open="${open}"><b>${title}</b><span>${value}</span><small>${small}</small></button>`;

export function renderMore(state, ctx) {
  const { wallet } = ctx;
  const m = state.market, g = governorState(state), net = g.equity - g.capital;
  const slots = Number(document.getElementById("slots")?.value) || 2;
  const a = analytics(state);
  const pf = !isFinite(a.profitFactor) ? "∞" : a.profitFactor.toFixed(2);
  const t = state.tally;

  $("mapBody").innerHTML = `
  <div class="hub-live">${state.live ? "" : `<button class="hub-livebtn" type="button" data-open="live">▶ ENTER LIVE MODE<small>broadcast cockpit · vote the tape</small></button>`}</div>
  <div class="map-metrics">
    ${readout("Lab Capital", money(state.metrics.balance), state.metrics.balance > 0 ? "good" : "bad")}
    ${readout("Net", (net >= 0 ? "+" : "-") + money(Math.abs(net)), net >= 0 ? "good" : "bad")}
    ${readout("Turnover", money(state.metrics.turnover), "gold")}
    ${readout("Win Rate", winRate(state).toFixed(0) + "%")}
    ${readout("Edge", edgePoints(state).toFixed(1) + "pt", edgePoints(state) >= 0 ? "good" : "bad")}
    ${readout("Governor", g.state, "good")}
    ${readout("Decisions", `${t.call}C ${t.put}P ${t.hold}H`)}
    ${readout("Exposure", g.exposure.toFixed(1) + "%", g.exposure > 30 ? "bad" : "")}
    ${readout("Session", state.session ? state.session.id : "—", "gold")}
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

  <div class="group-label">Desk</div>
  <div class="module-map">
    ${card("route:desk", "Chart", `${fmt(m.high)} - ${m.regime}`, "live tape - walls - structure")}
    ${card("route:desk", "Micro", `Depth ${state.book.bids.length ? Math.round(state.book.bids.at(-1).cum) : 0} - Skew ${Math.round(m.imb * 100)}`, "depth - spread - flow")}
    ${card("route:desk", "Heat", state.council.allowed ? "STRUCTURE CLEAR" : "STRUCTURE WAIT", "zones - walls - ladder")}
    ${card("route:council", "Breath", `Compress ${Math.round(state.council.structure)}`, "phase - rhythm - fatigue")}
  </div>

  <div class="group-label">Signals</div>
  <div class="module-map">
    ${card("route:council", "Council", `${state.council.action} - CONF ${state.council.conf.toFixed(0)}`, "votes - consensus - chamber")}
    ${card("page:doctrine", "Doctrine", state.council.allowed ? "MODEL ALIGNED" : "CONF BELOW", "the seven laws")}
    ${card("route:exec", "Exec", `${state.autopilot ? "AUTO ON" : "AUTO OFF"} - ${state.autoStatus}`, "rail - book - tape")}
    ${card("route:gov", "Wallet", `${state.transfers.length} transfers - ${wallet.label()}`, "deposit - withdraw - ledger")}
  </div>

  <div class="group-label">Product</div>
  <div class="module-map">
    ${card("page:fairness", "Fairness", state.session ? `${state.session.tickCount} ticks chained` : "—", "audit - seed - hash")}
    ${card("page:reports", "Reports", `${state.session ? state.session.eventCount : 0} events`, "json - csv - recap")}
    ${card("page:replay", "Replay Lab", `${state.ticks.length} prints on record`, "scrub - play - read-only")}
    ${card("page:sharekit", "Share Kit", BRAND.vote, "titles - invites - captions")}
    ${card("page:business", "Business", "Access & watchlist", "lite - pro - demo")}
    ${card("page:settings", "Settings", `${state.asset.symbol}`, "asset - speed - data")}
    ${card("page:onboarding", "What is this?", "Start here", "format in 60 seconds")}
    ${card("page:selftest", "Self-Test", "Acceptance checks", "run built-in tests")}
    ${card("page:about", "About", `${MODE.LIVE ? "LIVE" : "LAB"} - ${state.mode} - SW ${state.sw}`, BRAND.phase.toLowerCase())}
  </div>`;

  const accent = getComputedStyle(document.documentElement).getPropertyValue("--gold2").trim() || "#f2cc58";
  drawSparkline("equitySpark", state.equityCurve, accent);
}
