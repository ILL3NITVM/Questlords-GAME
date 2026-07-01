/* COUNCIL view — votes, consensus, chamber. */
import { $ } from "../../util.js";
import { readout, gauge } from "../components.js";

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

export function renderCouncil(state, ctx) {
  const c = state.council;
  document.querySelectorAll("[data-council-tab]").forEach(b => b.classList.toggle("active", b.dataset.councilTab === state.councilTab));
  if (state.councilTab === "votes") {
    $("councilBody").innerHTML = `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Vote Chamber Breakdown</span><span>${c.action}</span></div><div class="panel-body">${voteRows(state).map(v => `<div class="vote-row"><b>${v[0]}</b><i>${v[1]}</i><span>Weight ${v[2]}</span></div>`).join("")}</div></section></div>`;
  } else if (state.councilTab === "consensus") {
    $("councilBody").innerHTML = `<div class="panel-grid one"><section class="panel-card"><div class="panel-head"><span>Council Consensus</span><span>${c.reason}</span></div><div class="panel-body"><div class="council-score">${readout("Council Consensus", c.conf.toFixed(0), c.allowed ? "good" : "gold")}${readout("Tension", c.tension.toFixed(0), c.tension > 72 ? "bad" : "")}</div><div class="score" style="margin-top:7px"><div><span>State</span><b>${c.allowed ? "CLEAR" : "HOLD"}</b></div><div><span>Action</span><b>${c.action}</b></div><div><span>Gate</span><b>${ctx.settings().gate}</b></div></div></div></section></div>`;
  } else {
    $("councilBody").innerHTML = `<div class="panel-grid"><section class="panel-card"><div class="panel-head"><span>Chamber Pressure</span><span>macro flow gate risk</span></div><div class="panel-body"><div class="gauges">${gauge("Macro", c.macro)}${gauge("Flow", c.flow)}${gauge("Gate", c.gate)}${gauge("Structure", c.structure)}</div></div></section><section class="panel-card"><div class="panel-head"><span>S/R Probabilities</span><span>model feed</span></div><div class="panel-body"><div class="gauges">${gauge("Support", c.support)}${gauge("Resistance", c.resistance)}${gauge("Bull", c.bull)}${gauge("Bear", c.bear)}</div></div></section></div>`;
  }
}
