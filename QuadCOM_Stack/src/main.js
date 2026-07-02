/* Composition root. Wires state → feed → engines → UI, binds events, and runs
 * the runtime loop. Swapping MODE.LIVE in config.js changes the feed/wallet
 * adapters underneath without touching anything here. */
import { MODE, AUTO_MS } from "./config.js";
import { createState } from "./core/store.js";
import { createFeed } from "./data/feed.js";
import { createWallet } from "./data/wallet.js";
import { computeCouncil } from "./engines/council.js";
import { createExecution } from "./engines/execution.js";
import { createAutopilot } from "./engines/autopilot.js";
import { createRender } from "./ui/render.js";
import { createRouter } from "./ui/router.js";
import { createGateway } from "./ui/gateway.js";
import { createToast } from "./ui/toast.js";
import { createTheme } from "./ui/theme.js";
import { sampleEquity } from "./engines/analytics.js";
import { drawChart } from "./ui/chart.js";
import { now, clamp, $ } from "./util.js";

const state = createState();

function settings() {
  return {
    expiry: clamp(parseInt($("expiry").value, 10) || 30, 5, 300),
    stake: clamp(parseFloat($("stake").value) || 100, 1, 99999),
    slots: clamp(parseInt($("slots").value, 10) || 2, 1, 6),
    gate: clamp(parseInt($("gate").value, 10) || 62, 40, 95)
  };
}
function log(tag, txt, pnl = 0) {
  state.ledger.unshift({ t: now(), tag, txt, pnl });
  if (state.ledger.length > 80) state.ledger.length = 80;
}

const toast = createToast();
const theme = createTheme();

// Context passed to every module. render/persist are filled after wiring.
const ctx = { state, settings, log, toast, render: () => {}, persist: () => {} };

const wallet = createWallet(ctx);
ctx.persist = wallet.save;

const execution = createExecution(ctx);
const autopilot = createAutopilot(ctx, { execution });
const { render } = createRender(ctx, { wallet });
ctx.render = render;
const router = createRouter(ctx);
const gateway = createGateway(ctx, { wallet });
const feed = createFeed(state);

// One data cycle: recompute council, settle expiries, paint, draw chart.
function onData() {
  computeCouncil(state, settings().gate);
  execution.settle();
  if (state.sessionReady) sampleEquity(state);
  render();
  if (state.route === "desk") drawChart(state);
}

function bind() {
  $("arm").addEventListener("click", () => { state.armed = !state.armed; log("ARM", state.armed ? "protocol armed" : "protocol idle"); wallet.save(); render(); });
  $("call").addEventListener("click", () => execution.open("CALL", "MANUAL"));
  $("put").addEventListener("click", () => execution.open("PUT", "MANUAL"));
  $("autopilotBtn").addEventListener("click", () => {
    state.autopilot = !state.autopilot;
    if (state.autopilot && !state.armed) state.armed = true;
    log("AUTO", state.autopilot ? "autopilot enabled" : "autopilot disabled");
    wallet.save(); render();
  });
  $("connectBtn").addEventListener("click", () => gateway.connect($("operatorInput").value));
  $("operatorInput").addEventListener("keydown", e => { if (e.key === "Enter") gateway.connect($("operatorInput").value); });
  $("logoutBtn").addEventListener("click", () => { wallet.logout(); router.route("desk"); gateway.show(); render(); });
  document.querySelectorAll("[data-route]").forEach(b => b.addEventListener("click", () => router.route(b.dataset.route)));
  document.addEventListener("click", e => {
    const ct = e.target.closest("[data-council-tab]"); if (ct) { state.councilTab = ct.dataset.councilTab; render(); }
    const gt = e.target.closest("[data-gov-tab]"); if (gt) { state.govTab = gt.dataset.govTab; render(); }
    if (e.target.closest("#depositBtn")) wallet.faucet("IN");
    if (e.target.closest("#withdrawBtn")) wallet.faucet("OUT");
    const chip = e.target.closest("[data-stakepct]");
    if (chip) {
      const pct = +chip.dataset.stakepct;
      const v = Math.max(1, Math.round(state.metrics.balance * pct));
      $("stake").value = v.toFixed(2);
      render();
      toast(`Stake set ${pct === 1 ? "MAX" : (pct * 100) + "%"} · $${v.toFixed(2)}`, "");
    }
  });
  const logo = document.querySelector(".mark");
  if (logo) { logo.style.cursor = "pointer"; logo.title = "Tap to cycle accent theme"; logo.addEventListener("click", () => toast("Theme · " + theme.cycle(), "")); }
  document.addEventListener("input", e => { if (e.target.id === "transferAmount") state.transferDraft = e.target.value; });
  const stage = $("stage");
  stage.addEventListener("pointermove", e => { const r = stage.getBoundingClientRect(); state.pointer = { x: e.clientX - r.left, y: e.clientY - r.top }; drawChart(state); });
  stage.addEventListener("pointerleave", () => { state.pointer = null; const tip = $("tip"); if (tip) tip.style.display = "none"; drawChart(state); });
  new ResizeObserver(() => drawChart(state)).observe(stage);
}

async function registerSw() {
  if (!("serviceWorker" in navigator)) { state.sw = "NONE"; render(); return; }
  try {
    const reg = await navigator.serviceWorker.register("./sw.js");
    await navigator.serviceWorker.ready;
    state.sw = (reg.active || reg.waiting || reg.installing) ? "READY" : "INIT";
  } catch (_) { state.sw = "CACHE"; log("PWA", "cache handoff pending"); }
  render();
}

function init() {
  const standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
  state.mode = standalone ? "PWA" : "BROWSER";
  theme.init();
  bind();
  if (wallet.restore()) gateway.hide(); else gateway.show();
  feed.start(onData);
  setInterval(() => autopilot.tick(), AUTO_MS);
  registerSw();
  window.addEventListener("error", e => { try { log("ERR", String(e.message || e.error)); render(); } catch (_) {} });
  window.QUADCOM = { state, ctx, execution, wallet, router, MODE }; // debug/introspection handle
}

document.addEventListener("DOMContentLoaded", init);
