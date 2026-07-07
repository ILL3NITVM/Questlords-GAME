/* Council engine — derives the vote chamber from market + book. Source
 * agnostic: works identically for synthetic and live feeds. */
import { clamp } from "../util.js";

export function computeCouncil(state, gate) {
  // Tick-normalized (Phase 7C): all pressure terms are expressed in ticks so
  // the same council math reads every harvested instrument, from SBCI.FX16
  // (tick 0.00001) to US30.SYN (tick 1).
  const tick = (state.asset && state.asset.tick) || 0.5;
  const m = state.market, range = Math.max(tick, m.high - m.low);
  const loc = (m.last - m.low) / range, comp = clamp(100 - range / (tick * 8.4), 0, 100);
  const flow = clamp(50 + m.momentum / (tick * 8) + m.imb * 22, 0, 100);
  const macro = clamp(50 + ((m.vwap - m.poc) / tick) * .06 + ((m.last - m.vwap) / tick) * .02, 0, 100);
  const retail = clamp(50 + (loc - .5) * -55 + ((m.poc - m.last) / tick) * .03, 0, 100);
  const gateW = clamp(60 + comp * .18 - Math.abs(m.imb) * 8, 0, 100);
  const callScore = (flow + macro + gateW + (100 - retail)) / 4;
  const putScore = ((100 - flow) + (100 - macro) + gateW + retail) / 4;
  const action = callScore > putScore ? "CALL" : "PUT";
  const conf = Math.max(callScore, putScore), tension = clamp(Math.abs(callScore - putScore) * 2.2, 0, 100);
  const allowed = conf >= gate;
  state.council = {
    action: allowed ? action : "HOLD", conf, tension, allowed,
    reason: allowed ? "gate aligned" : "confidence below threshold",
    macro, retail, flow, gate: gateW, structure: comp,
    support: clamp(82 - loc * 58 + comp * .35, 0, 100),
    resistance: clamp(26 + loc * 62 + Math.max(0, m.momentum) * .2, 0, 100),
    bull: clamp(callScore + Math.max(0, m.imb) * 8, 0, 100),
    bear: clamp(putScore + Math.max(0, -m.imb) * 8, 0, 100)
  };
  return state.council;
}
