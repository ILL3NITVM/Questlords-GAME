/* Render aggregator — paints shared chrome (top bar, oracle, rail, nav) then
 * dispatches every view so persisted values stay fresh. Never rewrites the
 * faucet input while it holds focus. */
import { fmt, money, $ } from "../util.js";
import { INSTRUMENT } from "../config.js";
import { governorState } from "../engines/governor.js";
import { renderDesk } from "./views/desk.js";
import { renderExec } from "./views/exec.js";
import { renderCouncil } from "./views/council.js";
import { renderGov } from "./views/gov.js";
import { renderMore } from "./views/more.js";

export function createRender(ctx, { wallet }) {
  const { state, settings } = ctx;
  let prevLast = null, prevBal = null;
  function flash(el, up) {
    if (!el) return;
    el.classList.remove("fl-up", "fl-down");
    void el.offsetWidth; // force reflow so the animation restarts
    el.classList.add(up ? "fl-up" : "fl-down");
  }

  function render() {
    const m = state.market, c = state.council, s = settings(), g = governorState(state);

    $("accountPill").textContent = wallet.label();
    $("accountPill").title = state.accountId || "";
    $("swPill").textContent = `SW ${state.sw}`;
    $("swPill").className = `pill ${state.sw === "READY" ? "ok" : "warn"}`;
    $("arm").textContent = state.armed ? "ARMED" : "ARM";
    $("arm").classList.toggle("on", state.armed);

    $("lastTop").textContent = fmt(m.last);
    $("lastTag").textContent = fmt(m.last);
    if (prevLast !== null && m.last !== prevLast) flash($("lastTop"), m.last > prevLast);
    prevLast = m.last;
    if (prevBal !== null && state.metrics.balance !== prevBal) flash($("balanceLine"), state.metrics.balance > prevBal);
    prevBal = state.metrics.balance;
    const chg = m.last - m.open;
    $("chgTop").textContent = (chg >= 0 ? "+" : "") + fmt(chg);
    $("chgTop").className = `last chg ${chg >= 0 ? "up" : "down"}`;
    $("sprTop").textContent = fmt(m.spread);
    $("hi").textContent = fmt(m.high); $("lo").textContent = fmt(m.low);
    $("vwap").textContent = fmt(m.vwap); $("poc").textContent = fmt(m.poc);
    $("regime").textContent = m.regime; $("microPx").textContent = fmt(m.micro);

    $("oracleStrip").innerHTML = `<span><b>ORACLE</b> | ${c.action} | CONF ${c.conf.toFixed(0)} | ${c.allowed ? "PASS" : "CONF BELOW"} | ${c.reason.toUpperCase()} | BID ${fmt(m.bid)} | ASK ${fmt(m.ask)}</span><span class="watch">${INSTRUMENT}</span>`;
    $("railState").textContent = `${state.autoStatus} | ${state.armed ? "ARMED" : "WAIT"} | Open ${state.positions.length}/${s.slots} | ${c.allowed ? "PASS" : "HOLD"} | GOV ${g.state}`;
    $("balanceLine").textContent = `BAL ${money(state.metrics.balance)} | TURN ${money(state.metrics.turnover)}`;
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.route === state.route));

    renderDesk(state);
    renderExec(state, ctx);
    renderCouncil(state, ctx);
    if (document.activeElement && document.activeElement.id === "transferAmount") { /* keep faucet input */ }
    else renderGov(state, { wallet });
    renderMore(state, { wallet });
  }

  return { render };
}
