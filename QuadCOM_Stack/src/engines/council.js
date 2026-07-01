/* Council engine — derives the vote chamber from market + book. Source
 * agnostic: works identically for synthetic and live feeds. */
import { TICK } from "../config.js";
import { clamp } from "../util.js";

export function computeCouncil(state, gate) {
  const m = state.market, range = Math.max(TICK, m.high - m.low);
  const loc = (m.last - m.low) / range, comp = clamp(100 - range / 4.2, 0, 100);
  const flow = clamp(50 + m.momentum / 4 + m.imb * 22, 0, 100);
  const macro = clamp(50 + (m.vwap - m.poc) * .12 + (m.last - m.vwap) * .04, 0, 100);
  const retail = clamp(50 + (loc - .5) * -55 + (m.poc - m.last) * .06, 0, 100);
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
