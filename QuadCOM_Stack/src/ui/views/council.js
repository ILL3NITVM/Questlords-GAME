/* COUNCIL view — votes, consensus, chamber. Now with plain-language
 * explanations under every vote and a single readable verdict statement. */
import { $ } from "../../util.js";
import { readout, gauge } from "../components.js";

const EXPLAIN = {
  Macro: "broad directional pressure",
  Flow: "near-term movement",
  Gate: "permission layer",
  Structure: "tape / range condition",
  Retail: "crowd / behavioural pressure"
};

function voteRows(state) {
  const c = state.council;
  return [
    ["Macro", c.macro >= 50 ? "CALL" : "PUT", Math.round(c.macro)],
    ["Flow", c.flow >= 50 ? "CALL" : "PUT", Math.round(c.flow)],
    ["Gate", c.allowed ? c.action : "HOLD", Math.round(c.gate)],
    ["Structure", state.market.regime === "COMP" ? "COMPRESSION" : state.market.regime, Math.round(c.structure)],
    ["Retail", c.retail >= 50 ? "PUT" : "CALL", Math.round(c.retail)]
  ];
}

function verdict(state, gate) {
  const c = state.council;
  if (!c.allowed || c.action === "HOLD")
    return `Council says HOLD because confidence (${c.conf.toFixed(0)}) is below the gate threshold (${gate}).`;
  const drivers = c.action === "CALL" ? "Macro and Gate align above threshold" : "downside pressure and Gate align above threshold";
  return `Council says ${c.action} because ${drivers} (confidence ${c.conf.toFixed(0)} ≥ gate ${gate}).`;
}

export function renderCouncil(state, ctx) {
  const c = state.council, gate = ctx.settings().gate;
  document.querySelectorAll("[data-council-tab]").forEach(b => b.classList.toggle("active", b.dataset.councilTab === state.councilTab));

  if (state.councilTab === "votes") {
    const rows = voteRows(state).map(v =>
      `<div class="vote-row"><b>${v[0]}</b><i>${v[1]}</i><span>Weight ${v[2]}</span></div>` +
      `<div class="vote-explain">${EXPLAIN[v[0]] || ""}</div>`).join("");
    $("councilBody").innerHTML =
      `<div class="verdict">${verdict(state, gate)}</div>` +
      `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Vote Chamber Breakdown</span><span>${c.action}</span></div><div class="panel-body">${rows}</div></section></div>`;
  } else if (state.councilTab === "consensus") {
    $("councilBody").innerHTML =
      `<div class="verdict">${verdict(state, gate)}</div>` +
      `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Council Consensus</span><span>${c.reason}</span></div><div class="panel-body"><div class="council-score">${readout("Council Consensus", c.conf.toFixed(0), c.allowed ? "good" : "gold")}${readout("Tension", c.tension.toFixed(0), c.tension > 72 ? "bad" : "")}</div><div class="score" style="margin-top:7px"><div><span>State</span><b>${c.allowed ? "CLEAR" : "HOLD"}</b></div><div><span>Action</span><b>${c.action}</b></div><div><span>Gate</span><b>${gate}</b></div></div></div></section></div>`;
  } else {
    $("councilBody").innerHTML =
      `<div class="panel-grid"><section class="panel-card"><div class="panel-head"><span>Chamber Pressure</span><span>macro flow gate risk</span></div><div class="panel-body"><div class="gauges">${gauge("Macro", c.macro)}${gauge("Flow", c.flow)}${gauge("Gate", c.gate)}${gauge("Structure", c.structure)}</div></div></section><section class="panel-card"><div class="panel-head"><span>S/R Probabilities</span><span>model feed</span></div><div class="panel-body"><div class="gauges">${gauge("Support", c.support)}${gauge("Resistance", c.resistance)}${gauge("Bull", c.bull)}${gauge("Bear", c.bear)}</div></div></section></div>`;
  }
}
