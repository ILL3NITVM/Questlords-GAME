/* LIVE broadcast overlay — big readable cards for streaming (TikTok-first).
 * Pure renderer over live state; updated every cadence while visible. */
import { BRAND, SAFETY } from "../config.js";
import { $, fmt, money } from "../util.js";

function timerStr(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
  return (h ? h + ":" : "") + String(m).padStart(2, "0") + ":" + String(ss).padStart(2, "0");
}

export function renderLive(state, ctx) {
  const host = $("liveOverlay");
  if (!host) return;
  if (!state.live) { host.classList.remove("on"); host.innerHTML = ""; return; }
  host.classList.add("on");

  const m = state.market, c = state.council, s = ctx.settings();
  const sess = state.session || { started: Date.now() };
  const lastTick = state.ticks.length ? state.ticks[state.ticks.length - 1].t : Date.now();
  const cycleMs = Math.max(0, (state.settings.tickSpeed || 650) - (Date.now() - lastTick));
  const phase = m.regime === "COMP" ? "COMPRESSION" : m.regime;
  const act = c.allowed ? c.action : "HOLD";
  const actCls = act === "CALL" ? "call" : act === "PUT" ? "put" : "hold";
  const last = state.oracleLast;
  const votes = [
    ["MACRO", c.macro], ["FLOW", c.flow], ["GATE", c.gate], ["STRUCT", c.structure], ["RETAIL", c.retail]
  ];

  host.innerHTML = `
  <div class="lv-shell">
    <div class="lv-top">
      <div class="lv-brand"><b>${BRAND.name}</b><span>${BRAND.tagline} · LIVE</span></div>
      <button class="lv-exit" type="button" data-act="exit-live">EXIT</button>
    </div>

    <div class="lv-asset"><span>${state.asset.symbol}</span><b>${fmt(m.last)}</b></div>

    <div class="lv-action ${actCls}">${act}</div>

    <div class="lv-grid">
      <div class="lv-card"><span>CONFIDENCE</span><b>${c.conf.toFixed(0)}</b></div>
      <div class="lv-card"><span>GATE</span><b>${s.gate}</b></div>
      <div class="lv-card"><span>TAPE PHASE</span><b>${phase}</b></div>
      <div class="lv-card"><span>ORACLE</span><b>${c.allowed ? "PASS" : "CONF BELOW"}</b></div>
      <div class="lv-card"><span>SESSION</span><b>${timerStr(Date.now() - sess.started)}</b></div>
      <div class="lv-card"><span>NEXT PRINT</span><b>${(cycleMs / 1000).toFixed(1)}s</b></div>
    </div>

    <div class="lv-council">
      ${votes.map(([n, v]) => `<div class="lv-vote"><span>${n}</span><div class="lv-bar"><i style="width:${Math.round(v)}%"></i></div><b>${Math.round(v)}</b></div>`).join("")}
    </div>

    <div class="lv-last">${last
      ? `LAST RESOLVED · <b class="${last.out === "WIN" ? "w" : last.out === "LOSS" ? "l" : "r"}">${last.dir} ${last.out} ${(last.pnl >= 0 ? "+" : "") + money(last.pnl)}</b>`
      : "LAST RESOLVED · <b>awaiting first lab resolution</b>"}</div>

    <div class="lv-vote-prompt">Vote the tape: <b>CALL</b>, <b>PUT</b>, or <b>HOLD</b>.</div>
    <div class="lv-hero2">${BRAND.hero2}</div>

    <div class="lv-foot">${SAFETY}</div>
  </div>`;
}
