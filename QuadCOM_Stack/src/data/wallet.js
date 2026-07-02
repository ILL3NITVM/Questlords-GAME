/* Wallet manager — gateway connect, wallet-scoped persistence, and the faucet.
 * Storage is isolated per address under `quadcom_data_<ADDRESS>`; the active
 * session pointer is `quadcom_active_account`. Logout preserves each dataset. */
import { MODE, STORAGE } from "../config.js";
import { defaultMetrics, resetAccountState } from "../core/store.js";
import { simWallet } from "./simWallet.js";
import { liveWallet } from "./liveWallet.js";
import { now, money } from "../util.js";

const adapter = MODE.LIVE ? liveWallet : simWallet;

export function createWallet(ctx) {
  const { state, log, render } = ctx;
  const toast = ctx.toast || (() => {});

  const dataKey = () => (state.accountId ? STORAGE.prefix + state.accountId : null);
  const label = (id = state.accountId) => (id ? `OPR: ${id.slice(0, 5)}...${id.slice(-4)}` : "OPR: LOCKED");

  function save() {
    if (!state.sessionReady || !state.accountId) return;
    const data = {
      accountId: state.accountId, metrics: state.metrics,
      transfers: state.transfers.slice(0, 80), ledger: state.ledger.slice(0, 80),
      positions: state.positions.slice(0, 6), autoFires: state.autoFires,
      transferDraft: state.transferDraft, updated: Date.now()
    };
    try { localStorage.setItem(dataKey(), JSON.stringify(data)); } catch (_) {}
  }

  function loadInto(id) {
    resetAccountState(state);
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE.prefix + id) || "null");
      if (saved && saved.accountId === id) {
        state.metrics = { ...defaultMetrics(), ...(saved.metrics || {}) };
        state.transfers = Array.isArray(saved.transfers) ? saved.transfers.slice(0, 80) : [];
        state.ledger = Array.isArray(saved.ledger) ? saved.ledger.slice(0, 80) : [];
        state.positions = Array.isArray(saved.positions) ? saved.positions.slice(0, 6) : [];
        state.autoFires = Number(saved.autoFires) || 0;
        state.transferDraft = saved.transferDraft || "250.00";
      }
    } catch (_) {}
  }

  async function connect(raw, silent = false) {
    let id;
    try { id = await adapter.acquireAddress(raw); }
    catch (e) { log("GATEWAY", "connect failed: " + e.message); render(); return false; }
    state.accountId = id; state.sessionReady = true;
    try { localStorage.setItem(STORAGE.active, id); } catch (_) {}
    loadInto(id);
    if (!silent) log("GATEWAY", `operator ${label(id)} connected [${adapter.kind}]`);
    save(); render();
    return true;
  }

  function logout() {
    save();
    try { localStorage.removeItem(STORAGE.active); } catch (_) {}
    state.accountId = null;
    resetAccountState(state);
  }

  function restore() {
    let active = null;
    try { active = localStorage.getItem(STORAGE.active); } catch (_) {}
    if (active) { state.accountId = active; state.sessionReady = true; loadInto(active); save(); return true; }
    resetAccountState(state);
    return false;
  }

  // Faucet: simulated instant credit; LIVE routes to a real faucet/on-ramp.
  function faucet(side) {
    if (!state.sessionReady) return;
    const amount = Number(parseFloat(state.transferDraft).toFixed(2));
    if (!Number.isFinite(amount) || amount <= 0) { log("WALLET", "invalid transfer amount"); toast("Enter an amount > 0", "err"); render(); return; }
    if (side === "OUT" && amount > state.metrics.balance) { log("WALLET", "withdraw exceeds available balance"); toast("Withdraw exceeds balance", "err"); save(); render(); return; }
    if (side === "IN") {
      state.metrics.balance += amount;
      state.transfers.unshift({ t: now(), side: "IN", amount, balance: state.metrics.balance });
      state.metrics.peakEquity = Math.max(Number(state.metrics.peakEquity) || 0, state.metrics.balance);
      log("IN", `${MODE.LIVE ? "faucet" : "testnet faucet"} deposit ${money(amount)}`);
      toast(`Faucet +${money(amount)}`, "ok");
    } else {
      state.metrics.balance -= amount;
      state.transfers.unshift({ t: now(), side: "OUT", amount, balance: state.metrics.balance });
      log("OUT", `wallet withdrawal ${money(amount)}`);
      toast(`Withdraw -${money(amount)}`, "ok");
    }
    if (state.transfers.length > 80) state.transfers.length = 80;
    save(); render();
  }

  return { save, connect, logout, restore, faucet, label, adapter };
}
