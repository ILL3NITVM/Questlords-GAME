/* Session analytics — equity sampling + realized-edge statistics.
 * Pure over state; safe to call every cadence. */
import { equity } from "./account.js";

export function sampleEquity(state) {
  // Time series: one sample per cadence so the curve reads as equity-over-time,
  // stepping at each fill / settle / faucet event. ~240 samples ≈ a few minutes.
  const c = state.equityCurve;
  c.push(equity(state));
  if (c.length > 240) c.shift();
}

export function analytics(state) {
  const trades = state.ledger.filter(x => x.tag === "WIN" || x.tag === "LOSS" || x.tag === "REFUND");
  const wins = trades.filter(t => t.pnl > 0);
  const losses = trades.filter(t => t.pnl < 0);
  const grossWin = wins.reduce((a, t) => a + t.pnl, 0);
  const grossLoss = Math.abs(losses.reduce((a, t) => a + t.pnl, 0));
  const n = wins.length + losses.length;
  const profitFactor = grossLoss > 0 ? grossWin / grossLoss : (grossWin > 0 ? Infinity : 0);
  const avgWin = wins.length ? grossWin / wins.length : 0;
  const avgLoss = losses.length ? grossLoss / losses.length : 0;
  const winRate = n ? wins.length / n * 100 : 0;
  const expectancy = n ? (grossWin - grossLoss) / n : 0;
  const best = trades.reduce((m, t) => Math.max(m, t.pnl), 0);
  const worst = trades.reduce((m, t) => Math.min(m, t.pnl), 0);
  let peak = -Infinity, maxDD = 0;
  for (const e of state.equityCurve) { peak = Math.max(peak, e); if (peak > 0) maxDD = Math.max(maxDD, (peak - e) / peak * 100); }
  return { profitFactor, avgWin, avgLoss, winRate, expectancy, best, worst, maxDD, grossWin, grossLoss, trades: n };
}
