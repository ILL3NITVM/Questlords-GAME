/* Central application state container.
 * Plain, serializable state plus a tiny subscribe/notify scheduler. The state
 * is source-agnostic: the same shape is populated by the synthetic feed or the
 * live feed. Only the account slice is persisted (wallet-scoped). */
import { BASE, TICK } from "../config.js";

export function defaultMetrics() {
  return { balance: 0, turnover: 0, wins: 0, losses: 0, refunds: 0, lossStreak: 0, closed: 0, peakEquity: 0 };
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
    ledger: [],
    transfers: [],
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
  state.ledger = [];
  state.transfers = [];
  state.metrics = defaultMetrics();
  state.transferDraft = "250.00";
}
