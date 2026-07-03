/* Composition root. Wires state → session/audit → feed → engines → UI,
 * binds events, and runs the runtime loop. MODE.LIVE in config.js swaps the
 * feed/wallet adapters underneath without touching anything here. */
import { MODE, AUTO_MS, ASSETS, BRAND } from "./config.js";
import { createState, defaultTally, defaultSettings } from "./core/store.js";
import { newSession, makeRng } from "./engines/session.js";
import { createAudit } from "./audit.js";
import { createFeed } from "./data/feed.js";
import { createWallet } from "./data/wallet.js";
import { computeCouncil } from "./engines/council.js";
import { createExecution } from "./engines/execution.js";
import { createAutopilot } from "./engines/autopilot.js";
import { governorState } from "./engines/governor.js";
import { sampleEquity } from "./engines/analytics.js";
import { createRender } from "./ui/render.js";
import { createRouter } from "./ui/router.js";
import { createGateway } from "./ui/gateway.js";
import { createToast } from "./ui/toast.js";
import { createTheme } from "./ui/theme.js";
import { renderPage, handlePageAction, runSelfTests } from "./ui/pages.js";
import { drawChart } from "./ui/chart.js";
import { now, clamp, setDecimals, $ } from "./util.js";

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

// Context passed to every module. render/persist filled after wiring.
const ctx = { state, settings, log, toast, render: () => {}, persist: () => {} };

/* ---- session + audit boot ---- */
function bootSession(seed) {
  state.session = newSession(seed);
  state.rng = makeRng(state.session.seed);
  state.tally = defaultTally();
  state.auditLog = [];
  state.tradeHistory = [];
  state.oracleLast = null;
  state.crowd = { call: 0, put: 0, hold: 0 };
}
bootSession();
const audit = createAudit(state);
ctx.audit = audit;

const wallet = createWallet(ctx);
ctx.persist = wallet.save;
ctx.wallet = wallet;

const execution = createExecution(ctx);
const autopilot = createAutopilot(ctx, { execution });
const { render } = createRender(ctx, { wallet });
ctx.render = render;
const router = createRouter(ctx);
const gateway = createGateway(ctx, { wallet });
const feed = createFeed(ctx);

/* ---- tiny sound cue (optional, settings-gated) ---- */
let audioCtx = null;
function beep(freq = 660, dur = 0.07) {
  if (!state.settings.sound) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const o = audioCtx.createOscillator(), g = audioCtx.createGain();
    o.frequency.value = freq; o.type = "square";
    g.gain.value = 0.03;
    o.connect(g); g.connect(audioCtx.destination);
    o.start(); o.stop(audioCtx.currentTime + dur);
  } catch (_) {}
}

/* ---- global product settings (device-scoped) ---- */
const SETTINGS_KEY = "quadcom_settings";
function loadSettings() {
  try {
    const d = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "null");
    if (d) Object.assign(state.settings, defaultSettings(), d);
  } catch (_) {}
  try { state.waitlist = JSON.parse(localStorage.getItem("quadcom_waitlist") || "[]"); } catch (_) {}
  applySettingsSideEffects();
}
function saveSettings() {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings)); } catch (_) {}
}
function applySettingsSideEffects() {
  document.documentElement.setAttribute("data-intensity", state.settings.themeIntensity || "normal");
  document.documentElement.toggleAttribute("data-public", !!state.settings.publicWording);
}

/* ---- product actions (settings page, hub, live mode) ---- */
const product = {
  saveSettings,
  setSetting(key, val) {
    state.settings[key] = val;
    saveSettings(); applySettingsSideEffects();
    audit.event("SETTINGS_CHANGED", { key, val: String(val) });
    render();
  },
  switchAsset(sym) {
    if (!ASSETS[sym] || sym === state.asset.symbol) return;
    state.asset = { ...ASSETS[sym] };
    setDecimals(state.asset.decimals);
    Object.assign(state.market, {
      last: state.asset.base, open: state.asset.base, high: state.asset.base, low: state.asset.base,
      vwap: state.asset.base, poc: state.asset.base, momentum: 0
    });
    audit.event("SETTINGS_CHANGED", { key: "asset", val: sym });
    this.resetSession(true, `asset → ${sym}`);
  },
  resetSession(regenSeed, why) {
    const prevSeed = state.session ? state.session.seed : undefined;
    bootSession(regenSeed ? undefined : prevSeed);
    audit.event("SESSION_RESET", { why: why || (regenSeed ? "seed regenerated" : "manual reset") });
    if (feed.reseed) feed.reseed();
    state.equityCurve = [];
    render();
  },
  toggleLive() {
    state.live = !state.live;
    state.settings.liveMode = state.live;
    saveSettings();
    if (state.live) { state.page = null; renderPage(state, ctx); }
    render();
  }
};
ctx.product = product;

/* ---- oracle/council/governor audit sampling ---- */
let prevAction = null, prevHolding = null;
function govHolding(s) {
  const c = state.council;
  return !state.sessionReady || (state.metrics.balance <= 0 && !state.positions.length) ||
    state.positions.length >= s.slots || c.conf < s.gate || !state.armed;
}
function sampleProduct() {
  const s = settings(), c = state.council;
  const act = c.allowed ? c.action : "HOLD";
  state.tally[act === "CALL" ? "call" : act === "PUT" ? "put" : "hold"]++;
  state.tally.confSum += c.conf; state.tally.confN++;
  const g = governorState(state);
  state.tally.maxExposure = Math.max(state.tally.maxExposure, g.exposure);
  if (act !== prevAction) {
    audit.event("ORACLE_UPDATED", { action: act, conf: +c.conf.toFixed(0) });
    audit.event("COUNCIL_UPDATED", { action: c.action, conf: +c.conf.toFixed(0), tension: +c.tension.toFixed(0) });
    prevAction = act;
  }
  const holding = govHolding(s);
  if (holding !== prevHolding) {
    if (holding) { state.tally.govBlocks++; audit.event("GOVERNOR_BLOCK", { reason: c.conf < s.gate ? "confidence below threshold" : state.positions.length >= s.slots ? "exposure limit reached" : "capital/arm state" }); }
    else { state.tally.govClears++; audit.event("GOVERNOR_CLEAR", { reason: "gate + capital + arm aligned" }); }
    prevHolding = holding;
  }
}

/* ---- one data cycle ---- */
function onData() {
  // Phase 16: skip paint work while the tab is hidden (tape + audit continue).
  if (document.hidden) { computeCouncil(state, settings().gate); execution.settle(); sampleProduct(); if (state.sessionReady) sampleEquity(state); return; }
  computeCouncil(state, settings().gate);
  const before = state.metrics.closed;
  execution.settle();
  if (state.metrics.closed > before) beep(880, 0.09);
  sampleProduct();
  if (state.sessionReady) sampleEquity(state);
  render();
  if (state.route === "desk" && !state.live && !state.page) drawChart(state);
}

/* ---- event bindings ---- */
function bind() {
  $("arm").addEventListener("click", () => { state.armed = !state.armed; log("ARM", state.armed ? "lab armed" : "lab idle"); wallet.save(); render(); });
  $("call").addEventListener("click", () => { execution.open("CALL", "MANUAL"); beep(700); });
  $("put").addEventListener("click", () => { execution.open("PUT", "MANUAL"); beep(520); });
  $("autopilotBtn").addEventListener("click", () => {
    state.autopilot = !state.autopilot;
    if (state.autopilot && !state.armed) state.armed = true;
    log("AUTO", state.autopilot ? "autopilot lab enabled" : "autopilot lab disabled");
    wallet.save(); render();
  });
  $("connectBtn").addEventListener("click", () => gateway.connect($("operatorInput").value));
  $("operatorInput").addEventListener("keydown", e => { if (e.key === "Enter") gateway.connect($("operatorInput").value); });
  $("logoutBtn").addEventListener("click", () => { wallet.logout(); router.route("desk"); gateway.show(); render(); });
  const liveBtn = $("liveBtn");
  if (liveBtn) liveBtn.addEventListener("click", () => product.toggleLive());
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

    // Product hub cards + page/live actions.
    const open = e.target.closest("[data-open]");
    if (open) {
      const [kind, name] = open.dataset.open === "live" ? ["live", ""] : open.dataset.open.split(":");
      if (kind === "route") { state.page = null; renderPage(state, ctx); router.route(name); }
      else if (kind === "page") { state.page = name; renderPage(state, ctx); }
      else if (kind === "live") product.toggleLive();
    }
    const actEl = e.target.closest("[data-act]");
    if (actEl) {
      const act = actEl.dataset.act;
      if (act === "exit-live") product.toggleLive();
      else if (act.startsWith("crowd:")) {
        const side = act.slice(6).toLowerCase();
        if (state.crowd[side] !== undefined) {
          state.crowd[side]++;
          audit.event("CROWD_VOTE", { side: side.toUpperCase() });
          beep(side === "call" ? 760 : side === "put" ? 500 : 620, 0.05);
          render();
        }
      }
      else handlePageAction(act, state, ctx);
    }
  });

  document.addEventListener("input", e => {
    if (e.target.id === "transferAmount") state.transferDraft = e.target.value;
  });
  document.addEventListener("change", e => {
    if (e.target.id === "setAsset") product.switchAsset(e.target.value);
    if (e.target.id === "setIntensity") product.setSetting("themeIntensity", e.target.value);
    if (e.target.id === "setTick") product.setSetting("tickSpeed", clamp(parseInt(e.target.value, 10) || 650, 120, 4000));
    if (e.target.id === "setPreset" && e.target.value) {
      // Phase 13: doctrine gate presets — visible, logged, reversible.
      const presets = { strict: { gate: 75, slots: 1 }, standard: { gate: 62, slots: 2 }, aggressive: { gate: 55, slots: 4 } };
      const pz = presets[e.target.value];
      if (pz) {
        $("gate").value = pz.gate; $("slots").value = pz.slots;
        audit.event("SETTINGS_CHANGED", { key: "doctrinePreset", val: e.target.value });
        toast(`Doctrine · ${e.target.value.toUpperCase()} (gate ${pz.gate}, ${pz.slots} slot${pz.slots > 1 ? "s" : ""})`, "ok");
        render();
      }
    }
  });
  document.addEventListener("input", e => {
    if (e.target.id === "replayScrub") {
      import("./ui/pages.js").then(mod => mod.drawReplay(state, +e.target.value));
    }
  });

  // Phase 16: keyboard shortcuts (desktop) — never while typing.
  document.addEventListener("keydown", e => {
    if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    const k = e.key.toLowerCase();
    if (k === "c") execution.open("CALL", "MANUAL");
    else if (k === "p") execution.open("PUT", "MANUAL");
    else if (k === "a") { state.armed = !state.armed; log("ARM", state.armed ? "lab armed" : "lab idle"); render(); }
    else if (k === "l") product.toggleLive();
    else if (k === "escape" && state.page) { state.page = null; render(); }
  });

  const logo = document.querySelector(".mark");
  if (logo) { logo.style.cursor = "pointer"; logo.title = "Tap to cycle accent theme"; logo.addEventListener("click", () => toast("Theme · " + theme.cycle(), "")); }

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
  setDecimals(state.asset.decimals);
  theme.init();
  loadSettings();
  bind();
  if (wallet.restore()) gateway.hide(); else gateway.show();
  feed.start(onData);
  setInterval(() => autopilot.tick(), AUTO_MS);
  registerSw();
  window.addEventListener("error", e => { try { log("ERR", String(e.message || e.error)); render(); } catch (_) {} });
  // Debug/introspection + console self-tests: await QUADCOM.selfTest()
  window.QUADCOM = { state, ctx, execution, wallet, router, product, MODE, BRAND, selfTest: () => runSelfTests(state, ctx) };
}

document.addEventListener("DOMContentLoaded", init);
