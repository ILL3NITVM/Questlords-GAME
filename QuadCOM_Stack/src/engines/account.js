/* Account-derived pure selectors. */
export const equity = state => state.metrics.balance + state.positions.reduce((a, p) => a + p.stake, 0);
export const fundedCapital = state => state.transfers.reduce((a, x) => a + (x.side === "IN" ? x.amount : -x.amount), 0);
export const winRate = state => { const n = state.metrics.wins + state.metrics.losses; return n ? state.metrics.wins / n * 100 : 0; };
export const edgePoints = state => winRate(state) - 52.08;
