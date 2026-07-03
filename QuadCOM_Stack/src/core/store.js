/* Central application state container.
 * Plain, serializable state plus a tiny subscribe/notify scheduler. The state
 * is source-agnostic: the same shape is populated by the synthetic feed or the
 * live feed. Only the account slice is persisted (wallet-scoped). */
import { BASE, TICK, ASSETS, DEFAULT_ASSET } from "../config.js";

export function defaultMetrics() {
  return { balance: 0, turnover: 0, wins: 0, losses: 0, refunds: 0, lossStreak: 0, closed: 0, peakEquity: 0 };
}

export function defaultTally() {
  return { call: 0, put: 0, hold: 0, confSum: 0, confN: 0, govClears: 0, govBlocks: 0, maxExposure: 0, labOpened: 0, labResolved: 0 };
}

export function defaultSettings() {
  return {
    liveMode: false,
    publicWording: false,
    sound: false,
    tickSpeed: 650,
    themeIntensity: "normal"
  };
}

export function createState() {
  return {
    // ---- UI / session ----
    route: "desk",
    councilTab: "votes",
    govTab: "capital",
    armed: false,
    autopilot: false,
    autoStatus: "OFF",
    autoFires: 0,
    lastAuto: 0,
    sw: "INIT",
    mode: "BROWSER",
    pointer: null,
    transferDraft: "250.00",
    accountId: null,
    sessionReady: false,
    page: null,          // active full-screen product page (onboarding/fairness/…)
    live: false,         // broadcast overlay visible

    // ---- Product / audit ----
    asset: { ...ASSETS[DEFAULT_ASSET] },
    session: null,       // set by main on boot (seeded)
    rng: Math.random,    // replaced by the seeded RNG on boot
    auditLog: [],
    tally: defaultTally(),
    settings: defaultSettings(),
    waitlist: [],
    oracleLast: null,    // last resolved lab outcome for the broadcast card
    crowd: { call: 0, put: 0, hold: 0 },   // Phase 10: LIVE crowd vote tallies

    // ---- Market data (feed-populated) ----
    ticks: [],
    book: { bids: [], asks: [] },
    market: {
      last: BASE, open: BASE, high: BASE, low: BASE, vwap: BASE, poc: BASE,
      spread: TICK * 2, mid: BASE, bid: BASE - TICK, ask: BASE + TICK, micro: BASE,
      imb: 0, regime: "COMP", momentum: 0, vol: 22, upper: BASE + 80, lower: BASE - 80
    },

    // ---- Analytics ----
    council: {
      action: "HOLD", conf: 0, tension: 0, allowed: false, reason: "warming substrate",
      macro: 50, retail: 50, flow: 50, gate: 50, structure: 50,
      support: 50, resistance: 50, bull: 50, bear: 50
    },

    // ---- Account (persisted, wallet-scoped) ----
    positions: [],
    tradeHistory: [],   // closed-trade markers for the chart (session-only)
    ledger: [],
    transfers: [],
    equityCurve: [],
    metrics: defaultMetrics()
  };
}

/* Reset only the account-bound slice (used on connect/logout). */
export function resetAccountState(state) {
  state.armed = false;
  state.autopilot = false;
  state.autoStatus = "OFF";
  state.autoFires = 0;
  state.positions = [];
  state.tradeHistory = [];
  state.ledger = [];
  state.transfers = [];
  state.equityCurve = [];
  state.metrics = defaultMetrics();
  state.transferDraft = "250.00";
}
