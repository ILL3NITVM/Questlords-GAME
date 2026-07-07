/* Capital governor. Losses, loss streaks, and drawdown NEVER halt execution —
 * they are informational only. The governor stays CLEAR whenever funded. */
import { equity, fundedCapital } from "./account.js";

export function governorState(state) {
  const eq = equity(state);
  const peak = Math.max(Number(state.metrics.peakEquity) || 0, eq);
  const drawdown = peak > 0 ? Math.max(0, (peak - eq) / peak * 100) : 0;
  const exposure = state.positions.reduce((a, p) => a + p.stake, 0) / Math.max(1, eq) * 100;
  return {
    state: "CLEAR",
    drawdown, exposure, equity: eq, peak,
    capital: fundedCapital(state),
    lossStreak: state.metrics.lossStreak,
    reason: eq <= 0 ? "AWAITING DEPOSIT" : "CAPITAL CLEAR"
  };
}
