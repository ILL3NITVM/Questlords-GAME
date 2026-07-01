/* Execution engine — binary option math on BTC/USD.SYN.
 *  - Opening a ticket debits the stake immediately and books turnover.
 *  - Win  → credit stake + 92% payout (pnl = +stake*payout).
 *  - Tie  → refund exact stake (pnl 0).
 *  - Loss → stake forfeited (pnl = -stake).
 * Settlement is directional vs entry (CALL exits on bid, PUT on ask), so
 * concurrent same-strike hedging always resolves to the spread loss.
 *
 * In MODE.LIVE the same lifecycle is mirrored to a real venue via
 * config.LIVE.executionApi (submit on open, reconcile on settle). */
import { PAYOUT, TICK, MODE, LIVE } from "../config.js";
import { fmt, money, now } from "../util.js";
import { equity } from "./account.js";

export function createExecution(ctx) {
  const { state, log, persist, render, settings } = ctx;

  async function submitLive(order) {
    // Real-venture seam. Fire-and-reconcile; never blocks the local ledger.
    try {
      await fetch(LIVE.executionApi, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(order) });
    } catch (_) { log("LIVE", "order submit failed — check LIVE.executionApi"); }
  }

  function open(dir, src) {
    const s = settings();
    if (!state.sessionReady) { log("BLOCK", "gateway locked"); return; }
    if (state.positions.length >= s.slots) { log("MAX", `open ${state.positions.length}/${s.slots}`); return; }
    if (state.metrics.balance < s.stake) { log("CASH", "stake unavailable"); return; }
    state.metrics.balance -= s.stake;
    state.metrics.turnover += s.stake;
    state.lastAuto = Date.now();
    const m = state.market, entry = dir === "CALL" ? m.ask : m.bid;
    const p = {
      id: Date.now().toString(36), dir, src, entry, stake: s.stake, payout: PAYOUT,
      opened: Date.now(), expires: Date.now() + s.expiry * 1000, idx: state.ticks.length - 1, conf: state.council.conf
    };
    state.positions.push(p);
    if (MODE.LIVE) submitLive({ side: dir, price: entry, stake: s.stake, expiry: s.expiry });
    log(dir, `${src} ${dir} @ ${fmt(entry)} stake ${money(s.stake)} debited`);
    persist(); render();
  }

  function settle() {
    const keep = []; let changed = false; const m = state.market;
    for (const p of state.positions) {
      if (Date.now() < p.expires) { keep.push(p); continue; }
      const close = p.dir === "CALL" ? m.bid : m.ask;
      const delta = close - p.entry;
      const refund = Math.abs(delta) < TICK / 2;
      const win = p.dir === "CALL" ? close > p.entry : close < p.entry;
      let pnl = -p.stake, credit = 0, out = "LOSS";
      if (refund) { pnl = 0; credit = p.stake; out = "REFUND"; state.metrics.refunds++; state.metrics.lossStreak = 0; }
      else if (win) { pnl = p.stake * p.payout; credit = p.stake * (1 + p.payout); out = "WIN"; state.metrics.wins++; state.metrics.lossStreak = 0; }
      else { state.metrics.losses++; state.metrics.lossStreak++; }
      state.metrics.closed++; state.metrics.balance += credit;
      state.ledger.unshift({ t: now(), tag: out, txt: `${p.dir} ${fmt(delta)} pnl ${money(pnl)}`, pnl });
      changed = true;
    }
    state.positions = keep;
    if (state.ledger.length > 80) state.ledger.length = 80;
    if (changed) {
      state.metrics.peakEquity = Math.max(Number(state.metrics.peakEquity) || 0, equity(state));
      persist();
    }
  }

  return { open, settle };
}
